
Installare i seguenti programmi (su ubuntu)
```bash
    curl -fsSL https://ollama.com/install.sh | sh
    sudo apt install python3-scrapy -y
```
Prima di eseguire questo codice, è necessario creare un ambiente Python dedicato (ad esempio utilizzando `venv` o `conda`). Su macos puoi fare:
```bash
    sudo apt-get install python3.10-venv -y
    python3 -m venv env
    source env/bin/activate 
```
e installare tutte le dipendenze richieste eseguendo il comando:
```bash
    pip install -r requirements.txt
```

# Esecuzione
## Recupero calendario lezioni 
Parametri possibili:  
--start_date: Data di inizio nel formato dd-mm-yyyy  
--end_date: Data di fine nel formato dd-mm-yyyy
--num_departments: da specificare in fase di test o se vogliamo solo una parte dei dipartimenti, ma si può indicare solo il numero (es: 3 fa lo scraping solo dei primi 3 dipartimenti presenti in lista). 0 vuol dire tutti
```bash
    python3 orari_UNITS/fetch_orario_lezioni.py
```
## Recupero calendario occupazione aule:
Parametri possibili:  
--start_date: Data di inizio nel formato dd-mm-yyyy  
--end_date: Data di fine nel formato dd-mm-yyyy

```bash
    python3 occupazione_aule/fetch_calendario_aule.py
```
## Scraping link da units:
È richiesto un file .env nella root di questo tipo:
```
SCRAPY_PROXY_URL=https://ip:port
SCRAPY_PROXY_USER=username
SCRAPY_PROXY_PASS=password
SCRAPY_PROXY_RATE=0.4
```
Il proxy rate va da 0.0 a 1.0 e serve per indicare la percentuale di richieste che si vuole fare con il proxy.
È possibile avviare lo scaper con i seguenti comandi:

```bash
    cd units_scraper
    scrapy crawl scraper -s DEPTH_LIMIT=1 -O ../items.jsonl
```
Opzioni:
```
-s ROTARY_USER_AGENT    attivare la rotazione dello user agent
-s USE_PROXY            attivare la possibilità di usare il proxy per una % di request sul totale
```
## Conversione da html a markdown:
da eseguire dopo lo scraping
```bash
    python pages_cleaner.py --input items.jsonl --output filtered_items.jsonl --verbose
```

# RAG:
```bash
    cd rag
    python3 rag.py
```
Opzioni:
```
--create-index-from     file di input per creare l'index da salvare su disco (lento) (es: create-index-from="../results/filtered_items.jsonl")
--delete-index          cancellare l'index
-m                      forumare il messaggio
```
Exemples:
```
python3 rag.py --message "quali sono i dipartimenti dell'universita di Trieste?"
```