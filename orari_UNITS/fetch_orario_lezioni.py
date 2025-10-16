import multiprocessing
import shutil
from joblib import Parallel, delayed

from fetch_orario_lezioni_utils import *

if __name__ == "__main__":
    start_time = time.time()
    parser = argparse.ArgumentParser(description="Script per l'estrazione degli orari da orari.units.it")
    parser.add_argument("--start_date", type=parse_date, help="Data di inizio nel formato dd-mm-yyyy", default=date(datetime.now().year, 11, 6))
    parser.add_argument("--end_date", type=parse_date, help="Data di fine nel formato dd-mm-yyyy", default=date(datetime.now().year+1, 2, 20))
    parser.add_argument("--num_departments", type=int, help="per test posso considerare solo n dipartimenti e non tutti, ignorare per averli tutti", default=0)

    args = parser.parse_args()

    data_inizio = args.start_date
    data_fine = args.end_date    # la request vuole solo un anno come anno scolastico. ES 2023 per l'anno scolastico 2023/2024.
    num_departments = args.num_departments
    # quindi se la data è dopo il 15 agosto, l'anno scolastico è l'anno della data, altrimenti è l'anno precedente. 
    # Si presume che le richieste dopo il 15 agosto siano per l'anno scolastico che inizia a settembre (prima del 15 aosto solitamente non vengono pubblicati gli orari dell'AS nuovo).
    anno_scolastico = data_inizio.year if data_inizio >= date(data_inizio.year, 8, 15) else data_inizio.year - 1
    print_title(start_time, data_inizio, data_fine, anno_scolastico)

    ############### Inizializzazione WebDriver ####################
    # Imposta Chrome headless
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=UNITS Links Crawler (network lab)")
    BASE_URL = "https://orari.units.it/agendaweb/index.php"
    URL_FORM = BASE_URL + "?view=easycourse&_lang=it&include=corso"
    URL_orari_data = "https://orari.units.it/agendaweb/grid_call.php"

    OUTPUT_DIR = "calendario_lezioni_per_corso"

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    driver.get(URL_FORM)
    time.sleep(0.6)
    dipartimenti = get_dipartimenti(driver)
    if 0 < num_departments < len(dipartimenti):
        dipartimenti = dipartimenti[:num_departments]  # solo in fase di test per velocizzare
    else:
        num_departments = 0
    print(f"num_departments considered: {'all' if num_departments == 0 else num_departments}")
    driver.quit()

    num_cores = max(1, multiprocessing.cpu_count()*4)
    risultati = Parallel(n_jobs=16)(
        delayed(get_info_for_request)(dip, BASE_URL, anno_scolastico, data_inizio, chrome_options, URL_FORM) for dip in dipartimenti
    )

    blocchi_finali = []

    for blocco in risultati:
        blocchi_finali.extend(blocco)

    try:
        shutil.rmtree(OUTPUT_DIR)
    except:
        pass
    os.makedirs(OUTPUT_DIR, exist_ok=True)


    Parallel(n_jobs=8)(
        delayed(get_response_and_write_json_to_files)(info_schedule_corse, OUTPUT_DIR, URL_orari_data, BASE_URL, data_fine) for info_schedule_corse in blocchi_finali
    )

    print_result(start_time, data_inizio, data_fine, anno_scolastico, OUTPUT_DIR, num_departments)
