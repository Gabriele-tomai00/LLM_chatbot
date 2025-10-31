Prima di eseguire questo codice, è necessario creare un ambiente Python dedicato (ad esempio utilizzando `venv` o `conda`). Su macos puoi fare:
```bash
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

```bash
    cd units_scraper
    scrapy crawl scraper -s DEPTH_LIMIT=3 -O items.jsonl
```  
```bash
    cd linkcrawler/linkcrawler/spiders
    python3 link_spider.py
```