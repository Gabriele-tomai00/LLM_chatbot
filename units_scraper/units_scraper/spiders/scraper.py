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

    # WHITELIST DI URL/REGEX PERMESSI (puoi aggiungere pattern)
    ALLOW_URLS = [
        r"^https://portale\.units\.it/it$",
        # es: r".*didattica.*", r".*studenti.*"
    ]

    rules = (
        Rule(
            LinkExtractor(
                #allow=ALLOW_URLS,          # <-- solo questi URL vengono seguiti
                allow_domains=allowed_domains
            ),
            callback="parse_item",
            follow=True
        ),
    )




    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        dispatcher.connect(self.spider_closed, signals.engine_stopped)

    def parse_item(self, response):
        item = {}
        item['body'] = response.text
        item['url'] = response.url
        print(f"Scraped: {item['url']}, status: {response.status}")
        yield item


    def spider_closed(self):
        print_scraping_summary(self.crawler.stats.get_stats())

