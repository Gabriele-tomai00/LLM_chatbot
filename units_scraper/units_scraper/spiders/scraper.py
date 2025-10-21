from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from urllib.parse import urlparse
from w3lib.url import canonicalize_url


def normalize_url(url):
    parsed = urlparse(url)
    normalized = parsed._replace(fragment='')  # rimuove la parte dopo #
    return canonicalize_url(normalized.geturl())


class ScraperSpider(CrawlSpider):
    name = "scraper"
    allowed_domains = ["portale.units.it"]
    start_urls = ["https://portale.units.it/it"]

    rules = (
        Rule(LinkExtractor(allow=()), callback="parse_item", follow=True),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.visited_urls = set()

    def parse_item(self, response):
        normalized_url = normalize_url(response.url)

        if normalized_url not in self.visited_urls:
            self.visited_urls.add(normalized_url)
            yield {
                "Url": normalized_url
            }

    def closed(self, reason):
        """Scrapy chiama questo metodo quando termina lo spider."""
        with open("links.txt", "w", encoding="utf-8") as f:
            for url in sorted(self.visited_urls):
                f.write(url + "\n")

        self.logger.info(f"✅ Salvati {len(self.visited_urls)} link in links.txt")
