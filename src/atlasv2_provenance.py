import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import os
import json
from collections import defaultdict
import argparse
import unicodedata
import re

def load_csv_data(file_path):
    """Load CSV data from file."""
    print(f"Loading data from {file_path}...")
    df = pd.read_csv(file_path)
    print(f"Loaded {len(df)} rows")
    return df

def filter_valid_events(df):
    """Filter out events with invalid paths or object types."""
    print("Filtering valid events...")
    
    # Filter out rows with <unknown>, empty string, or UnnamedPipeObject

    ##    for cadets or theia, 
    # mask = (
    #     (df['path'].notna()) & (df['path'] != '') & (df['path'] != '<unknown>') &
    #     (df['object'] != 'UnnamedPipeObject')
    # )

    mask = (
        (df['source_process_path'].notna())  & (df['source_process_path'] != '') & (df['source_process_path'] != '<unknown>')
    )
    
    filtered_df = df[mask].copy()
    # filtered_df = df.copy()
    print(f"Retained {len(filtered_df)} rows after filtering")
    return filtered_df

 

import networkx as nx
from collections import defaultdict

def build_provenance_graph(df):
    """Build a provenance graph from the filtered data with focus on execution and IP address."""
    print("Building provenance graph...")
    
    # Create a directed graph
    G = nx.DiGraph()
    
    # Blacklist of processes to exclude from having edges
    process_blacklist = ['ld-elf.so.1']
    
    # Track process execution and IP mappings
    process_to_exec = {}
    process_to_ip = {}
    
    # First pass: Capture all executed process names and IP addresses
    all_execs = set()
    for _, row in df.iterrows():
        if row['process_id'] and row['process_cmdline']:
            process_to_exec[row['process_id']] = row['process_cmdline']
            all_execs.add(row['process_cmdline'])
        
        if row['process_id'] and row['remote_ip']:
            process_to_ip[row['process_id']] = row['remote_ip']
    
    # Remove empty execution names
    all_execs = {exec_name for exec_name in all_execs if exec_name}
    
    # Add all valid execution names as nodes
    for exec_name in all_execs:
        G.add_node(exec_name, type="process")
    
    # Track file read/write events for capturing information flow
    file_writes = defaultdict(list)  # path -> [(timestamp, exec_name, process_id)]
    
    # Second pass: Process execution events
    print("Processing execution events...")
    exec_edges = set()  # To avoid duplicate edges
    
    for _, row in df.iterrows():
        if row['action'] in ['EVENT_EXECUTE', 'ACTION_PROCESS_TERMINATE'] and row['process_id'] in process_to_exec and row['remote_ip']:
            source_exec = process_to_exec[row['process_id']]
            source_ip = process_to_ip.get(row['process_id'], None)  # Get IP address
            
            if not source_exec or not source_ip or source_exec in process_blacklist:
                continue
            
            # Add edge between exec and IP address (process -> IP address)
            edge_key = (source_exec, source_ip, "execute")
            if edge_key not in exec_edges:
                G.add_edge(
                    source_exec, 
                    source_ip, 
                    type="execute", 
                    timestamp=row['backend_timestamp'],
                    process_id=row['process_id'],
                    target_process=row['process_cmdline']
                )
                exec_edges.add(edge_key)
    
    # Third pass: Process read/write events if necessary
    print("Processing read/write events...")
    read_write_edges = set()  # To avoid duplicate edges
    
    for _, row in df.iterrows():
        if row['action'] == 'ACTION_WRITE_VALUE' and row['process_id'] in process_to_exec and row['remote_ip'] and row['process_cmdline'] in file_writes:
            target_exec = process_to_exec[row['process_id']]
            target_ip = process_to_ip.get(row['process_id'], None)  # Get IP address
            
            if not target_exec or not target_ip or target_exec in process_blacklist:
                continue
            
            for write_timestamp, source_exec, source_process_id in file_writes[row['process_cmdline']]:
                if source_exec not in all_execs or target_exec not in all_execs:
                    continue
                
                if source_exec == target_exec or source_exec in process_blacklist:
                    continue
                
                if write_timestamp < row['backend_timestamp']:
                    edge_key = (source_exec, target_exec, "information_flow", row['process_cmdline'])
                    if edge_key not in read_write_edges:
                        G.add_edge(
                            source_exec, 
                            target_exec, 
                            type="information_flow",
                            path=row['process_cmdline'],
                            write_timestamp=write_timestamp,
                            read_timestamp=row['backend_timestamp'],
                            source_process_id=source_process_id,
                            target_process_id=row['process_id']
                        )
                        read_write_edges.add(edge_key)
    
    print(f"Provenance graph built with {len(G.nodes())} nodes and {len(G.edges())} edges")
    return G


def save_graph(G, output_path):
    """Save the graph to a GEXF file for visualization."""
    nx.write_gexf(G, output_path)
    print(f"Graph saved to {output_path}")

def export_graph_json(G, output_path):
    """Export graph to JSON for visualization with tools like D3.js."""
    data = {
        "nodes": [],
        "links": []
    }
    
    for node in G.nodes():
        node_attrs = G.nodes[node]
        data["nodes"].append({
            "id": node,
            "type": node_attrs.get("type", "process")
        })
    
    for source, target, attrs in G.edges(data=True):
        edge_data = {
            "source": source,
            "target": target,
            "type": attrs.get("type", "unknown")
        }
        
        # Include path for information flow edges
        if attrs.get("type") == "information_flow":
            edge_data["path"] = attrs.get("path", "")
            
        data["links"].append(edge_data)
    
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"Graph exported to JSON: {output_path}")

def visualize_graph(G, output_path):
    """Create a simple visualization of the graph."""
    plt.figure(figsize=(20, 20))
    
    # Set positions using spring layout
    pos = nx.spring_layout(G, k=0.15, iterations=20)
    
    # Draw nodes
    nx.draw_networkx_nodes(G, pos, node_size=500)
    
    # Draw edges with different colors based on type
    execute_edges = [(u, v) for u, v, d in G.edges(data=True) if d['type'] == 'execute']
    info_flow_edges = [(u, v) for u, v, d in G.edges(data=True) if d['type'] == 'information_flow']
    
    nx.draw_networkx_edges(G, pos, edgelist=execute_edges, edge_color='blue', width=1.5, arrows=True)
    nx.draw_networkx_edges(G, pos, edgelist=info_flow_edges, edge_color='red', width=1.5, style='dashed', arrows=True)
    
    # Draw labels
    nx.draw_networkx_labels(G, pos, font_size=10)
    
    plt.axis('off')
    plt.tight_layout()
    plt.savefig(output_path, format="PNG", dpi=300)
    plt.close()
    print(f"Graph visualization saved to {output_path}")

def analyze_graph_clusters(G, output_component_file=None):
    """Identify clusters in the graph."""
    # Find connected components

    # connected_components = list(nx.weakly_connected_components(G))
    connected_components = list(nx.strongly_connected_components(G))


    print(f"Found {len(connected_components)} weakly connected components")
    
    # Print the largest connected components
    sorted_components = sorted(connected_components, key=len, reverse=True)
    
    # Save components to file if output file is provided
    if output_component_file:
        with open(output_component_file, 'w') as f:
            for component in sorted_components:
                print(component)
                # f.write(','.join(sorted(list(str(component)))) + '\n')
                f.write(','.join(sorted(map(str, component))) + '\n')                 
        print(f"Wrote {len(connected_components)} components to {output_component_file}")
    
    for i, component in enumerate(sorted_components[:5]):  # Print top 5 largest components
        print(f"Component {i+1}: {len(component)} nodes")
        print(component)
        # print(f"  Processes: {', '.join(sorted(list(component))[:10])}")
        # if len(component) > 10:
        #     print(f"  ... and {len(component) - 10} more")
        
    return connected_components


def extract_clusters_and_execs(G, df):
    """Extract clusters and associated exec values."""
    clusters = list(nx.weakly_connected_components(G))
    # clusters = list(nx.strongly_connected_components(G))
    # clusters = list(nx.edge_connected_components(G))
    

    exec_per_cluster = []

    # Build a reverse mapping of execs to their nodes
    exec_to_nodes = defaultdict(set)
    for _, row in df.iterrows():
        if row['actorID'] in G:
            exec_to_nodes[row['exec']].add(row['actorID'])

    for i, cluster in enumerate(clusters):
        exec_values = {exec_name for node in cluster if node in exec_to_nodes for exec_name in exec_to_nodes[node]}
        exec_values.discard("Unknown")  # Remove placeholder values

        if exec_values:  # Print only if there are valid exec values
            print(f"\nCluster {i+1}:")
            print(", ".join(exec_values))
            exec_per_cluster.append(exec_values)
    
    return exec_per_cluster



def main():
    # # Set paths
    # input_file = 'data/cadets_e3_attack_a1.csv'
    # output_gexf = 'provenance_graph.gexf'
    # output_json = 'provenance_graph.json'
    # output_viz = 'provenance_graph.png'
    # output_component_file = 'graph_components.txt'

    # Parse command-line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-input_files", type=str, required=True)
    parser.add_argument("-output_gexf", type=str, required=True)
    parser.add_argument("-output_json", type=str, required=True)
    parser.add_argument("-output_viz", type=str, required=True)
    parser.add_argument("-output_component_file", type=str, required=True)
   
    
    args = parser.parse_args()
    input_file = args.input_files
    output_gexf = args.output_gexf
    output_json = args.output_json
    output_viz = args.output_viz
    output_component_file = args.output_component_file
    
    # Load and filter data
    df = load_csv_data(input_file)
    filtered_df = filter_valid_events(df)
    
    # Build provenance graph
    G = build_provenance_graph(filtered_df)
    
    # Save the graph
    save_graph(G, output_gexf)
    export_graph_json(G, output_json)
    
    # Analyze graph clusters
    clusters = analyze_graph_clusters(G, output_component_file)

    # print(clusters)

     
    
    # Visualize (only for smaller graphs)
    if len(G.nodes()) < 100:  # Only visualize if graph is not too large
        visualize_graph(G, output_viz)
    else:
        print(f"Graph is too large to visualize automatically ({len(G.nodes())} nodes)")
    
    print("Graph generation complete")

if __name__ == "__main__":
    main()