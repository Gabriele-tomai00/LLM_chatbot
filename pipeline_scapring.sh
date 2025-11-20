#!/bin/bash
set -e  # Stop the script immediately if any command fails

ENV_DIR="env"
REQUIREMENTS_FILE="requirements.txt"

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

    # If the environment is not active, activate it
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
#scrapy crawl scraper -s DEPTH_LIMIT=1 -O ../results/items.jsonl -a save_each_file=False

cd ../links_study

echo "Run domains_numbers.py"
python3 domains_numbers.py


# --- Cleaning part ---
cd ..
echo -e "\nRun pages_cleaner.py"
python3 pages_cleaner.py --input results/items.jsonl --output results/filtered_items.jsonl --verbose


# --- RAG: create index ---
echo -e "\nCreation of RAG index in progress..."
cd rag
python3 rag.py --create-index-from "../results/filtered_items.jsonl"
#echo -e "\nQuestion: quali sono i dipartimenti dell'universita di Trieste?"
#python3 rag.py --message "quali sono i dipartimenti dell'universita di Trieste?"
