import requests
import json
import shutil
import os
import time
from datetime import datetime, timedelta
from joblib import Parallel, delayed
import multiprocessing

def response_filter(data, chiavi_celle=None, chiave_output_celle="orario_lezioni"):
    if chiavi_celle is None:
        chiavi_celle = [
            "codice_insegnamento",
            "nome_insegnamento",
            "data",
            "codice_aula",
            "codice_sede",
            "aula",
            "orario",
            "ora_inizio",
            "ora_fine",
            "Annullato",
            "codice_docente",
            "docente",
        ]

    celle_filtrate = [
        {k: cella[k] for k in chiavi_celle if k in cella}
        for cella in data.get("celle", [])
    ]

    data_filtrato = {}
    if "first_day_label" in data:
        data_filtrato["giorno_inizio_settimana"] = data["first_day_label"]

    data_filtrato[chiave_output_celle] = celle_filtrate
    return data_filtrato


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

def next_week(date_str: str) -> str:
    print("chiamata next_monday")
    # Riconosciamo il separatore
    if "-" in date_str:
        fmt = "%d-%m-%Y"
        sep = "-"
    elif "/" in date_str:
        fmt = "%d/%m/%Y"
        sep = "/"
    else:
        raise ValueError("Formato data non valido. Usa dd/mm/yyyy o dd-mm-yyyy.")
    
    d = datetime.strptime(date_str, fmt).date()

    days_ahead = 7 - d.weekday()
    if days_ahead == 0:  # se già lunedì
        days_ahead = 7
    next_mon = d + timedelta(days=days_ahead)

    return next_mon.strftime(f"%d{sep}%m{sep}%Y")

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


from datetime import datetime

def check_date(date_str):
    # Prova entrambi i formati
    for fmt in ("%d/%m/%Y", "%d-%m-%Y"):
        try:
            input_date = datetime.strptime(date_str, fmt)
            break
        except ValueError:
            continue
    else:
        raise ValueError("Formato data non valido. Usa dd/mm/yyyy o dd-mm-yyyy.")

    # Data di riferimento
    target_date = datetime(2026, 1, 20)

    return input_date < target_date






def get_response(info_schedule_corse, number_of_schedules, counter, lock):

    print("Richiesta per:", info_schedule_corse["data_settimana"])

    if (not check_date(info_schedule_corse["data_settimana"])):
        print("Data oltre il 20 gennaio dell'anno successivo, non procedo con la richiesta.")
        return
    try:
        url_specifico = info_schedule_corse["url"]
        anno_scolastico = info_schedule_corse["anno_scolastico"]
        dipartimento_value = info_schedule_corse["dipartimento_value"]
        codice_corso = info_schedule_corse["codice_corso"]
        corso_di_studi = info_schedule_corse["corso_di_studi"]
        codice_curriculum_e_anno_corso = info_schedule_corse["codice_curriculum_e_anno_corso"]
        anno_corso_di_studio_e_curriculum = info_schedule_corse["anno_corso_e_curriculum"]
        data_settimana = info_schedule_corse["data_settimana"]
    except Exception as e:
        print(f"Errore nel parsing del json: {e}")
        return

    url = "https://orari.units.it/agendaweb/grid_call.php"

    payload = {
        "view": "easycourse",
        "form-type": "corso",
        "include": "corso",
        "anno": anno_scolastico,
        "scuola": dipartimento_value,
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
        "Referer": "https://orari.units.it/agendaweb/index.php"
    }

    response = requests.post(url, data=payload, headers=headers)
    response.raise_for_status()

    final_json = {
        "url": url_specifico,
        "dipartimento": dipartimento_value,
        "codice_corso": codice_corso,
        "corso_di_studi": corso_di_studi,
        "codice_anno_corso_di_studio": codice_curriculum_e_anno_corso,
        "anno_corso_e_curriculum": anno_corso_di_studio_e_curriculum
    }

    orario_json = response_filter(response.json())
    if orario_json["orario_lezioni"] == []:
        with lock:
            counter.value += 1
            print(f"{counter.value}/{number_of_schedules} ATTENZIONE Orario vuoto per {codice_corso}---{codice_curriculum_e_anno_corso} in data {data_settimana}")
    next_schedule_corse = info_schedule_corse
    next_schedule_corse["data_settimana"] = next_week(info_schedule_corse["data_settimana"])
    print("Provo con la settimana successiva:", next_schedule_corse["data_settimana"])
    get_response(info_schedule_corse, number_of_schedules, counter, lock)

    final_json = {**final_json, **orario_json}

    nome_file = os.path.join(directory, f"{codice_corso}---{codice_curriculum_e_anno_corso}.json")
    write_json_to_file(nome_file, final_json)   
    # with open(nome_file, "w", encoding="utf-8") as f:
    #     json.dump(final_json, f, ensure_ascii=False, indent=2)

    with lock:
        counter.value += 1
        print(f"{counter.value}/{number_of_schedules} Orario salvato in {nome_file}")


if __name__ == "__main__":

    file_name = "requests_for_orari.json"
    start_datetime = datetime.now()
    start_time = time.time()
    directory = "response_json_files"
    try:
        shutil.rmtree(directory)
    except:
        pass
    os.makedirs(directory, exist_ok=True)

    with open(file_name, "r", encoding="utf-8") as f:
        info_schedules = json.load(f)
    if not info_schedules:
        raise ValueError("File " + file_name + " is empty")

    num_cores = max(1, multiprocessing.cpu_count() - 1)

    manager = multiprocessing.Manager()
    counter = manager.Value("i", 0)
    lock = manager.Lock()

    Parallel(n_jobs=num_cores)(
        delayed(get_response)(info_schedule_corse, len(info_schedules), counter, lock) for info_schedule_corse in info_schedules
    )

    print("time taken:", format_time(time.time() - start_time))
