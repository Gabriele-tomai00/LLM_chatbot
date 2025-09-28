from scrapy import Spider
import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy.linkextractors import LinkExtractor
from urllib.parse import urlparse, urlunparse
import os
import time
from datetime import datetime

def normalize_url(url):
    parsed = urlparse(url)
    # Rimuove query string e frammenti
    normalized = parsed._replace(query='', fragment='')
    return urlunparse(normalized)

def format_time(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = round(seconds % 60)
    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"


class UNITSspider(Spider):
    name = 'UNITSspider'
    start_urls = ['https://www.units.it']
    start_time = None
    # Set per URL normalizzati
    visited_urls = set()

    custom_settings = {
        'CONCURRENT_REQUESTS': 70,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 70,
        'AUTOTHROTTLE_ENABLED': True,
        'AUTOTHROTTLE_DEBUG': True,
        'AUTOTHROTTLE_START_DELAY': 0.1,
        'AUTOTHROTTLE_TARGET_CONCURRENCY': 50,
        'LOG_ENABLED': True,
        'LOG_LEVEL': 'INFO',
        'USER_AGENT': 'UNITS Links Crawler (network lab)',
        'ROBOTSTXT_OBEY': True,
        'DEPTH_LIMIT': 3
    }

    def __init__(self):
        self.link_extractor = LinkExtractor(
            unique=True,
            allow_domains=["units.it"],
            deny_domains=["arts.units.it", "openstarts.units.it"],
            deny=[r".*feedback.*", r".*search.*", r"#", r".*eventi-passati.*", r".*openstarts.*"]
        )
        try:
            os.remove('units_links.txt')
        except OSError:
            pass
        self.start_time = time.time()

    def start_requests(self):
        self.start_time = time.time()
        self.start_datetime = datetime.now()  # salvo data/ora di inizio
        for url in self.start_urls:
            yield scrapy.Request(url, callback=self.parse)



    def parse(self, response):
        for link in self.link_extractor.extract_links(response):
            normalized_url = normalize_url(link.url)
            if normalized_url not in self.visited_urls:
                self.visited_urls.add(normalized_url)
                print(f"Actual number of links fonud: {len(self.visited_urls)}")
                with open('units_links.txt','a+') as f:
                    f.write(f"\n{str(normalized_url)}")

                yield response.follow(url=link, callback=self.parse)


    def closed(self, reason):
        end_time = time.time()
        end_datetime = datetime.now()
        duration = format_time(end_time - self.start_time)

        with open('crawling_summary.log', 'a') as f:
            f.write("====== NEW CRAWLING SESSION ======\n")
            f.write(f"Start time: {self.start_datetime.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"End time:   {end_datetime.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Duration:   {duration}\n")
            f.write(f"Links found: {len(self.visited_urls)}\n")
            f.write("Custom settings:\n")
            f.write(f"   CONCURRENT_REQUESTS: {self.custom_settings.get('CONCURRENT_REQUESTS', 'N/A')}\n")
            f.write(f"   CONCURRENT_REQUESTS_PER_DOMAIN: {self.custom_settings.get('CONCURRENT_REQUESTS_PER_DOMAIN', 'N/A')}\n")
            f.write(f"   ROBOTSTXT_OBEY: {self.custom_settings.get('ROBOTSTXT_OBEY', 'N/A')}\n")
            f.write(f"   DEPTH_LIMIT: {self.custom_settings.get('DEPTH_LIMIT', 'N/A')}\n")
            f.write("\n")

if __name__ == "__main__":
    process = CrawlerProcess()
    process.crawl(UNITSspider)
    process.start()
