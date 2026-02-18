import argparse
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
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--depth", type=int, required=True, help="Depth limit")
    args = parser.parse_args()

    nome_file_input = f"../results/links_list_{args.depth}.txt"
    nome_file_output = f"../results/summary_domains_numbers_{args.depth}.txt"

    domini = conta_link_per_dominio(nome_file_input)

    # Scrive (sovrascrivendo ogni volta) il risultato nel file di output
    with open(nome_file_output, 'w', encoding='utf-8') as f:
        for dominio, conteggio in domini.most_common():
            f.write(f"{dominio}: {conteggio}\n")

    print(f"'{nome_file_output}' updated")
