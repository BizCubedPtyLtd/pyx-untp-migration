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

# ---------- DPP Transformer ----------
class DPPTransformer(CredentialTransformer):
    def transform(self) -> Dict[str, Any]:
        '''
        This function transforms data in "components" 
        '''
        
        ## TO RESOLVE: NestedComponents / LocalStorageLoader showing blank on issuing page. remove name, type, props, storagekey and flattens nestedcomponents to component
        if self.component['name'] == 'LocalStorageLoader':
            clean_data = self._clean_identifier_list(self.component, ['name', 'type'])
            self.component = clean_data
            self.component = self.component['props']['nestedComponents'][0]

        # Specific DFR data model changes for "component"
        data = self.component["props"]["data"]

        ## Reference Implementation Updates
        # 1. Updates Schema URL to v0.6.0
        schema = self.component["props"]["schema"]
        schema["url"] = "https://jargon.sh/user/unece/DigitalProductPassport/v/0.6.0/artefacts/jsonSchemas/ProductPassport.json?class=ProductPassport"
        

        ## Data Model Changes 
        # 2*. Credential Subject Structure: adds "type": ["ProductPassport"] to the original structure, added "granularityLevel": "item" to product
        credential_subject = data.get("credentialSubject", {})
        if credential_subject == {}:
            # get the credential_subject data from data
            credential_subject = data
        product = {k: v for k, v in credential_subject.items() if k != "conformityClaim"}
        product["granularityLevel"] = "item"
        new_credential_subject = {
            "type": ["ProductPassport"],
            "id": credential_subject.get("id", ""),
            "product": product,
            "conformityClaim": credential_subject.get("conformityClaim", [])
        }
        data["credentialSubject"] = new_credential_subject

        # 3*. Issuer Identifier Structure: The issuer’s otherIdentifier property is replaced with issuerAlsoKnownAs, simplifying the structure by removing the idScheme reference.
        # issuer = data.get('issuer', {})
        # if "otherIdentifier" in issuer:
        #     self._pop_and_replace_key(issuer, "otherIdentifier", "issuerAlsoKnownAs")

        # 3*. Issuer Identifier Structure: The issuer’s otherIdentifier property is replaced with issuerAlsoKnownAs, simplifying the structure by removing the idScheme reference.
        issuer = new_credential_subject.get('issuer', {})
        if "otherIdentifier" in issuer:
            clean_data_0 = self._pop_and_replace_key(issuer, "otherIdentifier", "issuerAlsoKnownAs")
            clean_data_0 = self._clean_identifier_list(clean_data_0, ["type", "idScheme"]) 
            issuer["issuerAlsoKnownAs"] = clean_data_0
        
        # 4.* Party Structure Changes:
        product = new_credential_subject.get('product', {})

        
        # Removed "type" in idScheme from the product object itself, as it’s no longer required in the inline structure.
        if "idScheme" in product:
            if "type" in product["idScheme"]:
                del product["idScheme"]["type"]

        '''removed the nested idScheme structure from producedByParty and producedAtFacility.
        removed 'type' and 'idscheme' from producedByParty and producedAtFacility.
        '''
        producedByParty = product.get('producedByParty', {})
        self._clean_identifier_list(producedByParty)

        producedAtFacility = product.get('producedAtFacility', {})
        self._clean_identifier_list(producedAtFacility)
        
        '''
        5. Material Structure Changes
        Key Changes:

        Renamed massAmount to mass and recycledAmount to recycledMassFraction.
        Simplified issuingParty in the Standard and administeredBy in Regulation by removing the nested idScheme structure.

        '''
        materialsProvenance = product.get('materialsProvenance', {})
        for material in materialsProvenance:
            if "type" in material:
                del material["type"]
            if "massAmount" in material:
                material["mass"] = material.pop("massAmount")
                if "type" in material['mass']:
                    del material['mass']['type']
            if "recycledAmount" in material:
                material["recycledMassFraction"] = material.pop("recycledAmount")

        # Change CredentialSubject
        # credentialSubject - conformityClaim - issuingParty structure change (Standard schema)
        # changes issuingParty to issuerAlsoKnownAs
        # Removes Type and idScheme
        conformityClaim = new_credential_subject.get('conformityClaim', {})
        for claim in conformityClaim:
            referencestandard = claim.get("referenceStandard", {})
            if "issuingParty" in referencestandard:
                # referencestandard["issuerAlsoKnownAs"] = referencestandard.pop("issuingParty")
                clean_data = self._clean_identifier_list(referencestandard["issuingParty"])
                referencestandard["issuingParty"] = clean_data
                if "type" in referencestandard["issuingParty"]:
                    del referencestandard["issuingParty"]["type"]
                if "idScheme" in referencestandard["issuingParty"]:
                    del referencestandard["issuingParty"]["idScheme"]

            # credentialSubject - conformityClaim - administeredBy structure change (Regulation schema)
            # Removes Type and idScheme from referenceStandard.issuingParty and referenceRegulation.administeredBy
            referenceregulation = claim.get("referenceRegulation", {})
            if "administeredBy" in referenceregulation:
                clean_data = self._clean_identifier_list(referenceregulation["administeredBy"])
                referenceregulation["administeredBy"] = clean_data

            
            ##### RESOLVE UNTP SCHEMA VALIDATION ISSUE #####
            # Location: credentialSubject → conformityClaim → 0 → declaredValue → 0 → metricValue
            # Issue: must have required property 'value' - add value in metricValue
            if "declaredValues" in claim:
                claim["declaredValue"] = claim.pop("declaredValues")
            
            declaredValues = claim.get('declaredValue', [])
            for declaredValue in declaredValues:
                # if metricvalue in declaredvalue is metricvalue: {}, add "value":0 and "unit":""
                if declaredValue.get("metricValue") == {} or not declaredValue.get("metricValue"):
                    declaredValue["metricValue"] = {"unit": "", "value": 0}

            ### RESOLVE JSON-LD SCHEMA VALIDATION ISSUE ###
            '''
            Location: credentialSubject → conformityClaim → 0 → conformityTopic Issue: must be equal to one of the allowed values
            Must be one of: environment.energy, environment.emissions, environment.water, environment.waste, environment.deforestation, environment.biodiversity, circularity.content, circularity.design, social.labour, social.rights, social.community, social.safety, governance.ethics, governance.compliance, governance.transparency
            #   */ 6*. Criterion Structure Enhancement
            '''
            conformityTopic = claim.get('conformityTopic', '')
            if conformityTopic not in ["environment.energy", "environment.emissions", "environment.water", "environment.waste", "environment.deforestation", "environment.biodiversity", "circularity.content", "circularity.design", "social.labour", "social.rights", "social.community", "social.safety", "governance.ethics", "governance.compliance", "governance.transparency"]:
                claim['conformityTopic'] = "environment.emissions" # sets a default/choose one

            '''
            6. Criterion Structure Enhancement
            Key Changes:

            Criterion now includes additional fields: description, conformityTopic, status, subCriterion, thresholdValue (replacing thresholdValues), performanceLevel, and tags. The thresholdValues property has been renamed to thresholdValue to reflect a singular metric focus per criterion. The subCriterion property allows for hierarchical structuring, enabling a criterion to reference subordinate criteria.
            issuingParty in the Standard and administeredBy in Regulation by removing the nested idScheme structure.

            '''
            assessmentCriteria = claim.get('assessmentCriteria', {})
            for assessment in assessmentCriteria:
                new_column_added = {
                    "description":"",
                    "conformityTopic":"environment.emissions",
                    "status":"active",
                    "subCriterion":[],
                    "performanceLevel":"",
                    "tags": ""
                }
                assessment.update(new_column_added)
                threshold_values = assessment.pop("thresholdValues",[])
                if threshold_values:
                    assessment["thresholdValue"] = threshold_values[0]
                else:
                    assessment['thresholdValue'] = []

            ### RESOLVE JSON-LD SCHEMA VALIDATION ISSUE: removes assessedProduct as not relevant to dpp###
            if "assessedProduct" in claim:
                del claim['assessedProduct']
    
        
        # Flatten credentialSubject and clean top-level data
        component_data = self.component["props"]["data"]
        self._clean_identifier_list(component_data, ['type', '@context', 'issuer'])
        self._flatten_credential_subject(component_data, 'credentialSubject')
        # RESOLVE UNTP SCHEMA VALIDATION ISSUE
        
        '''
        Issue: Properties "credentialSubject/product/granularityLevel, credentialSubject/product/dueDiligenceDeclaration, credentialSubject/product/materialsProvenance, credentialSubject/product/circularityScorecard, credentialSubject/product/emissionsScorecard, credentialSubject/product/traceabilityInformation, credentialSubject/product/characteristics" are defined in the credential but missing from the context.
        Incorrect value: credentialSubject/product/granularityLevel, credentialSubject/product/dueDiligenceDeclaration, credentialSubject/product/materialsProvenance, credentialSubject/product/circularityScorecard, credentialSubject/product/emissionsScorecard, credentialSubject/product/traceabilityInformation, credentialSubject/product/characteristics
        '''
        list_flatten = ['granularityLevel', 'dueDiligenceDeclaration', 'materialsProvenance', 'circularityScorecard', 'emissionsScorecard', 'traceabilityInformation']

        product = component_data.get('product', {})
        for key in list_flatten:
            if key in product:
                component_data[key] = product.pop(key)
        '''
        if traceabilityInformation in product and it is not a list, convert to list
        '''
        if "traceabilityInformation" in component_data:
            if not isinstance(component_data["traceabilityInformation"], list):
                component_data["traceabilityInformation"] = [component_data["traceabilityInformation"]]


        '''
        Resolve issues:
        Location: credentialSubject → product
        Issue: must have required property 'name'
        Missing field: name
        Location: credentialSubject → product → producedAtFacility
        Issue: must have required property 'id'
        Missing field: id
        Location: credentialSubject → emissionsScorecard
        Issue: must have required property 'carbonFootprint'
        Missing field: carbonFootprint
        '''
        # Ensure 'name' exists in product
        product.setdefault("name", "Example")

        # Ensure 'producedAtFacility' is a dict with default keys
        producedAtFacility = product.setdefault("producedAtFacility", {})
        producedAtFacility.setdefault("id", "http://localhost:3000/gs1/414/123456") # producedAtFacility needs to be an URI and has to have value
        producedAtFacility.setdefault("name", "Sample Facility")

        # Ensure 'emissionsScorecard' is a dict with default keys
        emissionsScorecard = component_data.setdefault("emissionsScorecard", {})
        emissionsScorecard.setdefault("declaredUnit", "kg")
        emissionsScorecard.setdefault("carbonFootprint", 0)
        emissionsScorecard.setdefault("operationalScope", "CradleToGate")
        emissionsScorecard.setdefault("primarySourcedRatio", 0)

        # Remove "type" in "emissionsScorecard"."reportingStandard"."issuingParty" 
        reportingStandard = emissionsScorecard.get("reportingStandard", {})
        issuingParty = reportingStandard.get("issuingParty", {})
        if "type" in issuingParty:
            del issuingParty["type"]
        # clean_data = self._clean_identifier_list(reportingStandard["issuingParty"])
        # reportingStandard["issuingParty"] = clean_data

        # Remove "type" in "dimensions"
        dimensions = product.get("dimensions", {})
        if "type" in dimensions:
            del dimensions["type"]

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
            context_configuration = param.get('dpp')
            if context_configuration:
                context_configuration['context'] = ["https://test.uncefact.org/vocabulary/untp/dpp/0.6.0/"]

            # 4. Render Template Updates
            hbs_template = "<!DOCTYPE html><html lang=\"en\"> <head> <meta charset=\"UTF-8\" /> <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" /> <link href=\"https://fonts.googleapis.com/css2?family=Lato:ital,wght@0,100;0,300;0,400;0,700;0,900;1,100;1,300;1,400;1,700;1,900&display=swap\" rel=\"stylesheet\" /> <title>Digital Product Passport</title> <style> :root { /* Brand Colors */ --color-primary: rgba(31, 90, 149, 1); /* Color for passport box item text, emission scorecard unit, conformity details, and history value chain process text; Default: rgba(31, 90, 149, 1) */ /* Neutrals */ --color-white: rgba(255, 255, 255, 1); /* Background color for main container, conformity cards, and issuing details section; Default: rgba(255, 255, 255, 1) */ --color-black: rgba(0, 0, 0, 1); /* Text color for section descriptions, information text, composition title, composition percent, composition tag item, history item span, and traceability card text; Default: rgba(0, 0, 0, 1) */ --color-gray-700: rgba(35, 46, 61, 1); /* Text color for links, section titles, table item values, declared value text, and header batch item links; Default: rgba(35, 46, 61, 1) */ --color-gray-600: rgba(85, 96, 110, 1); /* Text color for table item spans, conformity labels, score name, passport annotation, conformity info, declared value span, country code, footer text, and header image background; Default: rgba(85, 96, 110, 1) */ --color-gray-400: rgba(212, 214, 216, 1); /* Border color for table items, conformity cards, composition box items, history items, and passport box; Default: rgba(212, 214, 216, 1) */ --color-gray-100: rgba(247, 250, 253, 1); /* Background color for footer, verified ratio, composition tag item, header batch, and one passport box item; Default: rgba(247, 250, 253, 1) */ /* Semantic (Functional) Colors */ --color-link-underline-dark: rgba(79, 149, 221, 1); /* Underline color for blue-bottom-line-thick links; Default: rgba(79, 149, 221, 1) */ --color-accent-success: rgba(184, 236, 182, 1); /* Background color for green conformance badge; Default: rgba(184, 236, 182, 1) */ --color-accent-error: rgba(255, 188, 183, 1); /* Background color for red conformance badge; Default: rgba(255, 188, 183, 1) */ --color-icon: rgba(31, 90, 149, 1); /* Fill and stroke color for all SVG icons; Default: rgba(31, 90, 149, 1) */ /* Font Variables */ --font-family: \"Lato\", sans-serif; /* Font family for all text; Default: Lato, sans-serif */ /* Font Weight Variables */ --font-weight-light: 300; /* Font weight for information text; Default: 300 */ --font-weight-regular: 400; /* Font weight for section descriptions, conformity labels, table item spans, declared value text, passport annotation, conformity info, score name, composition tag item, country code, footer text, history item span, traceability card text, and header image top-left text; Default: 400 */ --font-weight-medium: 500; /* Font weight for links, table item paragraphs, composition percent, and header image top-left text; Default: 500 */ --font-weight-bold: 600; /* Font weight for section titles, composition title, and conformance badge text; Default: 600 */ --font-weight-black: 900; /* Font weight for header image bottom left h1, passport box item h3, and emission score unit; Default: 900 */ /* Other Variables */ --image-src: url(\"{{credentialSubject.product.productImage.linkURL}}\"); /* Background image for header image; Default: url(\"{{credentialSubject.product.productImage.linkURL}}\") */ } * { margin: 0; padding: 0; box-sizing: border-box; } body { font-family: var(--font-family); color: var(--color-gray-600); font-weight: var(--font-weight-regular); } .container { min-width: 150px; width: 100%; margin: 0 auto; display: flex; flex-direction: column; gap: 32px; word-break: break-word; background-color: var(--color-white); } section, header, footer { padding: 0 16px; } /* Neutralise default margins on header elements within sections */ section header { margin: 0; } .header-image { background-color: var(--color-gray-600); background-image: var(--image-src, none), linear-gradient( 248.36deg, rgba(0, 0, 0, 0.18) 7.6%, rgba(0, 0, 0, 0.6) 70.52% ); background-size: cover; background-position: center; background-repeat: no-repeat; height: 232px; position: relative; } .header-image-top-left { position: absolute; top: 25px; left: 15px; font-weight: var(--font-weight-medium); font-size: 16px; line-height: 22px; color: var(--color-white); } .header-image-bottom-left { position: absolute; bottom: 18px; left: 15px; color: var(--color-white); } .header-image-bottom-left h1 { font-size: 30px; font-weight: var(--font-weight-black); line-height: 32.5px; } .header-batch { padding: 12px 16px; background-color: var(--color-gray-100); display: flex; flex-wrap: wrap; justify-content: space-between; gap: 12px; } .header-batch-item { display: flex; align-items: center; gap: 6px; flex-grow: 1; min-width: 0; } .header-batch-item a { color: var(--color-gray-700); font-size: 14px; font-weight: var(--font-weight-medium); } .header-batch-item svg { fill: var(--color-icon); stroke: var(--color-icon); } /* General Section Styles */ .section-title { font-size: 18px; font-weight: var(--font-weight-bold); line-height: 19.62px; color: var(--color-gray-700); } .section-description { margin-top: 12px; font-size: 16px; line-height: 18.88px; color: var(--color-black); font-weight: var(--font-weight-regular); } /* Table Styles */ .table { display: flex; flex-direction: column; gap: 10px; } .table-item { display: grid; grid-template-columns: 1fr 2fr; column-gap: 16px; align-items: center; padding-bottom: 10px; border-bottom: 1px solid var(--color-gray-400); } .table-item span { font-size: 16px; font-weight: var(--font-weight-regular); color: var(--color-gray-600); } .table-item p, .table-item a { font-size: 16px; font-weight: var(--font-weight-medium); color: var(--color-gray-700); } .item-value { display: flex; flex-direction: column; font-size: 16px; font-weight: var(--font-weight-medium); color: var(--color-gray-600); } .item-value span { color: var(--color-gray-700); } .information-text { font-size: 19px; padding-bottom: 8px; font-weight: var(--font-weight-light); color: var(--color-black); line-height: 22.42px; } .information-show-more { display: flex; flex-direction: column; gap: 10px; font-size: 14px; font-weight: var(--font-weight-medium); } /* Production Section */ .production { display: flex; flex-direction: column; gap: 12px; } /* Passport Section */ .passport { display: flex; flex-direction: column; gap: 24px; } .passport-box { display: grid; grid-template-columns: 1fr 1fr; border: 1px solid var(--color-gray-400); border-radius: 5px; } .passport-box-item { display: flex; flex-direction: column; justify-content: center; align-items: center; padding: 12px 16px; border: 1px solid var(--color-gray-400); min-height: 94px; color: var(--color-primary); } .passport-box-item h3 { font-size: 40px; font-weight: var(--font-weight-black); line-height: 43.33px; letter-spacing: 2px; } .passport-box-item p { margin-top: 8px; font-size: 15px; font-weight: var(--font-weight-bold); } .passport-box-item:nth-child(4) { background-color: var(--color-gray-100); } .passport-annotation { font-size: 14px; font-weight: var(--font-weight-regular); line-height: 15.26px; color: var(--color-gray-600); } .traceability-cards { display: flex; flex-direction: column; gap: 12px; } .traceability-card { display: grid; grid-template-columns: 3fr 1fr; align-items: center; text-decoration: none; } .traceability-card-text { display: flex; align-items: center; gap: 8px; font-size: 16px; font-weight: var(--font-weight-regular); color: var(--color-black); } .traceability-card-text svg { fill: var(--color-icon); stroke: var(--color-icon); } .traceability-card-view-details { display: flex; justify-content: flex-end; gap: 8px; } /* Emission Scorecard */ .emission-score-card { display: flex; flex-direction: column; gap: 12px; } .score { display: flex; flex-direction: column; gap: 6px; } .score-unit { font-size: 40px; font-weight: var(--font-weight-black); line-height: 43.33px; color: var(--color-primary); letter-spacing: 2px; } .score-name { font-size: 16px; font-weight: var(--font-weight-regular); color: var(--color-gray-600); } /* Declarations */ .declarations { display: flex; flex-direction: column; gap: 12px; } .cards-conformities { display: flex; flex-direction: column; gap: 8px; } .cards-conformity { display: flex; flex-direction: column; gap: 8px; padding: 16px; background-color: var(--color-white); border: 1px solid var(--color-gray-400); border-radius: 4px; } .cards-conformity header { margin: 0; } .conformance-header { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 5px; } .conformance-status { display: flex; align-items: center; gap: 4px; } .conformance-label { font-size: 14px; font-weight: var(--font-weight-regular); color: var(--color-gray-600); } .tags-VC-badge-red, .tags-VC-badge-green { padding: 4px 8px; border-radius: 8px; font-size: 14px; font-weight: var(--font-weight-bold); } .tags-VC-badge-red { background-color: var(--color-accent-error); color: var(--color-gray-600); } .tags-VC-badge-green { background-color: var(--color-accent-success); color: var(--color-gray-600); } .conformity-details { font-size: 18px; font-weight: var(--font-weight-regular); color: var(--color-primary); } .conformity-info { display: flex; flex-direction: column; gap: 8px; } .conformity-info p { font-size: 14px; font-weight: var(--font-weight-regular); color: var(--color-gray-600); } .declared-values { display: flex; flex-direction: column; gap: 4px; } .declared-value p { font-size: 16px; font-weight: var(--font-weight-regular); color: var(--color-gray-700); } .declared-value span { font-size: 14px; color: var(--color-gray-600); } /* Composition */ .composition-box { display: flex; flex-direction: column; gap: 8px; margin-top: 12px; } .composition-box-item { display: grid; grid-template-columns: 1fr auto; border: 1px solid var(--color-gray-400); border-radius: 4px; padding: 16px; } .composition-first-column { display: grid; grid-template-columns: 40px 1fr; gap: 12px; } .composition-percent { font-size: 16px; font-weight: var(--font-weight-medium); color: var(--color-black); } .composition-title { font-size: 16px; font-weight: var(--font-weight-bold); color: var(--color-black); } .composition-tag { display: flex; gap: 4px; } .composition-tag-item { font-size: 14px; font-weight: var(--font-weight-regular); color: var(--color-black); background-color: var(--color-gray-100); padding: 2px 4px; } .country-code { font-size: 14px; font-weight: var(--font-weight-regular); color: var(--color-gray-600); } /* History */ .history { display: flex; flex-direction: column; gap: 12px; } .history-value-chain { display: flex; flex-direction: column; gap: 4px; } .history-value-chain p { font-size: 18px; font-weight: var(--font-weight-regular); color: var(--color-primary); } .verified-ratio { background-color: var(--color-gray-100); padding: 2px 4px; width: fit-content; } .history-item { display: grid; grid-template-columns: 1fr auto; padding: 10px 0; border-bottom: 1px solid var(--color-gray-400); } .history-item span { font-size: 16px; font-weight: var(--font-weight-regular); color: var(--color-black); } .history-item a { font-size: 16px; font-weight: var(--font-weight-medium); color: var(--color-gray-700); } /* Issued By */ .issued-by { display: flex; flex-direction: column; gap: 12px; } /* Footer */ footer { padding: 16px 16px 32px; background-color: var(--color-gray-100); } footer p { font-size: 14px; font-weight: var(--font-weight-regular); color: var(--color-gray-600); } /* Links */ .blue-bottom-line-thick { text-decoration: underline; text-decoration-thickness: 2px; text-decoration-color: var(--color-link-underline-dark); text-underline-offset: 3px; color: var(--color-gray-700); } .blue-bottom-line-thick.disabled { pointer-events: none; cursor: not-allowed; text-decoration: none; } .blue-bottom-line-thick.disabled:focus { outline: none; } .gray-bottom-line { border-bottom: 1px solid var(--color-gray-600); text-decoration: none; color: var(--color-gray-600); } /* Desktop Adjustments */ @media (min-width: 1200px) { .container { max-width: 1200px; } } </style> </head> <body> <div class=\"container\"> <header class=\"header\"> <div class=\"header-image\"> <p class=\"header-image-top-left\">PRODUCT PASSPORT</p> <div class=\"header-image-bottom-left\"> <h1>{{credentialSubject.product.name}}</h1> </div> </div> <div class=\"header-batch\"> {{#if credentialSubject.product.registeredId}} <div class=\"header-batch-item\"> <svg width=\"14\" height=\"14\" viewBox=\"0 0 14 14\" fill=\"none\" xmlns=\"http://www.w3.org/2000/svg\" > <path d=\"M2.45 3.5C2.17152 3.5 1.90445 3.38938 1.70754 3.19246C1.51062 2.99555 1.4 2.72848 1.4 2.45C1.4 2.17152 1.51062 1.90445 1.70754 1.70754C1.90445 1.51062 2.17152 1.4 2.45 1.4C2.72848 1.4 2.99555 1.51062 3.19246 1.70754C3.38938 1.90445 3.5 2.17152 3.5 2.45C3.5 2.72848 3.38938 2.99555 3.19246 3.19246C2.99555 3.38938 2.72848 3.5 2.45 3.5ZM13.587 6.706L7.287 0.406C7.035 0.154 6.685 0 6.3 0H1.4C0.623 0 0 0.623 0 1.4V6.3C0 6.685 0.154 7.035 0.413 7.287L6.706 13.587C6.965 13.839 7.315 14 7.7 14C8.085 14 8.435 13.839 8.687 13.587L13.587 8.687C13.846 8.435 14 8.085 14 7.7C14 7.308 13.839 6.958 13.587 6.706Z\" fill=\"var(--color-icon)\" stroke=\"var(--color-icon)\" /> </svg> <a href=\"{{credentialSubject.product.id}}\" class=\"blue-bottom-line-thick\" target=\"_blank\" >ID: {{credentialSubject.product.registeredId}}</a > </div> {{/if}} {{#if credentialSubject.product.batchNumber}} <div class=\"header-batch-item\"> <svg width=\"14\" height=\"14\" viewBox=\"0 0 14 14\" fill=\"none\" xmlns=\"http://www.w3.org/2000/svg\" > <path d=\"M2.45 3.5C2.17152 3.5 1.90445 3.38938 1.70754 3.19246C1.51062 2.99555 1.4 2.72848 1.4 2.45C1.4 2.17152 1.51062 1.90445 1.70754 1.70754C1.90445 1.51062 2.17152 1.4 2.45 1.4C2.72848 1.4 2.99555 1.51062 3.19246 1.70754C3.38938 1.90445 3.5 2.17152 3.5 2.45C3.5 2.72848 3.38938 2.99555 3.19246 3.19246C2.99555 3.38938 2.72848 3.5 2.45 3.5ZM13.587 6.706L7.287 0.406C7.035 0.154 6.685 0 6.3 0H1.4C0.623 0 0 0.623 0 1.4V6.3C0 6.685 0.154 7.035 0.413 7.287L6.706 13.587C6.965 13.839 7.315 14 7.7 14C8.085 14 8.435 13.839 8.687 13.587L13.587 8.687C13.846 8.435 14 8.085 14 7.7C14 7.308 13.839 6.958 13.587 6.706Z\" fill=\"var(--color-icon)\" stroke=\"var(--color-icon)\" /> </svg> <a target=\"_blank\">Batch: {{credentialSubject.product.batchNumber}}</a> </div> {{/if}} {{#if credentialSubject.product.serialNumber}} <div class=\"header-batch-item\"> <svg width=\"14\" height=\"14\" viewBox=\"0 0 14 14\" fill=\"none\" xmlns=\"http://www.w3.org/2000/svg\" > <path d=\"M2.45 3.5C2.17152 3.5 1.90445 3.38938 1.70754 3.19246C1.51062 2.99555 1.4 2.72848 1.4 2.45C1.4 2.17152 1.51062 1.90445 1.70754 1.70754C1.90445 1.51062 2.17152 1.4 2.45 1.4C2.72848 1.4 2.99555 1.51062 3.19246 1.70754C3.38938 1.90445 3.5 2.17152 3.5 2.45C3.5 2.72848 3.38938 2.99555 3.19246 3.19246C2.99555 3.38938 2.72848 3.5 2.45 3.5ZM13.587 6.706L7.287 0.406C7.035 0.154 6.685 0 6.3 0H1.4C0.623 0 0 0.623 0 1.4V6.3C0 6.685 0.154 7.035 0.413 7.287L6.706 13.587C6.965 13.839 7.315 14 7.7 14C8.085 14 8.435 13.839 8.687 13.587L13.587 8.687C13.846 8.435 14 8.085 14 7.7C14 7.308 13.839 6.958 13.587 6.706Z\" fill=\"var(--color-icon)\" stroke=\"var(--color-icon)\" /> </svg> <a target=\"_blank\">Serial: {{credentialSubject.product.serialNumber}}</a> </div> {{/if}} </div> </header> <section> {{#if credentialSubject.product.description}} <div class=\"information-text\"> {{credentialSubject.product.description}} </div> {{/if}} {{#if credentialSubject.product.furtherInformation}} <div class=\"information-show-more\"> {{#each credentialSubject.product.furtherInformation}} {{#if linkURL}} {{#if linkName}} <a href=\"{{linkURL}}\" class=\"blue-bottom-line-thick\" target=\"_blank\"> {{linkName}} </a> {{/if}} {{/if}} {{/each}} </div> {{/if}} </section> {{#if credentialSubject.product.characteristics}} <section class=\"production\"> <div class=\"section-title\">Characteristics</div> <div class=\"table\"> {{#each credentialSubject.product.characteristics}} <div class=\"table-item\"> <span>{{@key}}</span> <p class=\"item-value\">{{this}}</p> </div> {{/each}} </div> </section> {{/if}} <section class=\"production\"> <div class=\"section-title\">Production</div> <div class=\"table\"> {{#if credentialSubject.product.productCategory}} <div class=\"table-item\"> <span>Product category</span> <p class=\"item-value\"> {{#each credentialSubject.product.productCategory}}{{name}}{{#unless @last}}, {{/unless}}{{/each}} </p> </div> {{/if}} {{#if credentialSubject.product.producedByParty}} <div class=\"table-item\"> <span>Produced by</span> <a href=\"{{credentialSubject.product.producedByParty.id}}\" class=\"blue-bottom-line-thick\" target=\"_blank\" >{{credentialSubject.product.producedByParty.name}}</a > </div> {{/if}} {{#if credentialSubject.product.producedAtFacility}} {{#with credentialSubject.product.producedAtFacility}} <div class=\"table-item\"> <span>Produced at</span> <p class=\"item-value\"> <a href=\"{{id}}\" class=\"blue-bottom-line-thick\" target=\"_blank\">{{name}}</a> </p> </div> <!-- TODO: Add locationInformation and address back to the DPP data model --> {{#if address}} <div class=\"table-item\"> <span>Location</span> <p class=\"item-value\"> <a href=\"{{locationInformation.plusCode}}\" class=\"blue-bottom-line-thick {{#unless locationInformation.plusCode}}disabled{{/unless}}\" {{#unless locationInformation.plusCode}}aria-disabled=\"true\" tabindex=\"-1\"{{/unless}} aria-label=\"View location on map\" target=\"_blank\" > {{#if address.streetAddress}}{{address.streetAddress}}{{/if}} {{#if address.addressLocality}}{{address.addressLocality}}{{/if}} {{#if address.addressRegion}}{{address.addressRegion}}{{/if}} {{#if address.postalCode}}{{address.postalCode}}{{/if}} </a> </p> </div> {{/if}} {{/with}} {{/if}} {{#if credentialSubject.product.productionDate}} <div class=\"table-item\"> <span>Date produced</span> <p class=\"item-value\">{{credentialSubject.product.productionDate}}</p> </div> {{/if}} {{#if credentialSubject.product.countryOfProduction}} <div class=\"table-item\"> <span>Country</span> <p class=\"item-value\">{{credentialSubject.product.countryOfProduction}}</p> </div> {{/if}} {{#if credentialSubject.product.dimensions}} <div class=\"table-item\"> <span>Dimensions</span> <p class=\"item-value\"> {{#if credentialSubject.product.dimensions.weight}} <span>Weight: {{credentialSubject.product.dimensions.weight.value}}{{credentialSubject.product.dimensions.weight.unit}}</span> {{/if}} {{#if credentialSubject.product.dimensions.length}} <span>Length: {{credentialSubject.product.dimensions.length.value}}{{credentialSubject.product.dimensions.length.unit}}</span> {{/if}} {{#if credentialSubject.product.dimensions.width}} <span>Width: {{credentialSubject.product.dimensions.width.value}}{{credentialSubject.product.dimensions.width.unit}}</span> {{/if}} {{#if credentialSubject.product.dimensions.height}} <span>Height: {{credentialSubject.product.dimensions.height.value}}{{credentialSubject.product.dimensions.height.unit}}</span> {{/if}} {{#if credentialSubject.product.dimensions.volume}} <span>Volume: {{credentialSubject.product.dimensions.volume.value}}{{credentialSubject.product.dimensions.volume.unit}}</span> {{/if}} </p> </div> {{/if}} </div> </section> {{#if credentialSubject.circularityScorecard}} <section class=\"passport\"> <div> <h3 class=\"section-title\">Circularity Scorecard</h3> <p class=\"section-description\"> The circularity Scorecard provides a simple high level summary of circularity performance of the product. </p> </div> <div class=\"passport-box\"> {{#if credentialSubject.circularityScorecard.recyclableContent}} <div class=\"passport-box-item\"> <h3>{{credentialSubject.circularityScorecard.recyclableContent}}%</h3> <p>Recyclable content</p> </div> {{/if}} {{#if credentialSubject.circularityScorecard.recycledContent}} <div class=\"passport-box-item\"> <h3>{{credentialSubject.circularityScorecard.recycledContent}}%</h3> <p>Recycled content</p> </div> {{/if}} {{#if credentialSubject.circularityScorecard.utilityFactor}} <div class=\"passport-box-item\"> <h3>{{credentialSubject.circularityScorecard.utilityFactor}}</h3> <p>Utility factor</p> </div> {{/if}} {{#if credentialSubject.circularityScorecard.materialCircularityIndicator}} <div class=\"passport-box-item\"> <h3>{{credentialSubject.circularityScorecard.materialCircularityIndicator}}</h3> <p>Material circularity*</p> </div> {{/if}} </div> {{#if credentialSubject.circularityScorecard.materialCircularityIndicator}} <div class=\"passport-annotation\"> <p>*The Material Circularity Indicator provides an overall circularity score which is a function of all three of the earlier measures.</p> </div> {{/if}} <div class=\"traceability-cards\"> {{#if credentialSubject.circularityScorecard.recyclingInformation.linkURL}} <a href=\"{{credentialSubject.circularityScorecard.recyclingInformation.linkURL}}\" class=\"traceability-card\" target=\"_blank\"> <div class=\"traceability-card-text\"> <svg width=\"24\" height=\"24\" viewBox=\"0 0 24 24\" fill=\"none\" xmlns=\"http://www.w3.org/2000/svg\" > <path d=\"M21.82 15.42L19.32 19.75C18.83 20.61 17.92 21.06 17 21H15V23L12.5 18.5L15 14V16H17.82L15.6 12.15L19.93 9.65L21.73 12.77C22.25 13.54 22.32 14.57 21.82 15.42ZM9.21003 3.06H14.21C15.19 3.06 16.04 3.63 16.45 4.45L17.45 6.19L19.18 5.19L16.54 9.6L11.39 9.69L13.12 8.69L11.71 6.24L9.50003 10.09L5.16003 7.59L6.96003 4.47C7.37003 3.64 8.22003 3.06 9.21003 3.06ZM5.05003 19.76L2.55003 15.43C2.06003 14.58 2.13003 13.56 2.64003 12.79L3.64003 11.06L1.91003 10.06L7.05003 10.14L9.70003 14.56L7.97003 13.56L6.56003 16H11V21H7.40003C6.93154 21.0339 6.46293 20.9357 6.0475 20.7165C5.63206 20.4973 5.28648 20.1659 5.05003 19.76Z\" fill=\"var(--color-icon)\" stroke=\"var(--color-icon)\" /> </svg> <p>Recycling instructions</p> </div> <div class=\"traceability-card-view-details\"> <svg width=\"9\" height=\"16\" viewBox=\"0 0 9 16\" fill=\"none\" xmlns=\"http://www.w3.org/2000/svg\" > <path d=\"M1 1L8 8L1 15\" stroke=\"var(--color-icon)\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\" /> </svg> </div> </a> {{/if}} {{#if credentialSubject.circularityScorecard.repairInformation.linkURL}} <a href=\"{{credentialSubject.circularityScorecard.repairInformation.linkURL}}\" class=\"traceability-card\" target=\"_blank\"> <div class=\"traceability-card-text\"> <svg width=\"24\" height=\"24\" viewBox=\"0 0 24 24\" fill=\"none\" xmlns=\"http://www.w3.org/2000/svg\" > <path d=\"M18.85 21.975C18.7167 21.975 18.5917 21.9543 18.475 21.913C18.3583 21.8717 18.25 21.8007 18.15 21.7L13.05 16.6C12.95 16.5 12.879 16.3917 12.837 16.275C12.795 16.1583 12.7743 16.0333 12.775 15.9C12.7757 15.7667 12.7967 15.6417 12.838 15.525C12.8793 15.4083 12.95 15.3 13.05 15.2L15.175 13.075C15.275 12.975 15.3833 12.9043 15.5 12.863C15.6167 12.8217 15.7417 12.8007 15.875 12.8C16.0083 12.7993 16.1333 12.8203 16.25 12.863C16.3667 12.9057 16.475 12.9763 16.575 13.075L21.675 18.175C21.775 18.275 21.846 18.3833 21.888 18.5C21.93 18.6167 21.9507 18.7417 21.95 18.875C21.9493 19.0083 21.9287 19.1333 21.888 19.25C21.8473 19.3667 21.7763 19.475 21.675 19.575L19.55 21.7C19.45 21.8 19.3417 21.871 19.225 21.913C19.1083 21.955 18.9833 21.9757 18.85 21.975ZM18.85 19.6L19.575 18.875L15.9 15.2L15.175 15.925L18.85 19.6ZM5.125 22C4.99167 22 4.86267 21.975 4.738 21.925C4.61333 21.875 4.50067 21.8 4.4 21.7L2.3 19.6C2.2 19.5 2.125 19.3873 2.075 19.262C2.025 19.1367 2 19.008 2 18.876C2 18.744 2.025 18.619 2.075 18.501C2.125 18.383 2.2 18.2747 2.3 18.176L7.6 12.876H9.725L10.575 12.026L6.45 7.9H5.025L2 4.875L4.825 2.05L7.85 5.075V6.5L11.975 10.625L14.875 7.725L13.8 6.65L15.2 5.25H12.375L11.675 4.55L15.225 1L15.925 1.7V4.525L17.325 3.125L20.875 6.675C21.1583 6.95833 21.375 7.27933 21.525 7.638C21.675 7.99667 21.75 8.37567 21.75 8.775C21.75 9.17433 21.675 9.55767 21.525 9.925C21.375 10.2923 21.1583 10.6173 20.875 10.9L18.75 8.775L17.35 10.175L16.3 9.125L11.125 14.3V16.4L5.825 21.7C5.725 21.8 5.61667 21.875 5.5 21.925C5.38333 21.975 5.25833 22 5.125 22ZM5.125 19.6L9.375 15.35V14.625H8.65L4.4 18.875L5.125 19.6ZM5.125 19.6L4.4 18.875L4.775 19.225L5.125 19.6Z\" fill=\"var(--color-icon)\" stroke=\"var(--color-icon)\" /> </svg> <p>Repair instructions</p> </div> <div class=\"traceability-card-view-details\"> <svg width=\"9\" height=\"16\" viewBox=\"0 0 9 16\" fill=\"none\" xmlns=\"http://www.w3.org/2000/svg\" > <path d=\"M1 1L8 8L1 15\" stroke=\"var(--color-icon)\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\" /> </svg> </div> </a> {{/if}} </div> </section> {{/if}} {{#if credentialSubject.emissionsScorecard}} <section class=\"emission-score-card\"> <div> <h3 class=\"section-title\">Emissions Scorecard</h3> <p class=\"section-description\"> The Emissions Scorecard gives a clear snapshot of the product's greenhouse gas (GHG) emissions performance, providing a single indicator to assess its overall environmental impact. </p> </div> <div class=\"score\"> <p class=\"score-unit\"> {{credentialSubject.emissionsScorecard.carbonFootprint}}{{credentialSubject.emissionsScorecard.declaredUnit}} </p> <p class=\"score-name\">Co2Eq</p> </div> <div class=\"table\"> <div class=\"table-item\"> <span>Scope includes</span> <p class=\"item-value\">{{credentialSubject.emissionsScorecard.operationalScope}}</p> </div> <div class=\"table-item\"> <span>Primary sourced ratio*</span> <p class=\"item-value\">{{credentialSubject.emissionsScorecard.primarySourcedRatio}}% primary sources</p> </div> {{#if credentialSubject.emissionsScorecard.reportingStandard}} {{#if credentialSubject.emissionsScorecard.reportingStandard.name}} <div class=\"table-item\"> <span>Reporting standard</span> {{#if credentialSubject.emissionsScorecard.reportingStandard.id}} <a href=\"{{credentialSubject.emissionsScorecard.reportingStandard.id}}\" class=\"blue-bottom-line-thick\" target=\"_blank\"> {{credentialSubject.emissionsScorecard.reportingStandard.name}} </a> {{else}} <p class=\"item-value\"> {{credentialSubject.emissionsScorecard.reportingStandard.name}} </p> {{/if}} </div> {{/if}} {{#if credentialSubject.emissionsScorecard.reportingStandard.issueDate}} <div class=\"table-item\"> <span>Issue date</span> <p class=\"item-value\">{{credentialSubject.emissionsScorecard.reportingStandard.issueDate}}</p> </div> {{/if}} {{/if}} </div> <div class=\"passport-annotation\"> <p>*The Primary Sourced Ratio shows the percentage of scope 3 emissions data that is directly collected from actual sources, rather than being based on estimates.</p> </div> </section> {{/if}} {{#if credentialSubject.conformityClaim}} <section class=\"declarations\"> <div> <h3 class=\"section-title\">Declarations</h3> </div> <div class=\"cards-conformities\"> {{#each credentialSubject.conformityClaim}} <article class=\"cards-conformity\"> <div class=\"conformance-header\"> <div class=\"conformance-status\"> <span class=\"conformance-label\">Conformance:</span> <div class=\"{{#if conformance}}tags-VC-badge-green{{else}}tags-VC-badge-red{{/if}}\"> {{#if conformance}}Yes{{else}}No{{/if}} </div> </div> {{#if assessmentDate}} <span class=\"conformance-label\">Assessed: {{assessmentDate}}</span> {{/if}} </div> {{#if conformityEvidence.linkName}} <div class=\"conformity-details\">{{conformityEvidence.linkName}}</div> {{/if}} <div class=\"conformity-info\"> {{#if referenceRegulation}} <p> {{#if referenceRegulation.name}} {{referenceRegulation.name}} {{#if referenceRegulation.jurisdictionCountry}} administered in {{referenceRegulation.jurisdictionCountry}} {{/if}} {{#if referenceRegulation.administeredBy}} administered by <a href=\"{{referenceRegulation.administeredBy.id}}\" class=\"gray-bottom-line\" target=\"_blank\" > {{referenceRegulation.administeredBy.name}} </a> {{/if}} {{else if referenceRegulation.jurisdictionCountry}} Administered in {{referenceRegulation.jurisdictionCountry}} {{#if referenceRegulation.administeredBy}} by <a href=\"{{referenceRegulation.administeredBy.id}}\" class=\"gray-bottom-line\" target=\"_blank\" > {{referenceRegulation.administeredBy.name}} </a> {{/if}} {{else if referenceRegulation.administeredBy}} Administered by <a href=\"{{referenceRegulation.administeredBy.id}}\" class=\"gray-bottom-line\" target=\"_blank\" > {{referenceRegulation.administeredBy.name}} </a> {{/if}} </p> {{/if}} {{#if referenceStandard}} {{#if referenceStandard.name}} <p> {{referenceStandard.name}} {{#if referenceStandard.issuingParty}} issued by <a href=\"{{referenceStandard.issuingParty.id}}\" class=\"gray-bottom-line\" target=\"_blank\" > {{referenceStandard.issuingParty.name}} </a> {{/if}} </p> {{/if}} {{/if}} </div> {{#if declaredValue}} <div class=\"declared-values\"> {{#each declaredValue}} <div class=\"declared-value\"> <p>{{metricName}} is {{metricValue.value}}{{metricValue.unit}}</p> {{#if score}} <span> Score: {{score}}{{#if accuracy}} | Accuracy: {{accuracy}}{{/if}} </span> {{else if accuracy}} <span> Accuracy: {{accuracy}} </span> {{/if}} </div> {{/each}} </div> {{/if}} {{#if conformityEvidence.linkURL}} <a href=\"{{conformityEvidence.linkURL}}\" class=\"traceability-card\" target=\"_blank\"> <div class=\"traceability-card-text\"> <svg width=\"24\" height=\"24\" viewBox=\"0 0 24 24\" fill=\"none\" xmlns=\"http://www.w3.org/2000/svg\" > <path d=\"M5 21C4.45 21 3.97933 20.8043 3.588 20.413C3.19667 20.0217 3.00067 19.5507 3 19V5C3 4.45 3.196 3.97933 3.588 3.588C3.98 3.19667 4.45067 3.00067 5 3H19C19.55 3 20.021 3.196 20.413 3.588C20.805 3.98 21.0007 4.45067 21 5V19C21 19.55 20.8043 20.021 20.413 20.413C20.0217 20.805 19.5507 21.0007 19 21H5ZM5 5V19H19V5H17V12L14.5 10.5L12 12V5H5Z\" fill=\"var(--color-icon)\" ></path> </svg> <p>Evidence</p> </div> <div class=\"traceability-card-view-details\"> <svg width=\"9\" height=\"16\" viewBox=\"0 0 9 16\" fill=\"none\" xmlns=\"http://www.w3.org/2000/svg\" > <path d=\"M1 1L8 8L1 15\" stroke=\"var(--color-icon)\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\" /> </svg> </div> </a> {{/if}} </article> {{/each}} </div> </section> {{/if}} {{#if credentialSubject.materialsProvenance}} {{#if credentialSubject.materialsProvenance.0.massFraction}} {{#if credentialSubject.materialsProvenance.0.name}} <section class=\"composition\"> <div> <h3 class=\"section-title\">Product Composition</h3> <p class=\"section-description\"> A complete list of materials that make up the composition of this product. </p> </div> <div class=\"composition-box\"> {{#each credentialSubject.materialsProvenance}} <article class=\"composition-box-item\"> <div class=\"composition-first-column\"> <p class=\"composition-percent\">{{massFraction}}%</p> <div> <p class=\"composition-title\"> {{#if mass}}{{mass.value}}{{mass.unit}} {{/if}}{{name}} </p> <div class=\"composition-tag\"> {{#if recycledMassFraction}} <p class=\"composition-tag-item\">Recycled {{recycledMassFraction}}%</p> {{/if}} <!-- TODO: If hazardous is not present it will display the tag \"Hazard No\" which may not be true. --> <p class=\"composition-tag-item\">Hazard {{#if hazardous}}Yes{{else}}No{{/if}}</p> </div> {{#if materialSafetyInformation.linkURL}} <a href=\"{{materialSafetyInformation.linkURL}}\" class=\"blue-bottom-line-thick\" target=\"_blank\">{{materialSafetyInformation.linkName}}</a> {{/if}} </div> </div> {{#if originCountry}} <div class=\"country-code\">{{originCountry}}</div> {{/if}} </article> {{/each}} </div> </section> {{/if}} {{/if}} {{/if}} {{#if credentialSubject.traceabilityInformation}} <section class=\"history\"> <div> <h3 class=\"section-title\">History</h3> </div> {{#if credentialSubject.dueDiligenceDeclaration.linkURL}} <a href=\"{{credentialSubject.dueDiligenceDeclaration.linkURL}}\" class=\"traceability-card\" target=\"_blank\"> <div class=\"traceability-card-text\"> <svg width=\"24\" height=\"24\" viewBox=\"0 0 24 24\" fill=\"none\" xmlns=\"http://www.w3.org/2000/svg\" > <path d=\"M5 21C4.45 21 3.97933 20.8043 3.588 20.413C3.19667 20.0217 3.00067 19.5507 3 19V5C3 4.45 3.196 3.97933 3.588 3.588C3.98 3.19667 4.45067 3.00067 5 3H19C19.55 3 20.021 3.196 20.413 3.588C20.805 3.98 21.0007 4.45067 21 5V19C21 19.55 20.8043 20.021 20.413 20.413C20.0217 20.805 19.5507 21.0007 19 21H5ZM5 5V19H19V5H17V12L14.5 10.5L12 12V5H5Z\" fill=\"var(--color-icon)\" ></path> </svg> <p>Supply chain due diligence report</p> </div> <div class=\"traceability-card-view-details\"> <svg width=\"9\" height=\"16\" viewBox=\"0 0 9 16\" fill=\"none\" xmlns=\"http://www.w3.org/2000/svg\" > <path d=\"M1 1L8 8L1 15\" stroke=\"var(--color-icon)\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\" /> </svg> </div> </a> {{/if}} {{#each credentialSubject.traceabilityInformation}} <div class=\"history-value-chain\"> {{#if valueChainProcess}} <p>{{valueChainProcess}}</p> {{#if verifiedRatio}} <div class=\"verified-ratio\"> <p>Verified ratio {{verifiedRatio}}</p> </div> {{/if}} {{/if}} </div> {{#if traceabilityEvent}} <div> {{#each traceabilityEvent}} {{#if linkName}} {{#if linkURL}} <div class=\"history-item\"> <span>{{linkName}}</span> <a href=\"{{linkURL}}\" class=\"blue-bottom-line-thick\" target=\"_blank\">View</a> </div> {{/if}} {{/if}} {{/each}} </div> {{/if}} {{/each}} </section> {{/if}} <section class=\"issued-by\"> <div> <h3 class=\"section-title\">Passport Issued By</h3> </div> <div class=\"table\"> <div class=\"table-item\"> <span>Organisation</span> <p class=\"item-value\">{{issuer.name}}</p> </div> <div class=\"table-item\"> <span>Registered ID</span> <a href=\"{{issuer.id}}\" class=\"blue-bottom-line-thick\" target=\"_blank\">{{issuer.id}}</a> </div> {{#if validFrom}} <div class=\"table-item\"> <span>Valid from</span> <p class=\"item-value\">{{validFrom}}</p> </div> {{/if}} {{#if validUntil}} <div class=\"table-item\"> <span>Valid to</span> <p class=\"item-value\">{{validUntil}}</p> </div> {{/if}} </div> </section> <footer> <p> This Digital Product Passport (DPP) is a digital record of the product's sustainability and environmental performance, ensuring transparency and accountability in line with UNTP standards. For more information visit <a href=\"https://uncefact.github.io/spec-untp/\" class=\"gray-bottom-line\" target=\"_blank\">uncefact.github.io/spec-untp/</a>. </p> </footer> </div> </body></html>"
            render_template = context_configuration.get('renderTemplate',[])
            for item in render_template: #iterates through renderTemplate
                item["template"] = hbs_template

                # Removes duplicated type fields in renderTemplate
                if "@type" in item and "type" in item: # if both are present, delete "@type"
                    del item["@type"]
                elif "@type" in item and "type" not in item: # if only "@type" is present, change the field name to "type"
                    item["type"] = item.pop("@type")
            

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