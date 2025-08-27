import json
from pathlib import Path
from typing import Dict, Any, List
from dfr import DFRTransformer, CredentialTransformer



# ---------- Base Class ----------
class GeneralMigrator:
    @staticmethod # does not require self parameter
    def migrate_general_v_050_to_v_060(services: Dict[str, Any]) -> Dict[str, Any]:
        """
        Applies general migration rules from 0.5.0 to 0.6.0 for services.
        - Update service URLs to /api/1.0.0.
        - Change dlrAPIUrl and linkRegisterPath for IDR Service.
        """
        parameters = services.get('parameters',[])
       
        for param in parameters:
            # Storage Service
            storage = param.get('storage')
            if storage:
                storage['url'] = "http://localhost:3334/api/1.0.0/documents"
            
            # Identity Resolver (IDR) Service
            dlr = param.get('dlr')
            if dlr:
                dlr['dlrAPIUrl'] = "http://localhost:3000/api/1.0.0"
                dlr['linkRegisterPath'] = "resolver"
        
        return services



# ---------- Orchestrator ----------
class AppConfigProcessor:
    def __init__(self, config_path: str):
        self.config_path = Path(config_path)
        self.config_data = self.load_config()

    def load_config(self) -> Dict[str, Any]:
        with open(self.config_path, "r") as f:
            return json.load(f)

    def process(self) -> Dict[str, Any]:
        # The entire config is migrated, as transformations affect components and services
        # json_list = []
        apps = self.config_data.get("apps", [])
        
        for app in apps:
            features = app.get("features", [])
            for feature in features:
                components = feature.get("components", [])
                services = feature.get("services", [])

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
                        # elif "DigitalProductPassport" in schema_url:
                        #     credential_type = "DPP"
                        # elif "DigitalConformityCredential" in schema_url:
                        #     credential_type = "DCC"
                        else:
                            continue  # Skip unknown
                        transformer = TransformerFactory.get_transformer(credential_type, component)
                        transformed_component = transformer.transform()
                        # Update the component in place
                        component.update(transformed_component)
                # json_list.append(component)

                if credential_type:
                    for service in services: # update services 
                        if service['name'].startswith('process'):
                            # apply transformation for services
                            transformer = TransformerFactory.get_transformer(credential_type, service)
                            transformed_component = transformer.transform_services()
                            # Update the component in place
                            service.update(transformed_component)
                            # apply general transformation
                            transformed_component = GeneralMigrator.migrate_general_v_050_to_v_060(service)
                            # Update the component in place
                            service.update(transformed_component)
                else:
                    print("No valid credential type found.")
        return self.config_data #, json_list



# ---------- Factory ----------
class TransformerFactory:
    @staticmethod
    def get_transformer(credential_type: str, component: Dict[str, Any]) -> CredentialTransformer:
        transformers = {
            "DFR": DFRTransformer
            # "DPP": DPPTransformer,
            # "DCC": DCCTransformer,
        }
        if credential_type in transformers: # if "DFR" is in the dictionary list, then get the transformer name
            return transformers[credential_type](component) # Returns DFRTransformer
        else:
            raise ValueError(f"Unknown credential type: {credential_type}")


# ---------- Example Usage ----------
'''
This code takes input app-config.json, iterates through the apps & features, identifies credential type and applies transformations.
This code outputs the transofmred app-config.json
'''
if __name__ == "__main__":
    current_dir = Path(__file__).resolve().parent

    input_folder_name = "01_Data/app-config/RBTP"
    file_name = "app-config.json"
    output_file_name = "transformed-app-config-v5.json"
    processor = AppConfigProcessor(current_dir.parent / input_folder_name / file_name)
    output = processor.process()

    output_path = current_dir.parent / input_folder_name / output_file_name
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
    
    print("Transformation complete!")





