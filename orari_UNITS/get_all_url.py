import time
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import Select
from joblib import Parallel, delayed
from datetime import datetime
import json

def print_title():
    print(r"""
    _____                   _ _                                    _   _    _ _   _ _____ _______ _____ 
   / ____|                 | (_)                                  (_) | |  | | \ | |_   _|__   __/ ____|
  | |     _ __ _____      _| |_ _ __   __ _    ___  _ __ __ _ _ __ _  | |  | |  \| | | |    | | | (___  
  | |    | '__/ _ \ \ /\ / / | | '_ \ / _` |  / _ \| '__/ _` | '__| | | |  | | . ` | | |    | |  \___ \ 
  | |____| | | (_) \ V  V /| | | | | | (_| | | (_) | | | (_| | |  | | | |__| | |\  |_| |_   | |  ____) |
   \_____|_|  \___/ \_/\_/ |_|_|_| |_|\__, |  \___/|_|  \__,_|_|  |_|  \____/|_| \_|_____|  |_| |_____/ 
                                       __/ |                                                            
                                      |___/                                                             
    """)
    print("Script to extract all course schedule URLs from orari.units.it")
    print("In progress... \n")


############### Funzioni get e set ####################
from urllib.parse import urlencode, quote

def build_orario_url(anno_scolastico, scuola, corso, anno2, date, lang="it"):
    base_url = "https://orari.units.it/agendaweb/index.php"

    params = {
        "view": "easycourse",
        "form-type": "corso",
        "include": "corso",
        "txtcurr": "",
        "anno": anno_scolastico,
        "scuola": scuola,
        "corso": corso,
        "anno2[]": anno2,  # verrà encodato
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

############### Inizializzazione WebDriver ####################
# Imposta Chrome headless
chrome_options = Options()
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--window-size=1920,1080")


def estrai_url(dip):
    driver = webdriver.Chrome(options=chrome_options)
    driver.get(URL_FORM)
    time.sleep(0.4)

    anni_scolastici = get_anni_scolastici(driver)
    latest_value = max(anni_scolastici, key=lambda x: int(x['value']))
    set_anno_scolastico(latest_value, driver)
    
    set_dipartimento(dip, driver)
    corsi_di_studio = get_corsi_di_studio(driver)
    
    urls_local = set()
    blocchi = []
    for corso in corsi_di_studio:
        set_corso_di_studio(corso, driver)
        anni_di_studio_e_curriculum = get_anni_di_studio_e_curriculum(driver)
        
        for anno_studio in anni_di_studio_e_curriculum:
            set_anno_di_studio_e_curriculum(anno_studio, driver)
            
            log = "\n" + dip["label"] + "  --  Corso: " + corso["label"] + "  --  Anno di studio e curriculum: " + anno_studio["label"] + "\n"
            print(log)

            if anno_studio["label"].strip().endswith("Comune"):
                anno_studio["label"] += " con tutti gli altri curriculum di quel corso"
            url = build_orario_url("2025", dip["value"], corso["value"], anno_studio["value"], "29/09/2025", lang="it")
            
            blocco = {
                "url": url,
                "anno_scolastico": "2025",
                "dipartimento_value": dip["value"],
                "corso_di_studi": corso["value"],
                "codice_curriculum_e_anno_corso": anno_studio["value"],
                "anno_corso_e_curriculum": anno_studio["label"],
                "data_settimana": "1/09/2025"
            }

            blocchi.append(blocco)
            urls_local.add(url)
    
    driver.quit()

    return urls_local, blocchi


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
    URL_FORM = "https://orari.units.it/agendaweb/index.php?view=easycourse&_lang=it&include=corso"
    print_title()
    start_datetime = datetime.now()
    start_time = time.time()
    driver = webdriver.Chrome(options=chrome_options)
    driver.get(URL_FORM)
    time.sleep(0.6)
    dipartimenti = get_dipartimenti(driver)
    driver.quit()
    
    risultati = Parallel(n_jobs=4)(
        delayed(estrai_url)(dip) for dip in dipartimenti
    )

    urls_finali = set()
    blocchi_finali = []

    for urls_local, blocchi in risultati:
        urls_finali.update(urls_local)
        blocchi_finali.extend(blocchi)

    if len(urls_finali) != len(blocchi_finali):
        print("Attenzione: il numero di URL unici non corrisponde al numero di blocchi.\n")
        print(f"URL unici: {len(urls_finali)}, Blocchi: {len(blocchi_finali)}")
        exit(1)

    with open("requests_for_orari.json", "w", encoding="utf-8") as f:
        json.dump(blocchi_finali, f, ensure_ascii=False, indent=2)


    with open('orariUNITS_summary.log', 'a') as f:
            f.write("====== CRAWLING SESSION " + str(start_datetime.strftime('%d-%m-%Y %H:%M:%S')) + " ======\n")
            f.write(f"End time:   {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}\n")
            f.write(f"Duration:   {format_time(time.time() - start_time)}\n")
            f.write(f"Links generated: {len(urls_finali)}\n")
            f.write("\n")

    print("Totale URL:", len(urls_finali))
    print("tempo impiegato:", format_time(time.time() - start_time))
