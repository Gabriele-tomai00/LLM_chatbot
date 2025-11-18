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

def filter_response(html_content: str) -> str:
    """Cleans HTML by removing tags, classes, IDs, and empty elements. Returns cleaned HTML as string."""
    tree = html.fromstring(html_content)
    
    # tags to remove
    tags_to_remove = ["footer", "script", "style", "meta", "link", "img"]
    for tag in tags_to_remove:
        for el in tree.xpath(f"//{tag}"):
            el.drop_tree()

    # classes and IDs to remove
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

    # convert tree to string and remove empty tags
    cleaned_html = html.tostring(tree, encoding="unicode")
    soup = BeautifulSoup(cleaned_html, "lxml")
    for strong_tag in soup.find_all("strong"):
        strong_tag.unwrap()
    for tag in soup.find_all():
        if not tag.get_text(strip=True):
            tag.decompose()

    return str(soup)

def is_informative_markdown(text: str) -> bool:
    """Returns True if the text is considered informative, False otherwise."""
    # remove markdown titles
    cleaned = re.sub(r'#+\s*.*', '', text)
    # remove common footer/header phrases
    cleaned = re.sub(
        r'\b(Tutti gli avvisi|Link utili|Contatti|Servizi|Servizi digitali|Servizi di segreteria|Dipartimenti|Vai alla pagina)\b',
        '', cleaned, flags=re.IGNORECASE
    )
    # divide into lines and keep meaningful ones (>=2 words)
    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    meaningful_lines = [line for line in lines if len(line.split()) >= 2]
    # count total words
    cleaned_text = " ".join(meaningful_lines)
    word_count = len(cleaned_text.split())
    # criteria: at least 20 words total and at least 2 meaningful lines
    return word_count > 20 and len(meaningful_lines) > 1

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

    main(args.input, args.output, args.verbose)
