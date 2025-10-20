import scrapy
from scrapy.linkextractors import LinkExtractor
from urllib.parse import urlparse
from w3lib.url import canonicalize_url
from datetime import timezone
from zoneinfo import ZoneInfo  # disponibile da Python 3.9 in poi

def normalize_url(url):
    parsed = urlparse(url)
    normalized = parsed._replace(fragment='')  # rimuove l'anchor
    return canonicalize_url(normalized)

class ScraperSpider(scrapy.Spider):
    name = "scraper"
    allowed_domains = ["portale.units.it"]
    start_urls = ["https://portale.units.it/"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Link extractor configurato per il dominio e i domini da evitare
        self.link_extractor = LinkExtractor(
            allow_domains=["units.it"],
            deny_domains=[
                "arts.units.it", "openstarts.units.it", "moodle.units.it", 
                "moodle2.units.it", "wmail1.units.it", "cargo.units.it", 
                "cspn.units.it", "www-amm.units.it", "inside.units.it", 
                "flux.units.it", "centracon.units.it", "smats.units.it",
                "docenti.units.it", "orari.units.it"
            ],
            deny=[r".*feedback.*", r".*search.*", r"#", r".*eventi-passati.*",
                  r".*openstarts.*", r".*moodle.units.*", r".*moodle2.*",
                  r".*wmail.*", r".*cargo.*"]
        )
        # Set per URL già visitati
        self.visited_urls = set()
        # Set per accumulare tutti i link trovati
        self.all_links = set()

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(url, callback=self.parse)

    def parse(self, response):
        # estrazione dei link dalla pagina
        for link in self.link_extractor.extract_links(response):
            normalized_url = normalize_url(link.url)
            if normalized_url not in self.visited_urls:
                self.visited_urls.add(normalized_url)
                self.all_links.add(normalized_url)
                # continua il crawling su quel link
                # print(f"Found link: {normalized_url}")
                yield response.follow(url=link, callback=self.parse)

    def closed(self, reason):
        # stampa tutti i link unici trovati, ordinati
        # for url in sorted(self.all_links):

        stats = self.crawler.stats.get_stats()
        finish_time = stats.get("finish_time")
        readable_time = finish_time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"Finish time: {readable_time}")

        start_time = stats.get("start_time")
        finish_time = stats.get("finish_time")

        if start_time:
            local_start = start_time.astimezone(ZoneInfo("Europe/Rome"))
            self.logger.info("Start time: %s", local_start.strftime("%Y-%m-%d %H:%M:%S"))

        if finish_time:
            local_finish = finish_time.astimezone(ZoneInfo("Europe/Rome"))
            self.logger.info("End time: %s", local_finish.strftime("%Y-%m-%d %H:%M:%S"))
