import time
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import Select
from datetime import datetime
from datetime import date
from datetime import timedelta
import json
import requests
import argparse
from urllib.parse import urlencode, quote
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def print_title(start_time, data_inizio, data_fine, anno_scolastico):
    print(r"""
  _____    _       _                            _   _          _             _   _   _ _   _ ___ _____ ____  
 |  ___|__| |_ ___| |__     ___  _ __ __ _ _ __(_) | | ___ ___(_) ___  _ __ (_) | | | | \ | |_ _|_   _/ ___| 
 | |_ / _ \ __/ __| '_ \   / _ \| '__/ _` | '__| | | |/ _ \_  / |/ _ \| '_ \| | | | | |  \| || |  | | \___ \ 
 |  _|  __/ || (__| | | | | (_) | | | (_| | |  | | | |  __// /| | (_) | | | | | | |_| | |\  || |  | |  ___) |
 |_|  \___|\__\___|_| |_|  \___/|_|  \__,_|_|  |_| |_|\___/___|_|\___/|_| |_|_|  \___/|_| \_|___| |_| |____/ 
                                                                                                             
    """)
    formatted_time = time.strftime("%H:%M:%S", time.localtime(start_time))
    print(f"Script started at {formatted_time}")
    print(f"SCHOOL YEAR: {anno_scolastico}/{anno_scolastico+1} (first fetch date: {data_inizio.strftime("%d-%m-%Y")}, last fetch date: {data_fine.strftime("%d-%m-%Y")})")
    print(f"Starting the process to get all lessons schedule URLs from orari.units.it...\n")

def print_result(start_time, data_inizio, data_fine, anno_scolastico, OUTPUT_DIR, num_departments):
    print(f"\n#################### RESULT ####################")
    print(f"Script started at {time.strftime("%H:%M:%S", time.localtime(start_time))} and ended at {time.strftime("%H:%M:%S", time.localtime(time.time()))}")
    print(f"SCHOOL YEAR: {anno_scolastico}/{anno_scolastico+1} (first fetch date: {data_inizio.strftime("%d-%m-%Y")}, last fetch date: {data_fine.strftime("%d-%m-%Y")})")
    print(f"number of departments considered: {'all' if num_departments == 0 else num_departments}")
    print(f"Time needed: {format_time(time.time() - start_time)}")
    print(f"Results are in : /{OUTPUT_DIR}")
    print(f"################################################\n")


############### Funzioni get e set ####################

def build_orario_url(anno_scolastico, scuola, corso, codice_curriculum_e_anno_corso, date, base_url, lang="it"):
    #ES:

    # form-type   corso
    # include     corso
    # txtcurr     1 - Comune
    # anno        2025
    # scuola      DipartimentodiIngegneriaeArchitettura
    # corso.      AR03A
    # anno2[]     PDS0-2025|1
    # date        02-10-2023

    params = {
        "view": "easycourse",
        "form-type": "corso",
        "include": "corso",
        "txtcurr": "",
        "anno": anno_scolastico,
        "scuola": scuola,
        "corso": corso,
        "anno2[]": codice_curriculum_e_anno_corso,  # verrà encodato
        "visualizzazione_orario": "cal",
        "date": date,
        "periodo_didattico": "",
        "_lang": lang,
        "list": "",
        "week_grid_type": "-1",
        "ar_codes_": "",
        "ar_select_": "",
        "col_cells": "0",
        "empty_box": "0",
        "only_grid": "0",
        "highlighted_date": "0",
        "all_events": "0",
        "faculty_group": "0",
    }

    return f"{base_url}?{urlencode(params, quote_via=quote)}"


def get_anni_scolastici(job_driver):
    select_anno_scolastico = job_driver.find_element(By.ID, "cdl_aa")
    anni = [
        {"value": opt.get_attribute("value"), "label": opt.text}
        for opt in select_anno_scolastico.find_elements(By.TAG_NAME, "option")
        if opt.get_attribute("value")
    ]
    time.sleep(0.4)
    return anni


def set_anno_scolastico(anno, iob_driver):
    select_anno_scolastico = iob_driver.find_element(By.ID, "cdl_aa")
    Select(select_anno_scolastico).select_by_value(anno["value"])
    time.sleep(0.4)


def get_dipartimenti(iob_driver):
    select_dipartimento = iob_driver.find_element(By.ID, "cdl_scuola")
    dipartimenti = [
        {"value": opt.get_attribute("value"), "label": opt.text}
        for opt in select_dipartimento.find_elements(By.TAG_NAME, "option")
        if opt.get_attribute("value")
    ]
    time.sleep(0.4)
    return dipartimenti

def set_dipartimento(dipartimnento, iob_driver):
    select_dipartimento = iob_driver.find_element(By.ID, "cdl_scuola")
    Select(select_dipartimento).select_by_value(dipartimnento["value"])
    scuola = dipartimnento["value"]
    time.sleep(0.4)  

def get_corsi_di_studio(iob_driver):
    select_corso = iob_driver.find_element(By.ID, "cdl_co")
    corsi = [
        {"value": opt.get_attribute("value"), "label": opt.text}
        for opt in select_corso.find_elements(By.TAG_NAME, "option")
        if opt.get_attribute("value")
    ]
    return corsi


def set_corso_di_studio(corso, iob_driver):
    select_corso = iob_driver.find_element(By.ID, "cdl_co")
    Select(select_corso).select_by_value(corso["value"])
    corso = corso["value"]
    time.sleep(0.4)

def get_anni_di_studio_e_curriculum(iob_driver):
    select_Anno_di_studio_e_curriculum = iob_driver.find_element(By.ID, "cdl_a2_multi")
    anni = [
        {"value": opt.get_attribute("value"), "label": opt.text}
        for opt in select_Anno_di_studio_e_curriculum.find_elements(By.TAG_NAME, "option")
        if opt.get_attribute("value")
    ]
    time.sleep(0.4)
    return anni


def set_anno_di_studio_e_curriculum(anno, iob_driver):
    select_Anno_di_studio_e_curriculum = iob_driver.find_element(By.ID, "cdl_a2_multi")
    Select(select_Anno_di_studio_e_curriculum).select_by_value(anno["value"])
    anno2 = anno["value"]
    time.sleep(0.4)


def get_info_for_request(dip, base_url, anno_scolastico, data_inizio, chrome_options, URL_FORM):
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)    
    driver.get(URL_FORM)
    time.sleep(0.4)

    anni_scolastici = get_anni_scolastici(driver)
    if not anni_scolastici:
        print(f"Nessun anno scolastico trovato per il dipartimento {dip['label']}")
        return []
    latest_value = max(anni_scolastici, key=lambda x: int(x['value']))
    set_anno_scolastico(latest_value, driver)
    
    set_dipartimento(dip, driver)
    corsi_di_studio = get_corsi_di_studio(driver)
    
    blocchi = []
    for corso in corsi_di_studio:
        set_corso_di_studio(corso, driver)
        anni_di_studio_e_curriculum = get_anni_di_studio_e_curriculum(driver)
        
        for anno_studio in anni_di_studio_e_curriculum:
            set_anno_di_studio_e_curriculum(anno_studio, driver)
            
            log = "Getting " + dip["label"] + "  --  Corso: " + corso["label"] + "  --  Anno di studio e curriculum: " + anno_studio["label"]
            print(f"{log}\n")

            if anno_studio["label"].strip().endswith("Comune"):
                anno_studio["label"] += " con tutti gli altri curriculum di quel corso"

            if corso["label"].strip().endswith("(Laurea)"):
                corso["label"] = corso["label"][:-len("(Laurea)")] + "(Laurea triennale)"

            blocco = {
                "anno scolastico": anno_scolastico,
                "codice dipartimento": dip["value"],
                "codice corso": corso["value"],
                "corso di studi": corso["label"],
                "codice curriculum e anno corso": anno_studio["value"],
                "anno corso e curriculum": anno_studio["label"],
                "data settimana": data_inizio
            }

            blocchi.append(blocco)
    
    driver.quit()

    return blocchi


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
    


def response_filter(data, chiavi_celle=None, chiave_output_celle="orario lezioni"):
    if chiavi_celle is None:
        chiavi_celle = [
            "codice insegnamento",
            "nome insegnamento",
            "data",
            "codice aula",
            "codice sede",
            "aula",
            "orario",
            "Annullato",
            "codice docente",
            "docente",
        ]

    celle_filtrate = []
    for cella in data.get("celle", []):
        nuova_cella = {k: cella[k] for k in chiavi_celle if k in cella and k != "Annullato"}

        annullato_val = str(cella.get("Annullato", "0")).strip()
        if annullato_val == "1":
            nuova_cella["annullato"] = "si"
        celle_filtrate.append(nuova_cella)
    to_return = {}
    if "first_day_label" in data:
        to_return["giorno inizio settimana"] = data["first_day_label"]
    to_return[chiave_output_celle] = celle_filtrate
    return to_return



def format_time(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = round(seconds % 60)
    if hours > 0:
        return f"{hours}h {minutes}min {secs}s"
    elif minutes > 0:
        return f"{minutes}min {secs}s"
    else:
        return f"{secs}s"

def next_week(d: date) -> date:
    days_ahead = 7 - d.weekday()
    if days_ahead == 0:
        days_ahead = 7
    return d + timedelta(days=days_ahead)

def write_json_to_file(file_name, new_content):
    data = []
    if os.path.exists(file_name) and os.path.getsize(file_name) > 0:
        with open(file_name, "r", encoding="utf-8") as f:
            data = json.load(f)
    
    if not isinstance(data, list):
        raise ValueError("Il JSON esistente non è una lista, impossibile fare append.")
    if isinstance(new_content, list):
        data = new_content + data  # nuovi elementi prima
    else:
        data = [new_content] + data
    with open(file_name, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_response_and_write_json_to_files(info_schedule_corse, OUTPUT_DIR, url, BASE_URL, data_fine):
    session = requests.Session()
    retries = Retry(total=5, backoff_factor=0.3, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retries)
    session.mount('https://', adapter)

    while info_schedule_corse["data settimana"] <= data_fine:
        print("Richiesta per:", info_schedule_corse["data settimana"])
        try:
            anno_scolastico = info_schedule_corse["anno scolastico"]
            codice_dipartimento = info_schedule_corse["codice dipartimento"]
            codice_corso = info_schedule_corse["codice corso"]
            corso_di_studi = info_schedule_corse["corso di studi"]
            codice_curriculum_e_anno_corso = info_schedule_corse["codice curriculum e anno corso"]
            anno_corso_di_studio_e_curriculum = info_schedule_corse["anno corso e curriculum"]
            data_settimana = info_schedule_corse["data settimana"]
        except Exception as e:
            print(f"Errore nel parsing del json: {e}")
            break

        url_specifico = build_orario_url(anno_scolastico, codice_dipartimento, codice_corso, codice_curriculum_e_anno_corso, data_settimana, BASE_URL, lang="it")

        payload = {
            "view": "easycourse",
            "form-type": "corso",
            "include": "corso",
            "anno": anno_scolastico,
            "scuola": codice_dipartimento,
            "corso": codice_corso,
            "anno2[]": codice_curriculum_e_anno_corso,
            "visualizzazione_orario": "cal",
            "date": data_settimana,
            "_lang": "it",
            "col_cells": "0",
            "only_grid": "0",
            "all_events": "0"
        }

        headers = {
            "User-Agent": "UNITS Links Crawler (network lab)",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
            "Origin": "https://orari.units.it",
            "Referer": BASE_URL
        }

        try:
            time.sleep(0.1)  # evita saturazione porte
            response = session.post(url, data=payload, headers=headers)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Errore nella richiesta: {e}")
            break

        orario_json = response_filter(response.json())x
        try:
            orario = orario_json["orario lezioni"]
        except Exception as e:
            print(f"Errore nel parsing del json: {e}")
            break

        if orario_json["orario lezioni"] == []:
            print(f"ATTENZIONE Orario vuoto per {codice_corso}---{codice_curriculum_e_anno_corso} in data {data_settimana}")

        final_json = {
            "url": url_specifico,
            "dipartimento": codice_dipartimento,
            "codice corso": codice_corso,
            "corso di studi": corso_di_studi,
            "codice anno corso di studio": codice_curriculum_e_anno_corso,
            "anno corso e curriculum": anno_corso_di_studio_e_curriculum,
            **orario_json
        }

        file_name = os.path.join(OUTPUT_DIR, f"{codice_corso}---{codice_curriculum_e_anno_corso}---{data_settimana}.json")
        write_json_to_file(file_name, final_json)

        info_schedule_corse["data settimana"] = next_week(data_settimana)

def parse_date(s):
    try:
        return datetime.strptime(s, "%d-%m-%Y").date()
    except ValueError:
        raise argparse.ArgumentTypeError(f"Formato data non valido: '{s}'. Usa dd-mm-yyyy.")
