# Filter links matching dmg.units.it domain
def filter_links(input_file, output_file):
    with open(input_file, 'r') as f:
        links = f.readlines()
    
    with open(output_file, 'w') as f_out:
        for link in links:
            link = link.strip()
            if "dia.units.it" in link:
                f_out.write(link + "\n")

if __name__ == "__main__":
    filter_links("results/links_list.txt", "output.txt")
    print("Filtered links saved to output.txt")
