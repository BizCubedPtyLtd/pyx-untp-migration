import json
from pathlib import Path
from typing import Dict, Any, List
from dfr import CredentialTransformer
from dfr import DFRTransformer
from dte import DTETransformer
from dpp import DPPTransformer
from dcc import DCCTransformer
from dia import DIATransformer
from collections import defaultdict
import pandas as pd

# ---------- Base Class ----------
class GeneralMigrator:
    @staticmethod # does not require self parameter
    def migrate_general_v_050_to_v_060(services: Dict[str, Any]) -> Dict[str, Any]:
        """
        This function applies general migration rules from 0.5.0 to 0.6.0 for services.
        - Update service URLs to /api/1.0.0.
        - Change dlrAPIUrl and linkRegisterPath for IDR Service.
        Input/output: the "services" dictionary and returns the transformed dictionary.
        """
        parameters = services.get('parameters',[]) # gets parameters
       
        for param in parameters:
            # Update storage service URL if present
            storage = param.get('storage')
            if storage:
                storage['url'] = "http://localhost:3334/api/1.0.0/documents"
            
            # Update IDR service API URL and register path if present
            dlr = param.get('dlr')
            if dlr:
                dlr['dlrAPIUrl'] = "http://localhost:3000/api/1.0.0"
                dlr['linkRegisterPath'] = "resolver"
        
        return services



# ---------- Orchestrator / Master Function ----------
# This class processes the entire app-config.json, applies transformations based on credential types
class AppConfigProcessor:
    def __init__(self, config_path: str):
        self.config_path = Path(config_path)
        self.config_data = self.load_config()

    def load_config(self) -> Dict[str, Any]:
        # This function loads the app-config from a JSON file.
        with open(self.config_path, "r") as f:
            return json.load(f)

    def process(self) -> Dict[str, Any]:
        # This function processes the app configuration and applies necessary transformations.
        # json_list = []

        # update identitiyProvider
        identifyProvider = self.config_data.get("identifyProvider", [])
        print(identifyProvider)
        if "url" in identifyProvider:
            identifyProvider['url'] = 'http://localhost:3001/api/1.0.0'
            #self.config_data['identifyProvider'] = identifyProvider

        # update apps
        apps = self.config_data.get("apps", [])
        count = defaultdict(int)
        for app in apps:
            features = app.get("features", [])
            for feature in features:
                components = feature.get("components", [])
                services = feature.get("services", [])

                # Initialize credential_type to None
                credential_type = None
                updated_components = []
                for component in components: # update component
                    if component.get("type") == "EntryData": #only process 
                        # Identifies either 2 types of JSON structures: "LocalStorageLoader/NestedComponents" and standard "JsonForm"
                        # If "LocalStorageLoader" is found, then processes nested components. Otherwise, processes standard "JsonForm"
                        if component.get("name") == "LocalStorageLoader": 
                            nestedcomponents = component['props']['nestedComponents']
                            if len(nestedcomponents) == 1: # Assumes single nested component
                                schema_url = nestedcomponents[0]["props"]["schema"]["url"]
                            else:
                                break
                        else:
                            schema_url = component["props"]["schema"]["url"]
                        # Detect type from schema URL
                        if "DigitalFacilityRecord" in schema_url:
                            credential_type = "DFR"
                            count['DFR'] += 1
                            print("DFR found, continue to transform.")
                        elif "traceabilityEvents" in schema_url:
                            credential_type = "DTE"
                            count['DTE'] += 1
                            print("DTE found, continue to transform.")
                        elif "DigitalProductPassport" in schema_url:
                            credential_type = "DPP"
                            count['DPP'] += 1
                            print("DPP found, continue to transform.")
                        elif "ConformityCredential" in schema_url:
                             credential_type = "DCC"
                             count['DCC'] += 1
                             print("DCC found, continue to transform.")
                        elif "DigitalIdentityAnchor" in schema_url:
                            credential_type = "DIA"
                            count['DIA'] += 1
                            print("DIA found, continue to transform.")
                        else:
                            print('Unknown type of credential. Please investigate')
                            continue  # Skip unknown

                        transformer = TransformerFactory.get_transformer(credential_type, component) # Gets the transformer name, such as DFRTransformer
                        transformed_component = transformer.transform()
                        
                        # Update the component in place
                        component.update(transformed_component)
                        updated_components.append(component)
                    # If name = 'BarcodeGenerator', remove it
                    elif component.get('name') == 'BarcodeGenerator':
                        continue
                    else:
                        updated_components.append(component)
                components[:] = updated_components
                        
                #### UPDATE SERVICES ######

                updated_services = []
                if credential_type: # If a valid credential type was found
                    # The below transformer applies structural changes to "apps" -> "features" -> "services"
                    for service in services: # update services 
                        if service['name'].startswith('process'):
                            # Apply transformation for services specific to the credential types
                            transformer = TransformerFactory.get_transformer(credential_type, service)
                            # initialize the class
                            transformed_component = transformer.transform_services()
                            # Update the component in place
                            service.update(transformed_component)
                            # Apply general migration transformation to all credential types
                            transformed_component = GeneralMigrator.migrate_general_v_050_to_v_060(service)
                            # Update the component in place
                            service.update(transformed_component)
                            updated_services.append(service)
                        elif service['name'] in ['mergeToLocalStorage', 'getValueFromLocalStorage']: #, remove them from services
                            continue  
                        else:
                            updated_services.append(service)
                    services[:] = updated_services
                else:
                    print("No valid credential type found.")
        return self.config_data, count #, json_list



# ---------- Factory ----------
class TransformerFactory:
    @staticmethod
    def get_transformer(credential_type: str, component: Dict[str, Any]) -> CredentialTransformer:
        '''
        This function takes credential_type and retrieves the appropriate transformer for a given credential type.
        '''
        transformers = {
            "DFR": DFRTransformer,
            "DTE": DTETransformer,
            "DPP": DPPTransformer,
            "DCC": DCCTransformer,
            "DIA": DIATransformer
        }
        # If the credential type is in the dictionary keys, extracts the value to get transformer name
        # For example: if "DFR" is in the dictionary keys, then get the transformer name
        if credential_type in transformers: 
            print('transformer found for', transformers[credential_type])
            return transformers[credential_type](component) # Returns the value of input key
        else:
            raise ValueError(f"Unknown credential type: {credential_type}")


# ---------- Example Usage ----------
'''
This code takes input app-config.json, iterates through the apps & features, identifies credential type and applies transformations.
This code outputs the transformed app-config.json
'''
if __name__ == "__main__":

    ############## PARAMETERS & VARIABLES #####################

    current_dir = Path(__file__).resolve().parent

    input_folder_name = "01_Data/app-config"
    brand_name = 'ACRS'
    file_name = "app-config.json"
    version = '0.6.0'
    output_file_name = f"transformed-app-config-{brand_name}-v{version}.json"
    
    input_path = current_dir.parent / input_folder_name / brand_name  / file_name
    output_path = current_dir.parent / input_folder_name / brand_name / output_file_name #testing_folder / output_file_name

    ###########################################################

    processor = AppConfigProcessor(input_path)
    output, count = processor.process()

    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    df = pd.DataFrame(list(count.items()), columns=['Type', 'Count'])
    print('List of transformed credential types: \n', df)
    print("Transformation complete!")





