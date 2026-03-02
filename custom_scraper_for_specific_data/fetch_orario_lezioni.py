import multiprocessing
import shutil
from joblib import Parallel, delayed
import time
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from datetime import date, datetime
import argparse
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from fetch_orario_lezioni_utils import (
    print_title,
    parse_date,
    get_departments,
    get_info_for_request,
    get_response_and_write_json_to_files,
    print_result,
)
if __name__ == "__main__":
    OUTPUT_DIR = "lessons_schedule_by_course"


    start_time = time.time()
    parser = argparse.ArgumentParser(description="Script for extracting schedule from orari.units.it")
    parser.add_argument("--start_date", type=parse_date, help="Start date in dd-mm-yyyy format", default=date(datetime.now().year, 11, 6))
    parser.add_argument("--end_date", type=parse_date, help="End date in dd-mm-yyyy format", default=date(datetime.now().year+1, 2, 20))
    parser.add_argument("--num_departments", type=int, help="For testing, consider only n departments instead of all, ignore to get all", default=0)
    parser.add_argument("-o", "--output", type=str, help="Output file for the extracted data.", default=OUTPUT_DIR)
    args = parser.parse_args()

    OUTPUT_DIR = args.output

    start_date = args.start_date
    end_date = args.end_date    # the request wants only one year as school year. EX 2023 for school year 2023/2024.
    num_departments = args.num_departments
    # so if the date is after August 15th, the school year is the year of the date, otherwise it is the previous year. 
    # It is assumed that requests after August 15th are for the school year starting in September (usually schedules for the new SY are not published before August 15th).
    school_year = start_date.year if start_date >= date(start_date.year, 8, 15) else start_date.year - 1
    print_title(start_time, start_date, end_date, school_year)

    ############### WebDriver Initialization ####################
    # Set headless Chrome
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=UNITS Links Crawler (network lab)")
    BASE_URL = "https://orari.units.it/agendaweb/index.php"
    URL_FORM = BASE_URL + "?view=easycourse&_lang=it&include=corso"
    URL_schedule_data = "https://orari.units.it/agendaweb/grid_call.php"


    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    driver.get(URL_FORM)
    time.sleep(0.6)
    departments = get_departments(driver)
    if 0 < num_departments < len(departments):
        departments = departments[:num_departments]  # only for testing to speed up
    else:
        num_departments = 0
    print(f"num_departments considered: {'all' if num_departments == 0 else num_departments}")
    driver.quit()

    num_cores = max(1, multiprocessing.cpu_count()*4)
    results = Parallel(n_jobs=16)(
        delayed(get_info_for_request)(dept, BASE_URL, school_year, start_date, chrome_options, URL_FORM) for dept in departments
    )

    final_blocks = []

    for block in results:
        final_blocks.extend(block)

    try:
        shutil.rmtree(OUTPUT_DIR)
    except:
        pass
    os.makedirs(OUTPUT_DIR, exist_ok=True)


    Parallel(n_jobs=8)(
        delayed(get_response_and_write_json_to_files)(course_schedule_info, OUTPUT_DIR, URL_schedule_data, BASE_URL, end_date) for course_schedule_info in final_blocks
    )

    print_result(start_time, start_date, end_date, school_year, OUTPUT_DIR, num_departments)
