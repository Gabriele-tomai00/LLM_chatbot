import argparse
import json
import os
import sys
from urllib.parse import urlparse

def sanitize_filename(url):
    """Create a safe filename from a URL."""
    parsed = urlparse(url)
    filename = parsed.netloc + parsed.path
    # Replace unsafe characters
    filename = "".join(c if c.isalnum() or c in ('-', '_', '.') else '_' for c in filename)
    # Remove leading/trailing underscores and limit length
    filename = filename.strip('_')[:100]
    if not filename:
        filename = "unknown_url"
    return filename

def main():
    parser = argparse.ArgumentParser(description="Extract markdown content from a JSONL file based on URL.")
    parser.add_argument("-d", "--depth", type=int, required=True, help="Depth value to identify the input file (e.g., 2 for results/filtered_items_2.jsonl)")
    parser.add_argument("-u", "--url", type=str, required=True, help="The URL to search for.")
    
    args = parser.parse_args()
    
    # Construct input filename
    input_filename = f"results/filtered_items_{args.depth}.jsonl"
    
    # Check if input file exists
    if not os.path.exists(input_filename):
        print(f"Error: Input file '{input_filename}' not found.")
        sys.exit(1)
        
    found = False
    target_url = args.url.strip()
    
    try:
        with open(input_filename, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                
                try:
                    data = json.loads(line)
                    current_url = data.get("url", "").strip()
                    
                    if current_url == target_url:
                        content = data.get("content", "")
                        if not content:
                            print(f"Warning: URL found but content is empty.")
                        
                        # Create output filename
                        safe_name = sanitize_filename(target_url)
                        output_filename = os.path.join("results", f"{safe_name}.md")
                        
                        # Ensure results directory exists (though it should since input is there)
                        os.makedirs("results", exist_ok=True)
                        
                        with open(output_filename, 'w', encoding='utf-8') as out_f:
                            out_f.write(content)
                            
                        print(f"Success! Content for URL '{target_url}' saved to:\n{output_filename}")
                        found = True
                        break
                        
                except json.JSONDecodeError:
                    print(f"Warning: Could not decode JSON on line {line_num}")
                    continue
                    
        if not found:
            print(f"URL '{target_url}' not found in '{input_filename}'.")
            
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
