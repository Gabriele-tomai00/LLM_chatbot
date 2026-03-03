from operator import truediv
import requests
import json
import argparse
from datetime import datetime
import os

from torch.storage import T

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
            ordered_attrs = {}

            # Define priority fields mapping (internal key: source key)
            fields_to_process = [
                ("nome insegnamento", "NOME_INS"),
                ("nome insegnamento in inglese", "NOME_INS_ENG"),
                ("codice insegnamento", "AF_GEN_COD"),
                ("codice teams", "JCD_O365"),
                ("nome corso di studi", "NOME_CORSO"),
                ("nome corso di studi in inglese", "NOME_CORSO_ENG"),
                ("codice corso di studi", "CDS_COD"),
                ("anno accademico", "ANNO_ACCADEMICO"),
                ("docente", "DOCENTE"),
                ("periodo (semestre o quadrimestre)", "PERIODO_COD")
            ]

            for label, key in fields_to_process:
                if key in attrs:
                    val = attrs.pop(key)
                    # Check for empty strings or empty dictionaries
                    if val == "" or val == {}:
                        ordered_attrs[label] = "N/A"
                    else:
                        ordered_attrs[label] = val
                else:
                    # If the key is missing entirely from the source attributes
                    ordered_attrs[label] = "N/A"

            # Remove unwanted fields
            attrs.pop("URL_O365", None)
            attrs.pop("AF_ID", None)

            # Process remaining fields in attrs
            for k, v in attrs.items():
                if v == "" or v == {}:
                    ordered_attrs[k] = "N/A"
                else:
                    ordered_attrs[k] = v
        
            new_data.append(ordered_attrs)
    return new_data

def save_to_json(data, output_path):
    """Saves data in structured JSON format with N/A for empty fields."""
    output_data = {
        "title": "Teams Codes",
        "timestamp": datetime.now().strftime("%d/%m/%Y"),
        "URL for users": "https://www.units.it/catalogo-della-didattica-a-distanza",
        "codes": data
    }
    
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    print(f"Data successfully saved to JSON: {output_path}")

def save_to_txt(data, output_path):
    """Saves data in a plain text format optimized for RAG."""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"title: Teams Codes - University of Trieste\n")
        f.write(f"date: {datetime.now().strftime('%d/%m/%Y')}\n")
        f.write(f"source: https://www.units.it/catalogo-della-didattica-a-distanza\n")
        f.write("-" * 30 + "\n\n")

        for entry in data:
            for key, value in entry.items():
                # Keys and values are already cleaned by process_data
                f.write(f"{key}: {value}\n")
            f.write("\n")
            
    print(f"Data successfully saved to TXT: {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download Teams codes from UNITS")
    parser.add_argument("-o", "--output", help="Output file path (without extension)")    
    args = parser.parse_args()

    USE_JSON = True 

    print("Downloading data...")
    try:
        raw_data = download_data()
        print(f"Downloaded {len(raw_data)} records.")
        
        processed_data = process_data(raw_data)
        
        # Determine base path and file name
        base_path = args.output if args.output else "teams_codes"
        path_no_ext = os.path.splitext(base_path)[0]

        if USE_JSON:
            save_to_json(processed_data, f"{path_no_ext}.json")
        else:
            save_to_txt(processed_data, f"{path_no_ext}.txt")
            
    except Exception as e:
        print(f"An error occurred: {e}")