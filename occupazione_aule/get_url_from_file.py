import time
import os
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

URL_sedi = "https://orari.units.it/agendaweb/combo.php?sw=rooms_"
URL_FORM = "https://orari.units.it/agendaweb/index.php?view=rooms&include=rooms&_lang=it"

    
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
        "from", "to", "room", "NomeAula", "CodiceAula",
        "NomeSede", "CodiceSede", "name", "Prenotante_data",
        "utenti", "orario"
    ]
    chiavi_esterne = ["day"]

    filtered_data = {}

    # 🔹 Mantiene le chiavi esterne se esistono
    for key in chiavi_esterne:
        if key in data:
            filtered_data[key] = data[key]

    # 🔹 Filtra gli eventi se la chiave esiste
    if "events" in data:
        filtered_events = [
            {k: event[k] for k in chiavi_evento if k in event}
            for event in data["events"]
        ]
        filtered_data["eventi"] = filtered_events
        
    return filtered_data


def add_keys_and_reorder(filtered_data, sedi, aule, payload):
    filtered_data["sede"] = sedi[0]['label']
    filtered_data["codice_sede"] = sedi[0]['value']

    ordered_data = {
        "sede": sedi[0]['label'],
        "codice_sede": sedi[0]['value'],
        "aula": aule[2]['label'],
        "codice_aula": aule[2]['valore'],
        "url": build_units_url(payload),
        **filtered_data
    }
    return ordered_data

def build_units_url(payload):
    query_string = urlencode(payload, doseq=True)
    separator = "&" if "?" in URL_FORM else "?"
    full_url = URL_FORM + separator + query_string
    return full_url

def create_payload(info_room):
    try:
        sede = info_room["sede_code"]
        data_settimana = info_room["data_settimana"]
        valore_aula = info_room["valore"]
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

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    data = get_file_with_info()
    sedi = get_sedi(data)
    if not sedi:
        logging.error("Nessuna sede trovata, impossibile proseguire con il crowling del calendario delle aule")
        exit(1)

    aule = get_aule(data, sedi[0]['value'])
    aule[2]["data_settimana"] = "15/10/2025"
    payload = create_payload(aule[2])
    data = get_response(payload)
    filtered_data = response_filter(data)
    final_json = add_keys_and_reorder(filtered_data, sedi, aule, payload)

    # per salvare su file
    with open("response.json", "w", encoding="utf-8") as f:
        json.dump(final_json, f, indent=4, ensure_ascii=False)


