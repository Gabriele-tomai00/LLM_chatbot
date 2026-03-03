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
from functools import partial

# Set to True only if you want to inspect intermediate files
SAVE_DEBUG_FILES = False

def sanitize_filename(name: str, max_length: int = 150) -> str:
    """Sanitize URL to create a safe filename."""
    name = unquote(name)
    parsed = urlparse(name)
    basename = parsed.netloc + parsed.path
    basename = re.sub(r'[\\/?:*"<>|]', '_', basename).strip('_')
    if len(basename) > max_length:
        digest = hashlib.sha1(basename.encode()).hexdigest()[:8]
        basename = basename[:max_length] + "_" + digest
    return basename

def filter_response(html_content: str) -> str:
    """Remove boilerplate tags and specific classes/IDs from HTML."""
    try:
        tree = html.fromstring(html_content)
    except Exception:
        return ""

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
        "rsbtn", "rs_skip",
    ]

    for name in classes_and_ids_to_remove:
        for el in tree.xpath(f'//*[contains(translate(@class, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "{name.lower()}")]'):
            try: el.drop_tree()
            except: pass
        for el in tree.xpath(f'//*[contains(translate(@id, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "{name.lower()}")]'):
            try: el.drop_tree()
            except: pass

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

def is_informative_markdown(text: str) -> bool:
    """Basic heuristic to filter out non-informative pages."""
    text = normalize_markdown(text)
    cleaned = re.sub(r'#+\s*.*', '', text)
    lines = [l.strip() for l in cleaned.splitlines() if l.strip()]
    meaningful = [l for l in lines if len(l.split()) >= 5]
    if len(meaningful) < 3: return False
    words = " ".join(meaningful).split()
    if len(words) < 30: return False
    unique_ratio = len(set(words)) / len(words)
    return unique_ratio >= 0.6

def parse_html_content_html2text(html_content: str) -> str:
    h = html2text.HTML2Text()
    h.ignore_links = True
    h.ignore_images = True
    h.body_width = 0
    return normalize_markdown(h.handle(html_content))

def process_line(line, debug_dirs=None):
    """Worker function with optional debug directory support."""
    line = line.strip()
    if not line: return None, "skipped"
    try:
        item = json.loads(line)
    except: return None, "skipped"

    html_content = item.get("content", "")
    url = item.get("url", "")
    if not html_content: return None, "skipped"

    try:
        cleaned_html = filter_response(html_content)
        md = parse_html_content_html2text(cleaned_html)

        if not is_informative_markdown(md):
            return None, "skipped"

        item["content"] = md

        if SAVE_DEBUG_FILES and debug_dirs:
            fn = sanitize_filename(url)
            with open(os.path.join(debug_dirs['html'], fn + ".html"), "w", encoding="utf-8") as f:
                f.write(cleaned_html)
            with open(os.path.join(debug_dirs['md'], fn + ".md"), "w", encoding="utf-8") as f:
                f.write(md)

        return item, "saved"
    except:
        return None, "skipped"

def process_file_logic(input_file_path, output_file_handle, verbose, debug_dirs):
    max_workers = min(8, multiprocessing.cpu_count())
    saved, skipped = 0, 0
    
    # Use partial to pass debug_dirs to the worker function
    worker_func = partial(process_line, debug_dirs=debug_dirs)

    with open(input_file_path, "r", encoding="utf-8") as fin:
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            for result in tqdm(executor.map(worker_func, fin, chunksize=200),
                               desc=f"Processing {os.path.basename(input_file_path)}", 
                               leave=False):
                if not result:
                    skipped += 1
                    continue
                item, status = result
                if status == "saved" and item:
                    output_file_handle.write(json.dumps(item, ensure_ascii=False) + "\n")
                    saved += 1
                    if verbose: tqdm.write(f"SAVED: {item.get('url', '')}")
                else:
                    skipped += 1
    return saved, skipped

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str, required=True)
    parser.add_argument("--output", type=str, required=True)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    input_path = os.path.abspath(args.input)
    output_path = os.path.abspath(args.output)
    
    # The parent directory of the output file (e.g., $OUTPUT_DIR)
    base_output_dir = os.path.dirname(output_path)
    if base_output_dir and not os.path.exists(base_output_dir):
        os.makedirs(base_output_dir, exist_ok=True)

    # Define debug subdirectories inside the output folder
    debug_dirs = None
    if SAVE_DEBUG_FILES:
        debug_dirs = {
            'html': os.path.join(base_output_dir, "debug_filtered_html"),
            'md': os.path.join(base_output_dir, "debug_cleaned_md")
        }
        for d in debug_dirs.values():
            os.makedirs(d, exist_ok=True)

    if os.path.isfile(input_path):
        with open(output_path, "w", encoding="utf-8") as fout:
            process_file_logic(input_path, fout, args.verbose, debug_dirs)
    elif os.path.isdir(input_path):
        jsonl_files = [os.path.join(input_path, f) for f in os.listdir(input_path) if f.endswith(".jsonl")]
        with open(output_path, "w", encoding="utf-8") as fout:
            for f in jsonl_files:
                process_file_logic(f, fout, args.verbose, debug_dirs)

    print(f"\nProcessing complete. Output: {output_path}")

if __name__ == "__main__":
    main()