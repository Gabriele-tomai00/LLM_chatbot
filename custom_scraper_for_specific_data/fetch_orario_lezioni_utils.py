import time
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from datetime import date, datetime, timedelta
import json
import requests
from urllib.parse import urlencode, quote
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from utils import format_iso_date_to_italian_long, get_day_of_week, extract_time_range, safe
from selenium.webdriver.chrome.options import Options

def print_title(start_time, start_date, end_date, school_year):
    print(r"""
  _____    _       _                            _   _          _             _   _   _ _   _ ___ _____ ____  
 |  ___|__| |_ ___| |__     ___  _ __ __ _ _ __(_) | | ___ ___(_) ___  _ __ (_) | | | | \ | |_ _|_   _/ ___| 
 | |_ / _ \ __/ __| '_ \   / _ \| '__/ _` | '__| | | |/ _ \_  / |/ _ \| '_ \| | | | | |  \| || |  | | \___ \ 
 |  _|  __/ || (__| | | | | (_) | | | (_| | |  | | | |  __// /| | (_) | | | | | | |_| | |\  || |  | |  ___) |
 |_|  \___|\__\___|_| |_|  \___/|_|  \__,_|_|  |_| |_|\___/___|_|\___/|_| |_|_|  \___/|_| \_|___| |_| |____/ 
                                                                                                             
    """)
    formatted_time = time.strftime("%H:%M:%S", time.localtime(start_time))
    print(f"Script started at {formatted_time}")
    print(f"SCHOOL YEAR: {school_year}/{school_year+1} (first fetch date: {start_date.strftime('%d-%m-%Y')}, last fetch date: {end_date.strftime('%d-%m-%Y')})")
    print(f"Starting the process to get all lessons schedule URLs from orari.units.it...\n")

def print_result(start_time, start_date, end_date, school_year, output_dir, num_departments):
    print(f"\n#################### RESULT ####################")
    print(f"Script started at {time.strftime('%H:%M:%S', time.localtime(start_time))} and ended at {time.strftime('%H:%M:%S', time.localtime(time.time()))}")
    print(f"SCHOOL YEAR: {school_year}/{school_year+1} (first fetch date: {start_date.strftime('%d-%m-%Y')}, last fetch date: {end_date.strftime('%d-%m-%Y')})")
    print(f"number of departments considered: {'all' if num_departments == 0 else num_departments}")
    print(f"Time needed: {format_time(time.time() - start_time)}")
    print(f"Results are in : /{output_dir}")
    print(f"################################################\n")
    
############### Get and Set Functions ####################

def build_schedule_url(school_year, department, course, curriculum_code_and_year, date, base_url, lang="it"):
    #EX:

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
        "anno": school_year,
        "scuola": department,
        "corso": course,
        "anno2[]": curriculum_code_and_year,  # will be encoded
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


def get_school_years(driver):
    select_school_year = driver.find_element(By.ID, "cdl_aa")
    years = [
        {"value": opt.get_attribute("value"), "label": opt.text}
        for opt in select_school_year.find_elements(By.TAG_NAME, "option")
        if opt.get_attribute("value")
    ]
    time.sleep(0.4)
    return years


def set_school_year(year, driver):
    select_school_year = driver.find_element(By.ID, "cdl_aa")
    Select(select_school_year).select_by_value(year["value"])
    time.sleep(0.4)


def get_departments(driver):
    select_department = driver.find_element(By.ID, "cdl_scuola")
    departments = [
        {"value": opt.get_attribute("value"), "label": opt.text}
        for opt in select_department.find_elements(By.TAG_NAME, "option")
        if opt.get_attribute("value")
    ]
    time.sleep(0.4)
    return departments

def set_department(department, driver):
    select_department = driver.find_element(By.ID, "cdl_scuola")
    Select(select_department).select_by_value(department["value"])
    school = department["value"]
    time.sleep(0.4)  

def get_study_courses(driver):
    select_course = driver.find_element(By.ID, "cdl_co")
    courses = [
        {"value": opt.get_attribute("value"), "label": opt.text}
        for opt in select_course.find_elements(By.TAG_NAME, "option")
        if opt.get_attribute("value")
    ]
    return courses


def set_study_course(course, driver):
    select_course = driver.find_element(By.ID, "cdl_co")
    Select(select_course).select_by_value(course["value"])
    course = course["value"]
    time.sleep(0.4)

def get_study_years_and_curriculum(driver):
    select_year_and_curriculum = driver.find_element(By.ID, "cdl_a2_multi")
    years = [
        {"value": opt.get_attribute("value"), "label": opt.text}
        for opt in select_year_and_curriculum.find_elements(By.TAG_NAME, "option")
        if opt.get_attribute("value")
    ]
    time.sleep(0.4)
    return years


def set_study_year_and_curriculum(year, driver):
    select_year_and_curriculum = driver.find_element(By.ID, "cdl_a2_multi")
    Select(select_year_and_curriculum).select_by_value(year["value"])
    year2 = year["value"]
    time.sleep(0.4)


def get_info_for_request(dept, school_year, start_date, URL_FORM):
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=UNITS Links Crawler (network lab)")

    driver = webdriver.Chrome(options=chrome_options)
    driver = webdriver.Chrome(options=chrome_options)    
    driver.get(URL_FORM)
    time.sleep(0.4)

    school_years = get_school_years(driver)
    if not school_years:
        print(f"No school year found for department {dept['label']}")
        return []
    latest_value = max(school_years, key=lambda x: int(x['value']))
    set_school_year(latest_value, driver)
    
    set_department(dept, driver)
    study_courses = get_study_courses(driver)
    
    blocks = []
    for course in study_courses:
        set_study_course(course, driver)
        study_years_and_curriculum = get_study_years_and_curriculum(driver)
        
        for study_year in study_years_and_curriculum:
            set_study_year_and_curriculum(study_year, driver)
            
            log = "Getting " + dept["label"] + "  --  Course: " + course["label"] + "  --  Study year and curriculum: " + study_year["label"]
            print(f"{log}\n")

            if study_year["label"].strip().endswith("Comune"):
                study_year["label"] += " with all other curricula of that course"

            if course["label"].strip().endswith("(Laurea)"):
                course["label"] = course["label"][:-len("(Laurea)")] + "(Bachelor Degree)"

            block = {
                "school_year": school_year,
                "department_code": dept["value"],
                "course_code": course["value"],
                "study_course": course["label"],
                "curriculum_code_and_year": study_year["value"],
                "course_year_and_curriculum": study_year["label"],
                "week_date": start_date
            }

            blocks.append(block)
    
    driver.quit()

    return blocks


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
    


def response_filter(data, cell_keys=None, output_key_cells="lessons_schedule"):
    if cell_keys is None:
        cell_keys = [
            "codice_insegnamento",
            "nome_insegnamento",
            "data",
            "codice aula",
            "codice sede",
            "aula",
            "orario",
            "Annullato",
            "codice docente",
            "docente",
        ]

    filtered_cells = []
    for cell in data.get("celle", []):
        new_cell = {k: cell[k] for k in cell_keys if k in cell and k != "Annullato"}

        cancelled_val = str(cell.get("Annullato", "0")).strip()
        if cancelled_val == "1":
            new_cell["annullato"] = "yes"
        filtered_cells.append(new_cell)
    to_return = {}
    if "first_day_label" in data:
        to_return["week_start_day"] = data["first_day_label"]
    to_return[output_key_cells] = filtered_cells
    # print("RAW CELL KEYS:", data.get("celle", [{}])[0].keys() if data.get("celle") else "NO CELLE")
    # print("SAMPLE CELL:", data.get("celle", [{}])[0] if data.get("celle") else "EMPTY")
    return to_return



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
        raise ValueError("Existing JSON is not a list, cannot append.")
    if isinstance(new_content, list):
        data = new_content + data  # new elements first
    else:
        data = [new_content] + data
    with open(file_name, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
def get_response_and_write_json_to_files(course_schedule_info, OUTPUT_DIR, url, BASE_URL, end_date):
    session = requests.Session()
    retries = Retry(total=5, backoff_factor=0.3, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retries)
    session.mount('https://', adapter)

    while course_schedule_info["week_date"] <= end_date:
        print("Request for:", course_schedule_info["week_date"])
        try:
            school_year = course_schedule_info["school_year"]
            department_code = course_schedule_info["department_code"]
            course_code = course_schedule_info["course_code"]
            study_course = course_schedule_info["study_course"]
            curriculum_code_and_year = course_schedule_info["curriculum_code_and_year"]
            course_year_and_curriculum = course_schedule_info["course_year_and_curriculum"]
            week_date = course_schedule_info["week_date"]
        except Exception as e:
            print(f"Error parsing json: {e}")
            break

        specific_url = build_schedule_url(school_year, department_code, course_code, curriculum_code_and_year, week_date, BASE_URL, lang="it")

        payload = {
            "view": "easycourse",
            "form-type": "corso",
            "include": "corso",
            "anno": school_year,
            "scuola": department_code,
            "corso": course_code,
            "anno2[]": curriculum_code_and_year,
            "visualizzazione_orario": "cal",
            "date": week_date,
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
            time.sleep(0.1)  # avoid port saturation
            response = session.post(url, data=payload, headers=headers)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Error in request: {e}")
            break

        schedule_json = response_filter(response.json())
        lessons = schedule_json.get("lessons_schedule", [])

        if not lessons:
            print(f"WARNING Empty schedule for {course_code} on date {week_date}")
            # Optional: skip writing file if empty
        
        # --- NEW RAG-OPTIMIZED STRUCTURE ---
        rag_ready_lessons = []
        
        for lesson in lessons:
            if not lesson.get("nome_insegnamento"):
                continue

            iso_date = safe(datetime.strptime(lesson.get('data'), "%d-%m-%Y").strftime("%Y-%m-%d"))
            
            start_time = safe(extract_time_range(lesson.get("orario"))[0])
            end_time   = safe(extract_time_range(lesson.get("orario"))[1])
            read_time  = safe(format_iso_date_to_italian_long(iso_date)) + " (" + safe(get_day_of_week(iso_date)) + ")"

            flat_lesson = {
                "page_content": (
                    f"Lezione di {safe(lesson.get('nome_insegnamento'))} "
                    f"del corso {safe(study_course)}, {safe(course_year_and_curriculum)}. "
                    f"Data: {safe(read_time)}. "
                    f"Orario: {safe(start_time)} - {safe(end_time)}. "
                    f"Aula: {safe(lesson.get('aula'))}. "
                    f"Docente: {safe(lesson.get('docente'))}."
                ),
                "metadata": {
                    "department":      safe(department_code),
                    "course_code":     safe(course_code),
                    "study_course":    safe(study_course),
                    "subject_code":    safe(lesson.get("codice_insegnamento")),
                    "subject_name":    safe(lesson.get("nome_insegnamento")),
                    "study_year_code": safe(curriculum_code_and_year),
                    "curriculum":      safe(course_year_and_curriculum),
                    "date_iso":        safe(iso_date),
                    "read_time":       safe(read_time),
                    "start_time":      safe(start_time),
                    "end_time":        safe(end_time),
                    "full_location":   safe(lesson.get("aula")),
                    "professor":       safe(lesson.get("docente")),
                    "lesson_type":     safe(lesson.get("tipo")),
                    "cancelled":       lesson.get("annullato", "no"),
                    "url":             safe(specific_url),
                    "doc_type":        "course_schedule"
                }
            }
            rag_ready_lessons.append(flat_lesson)

        # file_name example: SM20---PDS0-2008|3---2026-03-16.json
        file_name = os.path.join(OUTPUT_DIR, f"{course_code}---{curriculum_code_and_year.replace('|','_')}---{week_date}.json")
        
        # Write the list of flattened objects
        with open(file_name, "w", encoding="utf-8") as f:
            json.dump(rag_ready_lessons, f, ensure_ascii=False, indent=2)

        course_schedule_info["week_date"] = next_week(week_date)

def parse_date(s):
    try:
        return datetime.strptime(s, "%d-%m-%Y").date()
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid date format: '{s}'. Use dd-mm-yyyy.")