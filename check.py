# import os

# notebook_folder = "C:/Users/91934/airaware/datasets"  # adjust path if needed

# for file in os.listdir(notebook_folder):
#     file_path = os.path.join(notebook_folder, file)
#     if os.path.isfile(file_path):
#         size_mb = os.path.getsize(file_path) / (1024 * 1024)
#         print(f"{file}: {size_mb:.2f} MB")

import pandas as pd

df = pd.read_csv("datasets/stations.csv")
print(df.columns)
print(df.head())
