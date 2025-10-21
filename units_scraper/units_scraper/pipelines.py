# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
import w3lib.html
import os


class RemoveFooterAndExtractTextPipeline:
    def __init__(self):
        # Cartella dove salvare i file
        self.output_dir = "output_bodies"
        os.makedirs(self.output_dir, exist_ok=True)
        self.counter = 1  # Per creare nomi di file unici

    def process_item(self, item, spider):
        if 'body' in item:
            # Salva il body originale
            original_path = os.path.join(self.output_dir, f"{self.counter}_original.html")
            with open(original_path, "w", encoding="utf-8") as f:
                f.write(item['body'])

            cleaned_html = w3lib.html.remove_tags_with_content(item['body'], which_ones=('footer','script','style', 'meta', 'link', 'img'))
            cleaned_path = os.path.join(self.output_dir, f"{self.counter}_cleaned.html")
            with open(cleaned_path, "w", encoding="utf-8") as f:
                f.write(cleaned_html)

            # Aggiorna l'item con il body pulito (opzionale)
            item['body'] = cleaned_html

            # Incrementa il contatore per il prossimo file
            self.counter += 1

        return item

