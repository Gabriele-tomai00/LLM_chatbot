from datetime import date, datetime, timedelta
import re

def format_iso_date_to_italian_long(iso_date):
    """
    Converts an ISO 8601 date (YYYY-MM-DD) to a readable Italian format like '25 marzo 2036'.
    """
    try:
        date_obj = datetime.strptime(iso_date, "%Y-%m-%d")
        months_mapping = {
            1: "gennaio", 2: "febbraio", 3: "marzo", 4: "aprile", 
            5: "maggio", 6: "giugno", 7: "luglio", 8: "agosto", 
            9: "settembre", 10: "ottobre", 11: "novembre", 12: "dicembre"
        }
        
        day = date_obj.day
        month = months_mapping[date_obj.month]
        year = date_obj.year
        
        return f"{day} {month} {year}"
    except ValueError:
        return None

def get_day_of_week(iso_date):
    """
    Returns the Italian day of the week for a given date in ISO 8601 format (YYYY-MM-DD).
    """
    date_obj = datetime.strptime(iso_date, "%Y-%m-%d")
    day_of_week = date_obj.strftime("%A")
    
    days_mapping = {
        "Monday": "lunedì",
        "Tuesday": "martedì",
        "Wednesday": "mercoledì",
        "Thursday": "giovedì",
        "Friday": "venerdì",
        "Saturday": "sabato",
        "Sunday": "domenica"
    }
    
    return f"{days_mapping.get(day_of_week, day_of_week)}"

def convert_dd_mm_yyyy_to_iso_date(date_str):
    """Converts a date string from DD-MM-YYYY format to ISO 8601 (YYYY-MM-DD) format."""
    try:
        # Parse the date string into a datetime object
        date_obj = datetime.strptime(date_str, "%d-%m-%Y")
        # Format the datetime object as ISO 8601 string
        iso_date = date_obj.strftime("%Y-%m-%d")
        return iso_date
    except ValueError:
        # Handle invalid date format
        return None


def extract_time_range(time_str):
    pattern = r"^(\d{2}:\d{2})\s*-\s*(\d{2}:\d{2})$"

    match = re.match(pattern, time_str)
    if match:
        time_start = match.group(1)  # "08:30"
        time_end   = match.group(2)  # "19:30"
        return time_start, time_end
    return None, None


def parse_docente(raw: str) -> tuple[str, str]:
    """
    "BEDON CHIARA (014686)" -> ("BEDON CHIARA", "014686")
    """
    match = re.match(r"^(.+?)\s*\((\d+)\)$", raw.strip())
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return raw.strip(), "N/A"

def clean_nome_insegnamento(raw: str) -> str:
    """
    "ANALISI DELLE STRUTTURE (041AR - 2025 - [PDS0-2018 - Ord. 2018] comune - AC 3)"
    -> "ANALISI DELLE STRUTTURE"
    """
    return re.sub(r"\s*\(.*", "", raw).strip()

def clean_nome_corso(raw: str) -> str:
    """
    "ARCHITETTURA (AR03)" -> "ARCHITETTURA"
    """
    return re.sub(r"\s*\(.*", "", raw).strip()

def safe(value, fallback="N/A"):
    if value is None or str(value).strip() == "":
        return fallback
    return value