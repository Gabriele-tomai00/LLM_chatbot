
import datetime
import json
import os
from bs4 import BeautifulSoup
import html2text
import re
import lxml.html as html
from scrapy.http import HtmlResponse
import unicodedata
import json
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

deny_domains = [
    "arts.units.it",
    "openstarts.units.it",
    "moodle.units.it",
    "moodle2.units.it",
    "wmail1.units.it",
    "cargo.units.it",
    "cspn.units.it",
    "www-amm.units.it",
    "inside.units.it",
    "flux.units.it",
    "centracon.units.it",
    "smats.units.it",
    "docenti.units.it",
    "orari.units.it",
    "pregresso.sba.units.it",
    "dryades.units.it",
    "stream.dia.units.it",
    "esse3.units.it",
    "esse3web.units.it",
    "biblio.units.it",
    "apply.units.it",
    "docu.units.it",
    "100anni.units.it",
    "rendiconti.dmi.units.it",
    "dmi.units.it",
    "wireless.units.it",
    "byzantine.units.it",
    "voip.units.it",
    "eut.units.it",
    "webmail.sp.units.it",
    "cloudmail.units.it",
    "cloudmail.studenti.units.it",
    "mail.scfor.units.it",
    "wmail2.units.it",
    "suggerimenti.units.it",
    "sebina.units.it"
]
deny_regex = [
    r".*feedback.*",
    r".*search.*",
    r".*eventi-passati.*",
    r".*openstarts.*",
    r".*moodle.units.*",
    r".*moodle2.units.*",
    r".*wmail1.*",
    r".*cargo.*",
    r".*wmail3.*",
    r".*wmail4.*",
    r".*@.*",
    r".*facebook.*",
    r".*instagram.*",
    r".*notizie.*",
]

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

def get_size_of_result_file(file_path: str) -> str:
    if os.path.exists(file_path):
        size_bytes = os.path.getsize(file_path)
        if size_bytes >= 1024**3:  # 1 GB
            size_str = f"{size_bytes / (1024**3):.2f} GB"
        else:
            size_str = f"{size_bytes / (1024**2):.2f} MB"
        return size_str
    return "File not found"

def print_scraping_summary(stats: dict, settings, summary_file_name: str = "scraping_summary.log"):
    print(json.dumps(stats, indent=4, default=str))

    start_time = stats.get("start_time", datetime.now())
    end_time = stats.get("finish_time", datetime.now())
    elapsed = stats.get("elapsed_time_seconds", (end_time - start_time).total_seconds())
    request_depth_max = stats.get("request_depth_max", 0)
    item_scraped_count = stats.get("item_scraped_count", 0)
    responses_per_minute = int(float(stats.get("responses_per_minute") or 0))
    file_name_of_results = "../items.jsonl"

    proxy_used = stats.get("proxy/used", 0)
    proxy_not_used = stats.get("proxy/not_used", 0)
    proxy_disabled = stats.get("proxy/disabled", 0)
    proxy_total = proxy_used + proxy_not_used + proxy_disabled

    if proxy_total > 0:
        if proxy_disabled > 0 and proxy_used == 0:
            proxy_summary = "Proxy disabled for this run"
        else:
            proxy_percent = (proxy_used / proxy_total) * 100
            proxy_summary = f"Proxy usage: {proxy_percent:.1f}% ({proxy_used}/{proxy_total})"
    else:
        proxy_summary = "Proxy usage: No data"

    summary_lines = [
        f"\n====== SCRAPING SESSION {start_time.strftime('%d-%m-%Y %H:%M')} ======",
        f"Elapsed time: {format_time(elapsed)}",
        f"End time: {end_time.strftime('%d-%m-%Y %H:%M')}",
        f"Total items scraped: {item_scraped_count}",
        f"Responses per minute: {responses_per_minute}",
        f"Max request depth: {request_depth_max}",
        f"Use of multiple user agents: {settings.getbool('ROTARY_USER_AGENT', False)}",
        f"{proxy_summary}",
        f"Output size: {get_size_of_result_file(file_name_of_results)}",
        "==============================================="
    ]
    for line in summary_lines:
        print(line)

    # Individua la root della repo risalendo fino a 'units_scraper' principale
    current_file = Path(__file__).resolve()
    repo_root = current_file.parents[1]  # sale di 2 livelli fino a 'units_scraper' root

    log_file = repo_root / summary_file_name

    # Scrittura del log
    with log_file.open("a", encoding="utf-8") as f:
        for line in summary_lines:
            f.write(line + "\n")


def remove_output_directory(dir_path):
    from shutil import rmtree
    from os import path

    if path.exists(dir_path) and path.isdir(dir_path):
        rmtree(dir_path)
        print(f"Output directory '{dir_path}' removed.")

def parse_html_content_soup(response) -> str:
    soup = BeautifulSoup(response.text, "lxml")
    for tag in soup(["script", "style", "footer", "meta", "link", "img"]):
        tag.decompose()
    for tag in soup.find_all("nav", class_=["blu", "navbar-expand-lg"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    return text

def parse_html_content_html2text(response) -> str:
    # cleaned_html = w3lib.html.remove_tags_with_content(
    #     response.text,
    #     which_ones=('footer','script','style', 'meta', 'link', 'img')
    # )
    h = html2text.HTML2Text()
    h.ignore_links = True          # <--- non stampa gli href
    h.ignore_images = True         # <--- nel dubbio
    h.body_width = 0               # <--- no wrapping forzato, più leggibile
    text = h.handle(response.text)
    #print(f"Cleaned content: {text}")
    return normalize_markdown(text)

def save_webpage_to_file(html_content, parsed_content, url, counter, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    # original_path = os.path.join(output_dir, f"{counter}_filtered.html")
    # with open(original_path, "w", encoding="utf-8") as f:
    #     f.write(html_content)

    parsed_url = urlparse(url)
    domain = parsed_url.netloc
    cleaned_path = os.path.join(output_dir, f"{counter}_{domain}.md")
    with open(cleaned_path, "w", encoding="utf-8") as f:
        f.write(parsed_content)

def get_article_date(response):
    # Estrai le date dai meta tag
    modified = response.xpath('//meta[@property="article:modified_time"]/@content').get()
    published = response.xpath('//meta[@property="article:published_time"]/@content').get()

    # Prova a catturare la data con regex
    modified_date = re.search(r'\b(\d{2}/\d{2}/\d{4})\b', modified) if modified else None
    published_date = re.search(r'\b(\d{2}/\d{2}/\d{4})\b', published) if published else None

    # Scegli la data disponibile, altrimenti oggi
    if modified_date:
        date = modified_date.group(1)
    elif published_date:
        date = published_date.group(1)
    else:
        date = ""

    return date

def get_metadata(response) -> dict:
        title = response.xpath('//meta[@property="og:title"]/@content').get()
        if not title:
            title = response.xpath('//title/text()').get()

        # --- DESCRIPTION ---
        description = response.xpath('//meta[@name="description"]/@content').get()
        if not description:
            description = response.xpath('//meta[@property="og:description"]/@content').get()
        date = get_article_date(response)
        return {
            "title": title,
            "description": description,
            "date": date
        }



def normalize_markdown(text: str) -> str:
    """Avoid problems in JSON line (in markdown) about special unicode characters."""
    if not text:
        return text

    replacements = {
        "’": "'",
        "‘": "'",
        "“": '"',
        "”": '"',
        "–": "-",
        "—": "-",
        "…": "...",
        "\u00A0": " ",  # space not-breaking
    }

    for old, new in replacements.items():
        text = text.replace(old, new)
    return unicodedata.normalize("NFKC", text)


def filter_response(response):
    tree = html.fromstring(response.body)
    
    tags_to_remove = ["footer", "script", "style", "meta", "link", "img"]
    for tag in tags_to_remove:
        for el in tree.xpath(f"//{tag}"):
            el.drop_tree()

    classes_to_remove = [
        "open-readspeaker-ui", "banner", "cookie-consent", 
        "nav-item dropdown", "clearfix navnavbar-nav",
        "clearfix menu menu-level-0", "sidebar", 
        "views-field views-field-link__uri", 
        "block block-layout-builder block-field-blocknodeeventofield-documenti-allegati",
        "visually-hidden-focusable", "clearfix dropdown-menu", "nav-link",
        "field__label visually-hidden", "field field--name-field-media-image field--type-image field--label-visually_hidden",
        "clearfix nav", "modal modal-search fade", "breadcrumb", "btn dropdown-toggle",
        "block block-menu navigation menu--menu-target", "view-content row"
    ]
    ids_to_remove = ["main-header", "footer-container"]

    for class_name in classes_to_remove:
        for el in tree.xpath(f'//*[@class="{class_name}"]'):
            el.drop_tree()
    for id_name in ids_to_remove:
        for el in tree.xpath(f'//*[@id="{id_name}"]'):
            el.drop_tree()

    cleaned_html = html.tostring(tree, encoding="unicode")
    soup = BeautifulSoup(cleaned_html, "lxml")
    for strong_tag in soup.find_all("strong"):
        strong_tag.unwrap()
    for tag in soup.find_all():
        if not tag.get_text(strip=True):
            tag.decompose()

    return HtmlResponse(
        url=response.url,
        body=str(soup),
        encoding='utf-8'
    )

def is_informative_markdown(text: str) -> bool:
    # remove markdown titles
    cleaned = re.sub(r'#+\s*.*', '', text)
    # remove common footer/header phrases
    cleaned = re.sub(r'\b(Tutti gli avvisi|Link utili|Contatti|Servizi|Servizi digitali|Servizi di segreteria|Dipartimenti|Vai alla pagina)\b',
                     '', cleaned, flags=re.IGNORECASE) 
    # divide into lines and remove non-meaningful ones (less than 2 words)
    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    meaningful_lines = [line for line in lines if len(line.split()) >= 2]
    # calculate word count
    cleaned_text = " ".join(meaningful_lines)
    word_count = len(cleaned_text.split())
    # criteria: at least 20 words total and at least 2 meaningful lines
    return word_count > 20 and len(meaningful_lines) > 1

def print_log(response, counter, settings):
    log = str(counter) + " " + response.url
    rotate = settings.getbool("ROTARY_USER_AGENT", False)
    proxy = settings.getbool("USE_PROXY", False)
    if proxy:
        current_proxy = response.meta.get("proxy")
        if current_proxy:
            log = log + "   PROXY: " + current_proxy
        else:
            log = log + "   direct (no proxy) " 
    if rotate:
        user_agent = response.request.headers.get("User-Agent", b"").decode("utf-8")
        ua_preview = user_agent[:20] + ("..." if len(user_agent) > 50 else "")
        log = log + " | UA: " + ua_preview
    print(log)