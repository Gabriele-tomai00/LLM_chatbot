import os
import requests
from tqdm import tqdm
from MagicConvert import MagicConvert
from os import path, makedirs
from shutil import rmtree

pdf_links_file = "results/pdf_links.txt"
output_dir_filtered = "results/filtered_pdf_output/"
output_dir_cleaned = "results/cleaned_pdf_output/"

if path.exists(output_dir_filtered) and path.isdir(output_dir_filtered):
    rmtree(output_dir_filtered)
if path.exists(output_dir_cleaned) and path.isdir(output_dir_cleaned):
    rmtree(output_dir_cleaned)

os.makedirs(output_dir_filtered, exist_ok=True)
os.makedirs(output_dir_cleaned, exist_ok=True)

with open(pdf_links_file, "r") as f:
    links = [line.strip() for line in f if line.strip()]

# 1: DOWNLOAD PDFS
for link in tqdm(links, desc="Downloading PDFs", unit="file"):
    try:
        filename = link.split("/")[-1]
        pdf_path = os.path.join(output_dir_filtered, filename)

        response = requests.get(link)
        response.raise_for_status()
        with open(pdf_path, "wb") as pdf_file:
            pdf_file.write(response.content)

    except Exception as e:
        print(f"Failed to download {link}: {e}")


# 2: PDF TO MD
converter = MagicConvert()
pdf_files = [f for f in os.listdir(output_dir_filtered) if f.lower().endswith(".pdf")]

for pdf_file in tqdm(pdf_files, desc="Converting PDFs", unit="file"):
    pdf_path = os.path.join(output_dir_filtered, pdf_file)
    try:
        result = converter.magic(pdf_path)
        cleaned_md_path = os.path.join(output_dir_cleaned, pdf_file.replace(".pdf", ".md"))
        with open(cleaned_md_path, "w", encoding="utf-8") as md_file:
            md_file.write(result.text_content)

    except Exception as e:
        print(f"Failed to convert {pdf_file}: {e}")