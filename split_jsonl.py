#!/usr/bin/env python3
import sys
import os
from tqdm import tqdm
import shutil

CHUNK_SIZE = 8 * 1024 * 1024 * 1024  # 8GB

def split_jsonl(input_path, output_dir):
    if not os.path.isfile(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    # Delete folder if exists
    if os.path.exists(output_dir) and os.path.isdir(output_dir):
        shutil.rmtree(output_dir)
        print(f"Folder '{output_dir}' removed.")

    # Recreate folder
    os.makedirs(output_dir, exist_ok=True)

    part = 1

    bytes_written = 0
    out_file = open(os.path.join(output_dir, f"part_{part}.jsonl"), "wb")

    # get total size for progress bar
    total_size = os.path.getsize(input_path)

    with open(input_path, "rb") as infile, tqdm(total=total_size, unit='B', unit_scale=True, desc="Splitting") as pbar:
        for line in infile:
            if bytes_written + len(line) > CHUNK_SIZE:
                out_file.close()
                part += 1
                bytes_written = 0
                out_file = open(os.path.join(output_dir, f"item_{part}.jsonl"), "wb")
            out_file.write(line)
            bytes_written += len(line)
            pbar.update(len(line))

    out_file.close()
    print(f"Done. Created {part} files in {output_dir}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python split_jsonl.py <input_file> <output_dir>")
        sys.exit(1)

    split_jsonl(sys.argv[1], sys.argv[2])
