import requests
from bs4 import BeautifulSoup
import json
import time
import re
from datetime import datetime
import argparse

SOURCE_URL = "https://portale.units.it/it/rubrica"
BASE_URL = "https://portale.units.it/it/views/ajax"

OUTPUT_FILE = "units_book.json"
DELAY = 0.15
MAX_RETRIES = 5
RETRY_WAIT = 10


def get_session_data():
    """Fetches the main page and extracts view_dom_id, libraries string, and total pages."""
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0"})
    resp = session.get(SOURCE_URL)
    soup = BeautifulSoup(resp.text, "html.parser")

    # Extract view_dom_id from the drupalSettings JSON embedded in the page
    script_tag = soup.find("script", string=re.compile("views_dom_id"))
    settings = json.loads(script_tag.string)
    ajax_views = settings["views"]["ajaxViews"]
    # Find the rubrica view specifically
    dom_id = next(
        v["view_dom_id"]
        for v in ajax_views.values()
        if v.get("view_name") == "rubrica"
    )

    # Extract the libraries string from ajaxPageState
    libraries = settings["ajaxPageState"]["libraries"]

    # Extract total pages
    last_link = soup.select_one("a[title='Go to last page']")
    total_pages = int(last_link["href"].split("=")[-1]) if last_link else None

    return session, dom_id, libraries, total_pages


def parse_page(html):
    soup = BeautifulSoup(html, "html.parser")
    people = []
    for card in soup.select(".rubrica__wrapper"):
        name  = card.select_one(".rubrica__name")
        role  = card.select_one(".rubrica__role.rubrica-bold")
        dept  = card.select_one(".rubrica-sede a")
        phone = card.select_one(".rubrica__phone a")
        email = card.select_one(".rubrica__email a")

        # Build absolute URL if href exists
        dept_href = dept.get("href", "") if dept else ""
        if dept_href and dept_href.startswith("/"):
            dept_href = "https://portale.units.it" + dept_href
        
        people.append({
            "name":       name.get_text(strip=True)  if name  else "",
            "role":       role.get_text(strip=True)  if role  else "",
            "department": dept.get_text(strip=True)  if dept  else "",
            "department_staff_url":   dept_href,
            "phone":      phone.get_text(strip=True) if phone else "",
            "email":      email.get_text(strip=True) if email else "",
        })
    return people


def save_data(people_list):
    output_data = {
        "title": "Units Institute Staff Address Book",
        "url": SOURCE_URL,
        "timestamp": datetime.now().strftime("%d/%m/%Y"),
        "entries": people_list
    }
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=4, ensure_ascii=False)


def process_page(session, page, total, dom_id, libraries):
    params = {
        "_wrapper_format": "drupal_ajax",
        "view_name": "rubrica",
        "view_display_id": "page_1",
        "view_args": "",
        "view_path": "/rubrica",
        "view_base_path": "rubrica",
        "view_dom_id": dom_id,
        "pager_element": "0",
        "page": str(page),
        "_drupal_ajax": "1",
        "ajax_page_state[theme]": "units_base",
        "ajax_page_state[theme_token]": "",
        "ajax_page_state[libraries]": libraries,
    }

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = session.get(BASE_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

            html = next(
                cmd["data"] for cmd in data
                if cmd.get("command") == "insert" and cmd.get("method") == "replaceWith"
            )
            people = parse_page(html)
            print(f"Page {page}/{total} -> {len(people)} people")
            return people

        except Exception as e:
            print(f"Page {page}, attempt {attempt}/{MAX_RETRIES} failed: {e}")
            if attempt < MAX_RETRIES:
                wait = RETRY_WAIT * attempt
                print(f"Waiting {wait}s...")
                time.sleep(wait)

    print(f"Page {page} permanently failed, skipping.")
    return []


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Script used to extract the Units Institute staff address book.")
    parser.add_argument("-o", "--output", type=str, help="Output file for the extracted data.", default=OUTPUT_FILE)
    args = parser.parse_args()
    if args.output:
        OUTPUT_FILE = args.output
    else:
        print("No output file specified. Using default: units_book.json")

    session, dom_id, libraries, total = get_session_data()
    total = 5
    print(f"Total pages: {total}. Saving to {OUTPUT_FILE}")

    all_people = []
    for page in range(0, total + 1):
        people = process_page(session, page, total, dom_id, libraries)
        all_people.extend(people)
        time.sleep(DELAY)

    print(f"Done. Total records: {len(all_people)}")
    save_data(all_people)