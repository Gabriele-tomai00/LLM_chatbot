from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from urllib.parse import urlparse
import time
from datetime import datetime
from units_scraper.utils import *
from pydispatch import dispatcher
from scrapy import signals
import os
import shutil
from bs4 import BeautifulSoup
class ScraperSpider(CrawlSpider):
    name = "scraper"
    allowed_domains = ["portale.units.it"]
    start_urls = ["https://portale.units.it/it/eventi/osservazioni-sulla-tortura-dialoghi-sul-contrasto-e-sullaccertamento-di-un-reato-universale"]
    counter = 1

    # WHITELIST DI URL/REGEX PERMESSI (puoi aggiungere pattern)
    ALLOW_URLS = [
        # r"^https://portale\.units\.it/it$",
        r"^https://portale\.units\.it/it/eventi/osservazioni-sulla-tortura-dialoghi-sul-contrasto-e-sullaccertamento-di-un-reato-universale$",
        # es: r".*didattica.*", r".*studenti.*"
    ]

    rules = (
        Rule(
            LinkExtractor(
                # allow=ALLOW_URLS,          # <-- solo questi URL vengono seguiti
                allow_domains=allowed_domains,
                allow=(r"/it/"),
            ),
            callback="parse_item",
            follow=True
        ),
    )




    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        remove_output_directory("output_bodies")
        dispatcher.connect(self.spider_closed, signals.engine_stopped)

    def parse_item(self, response):
        print(str(self.counter) + " " + response.url)
        metadata = get_metadata(response)
        cleaned_response = filter_response(response)
        content = parse_html_content_html2text(cleaned_response)
        save_webpage_to_file(cleaned_response.text, content, self.counter, output_dir="output_bodies")
        self.counter += 1
        item = {
            "title": metadata["title"],
            "url": response.url,
            "description": metadata["description"],
            "timestamp": metadata["date"],
            "content": content
         }
        yield item



    def spider_closed(self):
        print_scraping_summary(self.crawler.stats.get_stats())

