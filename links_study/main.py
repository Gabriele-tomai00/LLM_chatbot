from urllib.parse import urlparse
from collections import Counter

def conta_link_per_dominio(nome_file):
    contatore = Counter()

    with open(nome_file, 'r', encoding='utf-8') as file:
        for riga in file:
            url = riga.strip()
            if url:  # ignora righe vuote
                dominio = urlparse(url).netloc
                if dominio:
                    # Rimuove il prefisso 'www.' se presente
                    if dominio.startswith("www."):
                        dominio = dominio[4:]
                    contatore[dominio] += 1

    return contatore


if __name__ == "__main__":
    nome_file_input = "units_links.txt"
    nome_file_output = "domini_conteggi.txt"

    domini = conta_link_per_dominio(nome_file_input)

    # Scrive (sovrascrivendo ogni volta) il risultato nel file di output
    with open(nome_file_output, 'w', encoding='utf-8') as f:
        for dominio, conteggio in domini.most_common():
            f.write(f"{dominio}: {conteggio}\n")

    print(f"Risultato salvato in '{nome_file_output}' ✅")
