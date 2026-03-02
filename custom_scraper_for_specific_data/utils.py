import datetime

def format_iso_date_to_italian_long(iso_date):
    """
    Converts an ISO 8601 date (YYYY-MM-DD) to a readable Italian format like '25 marzo 2036'.
    """
    try:
        date_obj = datetime.datetime.strptime(iso_date, "%Y-%m-%d")
        
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
    date_obj = datetime.datetime.strptime(iso_date, "%Y-%m-%d")
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
        date_obj = datetime.datetime.strptime(date_str, "%d-%m-%Y")
        # Format the datetime object as ISO 8601 string
        iso_date = date_obj.strftime("%Y-%m-%d")
        return iso_date
    except ValueError:
        # Handle invalid date format
        return None
