from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from units_scraper.utils import *
from pydispatch import dispatcher
from scrapy import signals
class ScraperSpider(CrawlSpider):
    name = "scraper"
    allowed_domains = ["units.it"]
    start_urls = ["https://portale.units.it/it"]
    counter = 1

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
        remove_output_directory("scraper_md_output")
        dispatcher.connect(self.spider_closed, signals.engine_stopped)

    def parse_item(self, response):
        print_log(response, self.counter, self.crawler.settings)

        metadata = get_metadata(response)
        cleaned_response = filter_response(response)
        md_content = parse_html_content_html2text(cleaned_response)
        self.counter += 1
        if is_informative_markdown(md_content):
            #save_webpage_to_file(cleaned_response.text, md_content, response.url, self.counter, "scraper_md_output")
            item = {
                "title": metadata["title"],
                "url": response.url,
                "description": metadata["description"],
                "timestamp": metadata["date"],
                "content": md_content
            }
            yield item



    def spider_closed(self):
        print_scraping_summary(self.crawler.stats.get_stats(), self.settings, "scraping_summary.log")

