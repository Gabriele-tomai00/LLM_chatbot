def rimuovi_link_con_at(nome_file_input, nome_file_output):
    with open(nome_file_input, 'r', encoding='utf-8') as f_in:
        link_filtrati = [riga for riga in f_in if '@' not in riga and 'orari.units' not in riga]

    # Salva i link filtrati nel file di output (sovrascrivendo se esiste)
    with open(nome_file_output, 'w', encoding='utf-8') as f_out:
        f_out.writelines(link_filtrati)

    print(f"Link filtrati salvati in '{nome_file_output}' ✅")


if __name__ == "__main__":
    nome_file_input = "units_all_links_with_depth_12.txt"
    nome_file_output = "links_filtrati.txt"

    rimuovi_link_con_at(nome_file_input, nome_file_output)
