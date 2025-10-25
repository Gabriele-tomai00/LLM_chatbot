
import datetime
import json
import os
from bs4 import BeautifulSoup
import html2text
import w3lib

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
    
    # finish_time preferibile da stats, altrimenti usa adesso
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

    # Stampa a video
    for line in summary_lines:
        print(line)

    # Salva su file (append)
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
    return text

def save_webpage_to_file(html_content, parsed_content, counter=1, output_dir="output_bodies"):
    os.makedirs(output_dir, exist_ok=True)
    original_path = os.path.join(output_dir, f"{counter}_original.html")
    with open(original_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    cleaned_path = os.path.join(output_dir, f"{counter}_cleaned.html")
    with open(cleaned_path, "w", encoding="utf-8") as f:
        f.write(parsed_content)