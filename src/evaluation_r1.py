import pandas as pd
from sklearn.metrics import confusion_matrix, precision_score, recall_score
from datetime import datetime
import pytz
import os
import time
from time import mktime
import numpy as np
import argparse
from sklearn.metrics import matthews_corrcoef

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-attack", type=str, required=True)
    parser.add_argument("-data", type=str, required=True)

    args = parser.parse_args()

    attack = args.attack
    data = args.data

    # Load the CSV files
    test_df = pd.read_csv(f"./data/{data}/attack/edr-h1-{attack}-attack.csv")  # Test data
    test_df["backend_timestamp"] = test_df["backend_timestamp"].str.split("+").str[0]  # Remove timezone info
    test_df["backend_timestamp"] = pd.to_datetime(test_df["backend_timestamp"], format="%Y-%m-%d %H:%M:%S")
    max_time = max(test_df['backend_timestamp'])
    min_time = min(test_df['backend_timestamp'])
    

    test_all_df = pd.read_csv(f"./data/{data}/attack/edr-h1-{attack}.csv")
    ground_truth_df = pd.read_csv(f"./data/{data}/attack/{attack}_label.csv")  # Ground truth labels
    
    # get the ground truth value "label"
    test_all_df = pd.merge(test_all_df, ground_truth_df, on=["process_id", "target_process_path"], how="left")
    test_all_df = test_all_df.dropna(subset=["label"])

    test_df_with_label = pd.merge(test_df, ground_truth_df, on=["process_id", "target_process_path"], how="left")
    test_df_with_label['label'] = test_df_with_label['label'].fillna('benign')
    test_df_with_label = test_df_with_label.drop_duplicates()

    unique_timestamps = test_df_with_label[test_df_with_label['label'] =='attack']['backend_timestamp']
    
    df_tp = test_df_with_label[test_df_with_label["label"] == 'attack']

    ips_to_check = {}


    ### for s1
    if attack == "s1":
        ips_to_check = {
            "23.61.169.89",
            "152.199.5.11",
            "128.210.210.80",
            "34.107.221.82",
            "ortrta.net",
            "user-data-us-east.bidswitch.net",
            "ssp-ats-prod-us-west-1.one-mobile-prod.aws.oath.cloud",
            "C:\\Users\\aalsahee\\Desktop\\start_dns_logs.bat",
            'C:\\Program Files\\Wireshark\\tshark.exe -i 2 -t ad -f "udp port 53"',
            "services.exe",
            "spoolsv.exe",
            "svchost.exe",
            "C:\\Windows\\system32\\wbem\\WmiApSrv.exe"
        }

    print("iocs to check:", ips_to_check)


    mask = test_df_with_label.apply(lambda row: row.astype(str).isin(ips_to_check).any(), axis=1)
    filtered_rows = test_df_with_label[mask][['process_id', 'target_process_path']]

    filtered_set = set(zip(filtered_rows['process_id'], filtered_rows['target_process_path']))
    test_all_df['y_pred'] = test_all_df.apply(
        lambda row: 'attack' if (row['process_id'], row['target_process_path']) in filtered_set else 'benign', 
        axis=1
    )
    mapping = {"attack": 1, "benign": 0, "contaminated": 0}  # Treat "contaminated" as attack

    test_all_df["label"] = test_all_df["label"].fillna("benign")
    test_all_df["y_pred"] = test_all_df["y_pred"].fillna("benign")

    test_all_df["label_mapped"] = test_all_df["label"].map(mapping)
    test_all_df["y_pred_mapped"] = test_all_df["y_pred"].map(mapping)
    
    tn, fp, fn, tp = confusion_matrix(test_all_df["label_mapped"], test_all_df["y_pred_mapped"]).ravel()

    precision = precision_score(test_all_df["label_mapped"], test_all_df["y_pred_mapped"], zero_division=0)
    recall = recall_score(test_all_df["label_mapped"], test_all_df["y_pred_mapped"], zero_division=0)
    mcc_score = matthews_corrcoef(test_all_df["label_mapped"], test_all_df["y_pred_mapped"])


    # Print results
    print("attack: ", attack)
    print(f"True Positives (TP): {tp}")
    print(f"False Positives (FP): {fp}")

    print(f"True Negatives (TN): {tn}")
    print(f"False Negatives (FN): {fn}")
    print(f"Precision: {precision:.4f}")
    print(f"Recall: {recall:.4f}")
    print(f"MCC: {mcc_score:.4f}")


    # # **Filter and Print False Positives (FP)**
    # false_positives = test_all_df[(test_all_df["label_mapped"] == 0) & (test_all_df["y_pred_mapped"] == 1)]
    # print("\nFalse Positives (FP):")
    # print(false_positives[['process_id', 'target_process_path', 'remote_ip']].value_counts())
    

    # # **Filter and Print False Negatives (FN)**
    # false_negatives = test_all_df[(test_all_df["label_mapped"] == 1) & (test_all_df["y_pred_mapped"] == 0)]
    # print("\nFalse Negatives (FN):")
    # print(false_negatives[["process_id", "target_process_path"]].value_counts())


    # true_positives = test_all_df[(test_all_df["label_mapped"] == 1) & (test_all_df["y_pred_mapped"] == 1)]
    # print("\nTure Positive (FN):")
    # print(true_positives[["process_id", "target_process_path", "process_cmdline"]].value_counts())



    