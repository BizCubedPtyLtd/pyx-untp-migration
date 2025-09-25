import json
from pathlib import Path
from typing import Dict, Any, List
#from general_function import GeneralFunction

# The class below transforms DPP credentials from v0.5.0 to v0.6.0
# ---------- Base Class ----------
class CredentialTransformer:
    def __init__(self, component: Dict[str, Any]):
        """
        Initialize with the entire component dict, as transformations may affect props, data, services, etc.
        """
        self.component = component

    def transform(self) -> Dict[str, Any]:
        """Default transform, to be overridden by subclasses."""
        raise NotImplementedError("Subclasses must implement this method.")

# ---------- DIA Transformer ----------
class DIATransformer(CredentialTransformer):
    def transform(self) -> Dict[str, Any]:
        '''
        This function transforms data in "components" 
        '''
        
        ## TO RESOLVE: NestedComponents / LocalStorageLoader showing blank on issuing page. remove name, type, props, storagekey and flattens nestedcomponents to component
        if self.component['name'] == 'LocalStorageLoader':
            clean_data = self._clean_identifier_list(self.component, ['name', 'type'])
            self.component = clean_data
            self.component = self.component['props']['nestedComponents'][0]

        #####################################
        ## Data Model
        #####################################
        # Specific data model changes for "component"
        data = self.component["props"]["data"]

        credential_subject = data.get("credentialSubject", {})
        if credential_subject == {} or not credential_subject: # fix for credentials without credential_subject, reassign data to credential_subject
            credential_subject = data
        else: # if there is credential subject, clean top-level data
            self._clean_identifier_list(data, ['type', '@context', 'issuer'])

        # 2*. Issuer Identifier Structure: The issuer’s otherIdentifier property is replaced with issuerAlsoKnownAs, simplifying the structure by removing the idScheme reference.
        issuer = data.get('issuer', {})
        if "otherIdentifier" in issuer:
            clean_data_0 = self._pop_and_replace_key(issuer, "otherIdentifier", "issuerAlsoKnownAs")
            clean_data_0 = self._clean_identifier_list(clean_data_0, ["type", "idScheme"]) 
            issuer["issuerAlsoKnownAs"] = clean_data_0

        #Removed Identifier type inheritance from RegisteredIdentity
        data_type = data.get('type', {})
        if 'Identifier' in data_type:
            data_type.remove('Identifier')
        print(data_type)
        
        # Resolve JSON-LD Issue
        self._clean_identifier_list(data, ['entityId', 'businessNumber'])

        # Flatten credentialSubject and clean top-level data
        self._flatten_credential_subject(data, 'credentialSubject')
        
        return self.component
    
    def transform_services(self) -> Dict[str, Any]:
        '''
        Transforms the 'Services' section of the features.

        This function updates services for credential migration:
        - Sets the context for digitalFacilityRecord to the new vocabulary URL.
        - Updates the renderTemplate for each service with a new HTML template.
        - Cleans up type fields in renderTemplate items.
        - Renames 'otherIdentifier' to 'issuerAlsoKnownAs' in vckit issuer if present.

        Returns:
            Dict[str, Any]: The updated dictionary.
        '''
        # 2. Context in Services updates
        parameters = self.component.get('parameters', [])
        for param in parameters: #iterate through param -> services
            context_configuration = param.get('digitalIdentityAnchor')
            context = context_configuration.get('context', {})
            old = "https://test.uncefact.org/vocabulary/untp/dia/0.2.1/"
            new = "https://test.uncefact.org/vocabulary/untp/dia/0.6.0/"
            # Remove all occurrences of old and new
            context = [c for c in context if c not in (old, new)]
            # Insert new at the front
            context.insert(0, new)
            # Update the context in the config
            context_configuration['context'] = context


            # 4. Render Template Updates
            hbs_template = "<!DOCTYPE html><html lang=\"en\"><head> <meta charset=\"UTF-8\" /> <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" /> <link href=\"https://fonts.googleapis.com/css2?family=Lato:ital,wght@0,100;0,300;0,400;0,700;0,900;1,100;1,300;1,400;1,700;1,900&display=swap\" rel=\"stylesheet\"> <title>Digital Identity Anchor</title> <style> :root { /* Brand Colors */ --color-primary: rgba(35, 46, 61, 1); /* Main header background; Default: rgba(35, 46, 61, 1) */ /* Neutrals */ --color-white: rgba(255, 255, 255, 1); /* Text color for titles, descriptions, and values in header and details sections, background color for issuing details; Default: rgba(255, 255, 255, 1) */ --color-black: rgba(0, 0, 0, 1); /* Text color for issuing details title; Default: rgba(0, 0, 0, 1) */ --color-gray-700: rgba(35, 46, 61, 1); /* Text color for issuer links and issuing details values; Default: rgba(35, 46, 61, 1) */ --color-gray-600: rgba(85, 96, 110, 1); /* Background color for identity details section, text color for issuing details labels; Default: rgba(85, 96, 110, 1) */ --color-gray-500: rgba(169, 177, 183, 1); /* Border color for identity details rows; Default: rgba(169, 177, 183, 1) */ --color-gray-400: rgba(212, 214, 216, 1); /* Border color for issuing details rows; Default: rgba(212, 214, 216, 1) */ --color-gray-300: rgba(237, 239, 240, 1); /* Text color for identity details labels; Default: rgba(237, 239, 240, 1) */ /* Semantic (Functional) Colors */ --color-link-underline-dark: rgba(79, 149, 221, 1); /* Underline color for issuer links; Default: rgba(79, 149, 221, 1) */ --color-link-underline-light: rgba(148, 196, 245, 1); /* Underline color for identifier scheme links; Default: rgba(148, 196, 245, 1) */ /* Font Variables */ --font-family: \"Lato\", sans-serif; /* Font family for all text; Default: Lato, sans-serif */ /* Font Weight Variables */ --font-weight-regular: 400; /* Font weight for labels; Default: 400 */ --font-weight-medium: 500; /* Font weight for titles, descriptions, values, and links; Default: 500 */ --font-weight-bold: 700; /* Font weight for issuing details title; Default: 700 */ --font-weight-black: 900; /* Font weight for main title; Default: 900 */ } /* Global CSS */ * { margin: 0; box-sizing: border-box; } body { font-family: var(--font-family); } section { padding: 0 16px; } a { text-decoration: none; } .identity-anchor { width: 100%; margin: 0 auto; display: flex; flex-direction: column; } .identity-anchor-header { display: flex; flex-direction: column; width: 100%; align-items: center; } .identity-header { display: flex; flex-direction: column; width: 100%; align-items: flex-start; gap: 12px; padding: 32px 16px 20px; background-color: var(--color-primary); } .identity-anchor .identity-title { width: 100%; font-weight: var(--font-weight-medium); color: var(--color-white); font-size: 16px; line-height: 22px; text-transform: uppercase; } .identity-anchor .name-description { display: flex; flex-direction: column; gap: 8px; } .identity-anchor .name-description h1 { font-weight: var(--font-weight-black); color: var(--color-white); font-size: 30px; line-height: 32.5px; } .identity-anchor .name-description p { font-weight: var(--font-weight-medium); color: var(--color-white); font-size: 16px; line-height: 17.4px; } .identity-anchor .identity-details-section { padding: 0 16px 16px; align-self: stretch; width: 100%; display: flex; flex-direction: column; align-items: flex-start; gap: 4px; background-color: var(--color-gray-600); } .identity-anchor .grid-row { display: grid; grid-template-columns: 1fr 2fr; gap: 16px; padding: 10px 0 12px; width: 100%; border-bottom-width: 1px; border-bottom-style: solid; } .identity-anchor .grid-row:last-child { border-bottom: none; } .identity-anchor .border-bottom-gray-500 { border-color: var(--color-gray-500); } .identity-anchor .label { font-weight: var(--font-weight-regular); color: var(--color-gray-300); font-size: 16px; line-height: 22px; } .identity-anchor .grid-value { display: flex; align-items: center; gap: 10px; align-self: stretch; flex-grow: 1; flex: 1; } .identity-anchor .grid-value-text { font-weight: var(--font-weight-medium); color: var(--color-white); font-size: 16px; line-height: 17.4px; flex: 1; } .identity-anchor .issuing-details { width: 100%; padding: 24px 16px 36px; background-color: var(--color-white); display: flex; flex-direction: column; align-items: flex-start; gap: 4px; } .identity-anchor .typography-heading { display: inline-flex; align-items: center; justify-content: center; gap: 10px; } .identity-anchor .issuing-title { width: fit-content; font-weight: var(--font-weight-bold); color: var(--color-black); font-size: 20px; line-height: 21.8px; } .identity-anchor .identity-details { display: inline-flex; flex-direction: column; align-items: flex-start; width: 100%; } .identity-anchor .grid-row-alt { display: grid; grid-template-columns: 1.4fr 3fr; gap: 16px; padding: 10px 0 12px; width: 100%; border-bottom-width: 1px; border-bottom-style: solid; } .identity-anchor .border-bottom-gray-400 { border-color: var(--color-gray-400); } .identity-anchor .label-alt { font-weight: var(--font-weight-regular); color: var(--color-gray-600); font-size: 16px; line-height: 22px; } .identity-anchor .grid-value-link { flex-direction: column; align-items: flex-start; gap: 6px; align-self: stretch; display: flex; flex: 1; flex-grow: 1; } .identity-anchor .div-wrapper { gap: 10px; display: inline-flex; align-items: flex-start; text-decoration: underline; text-decoration-thickness: 2px; text-decoration-color: var(--color-link-underline-dark); text-underline-offset: 3px; } .identity-anchor .issuer-link { width: fit-content; font-weight: var(--font-weight-medium); color: var(--color-gray-700); font-size: 16px; line-height: 22px; } .identity-anchor .grid-value-text-alt { font-weight: var(--font-weight-medium); color: var(--color-gray-700); font-size: 16px; line-height: 17.4px; flex: 1; } .blue-bottom-line-2, .blue-bottom-line-2:link { width: fit-content; color: var(--color-white); text-decoration: underline; text-decoration-thickness: 2px; text-decoration-color: var(--color-link-underline-light); text-underline-offset: 3px; } /* Media Queries for Desktops */ @media (min-width: 1200px) { .identity-anchor { max-width: 1200px; } } </style></head><body> <div class=\"identity-anchor\"> <div class=\"identity-anchor-header\"> <header class=\"identity-header\"> <div class=\"identity-title\">DIGITAL IDENTITY ANCHOR</div> <div class=\"name-description\"> <h1>{{credentialSubject.name}}</h1> <p>{{credentialSubject.id}}</p> </div> </header> <section class=\"identity-details-section\"> <div class=\"identity-details\"> {{#if credentialSubject.idScheme.name}} <div class=\"grid-row border-bottom-gray-500\"> <div class=\"label\">Identifier Scheme</div> <div class=\"grid-value\"> {{#if credentialSubject.idScheme.id}} <a href=\"{{credentialSubject.idScheme.id}}\" class=\"blue-bottom-line-2\" aria-label=\"Visit {{credentialSubject.idScheme.name}}\" target=\"_blank\">{{credentialSubject.idScheme.name}}</a> {{else}} <div class=\"grid-value-text\">{{credentialSubject.idScheme.name}}</div> {{/if}} </div> </div> {{/if}} {{#if credentialSubject.registeredId}} <div class=\"grid-row border-bottom-gray-500\"> <div class=\"label\">Registered ID</div> <div class=\"grid-value\"> <div class=\"grid-value-text\">{{credentialSubject.registeredId}}</div> </div> </div> {{/if}} {{#if credentialSubject.registerType}} <div class=\"grid-row border-bottom-gray-500\"> <div class=\"label\">Register Type</div> <div class=\"grid-value\"> <div class=\"grid-value-text\">{{credentialSubject.registerType}}</div> </div> </div> {{/if}} </div> </section> </div> <section class=\"issuing-details\"> <div class=\"typography-heading\"> <h2 class=\"issuing-title\">Issuing Details</h2> </div> <div class=\"identity-details\"> <div class=\"grid-row-alt border-bottom-gray-400\"> <div class=\"label-alt\">Issued by</div> <div class=\"grid-value-link\"> <div class=\"div-wrapper\"> <a href=\"{{issuer.id}}\" class=\"issuer-link\" aria-label=\"Visit {{issuer.name}}\" target=\"_blank\">{{issuer.name}}</a> </div> </div> </div> {{#if validFrom}} <div class=\"grid-row-alt border-bottom-gray-400\"> <div class=\"label-alt\">Valid from</div> <div class=\"grid-value\"> <div class=\"grid-value-text-alt\">{{validFrom}}</div> </div> </div> {{/if}} {{#if validUntil}} <div class=\"grid-row-alt border-bottom-gray-400\"> <div class=\"label-alt\">Valid until</div> <div class=\"grid-value\"> <div class=\"grid-value-text-alt\">{{validUntil}}</div> </div> </div> {{/if}} </div> </section> </div></body></html>"
            render_template = context_configuration.get('renderTemplate',[])
            for item in render_template: #iterates through renderTemplate
                item["template"] = hbs_template

                # Removes duplicated type fields in renderTemplate
                if "@type" in item and "type" in item: # if both are present, delete "@type"
                    del item["@type"]
                elif "@type" in item and "type" not in item: # if only "@type" is present, change the field name to "type"
                    item["type"] = item.pop("@type")
            
            data_types = context_configuration.get('type', {})
            # # Removed Identifier type inheritance from RegisteredIdentity
            # if 'Identifier' in data_types:
            #     data_types.remove('Identifier')
        
            vckit = param.get('vckit')
            if vckit:
                vckit_issuer = vckit.get('issuer', {})
                if "otherIdentifier" in vckit_issuer: # Updates 'otherIdentifier' to 'issuerAlsoKnownAs' and retains the position
                    self._pop_and_replace_key(vckit_issuer, "otherIdentifier", "issuerAlsoKnownAs")
        return self.component

    
    def _pop_and_replace_key(self, d: Dict[str, Any], old_key: str, new_key: str):
        """
        Works like dict.pop(), but renames the key in-place
        while keeping its original position in the dict. For example:
        pop_and_replace_key(
            facility_new,         # d → the dict to modify
            "otherIdentifier",    # old_key → the key we want to change
            "facilityAlsoKnownAs" # new_key → the new name for the key
        )
        Before:

        {
            "otherIdentifier": [...],
            "address": {...},
            "locationInformation": {...}
        }
        After:

        {
            "facilityAlsoKnownAs": [...],
            "address": {...},
            "locationInformation": {...}
        }
        """
        if old_key not in d:
            return None
        value = d[old_key]
        new_dict = {}
        for k, v in d.items():
            if k == old_key:
                new_dict[new_key] = v
            else:
                new_dict[k] = v

        d.clear()
        d.update(new_dict)

        return value
    
    def _clean_identifier_list(self, identifier: Any, remove_fields: List[str] = None):
        """
        Removes specified fields from dictionaries within a list or from a single dictionary.

        This function is used to clean up identifier objects by removing unwanted fields
        (such as "type" and "idScheme") from each dictionary in a list, or directly from a dictionary.

        Args:
            identifier (Any): The identifier to clean, can be a list of dicts or a single dict.
            remove_fields (List[str], optional): List of field names to remove. Defaults to ["type", "idScheme"].

        Returns:
            Any: The cleaned identifier (list or dict).

        """
        if remove_fields is None:
            remove_fields = ["type", "idScheme"]
        if isinstance(identifier, list):
            for item in identifier:
                if isinstance(item, dict):
                    for field in remove_fields:
                        item.pop(field, None)
        elif isinstance(identifier, dict):
            for field in remove_fields:
                identifier.pop(field, None)
        return identifier
    
    def _flatten_credential_subject(self, data: Dict[str, Any], field_flatten: str) -> Dict[str, Any]:
        """
        Flattens a nested dictionary field into the parent dictionary.

        This function removes the specified field (`field_flatten`) from `data`,
        and merges its key-value pairs into the top-level of `data`.
        Useful for flattening structures like 'credentialSubject' so its contents
        are directly accessible in the parent dictionary.

        Args:
            data (Dict[str, Any]): The dictionary to flatten.
            field_flatten (str): The key of the nested dictionary to flatten.

        Returns:
            Dict[str, Any]: The updated, flattened dictionary.
        """

        if field_flatten in data:
            cs = data.pop(field_flatten)
            data.update(cs)
        return data