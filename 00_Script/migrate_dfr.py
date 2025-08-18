######################################
######## TESTING ####################
## Python script per migration guide
# https://uncefact.github.io/tests-untp/docs/next/migration-guides/v0.6.0/#digital-facility-record-dfr
#####################################
import json

def pop_and_replace_key(d, old_key, new_key):
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

def clean_identifier_list(identifier, remove_fields=None):
    """
    Removes remove_fields list keys from each item in a list or dict.
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


def flatten_credential_subject(data, field_flatten):
    """
    Flattens a field "field_flatten" field into the top level of 'data'.
    """
    # If 'credentialSubject' exists, merge its contents into 'data'
    if field_flatten in data:
        cs = data.pop(field_flatten)
        for k, v in cs.items():
            data[k] = v
    return data

## general migration function
def migrate_general_v_050_to_v_060(component):
    '''
    This function applies the general migration rules from 0.5.0 to 0.6.0.
    The rules are:
    1. Update all service URLs to use /api/1.0.0 instead of previous paths (e.g., /v1/documents).
    2. Change linkRegisterPath for IDR Service from /api/resolver to resolver (remove leading slash).
    3. Ensure all configuration references use the new API versioned endpoints for Storage, IDR, and Identity Provider services.
    '''

    # 1. Storage Service Configuration
    # Change services -> "storage": -> "url" to "http://localhost:3334/api/1.0.0/documents"
    services = component.get('services',{})
    for service in services:
        params = service.get('parameters',{})
        for param in params:
            if 'storage' in param:
                param['storage']["url"] = "http://localhost:3334/api/1.0.0/documents"
            #2. Identity Resolver (IDR) Service Configuration
            if 'dlr' in param:
                param['dlr']['dlrAPIUrl'] = "http://localhost:3000/api/1.0.0"
                param['dlr']['linkRegisterPath'] = "resolver"
    return component


# migrate DFR function

def migrate_dfr_v050_to_v060(dfr_component):
    '''
    This function migrates a Digital Facility Record (DFR) from version 0.5.0 to 0.6.0.
    '''
    data = dfr_component["components"][0]["props"]["data"]

    ######################################
    ####### Data model changes ##########
    #####################################
    #### Update @context 1. JSON-LD Context
    data["@context"] = [
        "https://www.w3.org/ns/credentials/v2",
        "https://test.uncefact.org/vocabulary/untp/dfr/0.6.0/"
    ]

    # Update credentialSubject structure and fills in the new format based on the existing data
    ### 2. changed the Credential Subject Structure 
    credential_subject = data.get("credentialSubject", {})
    facility = {key: value for key, value in credential_subject.items() if key != "conformityClaim"}
    # Create new credentialSubject with FacilityRecord type
    new_credential_subject = {
        "type": ["FacilityRecord"],
        "facility": facility,
        "conformityClaim": credential_subject.get("conformityClaim", [])
    }

    # Update the credentialSubject in the output
    data["credentialSubject"] = new_credential_subject

    ### 3. Issuer Identifier Structure:
    # Update otherIdentifier to issuerAlsoKnownAs
    issuer = data.get('issuer',{}) 

    if "otherIdentifier" in issuer:
        #rename otherIdentifier as issuerAlsoKnownAs
        x = pop_and_replace_key(issuer,"otherIdentifier", "facilityAlsoKnownAs")
        issuer["facilityAlsoKnownAs"] = x

    ### 4. Facility Structure
    ## otherIdentifier property replaced with new facilityAlsoKnownAs property
    ## operatedByParty structure simplified from Identifier.
    ## Remove "type": ["Identifier"],  "idScheme": {"type": ["IdentifierScheme"], "id": "https://abr.business.gov.au/ABN/", "name": "Australian Business Number (ABN)"

    credential_subject = data.get("credentialSubject", {}) #gets the new credentialsubject after updated on step 2
    facility_new = credential_subject.get('facility')
    if "otherIdentifier" in facility_new: ## otherIdentifier property replaced with new facilityAlsoKnownAs property
        clean_data = pop_and_replace_key(facility_new,"otherIdentifier", "facilityAlsoKnownAs")
        #Remove "type": ["Identifier"],  "idScheme": {"type": ["IdentifierScheme"], "id": "https://abr.business.gov.au/ABN/", "name": "Australian Business Number (ABN)"
        clean_data = clean_identifier_list(clean_data, ["type", "idScheme"])
        facility_new["facilityAlsoKnownAs"] = clean_data
    
    ## operatedByParty structure simplified from Identifier.
    operated_by_party = facility_new.get('operatedByParty', {})
    print(operated_by_party)
    #Remove "type": ["Identifier"],  "idScheme": {"type": ["IdentifierScheme"], "id": "https://abr.business.gov.au/ABN/", "name": "Australian Business Number (ABN)"
    clean_data2 = clean_identifier_list(operated_by_party, ["type", "idScheme"])
    print(clean_data2)
    facility_new["operatedByParty"] = clean_data2

    # NEW: UPDATE CONFOMIRTY CLAIM IN CREDENTIAL SUBJECT
    # ADD: "description": "Default description",
    #   "conformityTopic": "environment.emissions",
    #   "status": "proposed",
    #   "subCriterion": []
    conformity_claim = credential_subject.get('conformityClaim')
    for claim in conformity_claim: #iterate through each claim
        assessmentCriteria = claim.get('assessmentCriteria',[])
        for criterion in assessmentCriteria: #iterate through each criterion
            criterion["description"] = "Default description"
            criterion["conformityTopic"] = "environment.emissions"
            criterion["status"] = "proposed"
            criterion["subCriterion"] = []
        claim["conformityTopic"] = "environment.emissions"

    ###################################################
    ####### Reference Implementation Updates ##########
    ###################################################

    #### 1. Schema URL Updates: update value of Schema URL to version 0.6.0 for DFR
    schema = dfr_component["components"][0]["props"]["schema"]
    schema["url"] = "https://jargon.sh/user/unece/DigitalFacilityRecord/v/0.6.0/artefacts/jsonSchemas/FacilityRecord.json?class=FacilityRecord"
    #### NEW RULE: remove credentialsubject and merge everything inside to "data", remove fields inside data like "type", "@context", "issuer"
    component_data = dfr_component["components"][0]["props"]["data"]
    clean_data = clean_identifier_list(component_data, ['type', '@context', 'issuer'])
    flatten_data = flatten_credential_subject(component_data, 'credentialSubject')

    #### 2. Context Configuration in Services: change context within "digitalFacilityRecord" from 0.5.0 to 0.6.0
    dfr = next(iter(dfr_component.get('services', [])), {}).get('parameters', [{}])[0].get('digitalFacilityRecord')
    dfr['context'] = ["https://test.uncefact.org/vocabulary/untp/dfr/0.6.0/"]

    #### 3. Form Data Structure Updates: TBA. 

    #### 4. Render Template Updates: Update the render template to use the new 0.6.0 compliant template
    rendertemplate = dfr.get("renderTemplate","")

    hbs_template = "<!DOCTYPE html><html lang=\"en\"> <head> <meta charset=\"UTF-8\" /> <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" /> <link href=\"https://fonts.googleapis.com/css2?family=Lato:ital,wght@0,100;0,300;0,400;0,700;0,900;1,100;1,300;1,400;1,700;1,900&display=swap\" rel=\"stylesheet\" /> <title>Digital Facility Record</title> <style> :root { /* Brand Colors */ --color-primary: rgba(35, 46, 61, 1); /* Headers, titles; Default: rgba(35, 46, 61, 1) */ --color-secondary: rgba(31, 90, 149, 1); /* Evidence titles; Default: rgba(31, 90, 149, 1) */ /* Neutrals */ --color-white: rgba(255, 255, 255, 1); /* Text, backgrounds; Default: rgba(255, 255, 255, 1) */ --color-black: rgba(0, 0, 0, 1); /* Text; Default: rgba(0, 0, 0, 1) */ --color-gray-700: rgba(35, 46, 61, 1); /* Text, matches primary; Default: rgba(35, 46, 61, 1) */ --color-gray-600: rgba(85, 96, 110, 1); /* Backgrounds, text; Default: rgba(85, 96, 110, 1) */ --color-gray-500: rgba(169, 177, 183, 1); /* Borders; Default: rgba(169, 177, 183, 1) */ --color-gray-400: rgba(212, 214, 216, 1); /* Borders; Default: rgba(212, 214, 216, 1) */ --color-gray-300: rgba(237, 239, 240, 1); /* Backgrounds, text; Default: rgba(237, 239, 240, 1) */ /* Semantic (Functional) Colors */ --color-success-bg: rgba(184, 236, 182, 1); /* Success badge background; Default: rgba(184, 236, 182, 1) */ --color-success-text: rgba(8, 50, 0, 1); /* Success badge text; Default: rgba(8, 50, 0, 1) */ --color-error-bg: rgba(255, 188, 183, 1); /* Error badge background; Default: rgba(255, 188, 183, 1) */ --color-error-text: rgba(50, 0, 0, 1); /* Error badge text; Default: rgba(50, 0, 0, 1) */ --color-link-underline-dark: rgba(79, 149, 221, 1); /* Link underlines; Default: rgba(79, 149, 221, 1) */ --color-link-underline-light: rgba(148, 196, 245, 1); /* Link underlines; Default: rgba(148, 196, 245, 1) */ --color-icon: #1f5a95; /* SVG fill, stroke; Default: #1F5A95 */ /* Font Variables */ --font-family: 'Lato', sans-serif; /* All text; Default: Lato font */ /* Font Weight Variables */ --font-weight-regular: 400; /* Standard text; Default: 400 */ --font-weight-medium: 500; /* Titles, emphasized text; Default: 500 */ --font-weight-semi-bold: 600; /* Badges; Default: 600 */ --font-weight-bold: 700; /* Headings; Default: 700 */ --font-weight-black: 900; /* Main titles; Default: 900 */ } /* Globals CSS */ * { margin: 0; box-sizing: border-box; } body { font-family: var(--font-family); } section { padding: 0 16px 0 16px; } a { text-decoration: none; } .facility-record { width: 100%; margin: 0 auto; display: flex; flex-direction: column; gap: 32px; } .facility-record-header { display: flex; flex-direction: column; width: 100%; align-items: center; } .facility-header { display: flex; flex-direction: column; width: 100%; align-items: flex-start; gap: 12px; padding: 32px 16px 20px 16px; background-color: var(--color-primary); } .facility-record .facility-title { width: 100%; font-weight: var(--font-weight-medium); color: var(--color-white); font-size: 16px; line-height: 22px; text-transform: uppercase; } .facility-record .name-description { display: flex; flex-direction: column; gap: 8px; } .facility-record .name-description h1 { font-weight: var(--font-weight-black); color: var(--color-white); font-size: 30px; line-height: 32.5px; } .facility-record .name-description p { font-weight: var(--font-weight-medium); color: var(--color-white); font-size: 16px; line-height: 17.4px; } .facility-record .facility-details-section { padding: 0px 16px 16px; align-self: stretch; width: 100%; display: flex; flex-direction: column; align-items: flex-start; gap: 4px; background-color: var(--color-gray-600); } .facility-record .grid-row { display: grid; grid-template-columns: 1fr 2fr; gap: 16px; padding: 10px 0px 12px; width: 100%; border-bottom-width: 1px; border-bottom-style: solid; } .facility-record .grid-row:last-child { border-bottom: none; } .facility-record .declarations { display: flex; flex-direction: column; gap: 12px; padding: 0px 16px; width: 100%; } .facility-record .declaration-title { font-size: 20px; font-weight: var(--font-weight-bold); line-height: 21.8px; color: var(--color-gray-700); } .facility-record .conformities-list { display: flex; flex-direction: column; gap: 8px; } .facility-record .conformity-card { display: flex; flex-direction: column; align-items: flex-start; gap: 8px; min-width: 336px; padding: 16px 18px 16px 16px; position: relative; background-color: var(--color-white); border-radius: 4px; border: 1px solid; border-color: var(--color-gray-400); } .facility-record .conformance-header { display: flex; align-items: center; justify-content: space-between; position: relative; align-self: stretch; width: 100%; flex: 0 0 auto; } .facility-record .conformance-status { display: inline-flex; align-items: center; gap: 4px; position: relative; flex: 0 0 auto; } .facility-record .conformance-label { position: relative; width: fit-content; font-weight: var(--font-weight-regular); color: var(--color-gray-600); font-size: 14px; line-height: 19.2px; } .facility-record .tags-VC-badge-red { display: inline-flex; align-items: center; justify-content: center; gap: 10px; padding: 4px 8px; flex: 0 0 auto; background-color: var(--color-error-bg); color: var(--color-error-text); border-radius: 8px; overflow: hidden; } .facility-record .tags-VC-badge-green { display: inline-flex; align-items: center; justify-content: center; gap: 10px; padding: 4px 8px; flex: 0 0 auto; background-color: var(--color-success-bg); color: var(--color-success-text); border-radius: 8px; overflow: hidden; } .facility-record .verifiable { width: fit-content; font-weight: var(--font-weight-semi-bold); font-size: 14px; line-height: 15.3px; } .facility-record .evidence-details { display: flex; flex-direction: column; align-items: center; gap: 4px; position: relative; align-self: stretch; width: 100%; flex: 0 0 auto; } .facility-record .facility-name { position: relative; align-self: stretch; margin-top: -1px; font-weight: var(--font-weight-regular); color: var(--color-secondary); font-size: 18px; line-height: 21.2px; } .facility-record .regulation-details { color: var(--color-gray-600); font-size: 14px; line-height: 19.2px; align-self: stretch; font-weight: var(--font-weight-regular); } .facility-record .regulation-details-text { font-weight: var(--font-weight-regular); font-size: 14px; line-height: 19.2px; } .facility-record .regulation-link { color: var(--color-gray-600); } .facility-record .gray-bottom-line { border-bottom: 1px var(--color-gray-600) solid; width: fit-content; text-decoration: none; } .facility-record .metrics-list { display: flex; flex-direction: column; align-items: flex-start; justify-content: flex-end; gap: 8px; align-self: stretch; width: 100%; } .facility-record .metric-item { display: flex; flex-direction: column; align-items: flex-start; gap: 8px; flex: 1; flex-grow: 1; } .facility-record .typography-heading { display: inline-flex; align-items: center; justify-content: center; gap: 10px; } .facility-record .metric-value { flex: 1; color: var(--color-gray-700); font-size: 16px; font-weight: var(--font-weight-regular); line-height: 17.44px; } .facility-record .metric-score { flex: 1; font-weight: var(--font-weight-regular); color: var(--color-gray-600); font-size: 14px; line-height: 19.2px; } .facility-record .evidence-link-container { display: flex; align-items: center; justify-content: space-between; padding: 8px 0px; position: relative; align-self: stretch; width: 100%; flex: 0 0 auto; border-radius: 4px; } .facility-record .evidence-link { display: inline-flex; align-items: center; gap: 8px; position: relative; flex: 0 0 auto; } .facility-record .evidence-label-wrapper { display: flex; flex-direction: column; width: 260px; align-items: flex-start; gap: 4px; } .facility-record .evidence-text { color: var(--color-black); font-size: 16px; line-height: 17.4px; align-self: stretch; font-weight: var(--font-weight-regular); } .facility-record .issuing-details { width: 100%; padding: 24px 16px 36px; background-color: var(--color-gray-300); display: flex; flex-direction: column; align-items: flex-start; gap: 4px; } .facility-record .typography-heading { display: inline-flex; align-items: center; justify-content: center; gap: 10px; } .facility-record .issuing-title { width: fit-content; font-weight: var(--font-weight-bold); color: var(--color-black); font-size: 20px; line-height: 21.8px; } .facility-record .facility-details { display: inline-flex; flex-direction: column; align-items: flex-start; width: 100%; } .facility-record .grid-row-alt { display: grid; grid-template-columns: 1.4fr 3fr; gap: 16px; padding: 10px 0px 12px; width: 100%; border-bottom-width: 1px; border-bottom-style: solid; } .facility-record .border-bottom-gray-400 { border-color: var(--color-gray-400); } .facility-record .border-bottom-gray-500 { border-color: var(--color-gray-500); } .facility-record .label { font-weight: var(--font-weight-regular); color: var(--color-gray-300); font-size: 16px; line-height: 22px; } .facility-record .label-alt { font-weight: var(--font-weight-regular); color: var(--color-gray-600); font-size: 16px; line-height: 22px; } .facility-record .grid-value-link { flex-direction: column; align-items: flex-start; gap: 6px; align-self: stretch; display: flex; flex: 1; flex-grow: 1; } .facility-record .div-wrapper { gap: 10px; display: inline-flex; align-items: flex-start; text-decoration: underline; text-decoration-thickness: 2px; text-decoration-color: var(--color-link-underline-dark); text-underline-offset: 3px; } .facility-record .map-link { display: inline-flex; align-items: flex-start; gap: 10px; border-bottom-width: 2px; border-bottom-style: solid; border-color: var(--color-link-underline-light); } .facility-record .map-link-text { width: fit-content; font-weight: var(--font-weight-medium); color: var(--color-white); font-size: 16px; line-height: 17.4px; } .facility-record .issuer-link { width: fit-content; font-weight: var(--font-weight-medium); color: var(--color-gray-700); font-size: 16px; line-height: 22px; } .facility-record .map-link-wrapper { display: inline-flex; align-items: flex-start; gap: 10px; border-bottom-width: 2px; border-bottom-style: solid; border-color: var(--color-link-underline-dark); } .facility-record .grid-value { display: flex; align-items: center; gap: 10px; align-self: stretch; flex-grow: 1; flex: 1; } .facility-record .grid-value-list { display: flex; flex-wrap: wrap; row-gap: 4px; max-width: 100%; } .facility-record .grid-value-list a { margin-right: 10px; } .facility-record .grid-value-text { flex: 1; font-weight: var(--font-weight-medium); color: var(--color-white); font-size: 16px; line-height: 17.4px; } .facility-record .grid-value-text-alt { font-weight: var(--font-weight-medium); color: var(--color-gray-700); font-size: 16px; line-height: 17.4px; flex: 1; } .blue-bottom-line-2, .blue-bottom-line-2:link { width: fit-content; color: var(--color-white); text-decoration: underline; text-decoration-thickness: 2px; text-decoration-color: var(--color-link-underline-light); text-underline-offset: 3px; } .white-text { color: var(--color-white); } /* Media Queries for Desktops */ @media (min-width: 1200px) { .facility-record { max-width: 1200px; } } </style> </head> <body> <div class=\"facility-record\"> <div class=\"facility-record-header\"> <header class=\"facility-header\"> <div class=\"facility-title\">FACILITY RECORD</div> <div class=\"name-description\"> <h1>{{credentialSubject.facility.name}}</h1> {{#if credentialSubject.facility.description}} <p>{{credentialSubject.facility.description}}</p> {{/if}} </div> </header> <section class=\"facility-details-section\"> <div class=\"facility-details\"> {{#if credentialSubject.facility.operatedByParty}} <div class=\"grid-row border-bottom-gray-500\"> <div class=\"label\">Operator</div> <div class=\"grid-value\"> <a href=\"{{credentialSubject.facility.operatedByParty.id}}\" class=\"blue-bottom-line-2\" aria-label=\"Visit {{credentialSubject.facility.operatedByParty.name}}\" target=\"_blank\"> {{credentialSubject.facility.operatedByParty.name}} </a> </div> </div> {{/if}} {{#if credentialSubject.facility.countryOfOperation}} <div class=\"grid-row border-bottom-gray-500\"> <div class=\"label\">Country</div> <div class=\"grid-value\"> <div class=\"grid-value-text\">{{credentialSubject.facility.countryOfOperation}}</div> </div> </div> {{/if}} {{#if credentialSubject.facility.address}} <div class=\"grid-row border-bottom-gray-500\"> <div class=\"label\">Address</div> <div class=\"grid-value\"> {{#if credentialSubject.facility.locationInformation.plusCode}} <a href=\"{{credentialSubject.facility.locationInformation.plusCode}}\" class=\"blue-bottom-line-2\" aria-label=\"View {{credentialSubject.facility.address.streetAddress}} {{credentialSubject.facility.address.addressLocality}} on map\" target=\"_blank\"> {{#if credentialSubject.facility.address.streetAddress}} {{credentialSubject.facility.address.streetAddress}} {{/if}} {{#if credentialSubject.facility.address.addressLocality}} {{credentialSubject.facility.address.addressLocality}} {{/if}} {{#if credentialSubject.facility.address.addressRegion}} {{credentialSubject.facility.address.addressRegion}} {{/if}} {{#if credentialSubject.facility.address.postalCode}} {{credentialSubject.facility.address.postalCode}} {{/if}} </a> {{else}} <span class=\"white-text\"> {{#if credentialSubject.facility.address.streetAddress}} {{credentialSubject.facility.address.streetAddress}} {{/if}} {{#if credentialSubject.facility.address.addressLocality}} {{credentialSubject.facility.address.addressLocality}} {{/if}} {{#if credentialSubject.facility.address.addressRegion}} {{credentialSubject.facility.address.addressRegion}} {{/if}} {{#if credentialSubject.facility.address.postalCode}} {{credentialSubject.facility.address.postalCode}} {{/if}} </span> {{/if}} </div> </div> {{/if}} {{#if credentialSubject.facility.processCategory}} <div class=\"grid-row border-bottom-gray-500\"> <div class=\"label\">Processes</div> <div class=\"grid-value\"> <div class=\"grid-value-list\"> {{#each credentialSubject.facility.processCategory}} <a href=\"{{id}}\" class=\"blue-bottom-line-2\" aria-label=\"Visit {{name}}\" target=\"_blank\">{{name}}</a> {{/each}} </div> </div> </div> {{/if}} {{#if credentialSubject.facility.locationInformation}} {{#if credentialSubject.facility.locationInformation.geoLocation}} {{#if credentialSubject.facility.locationInformation.geoLocation.coordinates}} <div class=\"grid-row border-bottom-gray-500\"> <div class=\"label\">Geolocation</div> <a href=\"https://www.google.com/maps?q={{lookup credentialSubject.facility.locationInformation.geoLocation.coordinates 1}},{{lookup credentialSubject.facility.locationInformation.geoLocation.coordinates 0}}\" class=\"grid-value-link\" aria-label=\"View geolocation on map\" target=\"_blank\"> <div class=\"map-link-wrapper\"> <div class=\"map-link-text\">Show on map</div> </div> </a> </div> {{/if}} {{/if}} {{/if}} </div> </section> </div> {{#if credentialSubject.conformityClaim}} <section class=\"declarations\"> <h2 class=\"declaration-title\">Declarations</h2> <div class=\"conformities-list\"> {{#each credentialSubject.conformityClaim}} <article class=\"conformity-card\"> <header class=\"conformance-header\"> <div class=\"conformance-status\"> <div class=\"conformance-label\">Conformance:</div> <div class=\"{{#if conformance}}tags-VC-badge-green{{else}}tags-VC-badge-red{{/if}}\"> <div class=\"verifiable\">{{#if conformance}}Yes{{else}}No{{/if}}</div> </div> </div> {{#if assessmentDate}} <div class=\"conformance-label\">Assessed: {{assessmentDate}}</div> {{/if}} </header> <div class=\"evidence-details\"> {{#if conformityEvidence}} {{#if conformityEvidence.linkName}} <div class=\"facility-name\">{{conformityEvidence.linkName}}</div> {{/if}} {{/if}} {{#if referenceRegulation}} <p class=\"regulation-details\"> <span class=\"regulation-details-text\"> {{#if referenceRegulation.name}} {{referenceRegulation.name}} {{/if}} {{#if referenceRegulation.jurisdictionCountry}} administered in {{referenceRegulation.jurisdictionCountry}} {{/if}} by </span> <a href=\"{{referenceRegulation.administeredBy.id}}\" class=\"regulation-link gray-bottom-line\" aria-label=\"Visit {{referenceRegulation.administeredBy.name}}\" target=\"_blank\"> {{referenceRegulation.administeredBy.name}} </a> </p> {{/if}} {{#if referenceStandard}} <p class=\"regulation-details\"> <span class=\"regulation-details-text\">{{#if referenceStandard.name}} {{referenceStandard.name}} issued by {{else}} Issued by {{/if}}</span> <a href=\"{{referenceStandard.issuingParty.id}}\" class=\"regulation-link gray-bottom-line\" aria-label=\"Visit {{referenceStandard.issuingParty.name}}\" target=\"_blank\"> {{referenceStandard.issuingParty.name}} </a> </p> {{/if}} </div> {{#if declaredValue}} <div class=\"metrics-list\"> {{#each declaredValue}} <div class=\"metric-item\"> <div class=\"typography-heading\"> <p class=\"metric-value\">{{metricName}} is {{metricValue.value}}{{metricValue.unit}}</p> </div> {{#if score}} <div class=\"typography-heading\"> <p class=\"metric-score\">Score: {{score}} {{#if accuracy}} | Accuracy {{accuracy}} {{/if}}</p> </div> {{else}} {{#if accuracy}} <div class=\"typography-heading\"> <p class=\"metric-score\">Accuracy {{accuracy}}</p> </div> {{/if}} {{/if}} </div> {{/each}} </div> {{/if}} {{#if conformityEvidence}} {{#if conformityEvidence.linkURL}} <a href=\"{{conformityEvidence.linkURL}}\" class=\"evidence-link-container\" aria-label=\"View evidence for {{referenceRegulation.name}} {{referenceStandard.name}}\" target=\"_blank\"> <div class=\"evidence-link\"> <svg width=\"24\" height=\"24\" viewBox=\"0 0 24 24\" fill=\"none\" xmlns=\"http://www.w3.org/2000/svg\"> <path d=\"M5 21C4.45 21 3.97933 20.8043 3.588 20.413C3.19667 20.0217 3.00067 19.5507 3 19V5C3 4.45 3.196 3.97933 3.588 3.588C3.98 3.19667 4.45067 3.00067 5 3H19C19.55 3 20.021 3.196 20.413 3.588C20.805 3.98 21.0007 4.45067 21 5V19C21 19.55 20.8043 20.021 20.413 20.413C20.0217 20.805 19.5507 21.0007 19 21H5ZM5 5V19H19V5H17V12L14.5 10.5L12 12V5H5Z\" fill=\"var(--color-icon)\"></path> </svg> <div class=\"evidence-label-wrapper\"> <div class=\"evidence-text\">Evidence</div> </div> </div> <svg width=\"10\" height=\"15\" viewBox=\"0 0 10 15\" fill=\"none\" xmlns=\"http://www.w3.org/2000/svg\"> <path d=\"M1 1L8 8L1 15\" stroke=\"var(--color-icon)\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\"></path> </svg> </a> {{/if}} {{/if}} </article> {{/each}} </div> </section> {{/if}} <section class=\"issuing-details\"> <div class=\"typography-heading\"> <h2 class=\"issuing-title\">Issuing details</h2> </div> <div class=\"facility-details\"> <div class=\"grid-row-alt border-bottom-gray-400\"> <div class=\"label-alt\">Issued by</div> <div class=\"grid-value-link\"> <div class=\"div-wrapper\"> <a href=\"{{issuer.id}}\" class=\"issuer-link\" aria-label=\"Visit {{issuer.name}}\" target=\"_blank\">{{issuer.name}}</a> </div> </div> </div> {{#if validFrom}} <div class=\"grid-row-alt border-bottom-gray-400\"> <div class=\"label-alt\">Valid from</div> <div class=\"grid-value\"> <div class=\"grid-value-text-alt\">{{validFrom}}</div> </div> </div> {{/if}} {{#if validUntil}} <div class=\"grid-row-alt border-bottom-gray-400\"> <div class=\"label-alt\">Valid until</div> <div class=\"grid-value\"> <div class=\"grid-value-text-alt\">{{validUntil}}</div> </div> </div> {{/if}} </div> </section> </div> </body></html>"

    ## NEW UPDATE: ADD A RULE TO UPDATE ANY @TYPE FIELD TO TYPE. ALSO REMOVE ANY EXTRAS TO AVOID DUPLICATE
    for item in rendertemplate:
        item["template"] = hbs_template
        ### Remove inconsistencies for @type and type field, because @type will throw error when rendering VC
        # If both '@type' and 'type' exist, remove '@type'
        if "@type" in item and "type" in item:
            del item["@type"]
        # If only '@type' exists, rename it to 'type'
        elif "@type" in item and "type" not in item:
            item["type"] = item.pop("@type")
    
    # Update dfr with the modified renderTemplate
    dfr["renderTemplate"] = rendertemplate

    #### 5. VCkit Issuer Structure Updates: Update the VCkit issuer configuration to use the new identifier structure
    vckit = next(iter(dfr_component.get('services', [])), {}).get('parameters', [{}])[0].get('vckit')
    vckit_issuer = vckit.get('issuer','')
    if "otherIdentifier" in vckit_issuer:
        x = pop_and_replace_key(vckit,"otherIdentifier", "issuerAlsoKnownAs")
        vckit_issuer["issuerAlsoKnownAs"] = x

    return dfr_component

#########################
###### MAIN JOB #########
#########################

from pathlib import Path

current_dir = Path(__file__).resolve().parent


# Load the uploaded file
base_path = current_dir.parent / "01_Data"
# DFR BCMine farmers test: 
file_path = base_path / "DFR_BCMine/DFR.json"
# regen farmers test: MSPYX-653_regen
#file_path = base_path + r"\DFR_RegenFarmers\test4input.json"

with open(file_path, "r") as f:
    dfr_component = json.load(f)

# Apply migration
migrate_general_dfr = migrate_general_v_050_to_v_060(dfr_component)
migrated_dfr = migrate_dfr_v050_to_v060(migrate_general_dfr)

## DFR BCMine farmers test: 
migrated_dfr_path = base_path / "DFR_BCMine/DFR_migrated_v060_test_v6.json"
# regen farmers test: MSPYX-653_regen
#migrated_dfr_path = base_path + r"\DFR_RegenFarmers\test4input-python5.json"
with open(migrated_dfr_path, "w") as f:
    json.dump(migrated_dfr, f, indent=2)

migrated_dfr_path