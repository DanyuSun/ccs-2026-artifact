import pandas as pd
from collections import defaultdict
import json
import os
from datetime import datetime
import pytz
import glob
from tqdm import tqdm
import argparse

def build_profiles(log_files):
    profiles = defaultdict(int)  # flat dictionary

    

    for log_file in log_files:
        print(f"Reading log file: {os.path.basename(log_file)}")

        total_rows = sum(1 for _ in open(log_file, 'r')) - 1
        chunks = pd.read_csv(log_file, chunksize=10000)
        chunk_list = []

        with tqdm(total=total_rows, desc="Reading CSV") as pbar:
            for chunk in chunks:
                chunk_list.append(chunk)
                pbar.update(len(chunk))

        df = pd.concat(chunk_list, ignore_index=True)

        print("Building profiles...")
        for _, row in tqdm(df.iterrows(), total=len(df), desc="Processing entries"):
            path = row['process_cmdline'] if 'process_cmdline' in row and pd.notna(row['process_cmdline']) else ""
            if path:
                profiles[path] += 1

    return profiles

def save_profiles(profiles, output_filename):
    import json

    # Directly save the flat dictionary
    with open(output_filename, 'w') as f:
        json.dump(profiles, f, indent=2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-input_dir", type=str, required=True)   
    parser.add_argument("-output_filename", type=str, required=True)
    args = parser.parse_args()

    input_dir = args.input_dir  
    output_filename = args.output_filename

    # Build profiles from all matching CSV files
    profiles = build_profiles([input_dir])
    save_profiles(profiles, output_filename)

if __name__ == "__main__":
    main()