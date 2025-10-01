import requests
import json
import shutil
import os

def response_filter(data):
    CHIAVI_DA_TENERE = [
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
    celle_filtrate = [
        {k: cella[k] for k in CHIAVI_DA_TENERE if k in cella}
        for cella in data.get("celle", [])
    ]
    data_filtrato = {"orario_lezioni": celle_filtrate}
    return data_filtrato







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

for blocco in blocchi:    
    try:
        url_specifico = blocco["url"]
        anno_scolastico = blocco["anno_scolastico"]
        dipartimento_value = blocco["dipartimento_value"]
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
        "corso": corso_di_studi,
        "anno2[]": codice_curriculum_e_anno_corso,
        "visualizzazione_orario": "cal",
        "date": data_settimana,
        "_lang": "it",
        "col_cells": "0",
        "only_grid": "0",
        "all_events": "0"
    }

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
        "Origin": "https://orari.units.it",
        "Referer": "https://orari.units.it/agendaweb/index.php"
    }

    response = requests.post(url, data=payload, headers=headers)
    response.raise_for_status()
    final_json = {}
    final_json["url"] = url_specifico
    final_json["anno scolastico"] = "2025"
    final_json["dipartimento"] = dipartimento_value
    final_json["corso"] = corso_di_studi
    final_json["codice_anno_corso_di_studio"] = codice_curriculum_e_anno_corso
    final_json["anno_corso_e_curriculum"] = anno_corso_di_studio_e_curriculum
    final_json["orario_della_settimana_del"] = data_settimana


    orario_json = response_filter(response.json())
    if orario_json["orario_lezioni"] == []:
        print("Orario vuoto, salto\n")
        continue  
    final_json["orario"] = orario_json["orario_lezioni"]


    nome_file = os.path.join(cartella, f"{corso_di_studi}---{codice_curriculum_e_anno_corso}.json")
    with open(nome_file, "w", encoding="utf-8") as f:
        json.dump(final_json, f, ensure_ascii=False, indent=2)

    print(f"{blocchi.index(blocco)+1}/{len(blocchi)}    Orario salvato in {nome_file}")
