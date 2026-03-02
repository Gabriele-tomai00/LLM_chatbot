import requests
import json
import argparse
from datetime import datetime
import os

URL = "https://spweb.units.it/jsonapi/static/dad_grp.json"

# Download and load JSON
def download_data():
    response = requests.get(URL)
    response.raise_for_status()
    # The API returns a dict with a "data" key which contains the list
    return response.json().get("data", [])

def process_data(data):
    new_data = []
    for item in data:
        if "attributes" in item:
            attrs = item["attributes"]
            if "NOME_INS" in attrs:
                attrs["NOME_INSEGNAMENTO"] = attrs.pop("NOME_INS")
            
            if "NOME_INS_ENG" in attrs:
                attrs["NOME_INGLESE_INSEGNAMENTO"] = attrs.pop("NOME_INS_ENG")
            
            if "PERIODO_COD" in attrs:
                attrs["PERIODO"] = attrs.pop("PERIODO_COD")

            if "JCD_O365" in attrs:
                attrs["CODICE_TEAMS"] = attrs.pop("JCD_O365")
        
        new_data.append(attrs)
    return new_data

# Search functions
def search_by_course_name(data, keyword):
    return [
        item for item in data
        if keyword.lower() in item["attributes"]["NOME_INSEGNAMENTO"].lower()
    ]

def search_by_teacher(data, name):
    return [
        item for item in data
        if name.lower() in item["attributes"]["DOCENTE"].lower()
    ]

def search_by_course_code(data, course_code):
    return [
        item for item in data
        if course_code.lower() in item["attributes"]["CDS_COD"].lower()
    ]

def save_to_json(data, output_path):
    output_data = {
        "title": "Teams Codes",
        "timestamp": datetime.now().strftime("%d/%m/%Y"),
        "URL": URL,
        "codes": data
    }
    
    # Ensure the directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        print(f"Data successfully saved to {output_path}")
    except IOError as e:
        print(f"Error saving file: {e}")

if __name__ == "__main__":
    # exemple: python3 teams_code_downloader.py -o teams_codes.json
    parser = argparse.ArgumentParser(description="Download Teams codes from UNITS")
    parser.add_argument("-o", "--output", help="Output file path for the JSON data")    
    args = parser.parse_args()
    
    print("Downloading data...")
    try:
        data = download_data()
        print(f"Downloaded {len(data)} records.")
        
        data = process_data(data)
        
        if args.output:
            save_to_json(data, args.output)
            
    except Exception as e:
        print(f"An error occurred: {e}")
