# this code reads the output transformed app-config.json and gets only the specific credentials
# for example, after using main_transformer.py, we would like to get only the DFR credentials for testing
# then, run this code for DFR

import json

file_path = r"C:\Users\karinaliauw\Downloads\MSPYX-728 - Upgrade\python\DFR.json"


with open(file_path, "r") as f:
    dfr_component = json.load(f)
