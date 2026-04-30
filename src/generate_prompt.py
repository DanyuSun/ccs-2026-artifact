import openai
import json
import pandas as pd
import argparse
import requests
from openai import OpenAI


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

def replace_placeholders(template, unique_cmd):
    """Replace placeholders in the template with actual data."""
    prompt = template.replace("*CMDS*", unique_cmd, 1)
    return prompt


# Function to interact with OpenAI API (assuming you're using GPT-3 or GPT-4)
def generate_new_guidelines(old_guidelines):
    # Replace with your OpenAI API key
    openai.api_key = 'your-api-key'
    
    prompt = f"Given the following guidelines, please generate a new set of guidelines that are concise and relevant:\n{old_guidelines}\nNew Guidelines:"
    
    response = openai.Completion.create(
        engine="text-davinci-003",  # Or GPT-4, if you're using it
        prompt=prompt,
        max_tokens=150,  # Adjust as needed for the length of the new guidelines
        temperature=0.7  # Adjust creativity level
    )
    
    new_guidelines = response.choices[0].text.strip()
    return new_guidelines

# Read the prompt.txt file
def read_prompt_file(file_path):
    with open(file_path, 'r') as file:
        return file.read()

# Write the new prompt back to the file
def write_new_prompt(file_path, new_content):
    with open(file_path, 'w') as file:
        file.write(new_content)

# Main function
def update_guidelines_in_prompt(file_path, new_evidence):
    # Step 1: Read the content of prompt.txt
    content = read_prompt_file(file_path)
    
    # Step 2: Find the old guidelines section
    start_tag = "<Guidelines>"
    end_tag = "</Guidelines>"
    
    start_index = content.find(start_tag) + len(start_tag)
    end_index = content.find(end_tag)
    
    # Extract the guidelines section
    guidelines = content[start_index:end_index].strip()
    lines_to_keep = []
    lines = guidelines.split('\n')


    for line in lines:
        # Keep lines that start with "Environment:" or "Your available evidence:"
        if line.startswith("Environment:") or line.startswith("Your available evidence:"):
            lines_to_keep.append(line.strip())
    
    # Add the new evidence to the "Your available evidence:" section
    for i, line in enumerate(lines_to_keep):
        if line.startswith("Your available evidence:"):
            # Append new evidence to the existing evidence
            lines_to_keep[i] += f"\n2. {new_evidence}"
            break
    
    # Create the new guidelines content
    new_guidelines = "\n".join(lines_to_keep)
    
    # Replace the old guidelines with the new ones
    updated_content = content[:start_index] + "\n" + new_guidelines + "\n" + content[end_index:]
    
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


def query_openai(prompt, model="gpt-4o"):
    """Send a query to OpenAI API and get the response."""
    # OpenAI client will automatically use OPENAI_API_KEY environment variable
    client = openai.OpenAI(api_key="your api here")
    
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
    return response.choices[0].message.content


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
     
    parser.add_argument("-attack", type=str, default="s1", required=True)
    parser.add_argument("-model", type=str, default="gpt-4o", required=True)

    args = parser.parse_args()
    attack = args.attack
    model = args.model
    
    df = pd.read_csv(f"./data/atlasv2/attack/edr-h1-{attack}.csv")
   
    cleaned_df = df[['source_process_path','target_process_path']].dropna()
    unique_cmds = cleaned_df[['source_process_path','target_process_path']].drop_duplicates()
    unique_cmds = unique_cmds.to_dict(orient='records')
        # unique_cmds = list(unique_cmds)  # .to_dict(orient='records')
 

    #  Save the unique values to a JSON file
    with open(f'./data/atlasv2/attack/unique_exec_path.json', 'w') as json_file:
        json.dump(unique_cmds, json_file, indent=4)

    unique_cmd = load_json_data(f'./data/atlasv2/attack/unique_exec_path.json')
     

    template = load_template('src/prompt_cmd.txt')
    prompt = replace_placeholders(template, unique_cmd)
    # # print(prompt)

  
    if model == "r1":
        response = query_deepseek(prompt)
    elif model == "llama":
        response = query_llama(prompt)
    elif model == "sonar":
        response = query_perplexity(prompt)
    elif model == "o3-mini":
        response = query_openai_o3_mini(prompt)

    

    with open(f'./data/atlasv2/attack/{model}_{attack}_llm_unique_exec_path.txt', 'w') as f:
        f.write(response)
    
