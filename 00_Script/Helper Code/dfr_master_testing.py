'''this code reads the output transformed app-config.json and returns concatenated specific credentials based on "credential_request" for testing purposes
for example, after using main_transformer.py, we would like to get only the DFR credentials for testing in tests-untp
then, run this code by passing credential_request = 'DFR'
'''

import json
from pathlib import Path
from typing import Dict, Any, List


############## PARAMETERS & VARIABLES #####################

current_dir = Path(__file__).resolve().parent
input_path = (current_dir.parent.parent / "01_Data/app-config/RBTP" / "transformed-app-config-v4.json")
credential_request = 'DFR'

###########################################################


with open(input_path, "r") as f:
    config_data = json.load(f)

apps = config_data.get("apps", [])

json_list = [] # initialises json list for output
i=1
for app in apps:
    features = app.get("features", [])
    for feature in features:
        components = feature.get("components", [])
        # Initialize credential_type to None
        credential_type = None
    
        for component in components: # update component
            if component.get("type") == "EntryData": #only process 
                if component.get("name") == "LocalStorageLoader": #to identify 2 types of json types "LocalStorageLoader/NestedComponents" and standard "JsonForm"
                    nestedcomponents = component['props']['nestedComponents']
                    if len(nestedcomponents) == 1:
                        schema_url = nestedcomponents[0]["props"]["schema"]["url"]
                    else:
                        print('Multiple nested components found. Please investigate')
                        break
                else:
                    schema_url = component["props"]["schema"]["url"]
                # Detect type from schema URL
                if "DigitalFacilityRecord" in schema_url:
                    credential_type = "DFR"
                # elif "DigitalTraceabilityEvent" in schema_url:
                #     credential_type = "DTE"
                # elif "DigitalProductPassport" in schema_url:
                #     credential_type = "DPP"
                # elif "DigitalConformityCredential" in schema_url:
                #     credential_type = "DCC"
                # elif "DigitalIdentityAnchor" in schema_url:
                #     credential_type = "DIA"
                else:
                    continue  # Skip unknown
        
        if credential_type == credential_request:
            print(feature)
            print('credential_type', credential_type)
            feature['name'] += f" {str(i)}"
            json_list.append(feature)
            i += 1


output_path = current_dir.parent.parent / "01_Data/app-config/RBTP" / "transformed-app-config-dfr-only-v4.json"
with open(output_path, "w") as f:
    json.dump(json_list, f, indent=2)

# THE ABOVE ONLY OUTPUTS THE DFRS, can't test them in test-untp if they're in the same file