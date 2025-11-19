import lxml.html as html
from bs4 import BeautifulSoup
import re
import html2text
import unicodedata
import json
import logging
import argparse
from tqdm import tqdm
from concurrent.futures import ProcessPoolExecutor
import multiprocessing
import os
import shutil
from urllib.parse import urlparse
from collections import Counter

output_dir_FILTERED_HTML = "results/filtered_html_output/"
output_dir_CLEANED_MD = "results/cleaned_md_output/"
counter_html = 0  # global counter for saved files
counter_md = 0

def sanitize_filename(name: str) -> str:
    # sostituisce tutti i caratteri non validi con _
    return re.sub(r'[\\/?:*"<>|]', '_', name)


def save_filtered_html_to_file(url, parsed_content):
    global counter_html
    header = f"<!-- Original URL: {url} -->\n"
    url=urlparse(url)
    url = sanitize_filename(url.netloc + url.path)
    cleaned_path = os.path.join(output_dir_FILTERED_HTML, f"{url}.html")
    # inserisco il commento HTML con l'URL originale

    with open(cleaned_path, "w", encoding="utf-8") as f:
        f.write(header)
        f.write(parsed_content)

    counter_html += 1

def save_md_to_file(url, parsed_content):
    global counter_md
    header = f"<!-- Original URL: {url} -->\n"
    url=urlparse(url)
    url = sanitize_filename(url.netloc + url.path)
    cleaned_path = os.path.join(output_dir_CLEANED_MD, f"{url}.md")
    with open(cleaned_path, "w", encoding="utf-8") as f:
        f.write(parsed_content)
    counter_md += 1

def filter_response(html_content: str) -> str:
    """Cleans HTML by removing tags, classes, IDs, and empty elements. Returns cleaned HTML as string."""
    tree = html.fromstring(html_content)
    
    # tags to remove
    tags_to_remove = ["footer", "script", "style", "meta", "link", "img"]
    for tag in tags_to_remove:
        for el in tree.xpath(f"//{tag}"):
            el.drop_tree()

    # classes and IDs to remove
    classes_and_ids_to_remove = [
        "open-readspeaker-ui", "banner", "cookie", 
        "nav-item dropdown", "clearfix navnavbar-nav",
        "clearfix menu menu-level-0", "sidebar", 
        "views-field views-field-link__uri", 
        "block block-layout-builder block-field-blocknodeeventofield-documenti-allegati",
        "visually-hidden-focusable", "clearfix dropdown-menu", "nav-link",
        "field__label visually-hidden", "field field--name-field-media-image field--type-image field--label-visually_hidden",
        "clearfix nav", "modal modal-search fade", "breadcrumb", "btn dropdown-toggle",
        "block block-menu navigation menu--menu-target", "view-content row", "nice-menus", "block-menu-block", "menuleft_rwd_liv_top",
        "main-header", "footer-container", "openclose", "links"
    ]

    """remove specific classes and ids from the HTML tree"""
    # for class_name in classes_to_remove:
    #     for el in tree.xpath(f'//*[@class="{class_name}"]'):
    #         el.drop_tree()
    # for id_name in ids_to_remove:
    #     for el in tree.xpath(f'//*[@id="{id_name}"]'):
    #         el.drop_tree()

    """remove elements by class or id containing specific substrings (case-insensitive)"""
    for name in classes_and_ids_to_remove:
        # case-insensitive usando translate
        for el in tree.xpath(f'//*[contains(translate(@class, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "{name.lower()}")]'):
            el.drop_tree()
    for name in classes_and_ids_to_remove:
        # case-insensitive usando translate
        for el in tree.xpath(f'//*[contains(translate(@id, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "{name.lower()}")]'):
            el.drop_tree()
    for el in tree.xpath('//label[@for]'):
        el.drop_tree()

    soup = BeautifulSoup(html.tostring(tree, encoding="unicode"), "lxml")

    for strong_tag in soup.find_all("strong"):
        strong_tag.unwrap()
    for tag in soup.find_all():
        if not tag.get_text(strip=True):
            tag.decompose()

    for nav in soup.find_all("nav"):
        # ignora nav con contenuto significativo
        significant = nav.find(["p", "div", "ul", "ol", "table"])
        if not significant:
            nav.decompose()  # rimuove anche il titolo se non c'è altro

    return str(soup)

def normalize_markdown(text: str) -> str:
    """Normalize special characters to avoid JSON issues."""
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
        "\u00A0": " ",  # non-breaking space
    }

    for old, new in replacements.items():
        text = text.replace(old, new)
    return unicodedata.normalize("NFKC", text)

def is_informative_markdown(
    text: str,
    min_words_total: int = 30,
    min_lines: int = 3,
    min_words_per_line: int = 5,
    min_unique_ratio: float = 0.6
) -> bool:
    """Return True if the text is considered informative, False otherwise."""
    text = normalize_markdown(text)
    
    # 1. Remove markdown headers
    cleaned = re.sub(r'#+\s*.*', '', text)
    
    # 2. Remove common footer/header phrases and standard patterns
    patterns = [
        r'\b(Tutti gli avvisi|Link utili|Contatti|Servizi|Servizi digitali|Servizi di segreteria|Dipartimenti|Vai alla pagina|Visualizzazione e prenotazioni aule|Caselle di posta condivise|Calendario google|Sicurezza in dipartimento|Università degli studi di [^\n]+)\b',
        r'\b(©\d{4}.*|P\.IVA.*|C\.F\..*|PEC:.*|Fatturazione elettronica)\b',
        r'\b(Privacy|Mappa sito|Dove siamo|Ultimo aggiornamento:.*)\b',
        r'\b(mailto:.*|http[s]?://[^\s]+)\b'
    ]
    for pattern in patterns:
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)

    # 3. Split into lines and remove empty or too short lines
    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    meaningful_lines = [
        line for line in lines 
        if len(line.split()) >= min_words_per_line and not re.match(r'^[\*\-_\\]+$', line)
    ]

    # 4. Check if there are enough meaningful lines
    if len(meaningful_lines) < min_lines:
        return False

    # 5. Count total words
    cleaned_text = " ".join(meaningful_lines)
    words = cleaned_text.split()
    if len(words) < min_words_total:
        return False

    # 6. Check lexical richness (ratio of unique words)
    word_counts = Counter(words)
    unique_ratio = len(word_counts) / len(words)
    if unique_ratio < min_unique_ratio:
        return False

    return True

def normalize_markdown(text: str) -> str:
    """Normalizes special unicode characters to avoid JSON issues."""
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
        "\u00A0": " ",  # non-breaking space
    }

    for old, new in replacements.items():
        text = text.replace(old, new)
    return unicodedata.normalize("NFKC", text)

def parse_html_content_html2text(html_content: str) -> str:
    """Converts HTML string to Markdown text."""
    h = html2text.HTML2Text()
    h.ignore_links = True
    h.ignore_images = True
    h.body_width = 0  # no forced wrapping
    text = h.handle(html_content)
    return normalize_markdown(text)


def process_line(line):
    line = line.strip()
    if not line:
        return None, "skipped"

    try:
        item = json.loads(line)
    except json.JSONDecodeError:
        return None, "skipped"

    html_content = item.get("content", "")
    url = item.get("url", "")

    if not html_content.strip():
        return None, "skipped"

    try:
        cleaned_html = filter_response(html_content)
        md_content = parse_html_content_html2text(cleaned_html)
        if is_informative_markdown(md_content):
            item["content"] = md_content

            # JUST FOR DEVELOPMENT !!
            save_filtered_html_to_file(url, cleaned_html)
            save_md_to_file(url, md_content)
            ###

            return item, "saved"
        else:
            return None, "skipped"
    except Exception as e:
        logging.warning(f"Error processing {url}: {e}")
        return None, "skipped"


def main(input_file: str, output_file: str, verbose: bool):
    logging.basicConfig(
        format="%(asctime)s - %(levelname)s - %(message)s",
        level=logging.WARNING
    )

    with open(input_file, "r", encoding="utf-8") as f:
        total_lines = sum(1 for _ in f)

    saved_lines = 0
    skipped_lines = 0

    num_workers = multiprocessing.cpu_count()

    with open(input_file, "r", encoding="utf-8") as fin, open(output_file, "w", encoding="utf-8") as fout:
        with ProcessPoolExecutor(max_workers=num_workers) as executor:
            # iterator invece di list
            for result in tqdm(executor.map(process_line, fin), total=total_lines, desc="Processing lines"):
                item, status = result
                if status == "saved" and item is not None:
                    fout.write(json.dumps(item, ensure_ascii=False) + "\n")
                    saved_lines += 1
                    if verbose:
                        tqdm.write(f"saved: {item.get('url','')}")
                else:
                    skipped_lines += 1
                    if verbose and item is not None:
                        tqdm.write(f"skipped: {item.get('url','')}")

    print(f"\nTotal lines processed: {total_lines}")
    print(f"Lines saved: {saved_lines}")
    print(f"Lines skipped: {skipped_lines}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process JSONL and clean HTML content.")
    parser.add_argument("--input", type=str, default="items.jsonl", help="Input JSONL file")
    parser.add_argument("--output", type=str, default="filtered_items.jsonl", help="Output JSONL file")
    parser.add_argument("--verbose", action="store_true", help="Enable detailed logging")
    args = parser.parse_args()

    for directory in [output_dir_FILTERED_HTML, output_dir_CLEANED_MD]:
        if os.path.exists(directory):
            shutil.rmtree(directory)
        os.makedirs(directory)

    main(args.input, args.output, args.verbose)
