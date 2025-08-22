
import json
from pathlib import Path
from typing import Dict, Any, List
from dfr import DFRTransformer, CredentialTransformer



# ---------- Base Class ----------
class GeneralMigrator:
    @staticmethod
    def migrate_general_v_050_to_v_060(services: Dict[str, Any]) -> Dict[str, Any]:
        """
        Applies general migration rules from 0.5.0 to 0.6.0.
        - Update service URLs to /api/1.0.0.
        - Change linkRegisterPath for IDR Service.
        """
        
        # print('componentttt', component)
        parameters = services.get('parameters',[])
        # print('component', component)
        # print('parameters', services)
       
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
                #print('services111',services)
                for component in components: # update component
                    #print('component1',component)
                    if component.get("type") == "EntryData":
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
                    
                        transformer = TransformerFactory.get_transformer(credential_type, component)
                        transformed_component = transformer.transform()
                        # Update the component in place
                        component.update(transformed_component)
                # json_list.append(component)

                for service in services: # update services 
                    # apply transformation for services
                    transformed_component = transformer.transform_services()
                    # Update the component in place
                    service.update(transformed_component)

                    # apply general transformation
                    transformed_component = GeneralMigrator.migrate_general_v_050_to_v_060(service)
                    # Update the component in place
                    service.update(transformed_component)
        
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
if __name__ == "__main__":
    current_dir = Path(__file__).resolve().parent
    #print(current_dir)
    processor = AppConfigProcessor(current_dir.parent / "01_Data/app-config/RBTP" / "app-config.json")
    output = processor.process()

    output_path = current_dir.parent / "01_Data/app-config/RBTP" / "transformed-app-config.json"
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
    
    # output_path_testing = current_dir.parent / "01_Data/app-config/RBTP" / "dfr-transformed-app-config.json"
    # with open(output_path_testing, "w") as f:
    #     json.dump(for_testing, f, indent=2)

    print("Transformation complete!")





