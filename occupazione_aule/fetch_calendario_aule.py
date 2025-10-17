from joblib import Parallel, delayed
import multiprocessing
import shutil
from fetch_calendario_aule_utils import *

if __name__ == "__main__":
    start_datetime = datetime.now()
    start_time = time.time()
    parser = argparse.ArgumentParser(description="Script per l'estrazione del calendario delle aule da orari.units.it")
    parser.add_argument("--start_date", type=parse_date, help="Data di inizio nel formato dd-mm-yyyy", default=date(datetime.now().year, 11, 6))
    parser.add_argument("--end_date", type=parse_date, help="Data di fine nel formato dd-mm-yyyy", default=date(datetime.now().year+1, 2, 20))
    parser.add_argument("--num_sites", type=int, help="per test posso considerare solo n sedi e non tutte, ignorare per averle tutte", default=0)
    args = parser.parse_args()

    data_inizio = args.start_date
    data_fine = args.end_date    # la request vuole solo un anno come anno scolastico. ES 2023 per l'anno scolastico 2023/2024.
    num_sites = args.num_sites

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

    sites = get_sites(data_from_units)
    if 0 < num_sites < len(sites):
        sedi = sites[:num_sites]  # per test o per avere meno sedi per velocizzare
        print(f"number of sites: {num_sites}")
    else:
        print(f"number of sites: all")

    num_cores = max(1, multiprocessing.cpu_count())
    final_json = Parallel(n_jobs=num_cores)(
        delayed(get_data)(site, data_inizio, data_fine, TEMP_DIR) for site in sites
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

