import json
import csv
from argparse import ArgumentParser
import pandas as pd

def jsonl_to_csv(jsonl_file_path, csv_file_path):
    # Initialize an empty list to collect rows
    data_list = []

    # Read the jsonl file and collect the required data
    with open(jsonl_file_path, 'r') as jsonl_file:
        for line in jsonl_file:
            # Parse the line as a JSON object
            data = json.loads(line)

            event = data.get('type', '')


            source_process_path = data.get('parent_path', '')
            target_process_path = data.get('process_path', '')

            process_id = data.get('process_pid', '')
            guid = data.get('process_guid', '')
            backend_timestamp = data.get('backend_timestamp', '')
            action = data.get('action', '')
            remote_ip = data.get('remote_ip', '')
            netconn_domain = data.get('netconn_domain', '')
            remote_port = data.get('remote_port', '')
            process_cmdline = data.get('process_cmdline', '')

            # parent_id = data.get('parent_pid', '')
            # parent_path = data.get('parent_path', '')
            # parent_cmdline = data.get('parent_cmdline', '')

            mod_name = ''
            if event == "endpoint.event.filemod":
                mod_name = data.get('filemod_name', '')

            elif event == "endpoint.event.moduleload":
                mod_name = data.get('modload_name', '')

            elif event == "endpoint.event.regmod":
                mod_name = data.get('regmod_name', '')

            process_publisher = data.get('process_publisher', "")

            # Append the extracted values as a row to the list
            data_list.append({
                'guid': guid,
                'process_id': process_id,
                'source_process_path': source_process_path,
                'target_process_path': target_process_path,
                'backend_timestamp': backend_timestamp,
                'action': action,
                'remote_ip': remote_ip,
                'netconn_domain': netconn_domain,
                'remote_port': remote_port,
                'process_cmdline': process_cmdline,
            })

            # data_list.append({
            #     'event': event,
            #     'process_id': process_id,
            #     'guid': guid,
            #     'timestamp': timestamp,
            #     # 'action': action,
            #     'path': path,
            #     'exec': exec_file,
            #     # 'mod_name': mod_name,
            #     # 'process_publisher': process_publisher,

            #     # 'parent_id':parent_id,
            #     # 'parent_path':parent_path,
            #     # 'parent_exec': parent_cmdline
            # })

    # Convert the list of dictionaries to a DataFrame
      
    df = pd.DataFrame(data_list).sort_values(by='backend_timestamp')
    print(len(df))
    
    df = df.drop_duplicates()
    print(len(df))

    # Save the DataFrame to a CSV file without the index
    df.to_csv(csv_file_path, index=False)

def txt_to_csv(txt_file_path, csv_file_path):
    # Initialize an empty list to hold the data
    data = []

    # Read the txt file line by line
    with open(txt_file_path, 'r') as txt_file:
        for line in txt_file:
            # Split the line into parts (assuming they are space or comma-separated)
            parts = line.strip().split(', ')
            
            # Append the parts to the data list (assuming exactly 4 columns)
            if len(parts) == 4:
                data.append({
                    'attack': parts[0],
                    'process_id': parts[1],
                    'path_label': parts[2],
                    'label': parts[3]
                })

    # Convert the data to a pandas DataFrame
    df = pd.DataFrame(data)

    # Save the DataFrame to a CSV file with the specified header
    df.to_csv(csv_file_path, index=False)

    print(f"Data successfully saved to {csv_file_path}")

def merge_same_process_and_path(df, merge_cols):
    # Create a dictionary to store the merged results
    merged_data = {}

    # Iterate over each row
    for index, row in df.iterrows():
        # Create a tuple of process_id and path to identify unique rows
        key = (row['process_id'])
        
        # If this process_id and path combination has been seen before
        if key in merged_data:
            # Iterate over each column that needs merging
            for col in merge_cols:
                # Get the existing values for the column
                current_values = str(merged_data[key][col])
                new_value = str(row[col])
                
                # If the new value is not already in the existing values, append it
                if new_value not in current_values:
                    merged_data[key][col] = current_values + ',' + new_value
        else:
            # If this process_id and path combination is new, store the entire row
            merged_data[key] = {col: row[col] for col in df.columns}

    # Convert the merged data back into a DataFrame
    merged_df = pd.DataFrame([val for val in merged_data.values()])

    return merged_df

def merge_unique_values(df, group_column):
    # Function to concatenate unique values in a column
    df[group_column] = df[group_column].fillna(' ')
    def unique_concat(series):
        # Convert the column to a set to remove duplicates, then join into a string
        return ', '.join(series.dropna().unique())

    # def unique_concat(series):
    #     # Drop NaN values, convert the column to a set to remove duplicates, then join into a string
    #     unique_values = series.dropna().unique()
    #     return ', '.join(map(str, unique_values)) if len(unique_values) > 0 else ''


    # Group by the specified column and apply the unique_concat function to all other columns
    result = df.groupby(group_column).agg(unique_concat).reset_index()
    result = result[group_column]

    return result

# def merge_unique_values(df, group_column):
#     df[group_column] = df[group_column].fillna('unknown')
#     def unique_concat(series):
#         unique_vals = series.dropna().unique()
#         return ', '.join(map(str, sorted(unique_vals))) if len(unique_vals) > 0 else ''
    
#     return df.groupby(group_column).agg(unique_concat).reset_index()



if __name__ == "__main__":

    parser = ArgumentParser()
    parser.add_argument("--file", type=str, default='s1') # default='s1', 'benign'
    parser.add_argument("--d", type=str, default='data')
    args = parser.parse_args()
    file_path = args.file
    dataset = args.d

    # -----------------------------------------------------------------

    #### step 1: convert jsonl to csv
    if file_path == 'benign':
        jsonl_file_path = f'data/atlasv2/benign/h1/cbc-edr/edr-h1-{file_path}.jsonl'
        csv_file_path = f'data/atlasv2/{file_path}/edr-h1-{file_path}.csv'
        jsonl_to_csv(jsonl_file_path, csv_file_path)
        df = pd.read_csv(f"data/atlasv2/{file_path}/edr-h1-{file_path}.csv")
        merge_cols = ['process_id', 'target_process_path']
        df_merged = merge_same_process_and_path(df, merge_cols)
        df_merged.to_csv(f"data/atlasv2/{file_path}/edr-h1-{file_path}-merge.csv", index=False)
        
    elif file_path == 's1':
        jsonl_file_path = f'data/atlasv2/attack/h1/cbc-edr/edr-h1-{file_path}.jsonl'
        csv_file_path = f'data/atlasv2/attack/edr-h1-{file_path}.csv'
        jsonl_to_csv(jsonl_file_path, csv_file_path)
        df = pd.read_csv(f"data/atlasv2/attack/edr-h1-{file_path}.csv")
        merge_cols = ['process_id', 'target_process_path']
        df_merged = merge_same_process_and_path(df, merge_cols)
        df_merged.to_csv(f"data/atlasv2/attack/edr-h1-{file_path}-merge.csv", index=False)
         
    



