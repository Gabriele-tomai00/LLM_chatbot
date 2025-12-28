from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from units_scraper.utils import *
from pydispatch import dispatcher
from scrapy import signals
from urllib.parse import urlparse, urlunparse, quote, unquote

class ScraperSpider(CrawlSpider):
    name = "scraper"
    allowed_domains = ["units.it"]
    start_urls = ["https://portale.units.it/it"]
    #start_urls = ["https://portale.units.it/it", "https://lauree.units.it/it/0320106203900001/tasse-e-contributi"]
    counter = 1
    pdf_links_set = set()

    rules = (
        Rule(
            LinkExtractor(
                allow_domains=allowed_domains,
                allow=r"/it/",
                deny_domains= deny_domains,
                deny= deny_regex
            ),
            callback="parse_item",
            follow=True
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.save_each_file = kwargs.get("save_each_file", "False").lower() == "true"
        self.scrape_pdf = kwargs.get("scrape_pdf", "False").lower() == "true"

        os.makedirs("../results", exist_ok=True)
        remove_output_directory("scraper_md_output")
        dispatcher.connect(self.spider_closed, signals.engine_stopped)

    def parse_item(self, response):

        try:
            print_log(response, self.counter, self.crawler.settings)\

            metadata = get_metadata(response)
            self.counter += 1

            if self.save_each_file:
                save_webpage_to_file(response.text, response.url, self.counter, "../results/html_output/")
            if self.scrape_pdf:
                pdf_links = response.css("a::attr(href)").re(r'.*\.pdf$')
                for link in pdf_links:
                    absolute = response.urljoin(link)
                    parsed = urlparse(absolute)

                    # decode first
                    raw_path = unquote(parsed.path)
                    # Then encode exactly once
                    cleaned_path = quote(raw_path)
                    normalizated_pdf_link = urlunparse(parsed._replace(path=cleaned_path))
                    # print(f"PDF: {normalizated_pdf_link}")
                    self.pdf_links_set.add(normalizated_pdf_link)
            
            yield {
                "title": metadata["title"],
                "url": response.url,
                "description": metadata["description"],
                "timestamp": metadata["date"],
                "content": response.text
            }
        except Exception as e:
            self.logger.warning(f"Error parsing {response.url}: {e}")


    def spider_closed(self):
        save_pdf_list(self.pdf_links_set, "../results/")

        feed_uris = []
        feeds = getattr(self.crawler.settings, 'getdict', lambda x: {})('FEEDS')  # Scrapy >=2.1
        for uri in feeds.keys():
            feed_uris.append(uri)
        if feed_uris:
            feed_uri = feed_uris[0]
        else:
            feed_uri = None

        print("Output file from -O:", feed_uri)

        print_scraping_summary(self.crawler.stats.get_stats(), self.settings, len(self.pdf_links_set), feed_uri, "../results/scraping_summary.log")
