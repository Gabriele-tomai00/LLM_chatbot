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
        try:
            print_log(response, self.counter, self.crawler.settings)
            metadata = get_metadata(response)
            self.counter += 1
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
        print_scraping_summary(self.crawler.stats.get_stats(), self.settings, "scraping_summary.log")

