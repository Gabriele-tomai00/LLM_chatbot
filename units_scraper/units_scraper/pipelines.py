# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
import w3lib.html
import os
import shutil
from bs4 import BeautifulSoup
import html2text
from urllib.parse import urlparse

import json
import os

ITEM_CHECK_INTERVAL = 10000        # Check file size every N items
CHUNK_MAX_BYTES = 8 * 1024**3     # 8 GB

class MultiFileJsonPipeline:
    def open_spider(self, spider):
        self.output_dir = getattr(spider, "output_dir", "../results/scraper_results")
        # Clear output folder at start
        if os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir)
        os.makedirs(self.output_dir, exist_ok=True)

        self.part = 1
        self.counter = 0
        self.global_item_count = 0
        self._open_new_file()

    def _open_new_file(self):
        if hasattr(self, "file") and self.file:
            self.file.close()

        self.current_filename = os.path.join(self.output_dir, f"part_{self.part}.jsonl")
        self.file = open(self.current_filename, "w", encoding="utf-8")
        print(f"Opened new chunk: part_{self.part}.jsonl")
        self.part += 1
        self.counter = 0

    def process_item(self, item, spider):
        line = json.dumps(item, ensure_ascii=False) + "\n"
        self.file.write(line)
        self.counter += 1
        self.global_item_count += 1

        # Check file size only every ITEM_CHECK_INTERVAL items
        if self.global_item_count % ITEM_CHECK_INTERVAL == 0:
            file_size = os.path.getsize(self.current_filename)
            if file_size >= CHUNK_MAX_BYTES:
                print(f"Chunk reached {file_size/1024**3:.2f} GB, rotating file...")
                self._open_new_file()

        return item

    def close_spider(self, spider):
        if self.file:
            self.file.close()
        print("All items written, spider closed.")



class cleanContentPipeline:
    def process_item(self, item, spider):
        soup = BeautifulSoup(item.text, "lxml")
        to_return = {}
        to_return['body'] = item.text
        to_return['cleaned'] = soup.body.get_text(strip=True)
        return to_return

class saveBodyPipeline:
    def __init__(self):
        self.output_dir = "output_bodies"
        os.makedirs(self.output_dir, exist_ok=True)
        self.counter = 1  # Per creare nomi di file unici

    def process_item(self, item, spider):
        if 'body' in item:
            original_path = os.path.join(self.output_dir, f"{self.counter}_original.html")
            with open(original_path, "w", encoding="utf-8") as f:
                f.write(item['body'])

            parsed_url = urlparse(item.url)
            domain = parsed_url.netloc
            cleaned_path = os.path.join(self.output_dir, f"{self.counter}{domain}.html")
            with open(cleaned_path, "w", encoding="utf-8") as f:
                f.write(item['cleaned'])

            self.counter += 1

        return item
    

class getMetadataPipeline:
    def process_item(self, item, spider):
        return item

class html2textPipeline:
    def process_item(self, item, spider):
        h = html2text.HTML2Text()
        h.ignore_links = True          # <--- non stampa gli href
        h.ignore_images = True         # <--- nel dubbio
        h.body_width = 0               # <--- no wrapping forzato, più leggibile
        # item['content'] = h.handle(item['body'])
        del item["body"]
        return item
    

class saveWebpagePipeline:
    def __init__(self):
        self.output_dir = "output_bodies"
        if os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir)  # cancella TUTTA la cartella
        os.makedirs(self.output_dir, exist_ok=True)
        self.counter = 1  # Per creare nomi di file unici

    def process_item(self, item, spider):
        original_path = os.path.join(self.output_dir, f"{self.counter}_original.html")
        with open(original_path, "w", encoding="utf-8") as f:
            f.write(item['body'])

        cleaned_path = os.path.join(self.output_dir, f"{self.counter}_cleaned.html")
        with open(cleaned_path, "w", encoding="utf-8") as f:
            f.write(item['content'])

        self.counter += 1
        return item
    

class saveLinksPipeline:
    def __init__(self):
        self.file_path = "../results/units_links.txt"
        with open(self.file_path, "w") as f:
            pass

    def process_item(self, item, spider):
        if 'url' in item:
            with open(self.file_path, "a") as f:
                f.write(item['url'] + "\n")
        return item