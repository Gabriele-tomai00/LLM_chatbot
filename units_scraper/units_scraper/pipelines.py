# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
import w3lib.html
import os
from bs4 import BeautifulSoup

class RemoveFooterAndExtractTextPipeline:
    def process_item(self, item, spider):
        if 'body' in item:
            item['body'] = w3lib.html.remove_tags_with_content(item['body'], which_ones=('footer','script','style', 'meta', 'link', 'img'))
        return item

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

            cleaned_path = os.path.join(self.output_dir, f"{self.counter}_cleaned.html")
            with open(cleaned_path, "w", encoding="utf-8") as f:
                f.write(item['cleaned'])

            self.counter += 1

        return item