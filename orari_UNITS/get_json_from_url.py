import requests
import json
import shutil
import os
import time
from datetime import datetime
from joblib import Parallel, delayed
import multiprocessing

def response_filter(data, chiavi_celle=None, chiave_output_celle="orario_lezioni"):
    """
    Filtra un JSON di orario e permette di rinominare alcune chiavi globali.
    
    - data: JSON originale
    - chiavi_celle: lista di chiavi da mantenere nelle celle
    - chiave_output_celle: nome della chiave dove salvare le celle filtrate
    """
    if chiavi_celle is None:
        chiavi_celle = [
            "codice_insegnamento",
            "nome_insegnamento",
            "data",
            "codice_aula",
            "codice_sede",
            "aula",
            "orario",
            "tipo",
            "ora_inizio",
            "ora_fine",
            "Annullato",
            "codice_docente",
            "docente",
        ]
    
    # Filtra le celle
    celle_filtrate = [
        {k: cella[k] for k in chiavi_celle if k in cella}
        for cella in data.get("celle", [])
    ]

    # Mantieni e rinomina le chiavi globali
    data_filtrato = {}
    if "first_day_label" in data:
        data_filtrato["giorno_inizio_settimana"] = data["first_day_label"]
    if "last_day_label" in data:
        data_filtrato["giorno_fine_settimana"] = data["last_day_label"]

    # Inserisci le celle filtrate
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



def get_response(blocco):
        # if blocchi.index(blocco) < 310:
        #     return  # saltare i primi 310 blocchi già processati  
        try:
            url_specifico = blocco["url"]
            anno_scolastico = blocco["anno_scolastico"]
            dipartimento_value = blocco["dipartimento_value"]
            codice_corso = blocco["codice_corso"]
            corso_di_studi = blocco["corso_di_studi"]
            codice_curriculum_e_anno_corso = blocco["codice_curriculum_e_anno_corso"]
            anno_corso_di_studio_e_curriculum = blocco["anno_corso_e_curriculum"]
            data_settimana = blocco["data_settimana"]
        except Exception as e:
            print(f"Errore nel parsin del json")
            exit(1)
            
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
        with open("response_json_files/json_originale.json", "w", encoding="utf-8") as f:
            json.dump(response.json(), f, ensure_ascii=False, indent=2)

        final_json = {}
        final_json["url"] = url_specifico
        final_json["dipartimento"] = dipartimento_value
        final_json["codice_corso"] = codice_corso
        final_json["corso_di_studi"] = corso_di_studi
        final_json["codice_anno_corso_di_studio"] = codice_curriculum_e_anno_corso
        final_json["anno_corso_e_curriculum"] = anno_corso_di_studio_e_curriculum

        orario_json = response_filter(response.json())
        if orario_json["orario_lezioni"] == []:
            print(
                f"\n{blocchi.index(blocco)+1}/{len(blocchi)} ATTENZIONE Orario vuoto per {corso_di_studi}"
                f"\nnella settimana del {orario_json['giorno_inizio_settimana']}"
                f"\nurl di riferimento: {url_specifico}\n"
            )
            return  
        final_json = {**final_json, **orario_json}

        nome_file = os.path.join(cartella, f"{codice_corso}---{codice_curriculum_e_anno_corso}.json")
        with open(nome_file, "w", encoding="utf-8") as f:
            json.dump(final_json, f, ensure_ascii=False, indent=2)
        print(f"{blocchi.index(blocco)+1}/{len(blocchi)}    Orario salvato in {nome_file}")



start_datetime = datetime.now()
start_time = time.time()
cartella = "response_json_files"
try:
    shutil.rmtree(cartella)
except:
    pass
cartella = "response_json_files"
os.makedirs(cartella, exist_ok=True)

with open("requests_for_orari.json", "r", encoding="utf-8") as f:
    blocchi = json.load(f)
if not blocchi:
    raise ValueError("Il file blocchi.json è vuoto")


num_cores = max(1, multiprocessing.cpu_count() - 1)
Parallel(n_jobs=num_cores)(
    delayed(get_response)(blocco) for blocco in blocchi
)




print("tempo impiegato:", format_time(time.time() - start_time))
