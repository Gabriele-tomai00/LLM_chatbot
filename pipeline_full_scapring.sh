# exemple
# ./pipeline_full_scapring.sh -d 2 -s "02-02-2026" -e "10-02-2026"

# --- Default parameters ---
DEPTH_LIMIT=4
START_DATE="02-01-2026"
END_DATE="10-07-2026"
OUTPUT_DIR="results_custom_scapers"


#!/bin/bash
set -e

ENV_DIR="env"
REQUIREMENTS_FILE="requirements.txt"


# --- Parse arguments ---
while [[ $# -gt 0 ]]; do
    case "$1" in
        --depth|-d)
            DEPTH_LIMIT="$2"
            shift 2
            ;;
        --start_date|-s)
            START_DATE="$2"
            shift 2
            ;;
        --end_date|-e)
            END_DATE="$2"
            shift 2
            ;;
        *)
            echo "Unknown parameter: $1"
            exit 1
            ;;
    esac
done

echo "Using DEPTH_LIMIT = $DEPTH_LIMIT"
echo "Using START_DATE = $START_DATE"
echo "Using END_DATE = $END_DATE"

# --- Check/Create Virtual Environment ---
if [[ ! -d "$ENV_DIR" ]]; then
    echo "Virtual environment not found. Creating it in '$ENV_DIR'..."
    python3 -m venv "$ENV_DIR"

    echo "Virtual environment created. Activating it and installing requirements..."
    source "$ENV_DIR/bin/activate"

    if [[ -f "$REQUIREMENTS_FILE" ]]; then
        pip install --upgrade pip
        pip install -r "$REQUIREMENTS_FILE"
    else
        echo "WARNING: requirements.txt not found. Continuing without installing packages."
    fi
else
    echo "Virtual environment already exists."

    if [[ -z "$VIRTUAL_ENV" ]]; then
        echo "Activating virtual environment..."
        source "$ENV_DIR/bin/activate"
    else
        echo "Virtual environment already active: $VIRTUAL_ENV"
    fi
fi

# --- Delete old results ---
echo -e "\nDelete old results"
mkdir -p results
cd results
rm -rf scraper_results_${DEPTH_LIMIT} filtered_items_${DEPTH_LIMIT}.jsonl summary_domains_numbers_${DEPTH_LIMIT}.txt links_list_${DEPTH_LIMIT}.txt
rm -rf teams_codes.json
rm -rf units_book.json
rm -rf room_schedule_per_site
rm -rf lessons_schedule_by_course
cd ..


./pipeline_scapring.sh -d $DEPTH_LIMIT

# --- Address book ---
echo -e "\n\n\nADDRESS BOOK SCRAPER"
cd custom_scraper_for_specific_data
python3 fetch_rubrica_personale.py --output="../$OUTPUT_DIR/units_book.json"
cd ..

# --- Occupazione Aule ---
echo -e "\n\n\nOCCUPAZIONE AULE SCRAPER"
cd custom_scraper_for_specific_data
python3 fetch_calendario_aule.py --start_date "$START_DATE" --end_date "$END_DATE" --output="../$OUTPUT_DIR/room_schedule_per_site"
# esemple: python3 fetch_calendario_aule.py --start_date "02-02-2026" --end_date "10-02-2026" --output="../results_custom_scapers/room_schedule_per_site" --num_sites 1
cd ..

# --- Orario lezioni ---
echo -e "\nOrario lezioni scraper"
cd custom_scraper_for_specific_data
python3 fetch_orario_lezioni.py --start_date "$START_DATE" --end_date "$END_DATE" --output="../$OUTPUT_DIR/lessons_schedule_by_course"
# esemple: python3 fetch_orario_lezioni.py --start_date "02-02-2026" --end_date "10-02-2026" --num_departments 1 --output="../results_custom_scapers/lessons_schedule_by_course"
cd ..

# --- Teams codes ---
echo -e "\nTeams codes scraper"
cd custom_scraper_for_specific_data
python3 teams_code_downloader.py -o "../$OUTPUT_DIR/teams_codes.json"
