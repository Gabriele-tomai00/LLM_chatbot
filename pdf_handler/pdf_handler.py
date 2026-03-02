import os
import requests
from tqdm import tqdm
from MagicConvert import MagicConvert
from os import path, makedirs
from shutil import rmtree
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
import argparse
import re
from urllib.parse import unquote
import time
from datetime import datetime


pdf_links_file = "results/pdf_links.txt"
output_dir_filtered = "results/original_pdf_downloaded/"
output_dir_cleaned = "results/cleaned_pdf_output/"

def download_pdf(link, output_dir):
    try:
        filename = link.split("/")[-1]
        pdf_path = os.path.join(output_dir, filename)
        if is_file_before_year(filename, cutoff_year=2024):
            return (link, f"Skipped (before 2024): {filename}")

        r = requests.get(link, timeout=20)
        r.raise_for_status()
        if not r.content.startswith(b"%PDF"):
            return (link, "Invalid PDF header")


        with open(pdf_path, "wb") as f:
            f.write(r.content)

        return (link, None)

    except Exception as e:
        return (link, e)

def download_all_pdfs(links, output_dir, max_workers=20):
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(download_pdf, link, output_dir): link for link in links}

        for future in tqdm(as_completed(futures), total=len(futures), desc="Downloading PDFs", unit="file"):
            link = futures[future]
            link, error = future.result()
            if error:
                print(f"Failed to download {link}: {error}")

    print("Download completed.")


def is_valid_pdf(path):
    try:
        with open(path, "rb") as f:
            return f.read(4) == b"%PDF"
    except OSError:
        return False

def convert_pdf(pdf_path, output_dir):
    try:
        if not is_valid_pdf(pdf_path):
            return (pdf_path, "Invalid PDF header")

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
        return (pdf_path, repr(e))


def convert_all_pdfs_parallel(pdf_files, input_dir, output_dir, max_workers=4):
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

        for future in tqdm(as_completed(futures), total=len(futures), desc="Converting PDFs", unit="file"):
            pdf_file = futures[future]
            try:
                result = future.result()
            except Exception as e:
                print(f"Worker crashed on {pdf_file}: {e}")
                failed_files.append(pdf_file)
                continue

            pdf_path, error = result
            if error:
                print(f"Failed to convert {pdf_file}: {error}")
                failed_files.append(pdf_file)



def is_file_before_year(filepath, cutoff_year=2024):
    """
    Evaluates if a PDF file concerns events that occurred before a specified cutoff year.
    Returns True if the file appears to refer to dates before the cutoff year, False otherwise.
    
    Args:
        filepath: Path or URL of the file
        cutoff_year: Year threshold (default: 2024). Files before this year are excluded.
    
    Returns:
        bool: True if to exclude (event before cutoff_year), False otherwise
    """
    # Extract filename from path
    filename = unquote(filepath.split('/')[-1])
    
    # Remove .pdf extension (case insensitive)
    filename_without_ext = re.sub(r'\.pdf$', '', filename, flags=re.IGNORECASE)
    
    # Patterns to find years (4 consecutive digits)
    year_patterns = [
        r'\b(20\d{2})\b',           # years 2000-2099 isolated
        r'(20\d{2})[-._]',          # years with separators at the beginning
        r'[-._](20\d{2})[-._]',     # years with separators in the middle
        r'[-._](20\d{2})\b',        # years with separators at the end
        r'(20\d{2})[A-Za-z]',       # years followed by letters
        r'[A-Za-z](20\d{2})\b'      # years preceded by letters
    ]
    
    years_found = []
    
    for pattern in year_patterns:
        matches = re.findall(pattern, filename_without_ext)
        if matches:
            for match in matches:
                if isinstance(match, tuple):
                    # If pattern has capture groups
                    for m in match:
                        if m.isdigit():
                            year = int(m)
                            if 2000 <= year <= 2099:
                                years_found.append(year)
                elif match.isdigit():
                    year = int(match)
                    if 2000 <= year <= 2099:
                        years_found.append(year)
    
    # Remove duplicates while maintaining order
    years_found = list(dict.fromkeys(years_found))
    
    # If no years found, consider file undated
    if not years_found:
        return False  # Don't exclude files without clear dates
    
    # Check for complete date patterns
    date_patterns = [
        r'(20\d{2})[-._](\d{1,2})[-._](\d{1,2})',  # YYYY-MM-DD or YYYY.MM.DD
        r'(\d{1,2})[-._](\d{1,2})[-._](20\d{2})',  # DD-MM-YYYY
        r'(20\d{2})[-._](\d{1,2})',               # YYYY-MM (year-month only)
    ]
    
    for pattern in date_patterns:
        matches = re.findall(pattern, filename_without_ext)
        if matches:
            for match in matches:
                try:
                    if len(match[0]) == 4:  # YYYY-MM-DD or YYYY-MM
                        year = int(match[0])
                        if year < cutoff_year:
                            return True
                    elif len(match[2]) == 4:  # DD-MM-YYYY
                        year = int(match[2])
                        if year < cutoff_year:
                            return True
                except (ValueError, IndexError):
                    continue
    
    # Check if year might be part of version or code
    version_keywords = ['versione', '_v', ' vers', ' v[0-9]', 'rev', 'r[0-9]']
    
    for year in years_found:
        year_str = str(year)
        year_pos = filename_without_ext.find(year_str)
        if year_pos >= 0:
            start = max(0, year_pos - 10)
            context_before = filename_without_ext[start:year_pos].lower()
            
            is_version = False
            for keyword in version_keywords:
                if keyword in context_before:
                    is_version = True
                    break
            
            if is_version and year < cutoff_year and len(years_found) > 1:
                continue  # Ignore this year, check others
            
            if is_version and year < cutoff_year and len(years_found) == 1:
                return False  # Probably not an event year
    
    # Take the most recent year found
    latest_year = max(years_found)
    
    # If most recent year is before cutoff year, exclude file
    if latest_year < cutoff_year:
        return True
    
    return False

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

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download and/or convert PDFs")
    parser.add_argument("--download", action="store_true", help="Download PDFs from links")
    parser.add_argument("--convert", action="store_true", help="Convert downloaded PDFs to markdown")
    args = parser.parse_args()

    start_time = datetime.now()

    if args.download:
        if path.exists(output_dir_filtered) and path.isdir(output_dir_filtered):
            rmtree(output_dir_filtered)
            print(f"Removed existing directory: {output_dir_filtered}")
        os.makedirs(output_dir_filtered, exist_ok=True)
        
        with open(pdf_links_file, "r") as f:
            links = [line.strip() for line in f if line.strip()]
        download_all_pdfs(links, output_dir_filtered, max_workers=10)

    if args.convert:
        if path.exists(output_dir_cleaned) and path.isdir(output_dir_cleaned):
            rmtree(output_dir_cleaned)
            print(f"Removed existing directory: {output_dir_cleaned}")
        os.makedirs(output_dir_cleaned, exist_ok=True)

        pdf_files = [f for f in os.listdir(output_dir_filtered) if f.lower().endswith(".pdf")]
        convert_all_pdfs_parallel(pdf_files, output_dir_filtered, output_dir_cleaned, max_workers=4)

    end_time = datetime.now()
    print("End time:", end_time.strftime("%H:%M:%S"))
    elapsed = (end_time - start_time).total_seconds()
    print(f"Process completed in {format_time(elapsed)}")
