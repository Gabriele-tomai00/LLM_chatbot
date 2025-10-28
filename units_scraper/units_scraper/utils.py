
import datetime
import json
import os
from bs4 import BeautifulSoup
import html2text
import re
import lxml.html as html
from scrapy.http import HtmlResponse
import unicodedata

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
    
import json
from datetime import datetime
from pathlib import Path

def print_scraping_summary(stats: dict, log_file: str = "scraping_summary.log"):
    # Stampa raw dict per debug
    print(json.dumps(stats, indent=4, default=str))

    start_time = stats.get("start_time")
    if start_time is None:
        start_time = datetime.now()
    
    end_time = stats.get("finish_time", datetime.now())
    request_depth_max = stats.get("request_depth_max", 0)

    elapsed = stats.get("elapsed_time_seconds")
    if elapsed is None:
        elapsed = (end_time - start_time).total_seconds()
    
    item_scraped_count = stats.get("item_scraped_count", 0)

    summary_lines = [
        f"\n====== SCRAPING SESSION {start_time.strftime('%Y-%m-%d %H:%M:%S')} ======",
        f"🕒 elapsed time: {format_time(elapsed)}",
        f"Start time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"📄 Total items scraped: {item_scraped_count}",
        f"📊 Max request depth: {request_depth_max}",
        "==================================================="
    ]
    for line in summary_lines:
        print(line)
    log_path = Path(log_file)
    with log_path.open("a", encoding="utf-8") as f:
        for line in summary_lines:
            f.write(line + "\n")


def remove_output_directory(dir_path = "output_bodies"):
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

def save_webpage_to_file(html_content, parsed_content, counter=1, output_dir="output_bodies"):
    os.makedirs(output_dir, exist_ok=True)
    original_path = os.path.join(output_dir, f"{counter}_filtered.html")
    with open(original_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    cleaned_path = os.path.join(output_dir, f"{counter}_cleaned.md")
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
        date = datetime.today().strftime("%d/%m/%Y")

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
