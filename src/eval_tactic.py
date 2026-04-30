import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from transformers import DistilBertTokenizer, DistilBertModel
import torch
from sklearn.metrics import f1_score, matthews_corrcoef
import argparse
import re
import glob

def extract_attack_narrative_llama(file_path):
    # print(file_path)
    with open(file_path, "r", encoding="utf-8") as file:
        content = file.read()
    
    ioc_section = content.split("=== RESPONSE ===")[-1]
    key_steps_block = re.search(r"Key Steps(.*?)\n\n|\Z", ioc_section, re.DOTALL)
     
    if key_steps_block:
        steps_text = key_steps_block.group(1).strip()
        key_steps = re.findall(r"Step\s+\d+\s+-\s+([\w\s]+?):\s+(.*)", steps_text)

    original_steps = {step_type.lower(): description for step_type, description in key_steps}
    return original_steps

def extract_attack_narrative_sonar(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        content = file.read()
    
    ioc_section = content.split("=== RESPONSE ===")[-1]

    key_steps_block = re.search(r"\*\*Key Steps\*\*(.*?)(\n\n|\Z)", ioc_section, re.DOTALL)
    if key_steps_block:
        steps_text = key_steps_block.group(1).strip()

        # Merge multiline entries (if needed)
        lines = steps_text.splitlines()
        merged = []
        buffer = ""
        for line in lines:
            if re.match(r"\d+\.\s+\*\*", line):
                if buffer:
                    merged.append(buffer.strip())
                buffer = line
            else:
                buffer += " " + line
        if buffer:
            merged.append(buffer.strip())

        key_steps = re.findall(r"\d+\.\s+\*\*(.*?)\*\*\s+-\s+(.*)", "\n".join(merged))
        original_steps = {step_type.strip().lower(): description.strip() for step_type, description in key_steps}
    return original_steps



def extract_attack_narrative_o3(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        content = file.read()
    
    ioc_section = content.split("=== RESPONSE ===")[-1]
    key_steps_block = re.search(r"Key Steps(.*?)\n\n|\Z", ioc_section, re.DOTALL)
    if key_steps_block:
        steps_text = key_steps_block.group(1).strip()
        key_steps = re.findall(r"Step \d+\s*–\s*(.*?): (.*)", steps_text)
        original_steps = {step_type.lower(): description for step_type, description in key_steps}
    return original_steps



def extract_attack_narrative_r1(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        content = file.read()
    
    ioc_section = content.split("=== RESPONSE ===")[-1]
  

    key_steps_block = re.search(r"\*\*Key Steps\*\*(.*?)(\n\n|\Z)", ioc_section, re.DOTALL)
    if key_steps_block:
        steps_text = key_steps_block.group(1).strip()

        # Merge multiline descriptions
        lines = steps_text.splitlines()
        merged = []
        buffer = ""
        for line in lines:
            if re.match(r"\d+\.\s+\*\*", line):
                if buffer:
                    merged.append(buffer.strip())
                buffer = line
            else:
                buffer += " " + line
        if buffer:
            merged.append(buffer.strip())

        # Extract using pattern like: 1. **Tactic** – Description
        key_steps = re.findall(r"\d+\.\s+\*\*(.*?)\*\*\s+–\s+(.*)", "\n".join(merged))    

        # Save as dictionary
        original_steps = {step_type.strip().lower(): description.strip() for step_type, description in key_steps}
        for k, v in original_steps.items():
            print(f"{k}: {v}")

        
    # original_steps = {step_type.lower(): description for step_type, description in key_steps}

    return original_steps


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-data", type=str, default="s1")
    parser.add_argument("-model", type=str, default="r1")

    args = parser.parse_args()
    data = args.data
    model = args.model

    # original_steps = {}
    if data == "s1":
        original_steps = {
            "initial access": "The user logs in to Gmail and opens a malicious email containing a link to `http://0xevil.com:9999`, exploiting user interaction to deliver the attack.",
            "execution": "Upon clicking the link, the victim’s browser—vulnerable to a Flash exploit—executes code from the attacker-controlled website.",
            "command and control": "A connection is established to `0xevil.com:8888` to fetch and inject a Meterpreter HTTPS payload into the Firefox process.",
            "discovery": "The attacker uses the Meterpreter session to gather system and user information from the compromised host.",
            "persistence": "An additional payload (`payload.exe`) is dropped onto the system to maintain access and possibly automate further actions.",
            "collection": "The payload searches the victim's system for high-profile PDF files to prepare them for exfiltration.",
            "exfiltration": "The payload opens an HTTPS connection to `0xevil.com:8080` and sends the collected PDF files to the attacker."
        }

    import json

    file_path = "./example_result/r1_s1_20250421_221506.txt"
    # print(file_path)
    
    # if model == "llama":
    
    key_steps = extract_attack_narrative_sonar(file_path)
    # print(key_steps)

    key_steps_json = json.dumps(original_steps, indent=4)

    def calculate_cosine_similarity(text1, text2):
        vectorizer = TfidfVectorizer(stop_words='english')
        tfidf_matrix = vectorizer.fit_transform([text1, text2])
        return cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]


    # Initialize the DistilBERT tokenizer and model
    tokenizer = DistilBertTokenizer.from_pretrained('distilbert-base-uncased')
    model = DistilBertModel.from_pretrained('distilbert-base-uncased')

    # Function to get embeddings using DistilBERT
    def get_bert_embedding(text):
        inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=512)
        with torch.no_grad():
            outputs = model(**inputs)
        # Get the embeddings for the [CLS] token (first token in the sequence)
        embedding = outputs.last_hidden_state[:, 0, :]
        return embedding

    # Function to calculate cosine similarity between BERT embeddings
    def calculate_bert_cosine_similarity(text1, text2):
        embedding1 = get_bert_embedding(text1)
        embedding2 = get_bert_embedding(text2)
        return cosine_similarity(embedding1.cpu().numpy(), embedding2.cpu().numpy())[0][0]


    # Define function to compare steps
    def compare_steps(original_steps, key_steps):
        matches = {}
        FN = 0  # Initialize FN counter
        y_true = []  # True labels (1 for match, 0 for mismatch)
        y_pred = []  # Predicted labels (1 for match, 0 for mismatch)
        
        for step in original_steps:
            original_description = original_steps[step]
            
            if step in key_steps:
                key_description = key_steps[step]
                # Exact match (optional, depending on your needs)
                if original_description.lower() == key_description.lower():
                    matches[step] = 1  # TP (exact match)
                    y_true.append(1)
                    y_pred.append(1)
                else:
                    # If exact match doesn't work, use BERT-based cosine similarity for semantic match
                    similarity = calculate_bert_cosine_similarity(original_description, key_description)
                    if similarity > 0.7:  # Define threshold for matching (0.7 means 70% similarity)
                        matches[step] = 1  # TP (semantic match)
                        y_true.append(1)
                        y_pred.append(1)
                    else:
                        matches[step] = 0  # FP (mismatch)
                        y_true.append(1)
                        y_pred.append(0)
            else:
                FN += 1  # If key step does not exist in original steps, it is a FN
                y_true.append(1)  # False Negative
                y_pred.append(0)  # False Negative
        
        # For missing key steps (in key_steps but not in original_steps)
        for step in key_steps:
            if step not in original_steps:
                FN += 1  # Missing step in original_steps
                y_true.append(0)  # False Negative
                y_pred.append(1)  # False Positive

        return matches, FN, y_true, y_pred

    # Compare the steps
    matches, FN, y_true, y_pred = compare_steps(original_steps, key_steps)

    # Count TP and FP
    TP = sum([1 for match in matches.values() if match == 1])
    FP = sum([1 for match in matches.values() if match == 0])

    # Calculate precision
    precision = TP / (TP + FP) if (TP + FP) != 0 else 0
    f1 = f1_score(y_true, y_pred)
    mcc = matthews_corrcoef(y_true, y_pred)

    # Output the results
    print("Matching results:")
     
    print(f"Precision: {precision:.4f}")
    print(f"F1 Score: {f1:.4f}")
    
