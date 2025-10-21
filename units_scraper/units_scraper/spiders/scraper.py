from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from urllib.parse import urlparse
import time
from datetime import datetime
from units_scraper.utils import *
from pydispatch import dispatcher
from scrapy import signals

# def clean_urls(file_path="units_links.txt"):
#     with open(file_path, "r") as f:
#         urls = {line.strip() for line in f if line.strip()}


    
class ScraperSpider(CrawlSpider):
    name = "scraper"
    allowed_domains = ["portale.units.it"]
    start_urls = ["https://portale.units.it/it"]
    EXCLUDE_DOMAINS = [
        "arts.units.it", "openstarts.units.it", "moodle.units.it",
        "moodle2.units.it", "wmail1.units.it", "cargo.units.it",
        "cspn.units.it", "www-amm.units.it", "inside.units.it",
        "flux.units.it", "centracon.units.it", "smats.units.it",
        "docenti.units.it", "orari.units.it"
    ]

    EXCLUDE_URLS = [
        r".*feedback.*", r".*search.*", r"#", r".*eventi-passati.*",
        r".*openstarts.*", r".*moodle.units.*", r".*moodle2.*",
        r".*wmail1.*", r".*cargo.*", r".*wmail3.*", r".*wmail4.*"
    ]

    rules = (
        Rule(
            LinkExtractor(
                allow=(),           # o regex specifiche se vuoi limitare gli URL
                deny=EXCLUDE_URLS,
                deny_domains=EXCLUDE_DOMAINS
            ),
            callback="parse_item",
            follow=True
        ),
    )


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        dispatcher.connect(self.spider_closed, signals.engine_stopped)

    def parse_item(self, response):
        yield {
            "Url": response.url,
            "Status": response.status,
        }


    def spider_closed(self):
        print_scraping_summary(self.crawler.stats.get_stats())

