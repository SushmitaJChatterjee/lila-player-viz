import pandas as pd
import pyarrow.parquet as pq
import os

# Your folder path
folder = "/Users/sushmitachatterjee/Antigravity/Lila/player_data/February_10"

# Get first file from that folder
first_file = os.listdir(folder)[0]
filepath = os.path.join(folder, first_file)

print("File name:", first_file)
print("---")

# Read it
df = pq.read_table(filepath).to_pandas()
df['event'] = df['event'].apply(lambda x: x.decode('utf-8') if isinstance(x, bytes) else x)

print("Number of rows:", df.shape[0])
print("Number of columns:", df.shape[1])
print("---")
print("First 5 rows:")
print(df.head(5))
print("---")
print("Event types found:", df['event'].unique())
print("---")
print("Is this a bot or human?", first_file.split('_')[0])
