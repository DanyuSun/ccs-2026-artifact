import json
import os
import random
from collections import defaultdict
import argparse

def sample_items(items_dict, threshold, keep_ratio=0.5):
    if len(items_dict) <= threshold:
        return items_dict
    
    sorted_items = sorted(items_dict.items(), key=lambda x: x[1], reverse=True)
    
    keep_count = int(threshold * keep_ratio)
    top_items = dict(sorted_items[:keep_count])
    
    # Randomly sample from the rest
    sample_count = min(threshold - keep_count, len(sorted_items) - keep_count)
    if sample_count > 0:
        remaining = dict(random.sample(sorted_items[keep_count:], sample_count))
        return {**top_items, **remaining}
    else:
        return top_items

def condense_json(input_file, output_file, path_threshold=50, addr_threshold=50):
    with open(input_file, 'r') as f:
        data = json.load(f)
    
    print(f"Loaded {len(data)} processes from input file")
    

    condensed_data = {}
    
    
    for subject, interactions in data.items():
        condensed_data[subject] = {
            "paths": {},
            "addresses": {}
        }
        
        # Collect paths and addresses with their frequencies
        path_dict = {}
        addr_dict = {}

        print(interactions)
        exit()
        
        for obj, freq in interactions.items():
            if obj.startswith("path:"):
                path = obj[5:] 

                if not path or path == "<unknown>":
                    continue
                    
                path_dict[path] = freq
                
            elif obj.startswith("addr:"):
                addr = obj.split(',')[0][5:]   
                addr_dict[addr] = freq
        
        # Sample paths if they exceed threshold
        if len(path_dict) > path_threshold:
            print(f"Sampling {path_threshold} paths from {len(path_dict)} for {subject}")
            path_dict = sample_items(path_dict, path_threshold)
        
        # Sample addresses if they exceed threshold
        if len(addr_dict) > addr_threshold:
            print(f"Sampling {addr_threshold} addresses from {len(addr_dict)} for {subject}")
            addr_dict = sample_items(addr_dict, addr_threshold)
        
        # Add to condensed data
        if path_dict:
            condensed_data[subject]["paths"] = path_dict
        else:
            del condensed_data[subject]["paths"]
            
        if addr_dict:
            condensed_data[subject]["addresses"] = addr_dict
        else:
            del condensed_data[subject]["addresses"]
        
        # Remove empty collections
        if not condensed_data[subject].get("paths") and not condensed_data[subject].get("addresses"):
            del condensed_data[subject]
    
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
    
    # Write the condensed data to output file with proper formatting
    with open(output_file, 'w') as f:
        json.dump(condensed_data, f, indent=4)
    
    print(f"Condensed data saved to {output_file}")
    
    # Calculate compression statistics
    original_size = os.path.getsize(input_file)
    condensed_size = os.path.getsize(output_file)
    compression_ratio = (1 - (condensed_size / original_size)) * 100
    
    print(f"Original file size: {original_size:,} bytes")
    print(f"Condensed file size: {condensed_size:,} bytes")
    print(f"Compression ratio: {compression_ratio:.2f}%")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-input_file", type=str, required=True)
    parser.add_argument("-condensed_file", type=str, required=True)
    args = parser.parse_args()

    input_file = args.input_file
    condensed_file = args.condensed_file


    # input_file = "data/cadets-e3-profiles.json"
    # condensed_file = "data/cadets-e3-profiles-condensed.json"
    
    # Add thresholds as parameters
    condense_json(input_file, condensed_file, path_threshold=20, addr_threshold=20)
