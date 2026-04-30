import pandas as pd
from datetime import datetime, timedelta
import argparse

def filter_df(start_time, end_time, df):
    # start_dt = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
    # end_dt = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")

    print(start_dt, end_dt)

    # Filter rows within the time range
    filtered_df = df[(df["backend_timestamp"] >= start_dt) & (df["backend_timestamp"] <= end_dt)]
    return filtered_df

if __name__ == "__main__":  
    parser = argparse.ArgumentParser()
    parser.add_argument("-attack", type=str, default="s1")


    args = parser.parse_args()
    attack = args.attack
        
    start_time =  ["2022-07-19 13:10:00", "2022-07-19 13:25:00", "2022-07-19 13:30:00"]
     
    # Load the CSV file
    df = pd.read_csv(f"../data/atlasv2/attack/edr-h1-{attack}.csv")  # Ensure the timestamp column is parsed correctly
    # Convert timestamp column to datetime while ignoring the timezone part
    # df["backend_timestamp"] = df["backend_timestamp"].str.split("+").str[0]  # Remove timezone info
    df["backend_timestamp"] = pd.to_datetime(df["backend_timestamp"].str.split("+").str[0], errors='coerce')
    df["backend_timestamp"] = pd.to_datetime(df["backend_timestamp"], format="%Y-%m-%d %H:%M:%S")

    time_period = 5
    filtered_dfs = []

    for st in start_time:
        start_dt = datetime.strptime(st, "%Y-%m-%d %H:%M:%S")
        # Calculate end_time by adding the time_period (in minutes)
        end_dt = start_dt + timedelta(minutes=time_period)
        print(start_dt, end_dt)
         
        filtered_df = filter_df(start_dt, end_dt, df)
        filtered_dfs.append(filtered_df)
    
    final_filtered_df = pd.concat(filtered_dfs, ignore_index=True)

    # Save the filtered data
    final_filtered_df = final_filtered_df.drop_duplicates()
    final_filtered_df.to_csv(f"../data/atlasv2/attack/edr-h1-{attack}-attack.csv", index=False)
