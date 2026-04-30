import random
import json
import argparse

def stratified_sampling(input_file, sample_ratio=0.5, min_samples=5):
    with open(input_file, 'r') as f:
        data = json.load(f)  # flat: {path: count}

    path_list = list(data.items())

    # Sort by frequency (descending)
    path_list.sort(key=lambda x: x[1], reverse=True)

    print(len(path_list))

    # Determine sample size
    sample_size = max(min_samples, int(len(path_list) * sample_ratio))

    print(sample_size)

    # Split into 3 strata
    third = sample_size // 3
    high_freq = path_list[:third]
    mid_freq = path_list[third:2*third]
    low_freq = path_list[2*third:]

    # Sample from each stratum
    sampled_high = random.sample(high_freq, min(len(high_freq), third))
    sampled_mid = random.sample(mid_freq, min(len(mid_freq), third))
    sampled_low = random.sample(low_freq, sample_size - len(sampled_high) - len(sampled_mid))

    # Combine samples
    sampled_data = {k: v for k, v in sampled_high + sampled_mid + sampled_low}

    return sampled_data


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-input_file", type=str, required=True)
    parser.add_argument("-condensed_file", type=str, required=True)
    args = parser.parse_args()

    input_file = args.input_file
    condensed_file = args.condensed_file
    
    # Add thresholds as parameters
    sampled_rag = stratified_sampling(input_file, sample_ratio=0.5, min_samples=5)

    with open(condensed_file, 'w') as f:
        json.dump(sampled_rag, f, indent=4)


