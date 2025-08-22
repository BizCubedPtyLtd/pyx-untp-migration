# this code reads the output transformed app-config.json and gets only the specific credentials
# for example, after using main_transformer.py, we would like to get only the DFR credentials for testing
# then, run this code for DFR

import json
from pathlib import Path
from typing import Dict, Any, List

current_dir = Path(__file__).resolve().parent
    #print(current_dir)
input_path = (current_dir.parent.parent / "01_Data/app-config/RBTP" / "transformed-app-config.json")

with open(input_path, "r") as f:
    config_data = json.load(f)

apps = config_data.get("apps", [])

credential_request = 'DFR'
json_list = [] # initialises json list for output

for app in apps:
    features = app.get("features", [])
    for feature in features:
        components = feature.get("components", [])
        # services = feature.get("services", [])
        # #print('services111',services)

        # Initialize credential_type to None
        credential_type = None
    
        for component in components: # update component
            #print('component1',component)
            if component.get("type") == "EntryData": #only process 
                if component.get("name") == "LocalStorageLoader": #to identify 2 types of json types "LocalStorageLoader/NestedComponents" and standard "JsonForm"
                    nestedcomponents = component['props']['nestedComponents']
                    #print(type(nestedcomponents))
                    if len(nestedcomponents) == 1:
                        schema_url = nestedcomponents[0]["props"]["schema"]["url"]
                    else:
                        print('Multiple nested components found. Please investigate')
                        break
                else:
                    schema_url = component["props"]["schema"]["url"]
                # Detect type from schema URL
                #print(schema_url)
                if "DigitalFacilityRecord" in schema_url:
                    credential_type = "DFR"
                    #print('inside')
                # elif "DigitalProductPassport" in schema_url:
                #     credential_type = "DPP"
                # elif "DigitalConformityCredential" in schema_url:
                #     credential_type = "DCC"
                else:
                    continue  # Skip unknown
                # Update the component in place
        
        if credential_type == credential_request:
            print(feature)
            print('credential_type', credential_type)
            json_list.append(feature)


output_path = current_dir.parent.parent / "01_Data/app-config/RBTP" / "transformed-app-config-dfr-only.json"
with open(output_path, "w") as f:
    json.dump(json_list, f, indent=2)
