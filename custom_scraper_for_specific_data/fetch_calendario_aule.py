from joblib import Parallel, delayed
import multiprocessing
import shutil
from fetch_calendario_aule_utils import print_title, parse_date, get_sites, get_data, convert_json_structure, write_json_to_file, format_time
import time
import os
import requests
from datetime import date, datetime
import argparse

if __name__ == "__main__":
    start_datetime = datetime.now()
    start_time = time.time()
    parser = argparse.ArgumentParser(description="Script for extracting room schedule from orari.units.it")
    parser.add_argument("--start_date", type=parse_date, help="Start date in dd-mm-yyyy format", default=date(datetime.now().year, 11, 6))
    parser.add_argument("--end_date", type=parse_date, help="End date in dd-mm-yyyy format", default=date(datetime.now().year+1, 2, 20))
    parser.add_argument("--num_sites", type=int, help="For testing, consider only n sites instead of all, ignore to get all", default=0)
    parser.add_argument("-o", "--output", type=str, help="Output file for the extracted data.", default="room_schedule_per_site")
    args = parser.parse_args()

    start_date = args.start_date
    end_date = args.end_date    # the request wants only one year as school year. EX 2023 for school year 2023/2024.
    num_sites = args.num_sites

    print_title(start_time, start_date, end_date)
    
    OUTPUT_DIR = args.output
    TEMP_DIR = ".temp_room_schedule"
    URL_sites_data = "https://orari.units.it/agendaweb/combo.php?sw=rooms_"
    URL_PORTAL = "https://orari.units.it/agendaweb/index.php?view=rooms&include=rooms&_lang=it"


    if os.path.exists(TEMP_DIR):
        shutil.rmtree(TEMP_DIR)
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(TEMP_DIR, exist_ok=True)
    os.remove("site_names.txt") if os.path.exists("site_names.txt") else None

    resp = requests.get(URL_sites_data)
    resp.raise_for_status()
    data_from_units = resp.text

    sites = get_sites(data_from_units)
    if 0 < num_sites < len(sites):
        selected_sites = sites[:num_sites]  # for testing or to have fewer sites to speed up
        print(f"number of sites: {num_sites}")
    else:
        selected_sites = sites
        print(f"number of sites: all")

    num_cores = max(1, multiprocessing.cpu_count())
    final_json = Parallel(n_jobs=num_cores)(
        delayed(get_data)(site, start_date, end_date, TEMP_DIR) for site in selected_sites
    )

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    for file_name in os.listdir(TEMP_DIR):
        if file_name.endswith(".json"):
            file_path = os.path.join(TEMP_DIR, file_name)
            json_files = convert_json_structure(file_path)
            for file in json_files:
                write_json_to_file(file, OUTPUT_DIR, file["site_code"], start_date, end_date)


    if os.path.exists(TEMP_DIR):
        shutil.rmtree(TEMP_DIR)

    print("time taken:", format_time(time.time() - start_time))

