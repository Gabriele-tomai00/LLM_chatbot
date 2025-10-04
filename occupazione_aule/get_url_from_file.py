import time
import os
import shutil
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import Select
from joblib import Parallel, delayed
from datetime import datetime
import json
import multiprocessing
import logging
import requests
import json
import re
from urllib.parse import urlencode
from datetime import datetime, timedelta
URL_sedi = "https://orari.units.it/agendaweb/combo.php?sw=rooms_"
URL_FORM = "https://orari.units.it/agendaweb/index.php?view=rooms&include=rooms&_lang=it"

def write_json_to_file(nome_file, nuovo_contenuto):
    data = []
    # Se il file esiste e non è vuoto, carico i dati
    if os.path.exists(nome_file) and os.path.getsize(nome_file) > 0:
        with open(nome_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    
    # Mi assicuro che sia una lista
    if not isinstance(data, list):
        raise ValueError("Il JSON esistente non è una lista, impossibile fare append.")

        # Aggiungo il nuovo contenuto (può essere dict o lista di dict)
    if isinstance(nuovo_contenuto, list):
        data = nuovo_contenuto + data  # nuovi elementi prima
    else:
        data = [nuovo_contenuto] + data
        
    # Riscrivo il file
    with open(nome_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def iterate_dates(start_date, end_date):
    def parse_date(d):
        if "/" in d:
            return datetime.strptime(d, "%d/%m/%Y")
        elif "-" in d:
            return datetime.strptime(d, "%d-%m-%Y")
        else:
            raise ValueError("Formato data non valido")
    
    current = parse_date(start_date)
    end = parse_date(end_date)
    
    while current <= end:
        yield current.strftime("%d/%m/%Y")
        current += timedelta(days=1)

def get_file_with_info():
    resp = requests.get(URL_sedi)
    resp.raise_for_status()
    return resp.text

def get_sedi(text):
    match = re.search(r"var\s+elenco_sedi\s*=\s*(\[.*?\])\s*;", text, re.S)
    if not match:
        raise ValueError("Nessun elenco_aule trovato")
    elenco_json = match.group(1)
    elenco_sedi = json.loads(elenco_json)
    for sede in elenco_sedi:
        if 'valore' in sede:
            sede['value'] = sede.pop('valore')  # rinomina la chiave

    return elenco_sedi


def get_aule(text, sede):
    # cattura l'oggetto JSON tra graffe
    match_aule = re.search(r"var elenco_aule = (\{.*?\});", text, re.S)
    if not match_aule:
        raise ValueError("Nessun elenco_aule trovato")

    elenco_json = match_aule.group(1)
    elenco_aule = json.loads(elenco_json)

    # estrai solo le aule della sede richiesta
    if sede not in elenco_aule:
        raise ValueError(f"Sede '{sede}' non trovata")

    aule_sede = elenco_aule[sede]
    return aule_sede

def check_date(date_str):
    for fmt in ("%d/%m/%Y", "%d-%m-%Y"):
        try:
            input_date = datetime.strptime(date_str, fmt)
            break
        except ValueError:
            continue
    else:
        raise ValueError("Formato data non valido. Usa dd/mm/yyyy o dd-mm-yyyy.")

    target_date = datetime(2026, 1, 20)

    return input_date < target_date


def response_filter(data):
    chiavi_evento = [
        "room", "NomeAula", "CodiceAula",
        "NomeSede", "CodiceSede", "name",
        "utenti", "orario"
    ]
    if "events" in data:
        filtered_events = [
            {k: event[k] for k in chiavi_evento if k in event}
            for event in data["events"]
        ]
    return filtered_events


def add_keys_and_reorder(filtered_data, sedi, aule, payload):
    filtered_data["sede"] = sedi[0]['label']
    filtered_data["codice_sede"] = sedi[0]['value']
    ordered_data = {
        "sede": sedi[0]['label'],
        "codice_sede": sedi[0]['value'],
        "aula": aule[2]['label'],
        "codice_aula": aule[2]['valore'],
        "data_settimana": filtered_data["data_settimana"],
        "url": build_units_url(payload),
        **filtered_data
    }
    return ordered_data

def build_units_url(payload):
    query_string = urlencode(payload, doseq=True)
    separator = "&" if "?" in URL_FORM else "?"
    full_url = URL_FORM + separator + query_string
    return full_url

def create_payload(sede_code, aula_value, data_settimana):
    try:
        sede = sede_code
        valore_aula = aula_value
    except Exception as e:
        print(f"Errore nel parsing del json: {e}")
        return
    
    payload = {
        "form-type": "rooms",
        "view": "rooms",
        "include": "rooms",
        "aula": "",
        "sede_get[]": [sede],
        "sede[]": [sede],
        "aula[]": [valore_aula],
        "date": data_settimana,
        "_lang": "it",
        "list": "",
        "week_grid_type": "-1",
        "ar_codes_": "",
        "ar_select_": "",
        "col_cells": "0",
        "empty_box": "0",
        "only_grid": "0",
        "highlighted_date": "0",
        "all_events": "0"
    }
    return payload

def get_response(payload):
    url = "https://orari.units.it/agendaweb/rooms_call.php"
    headers = {
        "User-Agent": "UNITS Links Crawler (network lab)",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
        "Origin": "https://orari.units.it",
        "Referer": "https://orari.units.it/agendaweb/index.php"
    }
    response = requests.post(url, data=payload, headers=headers)
    response.raise_for_status()
    try:
        data = response.json()
        return data
    except json.JSONDecodeError:
        #print(response.text)
        return None
    
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
    
def create_day_schedules_json(data):
    return

if __name__ == "__main__":
    start_datetime = datetime.now()
    start_time = time.time()
    directory = "response_json_files"
    try:
        shutil.rmtree(directory)
    except:
        pass
    os.makedirs(directory, exist_ok=True)

    logging.basicConfig(level=logging.INFO)
    data = get_file_with_info()
    sedi = get_sedi(data)
    for sede in sedi:
        aulee = get_aule(data, sedi[0]['value'])
        for aula in aulee:
            print(f"----- Aula: {aula['label']} - Codice: {aula['valore']}")
            json_data = {}
            json_data["sede"] = sedi[0]['label']
            json_data["codice_sede"] = sedi[0]['value']
            json_data["aula"] = aula['label']
            json_data["codice_aula"] = aula['valore']
            json_data["calendario"] = []

            data_inizio = "5-10-2025"
            data_fine = "6-10-2025"

            for giorno_settimana in iterate_dates(data_inizio, data_fine):
                json_filtered = {}
                json_filtered["data_settimana"] = giorno_settimana
                # print(f"Giorno preciso: {giorno_settimana}")
                payload = create_payload(sedi[0]['value'], aula['valore'], giorno_settimana)
                response_data = get_response(payload)
                json_filtered["eventi"] = response_filter(response_data)
                json_data["calendario"].append(json_filtered)
            # print(json.dumps(json_data, indent=4, ensure_ascii=False))
            # per salvare su file
            nome_file = os.path.join(directory, f"{sede["value"]}---{aula["valore"]}---{data_inizio}_to_{data_fine}.json")
            with open(nome_file, "w", encoding="utf-8") as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
   
    print("time taken:", format_time(time.time() - start_time))


