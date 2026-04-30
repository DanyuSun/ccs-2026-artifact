from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import argparse
import re
import glob

def extract_attack_narrative_r1(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        lines = file.readlines()
    narrative = []
    capture = False
    for line in lines:
        if "**Attack Narrative**" in line:
            capture = True  # Start capturing text
            continue
        elif "**Key Steps**" in line:
            capture = False  # Stop capturing when reaching the next section
            break
        if capture:
            narrative.append(line.strip())
    return "\n".join(narrative)

def extract_attack_narrative_sonar(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        lines = file.readlines()
    narrative = []
    capture = False
    for line in lines:
        if "## Attack Narrative" in line:
            capture = True  # Start capturing text
            continue
        elif "## Key Steps" in line:
            capture = False  # Stop capturing when reaching the next section
            break
        if capture:
            narrative.append(line.strip())
    return "\n".join(narrative)

def extract_attack_narrative_o3(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        content = file.read()
    
    ioc_section = content.split("=== RESPONSE ===")[-1]

    # match = re.search(r"Attack Narrative\s*(.*?)\s*IOCs", ioc_section, re.DOTALL | re.IGNORECASE)
    # match = re.search(r"Attack Narrative\s*(.*?)\s*Key Steps", ioc_section, re.DOTALL | re.IGNORECASE)
    match = re.search(r"Attack Narrative\s*(.*?)\s*Key Steps\s*(.*?)\s*IOCs", ioc_section, re.DOTALL | re.IGNORECASE)

    # match.group(1).strip()

    return match.group(1).strip()


def extract_attack_ground_truth(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        lines = file.readlines()

    narrative = []
    capture = False

    for line in lines:
        if "Attack high-level description:" in line:
            capture = True  # Start capturing text
            continue
        elif "Attack steps and commands:" in line:
            capture = False  # Stop capturing when reaching the next section
            break

        if capture:
            narrative.append(line.strip())

    return "\n".join(narrative)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
 
    parser.add_argument("-model", type=str, default="r1")
    parser.add_argument("-attack", type=str, default="s1")

    args = parser.parse_args()
 
    model = args.model
    attack = args.attack
    
    story1 = extract_attack_ground_truth(f"./data/atlasv2/attack/{attack}.txt")
   
    file_path = "./example_result/r1_s1_20250421_221506.txt"

    print(file_path) 
     

    if model == "o3-mini" or model == "llama":
        story2 = extract_attack_narrative_o3(file_path) 
        # print(story2)
    elif model == "r1" or model == "sonar":
        story2 = extract_attack_narrative_r1(file_path)
        # print(story2)
     
    # Load a pre-trained semantic model
    model = SentenceTransformer('all-MiniLM-L6-v2')

    # Encode the stories into embeddings
    embedding1 = model.encode(story1, convert_to_tensor=True)
    embedding2 = model.encode(story2, convert_to_tensor=True)

    # Compute cosine similarity between embeddings
    similarity_score = cosine_similarity([embedding1.cpu().numpy()], [embedding2.cpu().numpy()])[0][0]

    print(f"Semantic Similarity Score: {similarity_score:.4f}")
