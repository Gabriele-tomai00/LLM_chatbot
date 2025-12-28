#!/bin/bash
set -e

ENV_DIR="env"
REQUIREMENTS_FILE="requirements.txt"

# --- Default depth limit ---
DEPTH_LIMIT=4

# --- Parse arguments ---
while [[ $# -gt 0 ]]; do
    case "$1" in
        --depth|-d)
            DEPTH_LIMIT="$2"
            shift 2
            ;;
        *)
            echo "Unknown parameter: $1"
            exit 1
            ;;
    esac
done

echo "Using DEPTH_LIMIT = $DEPTH_LIMIT"

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

mkdir -p results

# --- Scraping part ---
cd units_scraper
scrapy crawl scraper -s DEPTH_LIMIT="$DEPTH_LIMIT" -O ../results/items.jsonl -a save_each_file=False

cd ../links_study

echo "Run domains_numbers.py"
python3 domains_numbers.py

# --- Cleaning part ---
cd ..
echo -e "\nSplit file if too big"
python3 split_jsonl.py results/items.jsonl results/scraper_results/

echo -e "\nRun pages_cleaner.py"
python3 pages_cleaner.py --input results/scraper_results/ --output results/filtered_items.jsonl --verbose

# --- RAG: create index ---
echo -e "\nCreation of RAG index in progress..."
cd rag
python3 llm_query.py --create-index-from ../results/filtered_items.jsonl"