import time
import os
import shutil
import sys
from joblib import Parallel, delayed
from datetime import datetime
import json
import multiprocessing
import requests
import json
import re
from urllib.parse import urlencode
from datetime import datetime, timedelta
from collections import defaultdict

def print_title(start_time, data_inizio, data_fine):
    print(r"""
   ____                   _ _                         _                _            _                     _        _   _ _   _ ___ _____ ____  
  / ___|_ __ _____      _| (_)_ __   __ _    ___ __ _| | ___ _ __   __| | __ _ _ __(_) ___     __ _ _   _| | ___  | | | | \ | |_ _|_   _/ ___| 
 | |   | '__/ _ \ \ /\ / / | | '_ \ / _` |  / __/ _` | |/ _ \ '_ \ / _` |/ _` | '__| |/ _ \   / _` | | | | |/ _ \ | | | |  \| || |  | | \___ \ 
 | |___| | | (_) \ V  V /| | | | | | (_| | | (_| (_| | |  __/ | | | (_| | (_| | |  | | (_) | | (_| | |_| | |  __/ | |_| | |\  || |  | |  ___) |
  \____|_|  \___/ \_/\_/ |_|_|_| |_|\__, |  \___\__,_|_|\___|_| |_|\__,_|\__,_|_|  |_|\___/   \__,_|\__,_|_|\___|  \___/|_| \_|___| |_| |____/ 
                                    |___/                                                                                                      
    """)

    formatted_time = time.strftime("%H:%M:%S", time.localtime(start_time))
    print(f"Script started at {formatted_time}")
    print(f"First date: {data_inizio}, last date: {data_fine}")
    print(f"Starting the process to get all room occupation URLs from orari.units.it...\n")

def write_json_to_file(content, dir, sede, data_inizio, data_fine):
    nome_file = os.path.join(dir, f"{sede}---{data_inizio}_to_{data_fine}.json")
    with open(nome_file, "w", encoding="utf-8") as f:
        json.dump(content, f, ensure_ascii=False, indent=2)

def convert_json_structure(percorso_file):
    with open(percorso_file, "r", encoding="utf-8") as f:
        dati = json.load(f)

    sedi_data = defaultdict(lambda: {
        "Nome sede": "",
        "Codice sede": "",
        "Aule": defaultdict(lambda: {
            "Nome aula": "",
            "Codice aula": "",
            "Eventi": []
        })
    })

    for evento in dati:
        codice_sede = evento.get("CodiceSede")
        nome_sede = evento.get("NomeSede")
        codice_aula = evento.get("CodiceAula")
        nome_aula = evento.get("NomeAula")
        ultimo_agg = evento.get("ultimo_aggiornamento", "")
        annullato = "no" if evento.get("Annullato", "0") == "0" else "si"
        corso = evento.get("name")
        giorno = evento.get("Giorno")
        orario = evento.get("orario", "")
        docente = evento.get("utenti", "")
        sede_entry = sedi_data[codice_sede]
        sede_entry["Nome sede"] = nome_sede
        sede_entry["Codice sede"] = codice_sede

        aula_entry = sede_entry["Aule"][codice_aula]
        aula_entry["Nome aula"] = nome_aula
        aula_entry["Codice aula"] = codice_aula

        evento_dict = {
            "data": giorno,
            "orario": orario,
            "corso": corso,
            "docente": docente,
            "Ultimo aggiornamento": ultimo_agg
        }
        if annullato == "si":
            evento_dict["annullato"] = annullato

        aula_entry["Eventi"].append(evento_dict)

    sedi_array = []
    for codice_sede, sede_entry in sedi_data.items():
        sede_entry["Aule"] = list(sede_entry["Aule"].values())
        sedi_array.append(sede_entry)
    return sedi_array

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
    ultimo_aggiornamento = data.get("file_date", "")
    try:
        ultimo_aggiornamento = ultimo_aggiornamento.split(" ", 1)[0]
    except Exception:
        pass

    chiavi_evento = [
        "room", "NomeAula", "CodiceAula",
        "NomeSede", "CodiceSede", "name",
        "utenti", "orario", "Giorno", "Annullato"
    ]
    events = data.get("events", [])
    if not isinstance(events, list):
        raise ValueError("Il campo 'events' deve essere una lista")

    filtered_events = [
        {**{k: event[k] for k in chiavi_evento if k in event}, "ultimo_aggiornamento": ultimo_aggiornamento}
        for event in events
    ]
    # filtered_events = events

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
    separator = "&" if "?" in URL_PORTAL else "?"
    full_url = URL_PORTAL + separator + query_string
    return full_url

def create_payload(sede_code, data_settimana, aula_value="all"):    
    payload = {
        "form-type": "rooms",
        "view": "rooms",
        "include": "rooms",
        "aula": "",
        "sede_get[]": [sede_code],
        "sede[]": [sede_code],
        "aula[]": aula_value,
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


def get_response_from_request_with_payload(payload, retries=3, delay=1):
    url = "https://orari.units.it/agendaweb/rooms_call.php"
    headers = {
        "User-Agent": "UNITS Links Crawler (network lab)",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
        "Origin": "https://orari.units.it",
        "Referer": "https://orari.units.it/agendaweb/index.php"
    }

    for attempt in range(retries):
        try:
            response = requests.post(url, data=payload, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except (requests.ConnectionError, requests.Timeout) as e:
            print(f"[Retry {attempt+1}/{retries}] Errore di connessione: {e}")
            time.sleep(delay)
        except requests.RequestException as e:
            print(f"Errore HTTP non gestito: {e}")
            return None
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
    
from concurrent.futures import ThreadPoolExecutor, as_completed
 
def get_data(sede, data_inizio, data_fine):
    print(f"Processing sede: {sede['label']} ({sede['value']})...")
    final_json = []
    for giorno in iterate_dates(data_inizio, data_fine):
        payload = create_payload(sede["value"], giorno)
        response_data = get_response_from_request_with_payload(payload)
        if response_data is None:
            print(f"Failed to retrieve data for {sede['label']} on {giorno}. URL: {build_units_url(payload)}")
            continue
        if isinstance(response_data["events"], list) and not response_data["events"]:
            continue
        json_filtered = response_filter(response_data)
        with open("reponse.json", "w", encoding="utf-8") as f:
            json.dump(json_filtered, f, ensure_ascii=False, indent=2)

        final_json.extend(json_filtered)

    write_json_to_file(final_json, TEMP_DIR, sede['label'], data_inizio, data_fine)

    return final_json


if __name__ == "__main__":
    # Controlla quanti argomenti sono stati passati
    if len(sys.argv) > 2:
        data_inizio = sys.argv[1]
        data_fine = sys.argv[2]
    else:
        data_inizio = "6-11-2025"
        data_fine = "20-02-2026"

    start_datetime = datetime.now()
    start_time = time.time()
    print_title(start_time, data_inizio, data_fine)
    
    OUTPUT_DIR = "orario_aule_per_sede"
    TEMP_DIR = "." + OUTPUT_DIR + "_temp"
    URL_sedi_data = "https://orari.units.it/agendaweb/combo.php?sw=rooms_"
    URL_PORTAL = "https://orari.units.it/agendaweb/index.php?view=rooms&include=rooms&_lang=it"


    if os.path.exists(TEMP_DIR):
        shutil.rmtree(TEMP_DIR)
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(TEMP_DIR, exist_ok=True)
    os.remove("nomi_sedi.txt") if os.path.exists("nomi_sedi.txt") else None

    resp = requests.get(URL_sedi_data)
    resp.raise_for_status()
    data_from_units = resp.text

    sedi = get_sedi(data_from_units)
    # sedi = sedi[:2]  # per test, rimuovere per produzione

    num_cores = max(1, multiprocessing.cpu_count())
    final_json = Parallel(n_jobs=num_cores)(
        delayed(get_data)(sede, data_inizio, data_fine) for sede in sedi
    )

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    for file_name in os.listdir(TEMP_DIR):
        if file_name.endswith(".json"):
            percorso = os.path.join(TEMP_DIR, file_name)
            json_files = convert_json_structure(percorso)
            for file in json_files:
                write_json_to_file(file, OUTPUT_DIR, file["Codice sede"], data_inizio, data_fine)


    if os.path.exists(TEMP_DIR):
        shutil.rmtree(TEMP_DIR)

    print("time taken:", format_time(time.time() - start_time))

