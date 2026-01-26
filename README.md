## ⚠️ Project Status Notice ⚠️
This repository is **in high development** and is **not even in alpha**.  
Please **do not consult or use this repository**, as the code is incomplete, unstable, and strictly for internal development purposes at this time.

---

The project consists of a local AI-based chatbot that answers questions related to the University of Trieste (for students and staff).
It is divided into 3 main phases:
- retrieving information from university websites via scraping
- creating a RAG for question processing
- Integrating the RAG with a local LLM (e.g. Ollama) for response generation

<!-- 
Install the following programs (on Ubuntu):
```bash
    curl -fsSL https://ollama.com/install.sh | sh
    sudo apt install python3-scrapy -y
```
Before running this code, you need to create a dedicated Python environment (e.g. using `venv` or `conda`). On Linux/macOS you can do:
```bash
    sudo apt-get install python3.10-venv -y
    python3 -m venv env
    source env/bin/activate 
```
and install all required dependencies by running the command:
```bash
    pip install -r requirements.txt
```

# Execution
## Fetching Class Schedule 
Possible parameters:  
--start_date: Start date in dd-mm-yyyy format  
--end_date: End date in dd-mm-yyyy format
--num_departments: to be specified during testing or if you only want a subset of departments. Specify only the number (e.g., 3 scrapes only the first 3 departments in the list). 0 means all.
```bash
    python3 orari_UNITS/fetch_orario_lezioni.py
```
## Fetching Room Occupation Calendar:
Possible parameters:  
--start_date: Start date in dd-mm-yyyy format  
--end_date: End date in dd-mm-yyyy format

```bash
    python3 occupazione_aule/fetch_calendario_aule.py
```
## Scraping links from units:
A .env file in the root is required with the following format:
```
SCRAPY_PROXY_URL=https://ip:port
SCRAPY_PROXY_USER=username
SCRAPY_PROXY_PASS=password
SCRAPY_PROXY_RATE=0.4
```
The proxy rate ranges from 0.0 to 1.0 and indicates the percentage of requests to make via the proxy.
You can start the scraper with the following commands:

```bash
    cd units_scraper
    scrapy crawl scraper -s DEPTH_LIMIT=1 -O ../items.jsonl
```
Options:
```
-s ROTARY_USER_AGENT    enable user agent rotation
-s USE_PROXY            enable proxy usage for a % of total requests
```
## HTML to Markdown Conversion:
To be executed after scraping
```bash
    python pages_cleaner.py --input items.jsonl --output filtered_items.jsonl --verbose
```

# RAG:
```bash
    cd rag
    python3 rag.py
```
Options:
```
--create-index-from     input file to create the index to save to disk (slow) (e.g.: create-index-from="../results/filtered_items.jsonl")
--delete-index          delete the index
-m                      provide the message
```
Examples:
```
python3 rag.py --message "what are the departments of the university of Trieste?"
``` 
-->
