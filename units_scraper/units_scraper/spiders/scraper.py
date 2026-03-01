import re
import os
from urllib.parse import urlparse, urlunparse, quote, unquote

from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from scrapy import signals
from pydispatch import dispatcher

# Assuming all utilities are imported correctly
from units_scraper.utils import *

class ScraperSpider(CrawlSpider):
    name = "scraper"
    allowed_domains = ["units.it"]
    start_urls = ["https://portale.units.it/it"]
    #start_urls = ["https://portale.units.it/it", "https://lauree.units.it/it/0320106203900001/tasse-e-contributi"]
    counter = 1
    pdf_links_set = set()
    
    # Set to keep track of normalized page IDs to avoid language duplicates
    seen_pages_ids = set()

    rules = (
        Rule(
            LinkExtractor(
                allow_domains=allowed_domains,
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
        self.output_dir = kwargs.get("output_dir", "../results/scraper_results")

        os.makedirs("../results", exist_ok=True)
        remove_output_directory("scraper_md_output")
        dispatcher.connect(self.spider_closed, signals.engine_stopped)



# Set to store only canonical IDs
    seen_canonicals = set()

    def parse_item(self, response):
        # 1. Check for Canonical Tag (Content-based)
        canonical = response.xpath('//link[@rel="canonical"]/@href').get()
        
        if canonical:
            # Normalize the canonical as well to be safe
            norm_canonical = canonical.replace(':443', '')
            norm_canonical = re.sub(r'/(it|en)(/|$)', '/', norm_canonical).rstrip('/')
            
            if norm_canonical in self.seen_canonicals:
                self.logger.debug(f"Discarding: Canonical {norm_canonical} already processed.")
                return
            
            self.seen_canonicals.add(norm_canonical)

        # 2. Proceed with extraction
        try:
            print_log(response, self.counter, self.crawler.settings)

            metadata = get_metadata(response)
            self.counter += 1

            if self.save_each_file:
                save_webpage_to_file(response.text, response.url, self.counter, "../results/html_output/")
            if self.scrape_pdf:
                pdf_links = response.css("a::attr(href)").re(r'.*\.pdf$')
                for link in pdf_links:
                    absolute = response.urljoin(link)
                    parsed = urlparse(absolute)

                    # Decode first to handle already encoded parts
                    raw_path = unquote(parsed.path)
                    # Re-encode exactly once
                    cleaned_path = quote(raw_path)
                    normalized_pdf_link = urlunparse(parsed._replace(path=cleaned_path))
                    self.pdf_links_set.add(normalized_pdf_link)

            yield {
                "title": metadata["title"],
                "url": response.url,
                "canonical": canonical,
                "content": response.text
            }
        except Exception as e:
            self.logger.warning(f"Error parsing {response.url}: {e}")



    def spider_closed(self):
        if self.scrape_pdf and self.pdf_links_set:
            save_pdf_list(self.pdf_links_set, "../results/")

        feed_uris = []
        # Support for Scrapy >= 2.1 FEEDS setting
        feeds = getattr(self.crawler.settings, 'getdict', lambda x: {})('FEEDS')
        if feeds:
            feed_uris = list(feeds.keys())
        
        feed_uri = feed_uris[0] if feed_uris else None
        print("Output file from -O:", feed_uri)

        print_scraping_summary(self.crawler.stats.get_stats(), self.settings, len(self.pdf_links_set), self.output_dir, "../results/scraping_summary.log")
