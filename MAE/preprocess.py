import argparse
import random
import pandas as pd
from pathlib import Path
random.seed(42)

from transformers import AutoTokenizer
from datasets import Dataset  
import numpy as np
import nltk

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv_path", type=str, default=None)
    parser.add_argument("--data", type=str, default="benign")
    parser.add_argument("--tokenizer_name", type=str, default="bert-base-uncased")
    parser.add_argument("--output_dir", type=str)
    parser.add_argument("--max_seq_length", type=int, default=512)
    parser.add_argument("--short_seq_prob", type=float, default=0)
    parser.add_argument("--columns", type=str, default=None)

    return parser.parse_args()

def create_title_and_text(csv_path, columns_to_include):
    df = pd.read_csv(csv_path) 

    ########### for cadets dataset ########### 
    darpa_data = ['cadets', 'theia', 'trace', 'a1'] 
    if any(word in csv_path for word in darpa_data):
        df['process_id'] = df.index 
    
    nodlink_data = ['hw20', 'win10', 'hw17']

    examples = []
    for _, row in df.iterrows():
        process_id = row['process_id'] # add process id 
        
        if any(word in csv_path for word in darpa_data):
            ########### for darpa ###########
            cmd = row['path']  # Add cmd
            title = f"path: {row['path']}"
        elif any(word in csv_path for word in nodlink_data):
            cmd = row['cmd']  # Add cmd
            title = f"path: {row['cmd']}"
        else:
            ########### for atlasv2 ###########
            cmd = row['target_process_path']  # Add cmd
            title = f"path: {row['target_process_path']}"



        if columns_to_include == None:
            text_parts = " "
            text = " "
        else:
            # text_parts = [f"{col}: {row[col]}" for col in columns_to_include if col in row]
            text_parts = [f"{row[col]}" for col in columns_to_include if col in row]
            text = ", ".join(text_parts)
        examples.append({"process_id": process_id, "cmd": cmd, "title": title, "text": text})
    return examples

def create_passage_data(tokenizer_name: str, max_seq_length: int, csv_path: str, short_seq_prob: float = 0.0,  columns_to_include=None):
 
    nltk.download('punkt_tab')
    nltk.download('punkt')
    print("columns_to_include: ", columns_to_include)
    # print("csv_path: ", csv_path)

    tokenizer = AutoTokenizer.from_pretrained(tokenizer_name)
    target_length = max_seq_length - tokenizer.num_special_tokens_to_add(pair=False)

    def passage_tokenize_function(examples):
  
        if len(examples['title']) > 2:
            text = examples['title'] + ' ' + examples['text']
        else:
            text = examples['text']
        # print("-----------text------------")
        # print(text)
        # exit()
        #  split the combined text into sentences
        ##### make the text into some sentences. 
        sentences = nltk.sent_tokenize(text)
        # print("--------------sentences------------")
        # print(sentences)
        # tokenizer conver the list of sentence into token IDs                        
        return tokenizer(sentences, add_special_tokens=False, truncation=False, return_attention_mask=False,
                         return_token_type_ids=False)

    def passage_pad_each_line(examples):
        blocks = []
        for sents in examples['input_ids']:
            curr_block = []
            curr_tgt_len = target_length if random.random() > short_seq_prob else random.randint(3,
                                                                                                 target_length)
            for sent in sents:
                if len(curr_block) >= curr_tgt_len:
                    blocks.append(curr_block)
                    curr_block = []
                    curr_tgt_len = target_length if random.random() > short_seq_prob \
                        else random.randint(3, target_length)
                curr_block.extend(sent)
            if len(curr_block) > 0:
                blocks.append(curr_block)
        return {'token_ids': blocks}

    # Load dataset from CSV if provided
    # if csv_path and columns_to_include:
    print("csv_path: ", csv_path)


    examples = create_title_and_text(csv_path, columns_to_include)
    dataset = Dataset.from_pandas(pd.DataFrame(examples))
    # else:
    #     # Download dataset from huggingface if CSV is not provided
    #     dataset = load_dataset("Tevatron/msmarco-passage-corpus", split="train", cache_dir="/mnt/2_data_center/danyu/retromae/msmarco-passage-corpus")
    #     dataset = dataset.remove_columns("docid")

    tokenized_dataset = dataset.map(passage_tokenize_function, num_proc=8, remove_columns=["text", "title"])
    processed_dataset = tokenized_dataset.map(passage_pad_each_line, num_proc=8, batched=True, batch_size=None,
                                              remove_columns=["input_ids"])

    return processed_dataset, examples

def convert_labels_to_npy(input_df, output_npy, use_numeric_labels=False):
    # Read the CSV file
    data = input_df

    # Ensure 'label' column exists in the CSV
    if 'is_warn' not in data.columns:
        raise ValueError("The CSV file does not contain a 'label' column.")

    # Convert labels to numeric values
    labels = data['label'].copy()
    labels = labels.map(lambda x: 1 if x == False else -1)

    # print(labels)
    # Convert labels to a NumPy array with integer values
    labels_array = np.array(labels, dtype=int)
    print("label length: ",len(labels_array))
    # unique_values, counts = np.unique(labels_array, return_counts=True)

    # print(unique_values)
    # print(counts)

    # Save as .npy file
    np.save(output_npy, labels_array)
    print(f"Labels saved to {output_npy}")


if __name__ == '__main__':
    args = get_args()
    Path(args.output_dir).mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(args.csv_path)

    ### adding 'process_id' for darpa data
    darpa_data = ['cadets', 'theia', 'trace', 'a1']
    if args.data in darpa_data:
        df['process_id'] = df.index 
    
    if args.columns == "base":
        args.columns = " "

    columns_to_include = args.columns.split(',') if args.columns else None
    print("columns_to_include: ", columns_to_include)
    
    dataset, examples = create_passage_data(args.tokenizer_name, args.max_seq_length, args.csv_path, args.short_seq_prob, columns_to_include)
    dataset.save_to_disk(args.output_dir)
    # df = pd.DataFrame(examples)
    # df.to_csv(f"pretrain_data/benign_{args.data}/examples_{args.data}.csv", index=False)

 