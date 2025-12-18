import os
import requests
from tqdm import tqdm
from MagicConvert import MagicConvert
from os import path, makedirs
from shutil import rmtree
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed

pdf_links_file = "results/pdf_links.txt"
output_dir_filtered = "results/original_pdf_downloaded/"
output_dir_cleaned = "results/cleaned_pdf_output/"

def download_pdf(link, output_dir):
    try:
        filename = link.split("/")[-1]
        pdf_path = os.path.join(output_dir, filename)

        r = requests.get(link, timeout=20)
        r.raise_for_status()

        with open(pdf_path, "wb") as f:
            f.write(r.content)

        return (link, None)

    except Exception as e:
        return (link, e)

def download_all_pdfs(links, output_dir, max_workers=10):
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(download_pdf, link, output_dir): link for link in links}

        for future in tqdm(as_completed(futures), total=len(futures), desc="Downloading PDFs", unit="file"):
            link = futures[future]
            link, error = future.result()
            if error:
                print(f"Failed to download {link}: {error}")

    print("Download completed.")

def convert_pdf(pdf_path, output_dir):
    try:
        converter = MagicConvert()
        result = converter.magic(pdf_path)

        out_path = os.path.join(
            output_dir,
            os.path.basename(pdf_path).replace(".pdf", ".md")
        )
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(result.text_content)

        return (pdf_path, None)

    except Exception as e:
        return (pdf_path, e)

def convert_all_pdfs_parallel(pdf_files, input_dir, output_dir, max_workers=4):
    """Convert multiple PDFs in parallel, skipping errors."""
    os.makedirs(output_dir, exist_ok=True)
    failed_files = []

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                convert_pdf,
                os.path.join(input_dir, pdf_file),
                output_dir
            ): pdf_file
            for pdf_file in pdf_files
        }

    print("Conversion completed.")
    if failed_files:
        print(f"Failed to convert {len(failed_files)} PDFs.")


if __name__ == "__main__":
    if path.exists(output_dir_filtered) and path.isdir(output_dir_filtered):
        rmtree(output_dir_filtered)
    if path.exists(output_dir_cleaned) and path.isdir(output_dir_cleaned):
        rmtree(output_dir_cleaned)

    os.makedirs(output_dir_filtered, exist_ok=True)
    os.makedirs(output_dir_cleaned, exist_ok=True)

    with open(pdf_links_file, "r") as f:
        links = [line.strip() for line in f if line.strip()]

    download_all_pdfs(links, output_dir_filtered, max_workers=10)

    pdf_files = [f for f in os.listdir(output_dir_filtered) if f.lower().endswith(".pdf")]
    convert_all_pdfs_parallel(pdf_files, output_dir_filtered, output_dir_cleaned, max_workers=4)
