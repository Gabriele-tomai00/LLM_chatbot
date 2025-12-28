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

# set to False for massive processing on huge files
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
        "footer-container", "links"
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

        # per debug solo quando necessario
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


def process_file(input_file: str, output_file: str, verbose: bool):
    logging.basicConfig(format="%(levelname)s - %(message)s", level=logging.WARNING)

    max_workers = min(8, multiprocessing.cpu_count())
    saved = 0
    skipped = 0

    with open(input_file, "r", encoding="utf-8") as fin, \
         open(output_file, "w", encoding="utf-8") as fout, \
         ProcessPoolExecutor(max_workers=max_workers) as executor:

        for result in tqdm(executor.map(process_line, fin, chunksize=500),
                           desc=f"Processing {os.path.basename(input_file)}", mininterval=1):

            if not result:
                skipped += 1
                continue

            item, status = result
            if status == "saved" and item:
                fout.write(json.dumps(item, ensure_ascii=False) + "\n")
                saved += 1
                if verbose:
                    tqdm.write(f"SAVED: {item.get('url', '')}")
            else:
                skipped += 1

    print(f"Completed {os.path.basename(input_file)}: Saved {saved}, Skipped {skipped}")


def main(input_path: str, output_path: str, verbose: bool):
    if os.path.isfile(input_path):
        # single file
        if os.path.exists(output_path) and not os.path.isdir(output_path):
            raise ValueError(f"Output path {output_path} esiste ed è un file, deve essere una cartella.")
        os.makedirs(output_path, exist_ok=True)
        out_file = os.path.join(output_path, os.path.basename(input_path))
        process_file(input_path, out_file, verbose)

    elif os.path.isdir(input_path):
        # dir: process all .jsonl files inside
        if os.path.exists(output_path) and not os.path.isdir(output_path):
            raise ValueError(f"Output path {output_path} esiste ed è un file, deve essere una cartella.")
        os.makedirs(output_path, exist_ok=True)
        jsonl_files = [f for f in os.listdir(input_path) if f.endswith(".jsonl")]
        if not jsonl_files:
            print(f"Nessun file .jsonl trovato in {input_path}")
            return
        for f in jsonl_files:
            in_file = os.path.join(input_path, f)
            out_file = os.path.join(output_path, f)
            process_file(in_file, out_file, verbose)

    else:
        raise FileNotFoundError(f"Input path {input_path} non trovato.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str, required=True)
    parser.add_argument("--output", type=str, required=True)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    main(args.input, args.output, args.verbose)
