
import datetime
import json
import os
from bs4 import BeautifulSoup
import html2text
import re
import lxml.html as html
from scrapy.http import HtmlResponse
import unicodedata
import requests

def filter_response(response):
    tree = html.fromstring(response.text)
    
    tags_to_remove = ["footer", "script", "style", "meta", "link", "img"]
    for tag in tags_to_remove:
        for el in tree.xpath(f"//{tag}"):
            el.drop_tree()

    classes_to_remove = [
        "open-readspeaker-ui", "banner", "cookie-consent", 
        "nav-item dropdown", "clearfix navnavbar-nav",
        "clearfix menu menu-level-0", "sidebar", 
        "views-field views-field-link__uri", 
        "block block-layout-builder block-field-blocknodeeventofield-documenti-allegati",
        "visually-hidden-focusable", "clearfix dropdown-menu", "nav-link",
        "field__label visually-hidden", "field field--name-field-media-image field--type-image field--label-visually_hidden",
        "clearfix nav", "modal modal-search fade", "breadcrumb", "btn dropdown-toggle",
        "block block-menu navigation menu--menu-target", "view-content row"
    ]
    ids_to_remove = ["main-header", "footer-container"]

    for class_name in classes_to_remove:
        for el in tree.xpath(f'//*[@class="{class_name}"]'):
            el.drop_tree()
    for id_name in ids_to_remove:
        for el in tree.xpath(f'//*[@id="{id_name}"]'):
            el.drop_tree()

    cleaned_html = html.tostring(tree, encoding="unicode")
    soup = BeautifulSoup(cleaned_html, "lxml")
    for strong_tag in soup.find_all("strong"):
        strong_tag.unwrap()
    for tag in soup.find_all():
        if not tag.get_text(strip=True):
            tag.decompose()

    return HtmlResponse(
        url=response.url,
        body=str(soup),
        encoding='utf-8'
    )

def normalize_markdown(text: str) -> str:
    """Avoid problems in JSON line (in markdown) about special unicode characters."""
    if not text:
        return text

    replacements = {
        "’": "'",
        "‘": "'",
        "“": '"',
        "”": '"',
        "–": "-",
        "—": "-",
        "…": "...",
        "\u00A0": " ",  # space not-breaking
    }

    for old, new in replacements.items():
        text = text.replace(old, new)
    return unicodedata.normalize("NFKC", text)


def parse_html_content_html2text(response) -> str:
    h = html2text.HTML2Text()
    h.ignore_links = True          # <--- non stampa gli href
    h.ignore_images = True         # <--- nel dubbio
    h.body_width = 0               # <--- no wrapping forzato, più leggibile
    text = h.handle(response.text)
    #print(f"Cleaned content: {text}")
    return normalize_markdown(text)



if __name__ == "__main__":
    url = "https://ciamician.dia.units.it/it/ricerca/progetti-finanziati-dal-centro"
    try:
        response = requests.get(url, verify=False)  # <- disabilita la verifica SSL
        cleaned_response = filter_response(response)

        res = parse_html_content_html2text(cleaned_response)
        print(res)
            # Salva i link filtrati nel file di output (sovrascrivendo se esiste)
        with open("test.md", 'w', encoding='utf-8') as f_out:
            f_out.writelines(res)

    except requests.exceptions.RequestException as e:
        print(f"Si è verificato un errore: {e}")
