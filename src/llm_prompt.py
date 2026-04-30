import os
import json
import csv
import time
import openai
from datetime import datetime
import pandas as pd
import requests
import argparse
from openai import OpenAI

# remember to set the OPENAI_API_KEY environment variable

def load_template(file_path):
    """Load the prompt template from a file."""
    with open(file_path, 'r') as f:
        template = f.read()
    return template

def load_json_data(file_path):
    """Load and format JSON data for the prompt."""
    with open(file_path, 'r') as f:
        data = json.load(f)
    return json.dumps(data, indent=2)

def load_csv_data(file_path):
    """Load and format CSV data for the prompt."""
    df = pd.read_csv(file_path)
    # df = df.drop(columns=['guid'])
    return df.to_string(index=False)

def replace_placeholders(template, logs_data, baseline_data):
    """Replace placeholders in the template with actual data."""
    prompt = template.replace("*LOGS*", logs_data, 1)
    prompt = prompt.replace("*PROFILES*", baseline_data, 1)
    return prompt


def query_openai_o3_mini(prompt, model="o3-mini"):
    """Send a query to OpenAI API and get the response."""
    client = openai.OpenAI(api_key="your api here")
    
    response = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": "You're a threat hunter to investigate cyber-attacks from logs."},
            {"role": "user", "content": prompt}
        ],
        text={
            "format": {
            "type": "text"
            }
        },
        reasoning={
            "effort": "medium"
        },
        tools=[],
        store=True
    )
    return response.output_text


def query_perplexity(prompt, model="sonar-reasoning-pro"):
    """Send a query to OpenAI API and get the response."""
    # OpenAI client will automatically use OPENAI_API_KEY environment variable
    client = openai.OpenAI(api_key="your api here", base_url="https://api.perplexity.ai")
    
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You're a threat hunter to investigate cyber-attacks from logs."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.1,
    )
    
    return response.choices[0].message.content

def query_deepseek(prompt, model="r1-1776"):
    """Send a query to OpenAI API and get the response."""
    # OpenAI client will automatically use OPENAI_API_KEY environment variable
    client = openai.OpenAI(api_key="your api here", base_url="https://api.perplexity.ai")
    
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You're a threat hunter to investigate cyber-attacks from logs."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.1,
    )
    print(response.usage)
    return response.choices[0].message.content

def query_llama(prompt):
    openai = OpenAI(
        api_key="your api here",
        base_url="https://api.deepinfra.com/v1/openai",
    )    
    response = openai.chat.completions.create(
        model="meta-llama/Llama-3.3-70B-Instruct-Turbo",
        messages=[
            {"role": "system", "content": "You're a threat hunter to investigate cyber-attacks from logs."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.1,
    )
    return response.choices[0].message.content



def save_result(prompt, response, model_name, attack):
    """Save the prompt and response to a file."""
    # Create llm-logs directory if it doesn't exist
    logs_dir = "llm-logs/"
    os.makedirs(logs_dir, exist_ok=True)
    
    # Create filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(logs_dir, f"{model_name}_{attack}_{timestamp}.txt")
    
    with open(filename, 'w') as f:
        f.write("=== PROMPT ===\n\n")
        f.write(prompt)
        f.write("\n\n=== RESPONSE ===\n\n")
        f.write(response)
    
    return filename    


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-base_dir", type=str, default="")
    parser.add_argument("-attack", type=str, required=True)
    parser.add_argument("-model", type=str, required=True)

    args = parser.parse_args()
    base_dir = args.base_dir
    attack = args.attack
    model = args.model
 
    
    # Load the template using absolute path
    template = load_template(os.path.join(base_dir, "src/prompt.txt"))

    logs_data = load_csv_data(os.path.join(base_dir, f"./filtered/{attack}/filtered_logs_{attack}_{model}.csv"))
    baseline_data = load_json_data(os.path.join(base_dir, f"data/atlasv2-profiles-condensed.json"))
    
    # Replace placeholders
    prompt = replace_placeholders(template, logs_data, baseline_data)
    # print(prompt)
    
    # Query OpenAI
    if model == "o3-mini":
        response = query_openai_o3_mini(prompt)
    elif model == "r1":
        response = query_deepseek(prompt)
    elif model == "llama":
        response = query_llama(prompt)
    elif model == "sonar":
        response = query_perplexity(prompt)
    
    # Save result
    filename = save_result(prompt, response, model, attack)
    print(f"Results saved to {filename}")

if __name__ == "__main__":
    main()