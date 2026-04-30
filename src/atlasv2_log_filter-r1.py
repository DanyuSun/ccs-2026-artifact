import pandas as pd
import os
import json
import argparse

def summarize_csv(input_file, output_file):
    keep_columns = ['source_process_path', 'target_process_path', 'action','remote_ip', 'process_cmdline', 'netconn_domain', 'remote_port','backend_timestamp']


    print(f"Summarizing {input_file}")
    
    # Read the CSV into a DataFrame
    print("Reading CSV file...")
    df = pd.read_csv(input_file)
    total_rows = len(df)


    target_prefix = r'"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" -nop -w hidden -e'
    replacement = r'"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" -nop -w hidden -e'


    df["process_cmdline"] = df["process_cmdline"].apply(
        lambda p: replacement if isinstance(p, str) and p.startswith(target_prefix) else p
    )

 

    target_prefix = r'"powershell.exe" -nop -w hidden -c'
    replacement = r'"powershell.exe" -nop -w hidden -c'

    df["process_cmdline"] = df["process_cmdline"].apply(
        lambda p: replacement if isinstance(p, str) and p.startswith(target_prefix) else p
    )
    
    # Define a function to check if a value is meaningful
    def is_meaningful(value):
        return pd.notna(value) and value != '' and value != '<unknown>' and value != 'UnnamedPipeObject'
    
    # Filter out rows where none of path, address have meaningful values
    print("Filtering rows with no meaningful values...")
    
    # Create masks for meaningful values in each column
    meaningful_source_path = df['source_process_path'].apply(is_meaningful)
    meaningful_target_path = df['target_process_path'].apply(is_meaningful)
    meaningful_ip = df['remote_ip'].apply(is_meaningful)
    meaningful_port = df['remote_port'].apply(is_meaningful)
    meaningful_domain = df['netconn_domain'].apply(is_meaningful)
    
    # Keep rows where at least one column has a meaningful value
    df = df[meaningful_source_path | meaningful_target_path | meaningful_port | meaningful_domain | meaningful_ip]
    
    # Select only the columns we want to keep
    filtered_df = df[keep_columns]
    
    # Drop duplicates
    print("Removing duplicates...")
    filtered_df = filtered_df.drop_duplicates()
    
    print(f"Found {len(filtered_df)} unique rows out of {total_rows} total rows")
    
    # Handle empty values and calculate summary
    if len(filtered_df) > 0:
        # Fill NaN values with "<empty>"
        filtered_df = filtered_df.fillna({
            'source_process_path': '<empty>',
            'target_process_path': '<empty>',
            'action': '<empty>',
            'process_cmdline': '<empty>',
            'netconn_domain': '<empty>',
            'backend_timestamp': '<empty>',
            'remote_port': 0,
            'remote_ip': 0
        })
        
        # Convert timestamp to numeric if needed
        if pd.api.types.is_object_dtype(filtered_df['backend_timestamp']):
            filtered_df['backend_timestamp'] = pd.to_numeric(filtered_df['backend_timestamp'], errors='coerce').fillna(0)
            
        # Calculate summary statistics
        print("Calculating summary statistics...")
        
        # Group by columns and create summary
        summary_rows = []
        
        # Group by columns manually to handle NaN values
        for (sour_path_val, tar_path_val, action_val, cmd_val, domain_val, port_val, ip_val), group in filtered_df.groupby(
            [filtered_df['source_process_path'].fillna('<empty>'),
             filtered_df['target_process_path'].fillna('<empty>'),
             filtered_df['action'].fillna('<empty>'),
             filtered_df['process_cmdline'].fillna('<empty>'),
             filtered_df['netconn_domain'].fillna('<empty>'),
             filtered_df['remote_port'].fillna('<empty>'),
             filtered_df['remote_ip'].fillna('<empty>'),
             ]
        ):
            summary_rows.append({
                'source_process_path': sour_path_val,
                'target_process_path': tar_path_val,
                'action': action_val,
                'process_cmdline': cmd_val,
                'netconn_domain': domain_val,
                'remote_port': port_val,
                'remote_ip': ip_val,

                'ts_min': group['backend_timestamp'].min(),
                'ts_max': group['backend_timestamp'].max(),
                'count': len(group)
            })
        
        # Create summary DataFrame
        if summary_rows:
            result_df = pd.DataFrame(summary_rows)
            
            # Sort the summary by ts_min
            result_df = result_df.sort_values(by='ts_min')
            
            # Replace '<empty>' with '' to save space
            result_df = result_df.replace('<empty>', '')

            # Extract list of unique execs for profile filtering
            unique_execs = result_df['process_cmdline'].unique().tolist()
            unique_execs = [exec_name for exec_name in unique_execs if exec_name]
            
            print(f"Found {len(unique_execs)} unique executables")
            
            # Create output directory if it doesn't exist
            os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
            
            # Save summary to CSV
            result_df.to_csv(output_file, index=False)
            
            print(f"Summary saved to {output_file} ({len(result_df)} rows)")
            
            return result_df, unique_execs
        else:
            # Create an empty DataFrame with the right columns if no summary rows
            empty_df = pd.DataFrame(columns=['source_process_path', 'target_process_path', 'action','remote_ip', 'process_cmdline', 'netconn_domain', 'remote_port', 'ts_min', 'ts_max', 'count'])
            
            # Create output directory if it doesn't exist
            os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
            
            # Save empty summary
            empty_df.to_csv(output_file, index=False)
            
            print("No summary rows generated")
            return empty_df, []
    else:
        # Create an empty DataFrame with the right columns
        empty_df = pd.DataFrame(columns=['source_process_path', 'target_process_path', 'action','remote_ip', 'process_cmdline', 'netconn_domain', 'remote_port', 'ts_min', 'ts_max', 'count'])
        
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
        
        # Save empty summary
        empty_df.to_csv(output_file, index=False)
        
        print("No rows with meaningful values found")
        return empty_df, []

def filter_summary(summary_df, output_file, exec_list):
    print(f"Filtering summary for executables: {', '.join(exec_list) if exec_list else 'ALL'}")
    
    if not exec_list:
        # If no exec list provided, return the entire summary
        print(f"No filter applied, keeping all {len(summary_df)} rows")
        
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
        
        # Save the unfiltered summary
        summary_df.to_csv(output_file, index=False)
        
        # Get unique executables
        unique_execs = summary_df['process_cmdline'].unique().tolist()
        unique_execs = [exec_name for exec_name in unique_execs if exec_name]
        
        return summary_df, unique_execs
    
    # Filter by exec list
    filtered_df = summary_df[summary_df['process_cmdline'].isin(exec_list)]
    
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
    
    # Save filtered summary
    filtered_df.to_csv(output_file, index=False)
    
    # Get executables that actually appear in the filtered summary
    filtered_execs = filtered_df['process_cmdline'].unique().tolist()
    filtered_execs = [exec_name for exec_name in filtered_execs if exec_name]
    
    print(f"Filtered summary saved to {output_file} ({len(filtered_df)} rows)")
    print(f"Found {len(filtered_execs)} executables in filtered summary")
    
    return filtered_df, filtered_execs


import pandas as pd
import networkx as nx
import os


import pandas as pd
import networkx as nx
import os



import pandas as pd
import networkx as nx
import os

def filter_summary_with_k_hop(attack, summary_df, output_file, exec_list, k):
    print(f"Processing {len(exec_list)} executables individually with {k}-hop neighborhood...")

    # Build graph once using source_process_path → target_process_path

    G = nx.Graph()
    for _, row in summary_df.iterrows():
        src = row["source_process_path"]
        tgt = row["target_process_path"]

        edge_data = {
            'exec_name': row["process_cmdline"],
            'action': row["action"],
            'remote_ip': row["remote_ip"],
            'netconn_domain': row["netconn_domain"],
            'remote_port': row["remote_port"],
            'ts_min': row["ts_min"],
            'ts_max': row["ts_max"],
            'count': row["count"]
        }

        G.add_edge(src, tgt, **edge_data)

    for exec_name in exec_list:
        print(f"Filtering for: {exec_name}")

        matched_rows = summary_df[(summary_df["source_process_path"] == exec_name) | (summary_df["target_process_path"] == exec_name)]
        seed_nodes = set(matched_rows["source_process_path"]).union(matched_rows["target_process_path"])
    

    print(f"Found {len(seed_nodes)} seed nodes from exec/path matches")
 
    event_limit = 500 
    max_k = 10     

    selected_nodes = set()
    current_k = 1
    filtered_df = pd.DataFrame()  # Init as empty

  

    while current_k <= max_k:
        print(f"🔎 Trying with k = {current_k}")

        hop_nodes = set()
        for node_id in seed_nodes:
            try:
                neighbors = nx.single_source_shortest_path_length(G, node_id, cutoff=current_k)
                hop_nodes.update(neighbors.keys())
            except nx.NetworkXError:
                continue

        # Only use new nodes in this hop
        new_nodes = hop_nodes - selected_nodes
        selected_nodes.update(new_nodes)

        # Get the new rows
        new_filtered = summary_df[(summary_df["source_process_path"].isin(new_nodes)) | (summary_df["target_process_path"].isin(new_nodes))]

        if current_k == 1:
            # Always keep all k=1 rows
            filtered_df = new_filtered.copy()
            break
        else:
            remaining_quota = event_limit - len(filtered_df)

            if remaining_quota <= 0:
                print(f"Reached event limit at k = {current_k - 1}, skipping further hops.")
                break

            if len(new_filtered) > remaining_quota:
                print(f"Sampling {remaining_quota} rows from {len(new_filtered)} new rows at k = {current_k}")
                new_filtered = new_filtered.sample(n=remaining_quota, random_state=42)

            filtered_df = pd.concat([filtered_df, new_filtered], ignore_index=True)

            if len(filtered_df) >= event_limit:
                print(f"Reached event limit: {len(filtered_df)} rows.")
                break

        current_k += 1


 
    filtered_df.to_csv(output_file, index=False)
    return filtered_df





def filter_profiles(profiles_file, output_profiles_file, exec_list):
    print(f"Filtering profiles for matching executables...")
    
    try:
        with open(profiles_file, 'r') as f:
            profiles = json.load(f)
        
        # Filter profiles to only include entries for executables in exec_list
        filtered_profiles = {}
        
        for exec_name in exec_list:
            if exec_name in profiles:
                filtered_profiles[exec_name] = profiles[exec_name]
        
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(output_profiles_file)), exist_ok=True)
        
        # Save the filtered profiles
        with open(output_profiles_file, 'w') as f:
            json.dump(filtered_profiles, f, indent=2)
        
        print(f"Filtered profiles saved to {output_profiles_file} ({len(filtered_profiles)} entries out of {len(exec_list)} executables in list)")
        
        # Report any missing executables
        missing_execs = [exec_name for exec_name in exec_list if exec_name not in profiles]
        if missing_execs:
            print(f"Note: {len(missing_execs)} executables not found in profiles: {', '.join(missing_execs[:5])}{' and more...' if len(missing_execs) > 5 else ''}")
            
    except Exception as e:
        print(f"Error filtering profiles: {e}")

def filter_csv(attack, input_file, output_file, profiles_file, output_profiles_file, exec_list, k):
    # Generate full summary file path
    summary_file = output_file.replace('.csv', '-full.csv')
    
    # Path for the exec pairs output
    pairs_file = output_file.replace('.csv', '-pairs.csv')
    
    # First, create a full summary of the CSV
    summary_df, all_execs = summarize_csv(input_file, summary_file)
    if attack == 's1':
        exec_list = [
            
            'c:\\users\\aalsahee\\payload.exe',
            'c:\\windows\\system32\\cmd.exe',
            
            'c:\\windows\\system32\\services.exe',
            'c:\\windows\\system32\\sysmon.exe',
            'c:\\program files\\confer\\repmgr.exe',
            'c:\\program files\\confer\\scanner\\upd.exe',
            'c:\\windows\\system32\\sc.exe',
            'c:\\windows\\system32\\wsqmcons.exe',
            'c:\\windows\\system32\\schtasks.exe',
            'c:\\program files\\mozilla firefox\\plugin-container.exe',
        ]

    filtered_df = filter_summary_with_k_hop(attack,summary_df, output_file, exec_list, k)

def pair_execs(summary_df, output_file):
    print(f"Analyzing executable connections...")
    
    # Initialize empty list to store pairs
    pairs = []
    
    # Dictionary to track shared objects
    shared_paths = {}
    shared_addresses = {}
    
    # Extract path and address connections
    for _, row in summary_df.iterrows():
        exec_name = row['exec']
        path = row['path']
        address = row['address']
        
        # Skip rows with empty exec name or where both path and address are empty
        if not exec_name or (not path and not address):
            continue
            
        # Process paths
        if path:
            if path in shared_paths:
                shared_paths[path].append(exec_name)
            else:
                shared_paths[path] = [exec_name]
                
        # Process addresses
        if address:
            if address in shared_addresses:
                shared_addresses[address].append(exec_name)
            else:
                shared_addresses[address] = [exec_name]
    
    # Find SHARED_OBJECT connections
    for path, execs in shared_paths.items():
        if len(execs) > 1:
            # Create pairs from all executables that share this path
            for i in range(len(execs)):
                for j in range(i+1, len(execs)):
                    exec1 = execs[i]
                    exec2 = execs[j]
                    # Skip if the executables are the same
                    if exec1 == exec2:
                        continue
                    # Count how many times this pair shares paths
                    count = len([p for p, e in shared_paths.items() if exec1 in e and exec2 in e])
                    pairs.append({
                        'exec1': exec1,
                        'exec2': exec2,
                        'type': 'SHARED_OBJECT',
                        'count': count,
                        'detail': f"shared path: {path}"
                    })
    
    # Do the same for shared addresses
    for address, execs in shared_addresses.items():
        if len(execs) > 1:
            for i in range(len(execs)):
                for j in range(i+1, len(execs)):
                    exec1 = execs[i]
                    exec2 = execs[j]
                    # Skip if the executables are the same
                    if exec1 == exec2:
                        continue
                    # Count how many times this pair shares addresses
                    count = len([a for a, e in shared_addresses.items() if exec1 in e and exec2 in e])
                    pairs.append({
                        'exec1': exec1,
                        'exec2': exec2,
                        'type': 'SHARED_OBJECT',
                        'count': count,
                        'detail': f"shared address: {address}"
                    })
    
    all_execs = summary_df['exec'].unique()
    all_execs = [e for e in all_execs if e]  # Filter out empty values
    
    # For each path in the summary
    for _, row in summary_df.iterrows():
        path = row['path']
        if not path:
            continue
        
        # Check if any executable name appears at the end of the path
        for exec_name in all_execs:
            if path.endswith(f"/{exec_name}"):
                parent_exec = row['exec']
                child_exec = exec_name
                
                # Don't pair an executable with itself
                if parent_exec != child_exec:
                    # Count how many times this parent-child relationship appears
                    count = len(summary_df[(summary_df['exec'] == parent_exec) & 
                                           (summary_df['path'].str.endswith(f"/{child_exec}", na=False))])
                    
                    pairs.append({
                        'exec1': parent_exec,
                        'exec2': child_exec,
                        'type': 'PARENT_CHILD',
                        'count': count,
                        'detail': f"path: {path}"
                    })
    
    # Convert to DataFrame
    if pairs:
        pairs_df = pd.DataFrame(pairs)
        
        # Sort by count in descending order
        pairs_df = pairs_df.sort_values('count', ascending=False)
        
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
        
        # Save to CSV
        pairs_df.to_csv(output_file, index=False)
        
        print(f"Found {len(pairs_df)} exec pairs, saved to {output_file}")
        return pairs_df
    else:
        # Create empty DataFrame with the right columns
        empty_df = pd.DataFrame(columns=['exec1', 'exec2', 'type', 'count', 'detail'])
        
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
        
        # Save empty DataFrame to CSV
        empty_df.to_csv(output_file, index=False)
        
        print("No executable pairs found")
        return empty_df

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-input_file", type=str, required=True)
    parser.add_argument("-output_file", type=str, required=True)
    parser.add_argument("-profiles_file", type=str, required=True)
    parser.add_argument("-output_profiles_file", type=str, required=True)
    parser.add_argument("-attack", type=str, required=True)
    parser.add_argument("-k", type=int, default=2)

    args = parser.parse_args()
    input_file = args.input_file
    output_file = args.output_file
    profiles_file = args.profiles_file
    output_profiles_file = args.output_profiles_file
    attack = args.attack
    k = args.k


    import pandas as pd
    import networkx as nx

    # Load the dataset (Ensure it contains 'process_id', 'parent_process_id', 'process_name')
    df = pd.read_csv(input_file)

    print(len(df[['source_process_path', 'target_process_path', 'action','remote_ip', 'process_cmdline', 'netconn_domain', 'remote_port']].drop_duplicates()))

    # Ensure required columns exist
    required_cols = {"source_process_path", "target_process_path", "process_cmdline", "action","process_cmdline"}
    if not required_cols.issubset(df.columns):
        raise ValueError(f"Missing required columns: {required_cols - set(df.columns)}")

    # Replace NaN values in 'exec' with 'Unknown'
    df["process_cmdline"] = df["process_cmdline"].fillna("Unknown").astype(str)
    exec_list = []
    filter_csv(attack,input_file, output_file, profiles_file, output_profiles_file, exec_list, k)

if __name__ == "__main__":
    main()