import scrapy
from scrapy import Spider
from scrapy import Request
from scrapy.crawler import CrawlerProcess
from scrapy.linkextractors import LinkExtractor

import os

class UNITSspider(Spider):

    name = 'UNITSspider'
    start_urls = ['http://www.amiciinsoliti.altervista.org']
    
    try:
        os.remove('units_links.txt')
    except OSError:
        pass

    custom_settings = {
        'CONCURRENT_REQUESTS' : 48,  
        'CONCURRENT_REQUESTS_PER_DOMAIN' : 16,              

        'AUTOTHROTTLE_ENABLED': True,
        'AUTOTHROTTLE_DEBUG': True,
        'AUTOTHROTTLE_START_DELAY': 1,
        'AUTOTHROTTLE_TARGET_CONCURRENCY': 8,
        'LOG_ENABLED': True,
        'LOG_LEVEL': 'INFO',
        'USER_AGENT': 'UNITS Link Crawler (network lab)'
    }

    def __init__(self):
        self.link_extractor = LinkExtractor(unique=True, allow_domains=["amiciinsoliti.altervista.org"], 
                                            deny_domains=["arts.units.it"],
                                            deny=[r".*feedback.*", r".*search.*", r"#", r".*eventi-passati.*"]
                                            )                                             
        
    def parse(self, response):
        for link in self.link_extractor.extract_links(response):
            with open('units_links.txt','a+') as f:
                f.write(f"\n{str(link.url)}")

            yield response.follow(url=link, callback=self.parse)

if __name__ == "__main__":
    process = CrawlerProcess()
    process.crawl(UNITSspider)
    process.start()