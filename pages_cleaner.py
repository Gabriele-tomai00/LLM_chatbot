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
import os
from urllib.parse import urlparse, unquote
import hashlib
import multiprocessing

# Set to False for large-scale processing
SAVE_DEBUG_FILES = False

output_dir_FILTERED_HTML = "results/filtered_html_output/"
output_dir_CLEANED_MD = "results/cleaned_md_output/"

def sanitize_filename(name: str, max_length: int = 150) -> str:
    name = unquote(name)
    parsed = urlparse(name)
    basename = parsed.netloc + parsed.path
    basename = re.sub(r'[\\/?:*"<>|]', '_', basename).strip('_')
    if len(basename) > max_length:
        digest = hashlib.sha1(basename.encode()).hexdigest()[:8]
        basename = basename[:max_length] + "_" + digest
    return basename


def filter_response(html_content: str) -> str:
    tree = html.fromstring(html_content)
    for tag in ["footer", "script", "style", "meta", "link", "img"]:
        for el in tree.xpath(f"//{tag}"):
            el.drop_tree()

    classes_and_ids_to_remove = [
        "open-readspeaker-ui", "banner", "cookie", "nav-item dropdown",
        "sidebar", "breadcrumb", "btn dropdown-toggle", "main-header",
        "footer-container", "links",
        "clearfix navnavbar-nav", "clearfix menu menu-level-0",
        "views-field views-field-link__uri",
        "block-layout-builder", "block-field-blocknodeeventofield-documenti-allegati",
        "visually-hidden-focusable", "clearfix dropdown-menu", "nav-link",
        "field__label visually-hidden", "visually-hidden",
        "field field--name-field-media-image field--type-image field--label-visually_hidden",
        "clearfix nav", "modal modal-search fade",
        "block block-menu navigation menu--menu-target", "view-content row",
        "rsbtn",    # ← ReadSpeaker player ("Ascolta")
        "rs_skip",  # ← ReadSpeaker wrapper
    ]

    for name in classes_and_ids_to_remove:
        for el in tree.xpath(f'//*[contains(translate(@class, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "{name.lower()}")]'):
            el.drop_tree()
        for el in tree.xpath(f'//*[contains(translate(@id, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "{name.lower()}")]'):
            el.drop_tree()

    soup = BeautifulSoup(html.tostring(tree, encoding="unicode"), "lxml")

    for strong_tag in soup.find_all("strong"):
        strong_tag.unwrap()
    for tag in soup.find_all():
        if not tag.get_text(strip=True):
            tag.decompose()

    return str(soup)

def normalize_markdown(text: str) -> str:
    if not text:
        return text
    replacements = {
        "’": "'", "‘": "'", "“": '"', "”": '"',
        "–": "-", "—": "-", "…": "...", "\u00A0": " "
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
    text = normalize_markdown(text)
    cleaned = re.sub(r'#+\s*.*', '', text)

    patterns = [
        r'\b(Tutti gli avvisi|Link utili|Contatti|Servizi|Privacy|Dove siamo)\b',
        r'\b(P\.IVA|C\.F\.|PEC:|Fatturazione elettronica)\b',
        r'\b(http[s]?://[^\s]+)\b'
    ]
    for pattern in patterns:
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)

    lines = [l.strip() for l in cleaned.splitlines() if l.strip()]
    meaningful = [l for l in lines if len(l.split()) >= min_words_per_line]

    if len(meaningful) < min_lines:
        return False

    words = " ".join(meaningful).split()
    if len(words) < min_words_total:
        return False

    unique_ratio = len(set(words)) / len(words)
    return unique_ratio >= min_unique_ratio


def parse_html_content_html2text(html_content: str) -> str:
    h = html2text.HTML2Text()
    h.ignore_links = True
    h.ignore_images = True
    h.body_width = 0
    return normalize_markdown(h.handle(html_content))


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
    if not html_content:
        return None, "skipped"

    try:
        cleaned_html = filter_response(html_content)
        md = parse_html_content_html2text(cleaned_html)

        if not is_informative_markdown(md):
            return None, "skipped"

        item["content"] = md

        if SAVE_DEBUG_FILES:
            fn = sanitize_filename(url)
            os.makedirs(output_dir_FILTERED_HTML, exist_ok=True)
            os.makedirs(output_dir_CLEANED_MD, exist_ok=True)
            with open(os.path.join(output_dir_FILTERED_HTML, fn + ".html"), "w") as f:
                f.write(cleaned_html)
            with open(os.path.join(output_dir_CLEANED_MD, fn + ".md"), "w") as f:
                f.write(md)

        return item, "saved"

    except Exception:
        return None, "skipped"


def process_file(input_file: str, output, verbose: bool, write_to_existing=False):
    # If write_to_existing=False, 'output' is a file path and we open it
    close_after = False
    if not write_to_existing:
        output = open(output, "w", encoding="utf-8")
        close_after = True

    max_workers = min(8, multiprocessing.cpu_count())
    saved = 0
    skipped = 0

    with open(input_file, "r", encoding="utf-8") as fin, \
         ProcessPoolExecutor(max_workers=max_workers) as executor:

        for result in tqdm(executor.map(process_line, fin, chunksize=500),
                           desc=f"Processing {os.path.basename(input_file)}", mininterval=1):

            if not result:
                skipped += 1
                continue

            item, status = result
            if status == "saved" and item:
                output.write(json.dumps(item, ensure_ascii=False) + "\n")
                saved += 1
                if verbose:
                    tqdm.write(f"SAVED: {item.get('url', '')}")
            else:
                skipped += 1

    if close_after:
        output.close()

    print(f"Finished {os.path.basename(input_file)}: Saved {saved}, Skipped {skipped}")


def main(input_path: str, output_path: str, verbose: bool):
    # Output must always be a file
    if output_path.endswith("/") or output_path.endswith("\\") or os.path.isdir(output_path):
        raise ValueError("Error: --output must be a file, not a directory.")

    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    if os.path.isfile(input_path):
        print(f"Processing single input file: {input_path}")
        process_file(input_path, output_path, verbose)
        return

    if os.path.isdir(input_path):
        jsonl_files = [os.path.join(input_path, f) for f in os.listdir(input_path) if f.endswith(".jsonl")]
        if not jsonl_files:
            print(f"No .jsonl files found in directory: {input_path}")
            return

        print(f"Processing directory: {input_path}")
        print(f"Merging all cleaned content into: {output_path}\n")

        with open(output_path, "w", encoding="utf-8") as fout:
            for f in jsonl_files:
                print(f"Processing {f} ...")
                process_file(f, fout, verbose, write_to_existing=True)

        print(f"\nAll files processed successfully. Output written to: {output_path}")
        return

    raise FileNotFoundError(f"Input path not found: {input_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str, required=True, help="Input file or directory")
    parser.add_argument("--output", type=str, required=True, help="Output file (.jsonl)")
    parser.add_argument("--verbose", action="store_true", help="Print each saved URL")
    args = parser.parse_args()

    logging.basicConfig(format="%(levelname)s - %(message)s", level=logging.WARNING)

    main(args.input, args.output, args.verbose)
