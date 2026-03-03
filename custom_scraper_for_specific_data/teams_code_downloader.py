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
            ordered_attrs = {}

            # Add priority fields
            if "NOME_INS" in attrs:
                ordered_attrs["nome insegnamento"] = attrs.pop("NOME_INS")

            if "NOME_INS_ENG" in attrs:
                ordered_attrs["nome insegnamento in inglese"] = attrs.pop("NOME_INS_ENG")

            # already in "nome insegnamento"
            # if "AF_GEN_COD" in attrs:
            #     ordered_attrs["codice ingegnamento"] = attrs.pop("AF_GEN_COD")

            if "JCD_O365" in attrs:
                ordered_attrs["codice teams"] = attrs.pop("JCD_O365")
            
            if "NOME_CORSO" in attrs:
                ordered_attrs["nome corso di studi"] = attrs.pop("NOME_CORSO")

            if "NOME_CORSO_ENG" in attrs:
                ordered_attrs["nome corso di studi in inglese"] = attrs.pop("NOME_CORSO_ENG")
            
            # already in "nome corso di studi"
            # if "CDS_COD" in attrs:
            #     ordered_attrs["codice corso di studi"] = attrs.pop("CDS_COD")

            if "ANNO_ACCADEMICO" in attrs:
                ordered_attrs["anno accademico"] = attrs.pop("ANNO_ACCADEMICO")
                
            if "DOCENTE" in attrs:
                ordered_attrs["docente"] = attrs.pop("DOCENTE")

            if "PERIODO_COD" in attrs:
                ordered_attrs["periodo (semestre o quadrimestre)"] = attrs.pop("PERIODO_COD")      

            # Remove unwanted fields
            if "URL_O365" in attrs:
                attrs.pop("URL_O365")
            if "AF_ID" in attrs: # used for DB (for deveolper)
                attrs.pop("AF_ID")
            if "AF_GEN_COD" in attrs:
                attrs.pop("AF_GEN_COD")
            if "CDS_COD" in attrs:
                attrs.pop("CDS_COD")

            # Add remaining fields
            ordered_attrs.update(attrs)
        
            new_data.append(ordered_attrs)
    return new_data


def save_to_json(data, output_path):
    output_data = {
        "title": "Teams Codes",
        "timestamp": datetime.now().strftime("%d/%m/%Y"),
        "URL for users": "https://www.units.it/catalogo-della-didattica-a-distanza",
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
