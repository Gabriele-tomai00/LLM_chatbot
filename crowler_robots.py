import requests
import argparse
from termcolor import colored
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

class WebCrawler:
    def __init__(self, url, max_depth, user_agent='MyCrawler'):
        self.url = url
        self.max_depth = max_depth
        self.user_agent = user_agent
        self.visited_links = set()
        self.subdomains = set()
        self.robot_parsers = {}  # Salva robots.txt per dominio

    def can_fetch(self, url):
        parsed = urlparse(url)
        domain = f"{parsed.scheme}://{parsed.netloc}"

        if domain not in self.robot_parsers:
            robots_url = urljoin(domain, '/robots.txt')
            rp = RobotFileParser()
            rp.set_url(robots_url)
            try:
                rp.read()
            except:
                rp = None
            self.robot_parsers[domain] = rp

        rp = self.robot_parsers[domain]
        if rp:
            return rp.can_fetch(self.user_agent, url)
        return True  # Se non si riesce a leggere robots.txt, assume consentito

    def start_crawling(self):
        self.crawl(self.url, depth=1)

    def crawl(self, url, depth):
        if depth > self.max_depth or url in self.visited_links:
            return
        if not self.can_fetch(url):
            print(f"[-] Skipping (robots.txt disallow): {url}")
            return

        print(f"[+] Visiting: {url}")
        self.visited_links.add(url)

        parsed_url = urlparse(url)
        self.subdomains.add(parsed_url.netloc)  # memorizza solo il dominio reale

        try:
            response = requests.get(url, timeout=3, allow_redirects=True)
            soup = BeautifulSoup(response.text, 'html.parser')
        except requests.exceptions.RequestException as err:
            print(f"[-] An error occurred: {err}")
            return

        # Estrai tutti i link
        for link_tag in soup.find_all('a', href=True):
            link = urljoin(url, link_tag['href'])  # trasforma in URL assoluto
            if link not in self.visited_links:
                self.crawl(link, depth + 1)

    def print_banner(self):
        print("-" * 80)
        print(colored(f"Recursive Web Crawler starting at {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", 'cyan', attrs=['bold']))
        print("-" * 80)
        print(f"[*] URL".ljust(20, " "), ":", self.url)
        print(f"[*] Max Depth".ljust(20, " "), ":", self.max_depth)
        print("-" * 80)

    def print_results(self):
        print(f"[+] Number of subdomains found: {len(self.subdomains)}")
        for sub in self.subdomains:
            print(f"    {sub}")
        print(f"[+] Number of links visited : {len(self.visited_links)}")
        for link in self.visited_links:
            print(f"    {link}")

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--url', dest='url', help="Specify the URL (include http/https)", required=True)
    parser.add_argument('-d', '--depth', dest='depth', type=int, default=1, help="Specify the recursion depth limit")
    return parser.parse_args()

if __name__ == "__main__":
    args = get_args()
    crawler = WebCrawler(args.url, args.depth)
    crawler.print_banner()
    crawler.start_crawling()
    crawler.print_results()
