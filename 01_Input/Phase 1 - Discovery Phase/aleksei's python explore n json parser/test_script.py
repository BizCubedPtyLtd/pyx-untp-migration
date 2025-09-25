import json
from deepdiff import DeepDiff
from copy import deepcopy

# Function to load JSON from file
def load_json(filename):
    with open(filename, 'r') as f:
        return json.load(f)

# Function to save JSON to file
def save_json(data, filename):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)

# Function to analyze differences between old and new samples
def analyze_differences(old_sample, new_sample):
    diff = DeepDiff(old_sample, new_sample, ignore_order=True, report_repetition=True)
    return str(diff)

# Function to fill missing fields recursively from template
def fill_missing(data, template):
    if isinstance(data, dict) and isinstance(template, dict):
        for key, value in template.items():
            if key not in data:
                data[key] = deepcopy(value)
            else:
                fill_missing(data[key], value)
    elif isinstance(data, list) and isinstance(template, list) and len(data) > 0 and len(template) > 0:
        for i, item in enumerate(data):
            fill_missing(item, template[i % len(template)])
    return data

# Function to upgrade credential subject from v0.5.0 to v0.6.0
def upgrade_subject(old_subject, new_subject_template):
    upgraded_subject = {
        'type': ['FacilityRecord'],
        'facility': {
            'type': ['Facility'],
            'id': old_subject.get('id'),
            'name': old_subject.get('name'),
            'registeredId': old_subject.get('registeredId'),
            'idScheme': old_subject.get('idScheme'),
            'description': old_subject.get('description'),
            'countryOfOperation': old_subject.get('countryOfOperation'),
            'processCategory': old_subject.get('processCategory', []),
            'operatedByParty': old_subject.get('operatedByParty', {}),
            'facilityAlsoKnownAs': old_subject.pop('otherIdentifier', []),
            'locationInformation': old_subject.get('locationInformation'),
            'address': old_subject.get('address')
        },
        'conformityClaim': old_subject.get('conformityClaim', [])
    }

    # Remove type from operatedByParty and pop idScheme to simplify
    upgraded_subject['facility']['operatedByParty'].pop('type', None)
    upgraded_subject['facility']['operatedByParty'].pop('idScheme', None)

    # Remove type and idScheme from facilityAlsoKnownAs items
    for aka in upgraded_subject['facility']['facilityAlsoKnownAs']:
        aka.pop('type', None)
        aka.pop('idScheme', None)

    # Update conformityClaim
    claims_template = new_subject_template.get('conformityClaim', [])
    for i, claim in enumerate(upgraded_subject['conformityClaim']):
        template_claim = claims_template[i % len(claims_template)] if claims_template else {}

        # Fill missing fields like description
        fill_missing(claim, template_claim)

        # Update referenceStandard issuingParty: remove type and idScheme
        if 'referenceStandard' in claim and 'issuingParty' in claim['referenceStandard']:
            claim['referenceStandard']['issuingParty'].pop('type', None)
            claim['referenceStandard']['issuingParty'].pop('idScheme', None)

        # Update referenceRegulation administeredBy: remove type and idScheme
        if 'referenceRegulation' in claim and 'administeredBy' in claim['referenceRegulation']:
            claim['referenceRegulation']['administeredBy'].pop('type', None)
            claim['referenceRegulation']['administeredBy'].pop('idScheme', None)

        # Update assessmentCriteria
        criteria_template = template_claim.get('assessmentCriteria', [])
        for j, criterion in enumerate(claim.get('assessmentCriteria', [])):
            template_crit = criteria_template[j % len(criteria_template)] if criteria_template else {}

            # Rename thresholdValues to thresholdValue, take first if array
            if 'thresholdValues' in criterion:
                threshold_values = criterion.pop('thresholdValues')
                if threshold_values:
                    criterion['thresholdValue'] = threshold_values[0]
                else:
                    criterion['thresholdValue'] = {}

            # Fill missing fields from template
            fill_missing(criterion, template_crit)

            # For category, keep as is (array with type etc.)

    return upgraded_subject

# Function to upgrade the full credential (including issuer, validFrom, etc.)
def upgrade_credential(old_cred, new_sample):
    upgraded = deepcopy(old_cred)

    # Update @context
    if '@context' in upgraded:
        for i, ctx in enumerate(upgraded['@context']):
            if 'untp/dfr/0.5.0' in ctx:
                upgraded['@context'][i] = 'https://test.uncefact.org/vocabulary/untp/dfr/0.6.0/'

    # Update validFrom and validUntil to include Z
    if 'validFrom' in upgraded and not upgraded['validFrom'].endswith('Z'):
        upgraded['validFrom'] += 'Z'
    if 'validUntil' in upgraded and not upgraded['validUntil'].endswith('Z'):
        upgraded['validUntil'] += 'Z'

    # Update issuer: rename otherIdentifier to issuerAlsoKnownAs, remove type and idScheme from items
    if 'issuer' in upgraded:
        issuer_template = new_sample.get('issuer', {})
        fill_missing(upgraded['issuer'], issuer_template)
        if 'otherIdentifier' in upgraded['issuer']:
            upgraded['issuer']['issuerAlsoKnownAs'] = upgraded['issuer'].pop('otherIdentifier')
            for aka in upgraded['issuer']['issuerAlsoKnownAs']:
                aka.pop('type', None)
                aka.pop('idScheme', None)

    # Upgrade credentialSubject
    if 'credentialSubject' in upgraded:
        upgraded['credentialSubject'] = upgrade_subject(upgraded['credentialSubject'], new_sample['credentialSubject'])

    return upgraded

# Main script execution
if __name__ == '__main__':
    # Load samples
    old_sample = load_json('0.5.0_sample.json')
    new_sample = load_json('0.6.0_sample.json')
    
    # Analyze and log differences
    changes = analyze_differences(old_sample, new_sample)
    with open('versions_changes.log', 'w') as log_file:
        log_file.write(changes)
    
    # Load client data
    client = load_json('client_test_data.json')
    
    # Upgrade schema URL
    if 'components' in client and client['components'] and 'props' in client['components'][0] and 'schema' in client['components'][0]['props']:
        schema_url = client['components'][0]['props']['schema']['url']
        schema_url = schema_url.replace('/v/working/', '/v/0.6.0/').replace('Facility.json?class=Facility', 'FacilityRecord.json?class=FacilityRecord')
        client['components'][0]['props']['schema']['url'] = schema_url
    
    # Upgrade data (credentialSubject)
    if 'components' in client and client['components'] and 'props' in client['components'][0] and 'data' in client['components'][0]['props']:
        old_data = client['components'][0]['props']['data']
        # Wrap old_data as credentialSubject for upgrade function
        wrapped_old = {'credentialSubject': old_data}
        upgraded_wrapped = upgrade_credential(wrapped_old, new_sample)
        client['components'][0]['props']['data'] = upgraded_wrapped['credentialSubject']
    
    # If 'services' exists, update relevant parts
    if 'services' in client:
        for service in client['services']:
            if service.get('name') == 'processDigitalFacilityRecord' and 'parameters' in service:
                for param in service['parameters']:
                    # Update digitalFacilityRecord context
                    if 'digitalFacilityRecord' in param and 'context' in param['digitalFacilityRecord']:
                        for i, ctx in enumerate(param['digitalFacilityRecord']['context']):
                            if '0.5.0' in ctx or '0.6.0-beta7' in ctx:
                                param['digitalFacilityRecord']['context'][i] = 'https://test.uncefact.org/vocabulary/untp/dfr/0.6.0/'
                    
                    # Update renderTemplate to the new one provided
                    if 'digitalFacilityRecord' in param and 'renderTemplate' in param['digitalFacilityRecord']:
                        new_template = "<!DOCTYPE html> <html lang=\"en\"> <head> <meta charset=\"UTF-8\" /> <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" /> <link href=\"https://fonts.googleapis.com/css2?family=Lato:ital,wght@0,100;0,300;0,400;0,700;0,900;1,100;1,300;1,400;1,700;1,900&display=swap\" rel=\"stylesheet\"> <title>Digital Facility Record</title> <style> :root { --primary-colorsblue-10: rgba(247, 250, 253, 1); --primary-colorsgray-100: rgba(250, 250, 250, 1); --white: rgba(255, 255, 255, 1); --black: rgba(0, 0, 0, 1); --primary-colorsgray-300: rgba(237, 239, 240, 1); --primary-colorsgray-500: rgba(169, 177, 183, 1); --primary-colorsgray-600: rgba(85, 96, 110, 1); --primary-colorsblue-700: rgba(31, 90, 149, 1); --primary-colorsgray-700: rgba(35, 46, 61, 1); --primary-colorsblue-100: rgba(181, 213, 245, 0.5); --primary-colorsblue-100-full: rgba(181, 213, 245, 1); --primary-colorsblue-200: rgba(148, 196, 245, 1); --primary-colorsblue-400: rgba(79, 149, 221, 1); --primary-colorsblue-600: rgba(0, 110, 181, 1); --primary-colorsgray-400: rgba(212, 214, 216, 1); --primary-colorsgray-300: rgba(237, 239, 240, 1); --accent-colorslight-green: rgba(184, 236, 182, 1); --text-color-green: rgba(8, 50, 0, 1); --accent-colorslight-red: rgba(255, 188, 183, 1); --text-color-red: rgba(50, 0, 0, 1); } /* Globals CSS */ * { margin: 0; box-sizing: border-box; } body { font-family: 'Lato', sans-serif; } section { padding: 0 16px 0 16px; } a { text-decoration: none; } .facility-record { width: 100%; margin: 0 auto; display: flex; flex-direction: column; gap: 32px; word-break: break-word; } .facility-record .contents { display: flex; flex-direction: column; gap: 24px; } .facility-record .traceability-header { display: flex; flex-direction: column; width: 100%; align-items: center; } .facility-record .TRACE-header { display: flex; flex-direction: column; width: 100%; align-items: flex-start; gap: 12px; padding: 32px 16px 20px 16px; background-color: var(--primary-colorsgray-700); } .facility-record .PP-title { width: 100%; font-weight: 500; color: var(--white); font-size: 16px; line-height: 22px; text-transform: uppercase; } .facility-record .name-description { display: flex; flex-direction: column; gap: 8px; } .facility-record .name-description h1 { font-weight: 900; color: var(--white); font-size: 30px; line-height: 32.5px; } .facility-record .name-description p { font-weight: 500; color: var(--white); font-size: 16px; line-height: 17.4px; } .facility-record .text-wrapper { align-self: stretch; font-weight: 900; color: var(--white); font-size: 30px; line-height: 32.5px; } .facility-record .issuing-organisation { padding: 0px 16px 16px; align-self: stretch; width: 100%; display: flex; flex-direction: column; align-items: flex-start; gap: 4px; background-color: var(--primary-colorsgray-600); } .facility-record .data-two-columns { display: grid; grid-template-columns: 1fr 2fr; gap: 16px; padding: 10px 0px 12px; width: 100%; border-bottom-width: 1px; border-bottom-style: solid; } .facility-record .data-two-columns:last-child { border-bottom: none; } .facility-record .table-line { border-bottom: 1px solid #d4d6d8; } .facility-record .item-value a { color: #232E3D; } .facility-record .declarations { display: flex; flex-direction: column; gap: 12px; padding: 0px 16px; width: 100%; } .facility-record .declaration-title { font-size: 20px; font-weight: 700; line-height: 21.8px; color: var(--primary-colorsgray-700); } .facility-record .cards-conformities { display: flex; flex-direction: column; gap: 8px; } .facility-record .cards-conformity { display: flex; flex-direction: column; align-items: flex-start; gap: 8px; min-width: 100%; padding: 16px 18px 16px 16px; position: relative; background-color: var(--white); border-radius: 4px; border: 1px solid; border-color: var(--primary-colorsgray-400); } .facility-record .frame { display: flex; align-items: center; justify-content: space-between; position: relative; align-self: stretch; width: 100%; flex: 0 0 auto; } .facility-record .div-2 { display: inline-flex; align-items: center; gap: 4px; position: relative; flex: 0 0 auto; } .facility-record .company-name { position: relative; width: fit-content; font-weight: 400; color: var(--primary-colorsgray-600); font-size: 14px; line-height: 19.2px; } .facility-record .tags-VC-badge-red { display: inline-flex; align-items: center; justify-content: center; gap: 10px; padding: 4px 8px; flex: 0 0 auto; background-color: var(--accent-colorslight-red); color: var(--text-color-red); border-radius: 8px; overflow: hidden; } .facility-record .tags-VC-badge-green { display: inline-flex; align-items: center; justify-content: center; gap: 10px; padding: 4px 8px; flex: 0 0 auto; background-color: var(--accent-colorslight-green); color: var(--text-color-green); border-radius: 8px; overflow: hidden; } .facility-record .verifiable { width: fit-content; font-weight: 600; font-size: 14px; line-height: 15.3px; } .facility-record .frame-2 { display: flex; flex-direction: column; align-items: center; gap: 4px; position: relative; align-self: stretch; width: 100%; flex: 0 0 auto; } .facility-record .text-wrapper { position: relative; align-self: stretch; margin-top: -1px; font-weight: 400; color: var(--primary-colorsblue-700); font-size: 18px; line-height: 21.2px; } .facility-record .p { color: var(--primary-colorsgray-600); font-size: 14px; line-height: 19.2px; align-self: stretch; font-weight: 400; color: #55606e; } .facility-record .span { font-weight: 400; font-size: 14px; line-height: 19.2px; } .facility-record .text-wrapper-3 { color: #55606e; } .facility-record .gray-bottom-line { border-bottom: 1px #55606e solid; width: fit-content; text-decoration: none; } .facility-record .frame-3 { display: flex; flex-direction: column; align-items: flex-start; justify-content: flex-end; gap: 8px; align-self: stretch; width: 100%; } .facility-record .frame-4 { display: flex; flex-direction: column; align-items: flex-start; gap: 8px; flex: 1; flex-grow: 1; } .facility-record .typography-heading { display: inline-flex; align-items: center; justify-content: center; gap: 10px; } .facility-record .heading { flex: 1; color: var(--primary-colorsgray-700); font-size: 16px; font-weight: 400; line-height: 17.44px; } .facility-record .heading-2 { flex: 1; font-weight: 400; color: var(--primary-colorsgray-600); font-size: 14px; line-height: 19.2px; } .facility-record .cards-traceability { display: grid; grid-template-columns: 1fr auto; align-items: center; justify-content: space-between; padding: 8px 0px; position: relative; align-self: stretch; width: 100%; flex: 0 0 auto; border-radius: 4px; } .facility-record .frame-5 { display: inline-flex; align-items: center; gap: 8px; position: relative; flex: 0 0 auto; } .facility-record .company-name-wrapper { display: flex; flex-direction: column; align-items: flex-start; gap: 4px; } .facility-record .company-name-2 { color: var(--black); font-size: 16px; line-height: 17.4px; align-self: stretch; font-weight: 400; } .facility-record .issuing-details { width: 100%; padding: 24px 16px 36px; background-color: var(--primary-colorsgray-300); display: flex; flex-direction: column; align-items: flex-start; gap: 4px; } .facility-record .typography-heading { display: inline-flex; align-items: center; justify-content: center; gap: 10px; } .facility-record .text-wrapper-2 { width: fit-content; font-weight: 700; color: var(--black); font-size: 20px; line-height: 21.8px; } .facility-record .div { display: inline-flex; flex-direction: column; align-items: flex-start; width: 100%; } .facility-record .data-two-columns-2 { display: grid; grid-template-columns: 1.4fr 3fr; gap: 16px; padding: 10px 0px 12px; width: 100%; border-bottom-width: 1px; border-bottom-style: solid; } .facility-record .border-bottom-gray-400 { border-color: var(--primary-colorsgray-400); } .facility-record .border-bottom-gray-500 { border-color: var(--primary-colorsgray-500); } .facility-record .border-bottom-blue-100 { border-color: var(--primary-colorsblue-100-full); } .facility-record .border-bottom-blue-200 { border-color: var(--primary-colorsblue-200); } .facility-record .label { font-weight: 400; color: var(--primary-colorsgray-300); font-size: 16px; line-height: 22px; } .facility-record .label-2 { font-weight: 400; color: var(--primary-colorsgray-600); font-size: 16px; line-height: 22px; } .facility-record .data-data-link { flex-direction: column; align-items: flex-start; gap: 6px; align-self: stretch; display: flex; flex: 1; flex-grow: 1; } .facility-record .div-wrapper { gap: 10px; display: inline-flex; align-items: flex-start; text-decoration: underline; text-decoration-thickness: 2px; text-decoration-color: var(--primary-colorsblue-400); text-underline-offset: 3px; } .facility-record .line { display: inline-flex; align-items: flex-start; gap: 10px; border-bottom-width: 2px; border-bottom-style: solid; border-color: var(--primary-colorsblue-200); } .facility-record .line-2 { width: fit-content; font-weight: 500; color: var(--white); font-size: 16px; line-height: 17.4px; } .facility-record .line-3 { width: fit-content; font-weight: 500; color: var(--primary-colorsgray-700); font-size: 16px; line-height: 22px; } .facility-record .line-4 { display: inline-flex; align-items: flex-start; gap: 10px; border-bottom-width: 2px; border-bottom-style: solid; border-color: var(--primary-colorsblue-400); } .facility-record .data-data { display: flex; align-items: center; gap: 10px; align-self: stretch; flex-grow: 1; flex: 1; } .facility-record .data-data a { line-height: 22px; } .facility-record .data-data-2 a { margin-right: 10px; } .facility-record .data { flex: 1; font-weight: 500; color: var(--white); font-size: 16px; line-height: 17.4px; } .facility-record .data-2 { font-weight: 500; color: var(--primary-colorsgray-700); font-size: 16px; line-height: 17.4px; flex: 1; } .blue-bottom-line, .blue-bottom-line:link { border-bottom: 2px hsl(210, 68%, 59%) solid; width: fit-content; justify-content: flex-start; align-items: flex-start; gap: 10px; display: inline-flex; cursor: pointer; text-decoration: none; color: #232E3D; } .blue-bottom-line-2, .blue-bottom-line-2:link { width: fit-content; color: var(--white); text-decoration: underline; text-decoration-thickness: 2px; text-decoration-color: var(--primary-colorsblue-200); text-underline-offset: 3px; } /* Media Queries for Mobiles */ @media (min-width: 50px) { .facility-record { min-width: 100%; } } div:has(.facility-record) .facility-record .declarations, div:has(.facility-record) .facility-record section { padding: 0px; } </style> </head> <body> <div class=\"facility-record\"> <div class=\"contents\"> <div class=\"traceability-header\"> <div class=\"TRACE-header\"> <div class=\"PP-title\">FACILITY RECORD</div> <div class=\"name-description\"> <h1>{{credentialSubject.name}}</h1> <p>{{credentialSubject.description}}</p> </div> </div> <div class=\"issuing-organisation\"> <div class=\"div\"> <div class=\"data-two-columns border-bottom-gray-500\"> <div class=\"label\">Operator</div> <div class=\"data-data\"> <a href=\"{{credentialSubject.operatedByParty.id}}\" class=\"blue-bottom-line-2\">{{credentialSubject.operatedByParty.name}}</a> </div> </div> <div class=\"data-two-columns border-bottom-gray-500\"> <div class=\"label\">Country</div> <div class=\"data-data\"> <div class=\"data\">{{credentialSubject.countryOfOperation}}</div> </div> </div> <div class=\"data-two-columns border-bottom-gray-500\"> <div class=\"label\">Address</div> <div class=\"data-data\"> {{!-- TODO 1: plain text --}} {{!-- <div class=\"data\">{{credentialSubject.address.streetAddress}} {{credentialSubject.address.addressLocality}}, {{credentialSubject.address.postalCode}}</div> --}} {{!-- TODO 2: confirm --}} {{!-- <a href=\"https://www.google.com/maps/?q={{credentialSubject.address.streetAddress}} {{credentialSubject.address.addressRegion}} {{credentialSubject.address.postalCode}} {{credentialSubject.address.addressCountry}}\" class=\"blue-bottom-line-2\" target=\"_blank\">{{credentialSubject.address.streetAddress}}</a> --}} {{!-- TODO 3: confirm --}} <a href=\"{{credentialSubject.locationInformation.plusCode}}\" class=\"blue-bottom-line-2\" target=\"_blank\">{{credentialSubject.address.streetAddress}} {{credentialSubject.address.addressLocality}}, {{credentialSubject.address.postalCode}}</a> </div> </div> <div class=\"data-two-columns border-bottom-gray-500\"> <div class=\"label\">Processes</div> <div class=\"data-data-2\"> {{#each credentialSubject.processCategory}} <a href=\"{{id}}\" class=\"blue-bottom-line-2\">{{name}}</a> {{/each}} </div> </div> <div class=\"data-two-columns border-bottom-gray-500\"> <div class=\"label\">Geolocation</div> <a href=\"https://www.google.com/maps?q={{lookup credentialSubject.locationInformation.geoLocation.coordinates 0}},{{lookup credentialSubject.locationInformation.geoLocation.coordinates 1}}&ll={{lookup credentialSubject.locationInformation.geoLocation.coordinates 0}},{{lookup credentialSubject.locationInformation.geoLocation.coordinates 1}}&z=13\" class=\"data-data-link\" target=\"_blank\"> <div class=\"line-4\"> <div class=\"line-2\">Show on map</div> </div> </a> </div> </div> </div> </div> <section class=\"declarations\"> <div class=\"declaration-title\">Declarations</div> <div class=\"cards-conformities\"> {{#each credentialSubject.conformityClaim}} <div class=\"cards-conformity\"> <div class=\"frame\"> <div class=\"div-2\"> <div class=\"company-name\">Conformance:</div> <div class=\"{{#if conformance}}tags-VC-badge-green{{else}}tags-VC-badge-red{{/if}}\"> <div class=\"verifiable\">{{#if conformance}}Yes{{else}}No{{/if}}</div> </div> </div> <div class=\"company-name\">Assessed: {{assessmentDate}}</div> </div> <div class=\"frame-2\"> <div class=\"text-wrapper\">{{conformityEvidence.linkName}}</div> <p class=\"p\"> <span class=\"span\">{{referenceRegulation.name}} administered in {{referenceRegulation.jurisdictionCountry}} by </span> <a href=\"{{referenceRegulation.administeredBy.id}}\" class=\"text-wrapper-3 gray-bottom-line\">{{referenceRegulation.administeredBy.name}}</a> </p> <p class=\"p\"> <span class=\"span\">{{referenceStandard.name}} issued by </span> <a href=\"{{referenceStandard.issuingParty.id}}\" class=\"text-wrapper-3 gray-bottom-line\">{{referenceStandard.issuingParty.name}}</a> </p> </div> <div class=\"frame-3\"> {{#each declaredValue}} <div class=\"frame-4\"> <div class=\"typography-heading\"> <p class=\"heading\">{{metricName}} is {{metricValue.value}}{{metricValue.unit}}</p> </div> <div class=\"typography-heading\"> <p class=\"heading-2\">Score: {{score}} | Accuracy {{accuracy}}</p> </div> </div> {{/each}} </div> <a href=\"{{conformityEvidence.linkURL}}\" class=\"cards-traceability\"> <div class=\"frame-5\"> <svg width=\"24\" height=\"24\" viewBox=\"0 0 24 24\" fill=\"none\" xmlns=\"http://www.w3.org/2000/svg\"> <path d=\"M5 21C4.45 21 3.97933 20.8043 3.588 20.413C3.19667 20.0217 3.00067 19.5507 3 19V5C3 4.45 3.196 3.97933 3.588 3.588C3.98 3.19667 4.45067 3.00067 5 3H19C19.55 3 20.021 3.196 20.413 3.588C20.805 3.98 21.0007 4.45067 21 5V19C21 19.55 20.8043 20.021 20.413 20.413C20.0217 20.805 19.5507 21.0007 19 21H5ZM5 5V19H19V5H17V12L14.5 10.5L12 12V5H5Z\" fill=\"#1F5A95\"></path> </svg> <div class=\"company-name-wrapper\"> <div class=\"company-name-2\">Evidence</div> </div> </div> <svg width=\"10\" height=\"15\" viewBox=\"0 0 10 15\" fill=\"none\" xmlns=\"http://www.w3.org/2000/svg\"> <path d=\"M1 1L8 8L1 15\" stroke=\"#1F5A95\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\"> </path> </svg> </a> </div> {{/each}} </div> </section> </div> <div class=\"issuing-details\"> <div class=\"typography-heading\"> <div class=\"text-wrapper-2\">Issuing details</div> </div> <div class=\"div\"> <div class=\"data-two-columns-2 border-bottom-gray-400\"> <div class=\"label-2\">Issued by</div> <div class=\"data-data-link\"> <div class=\"div-wrapper\"> <a href=\"{{issuer.id}}\" class=\"line-3\">{{issuer.name}}</a> </div> </div> </div> <div class=\"data-two-columns-2 border-bottom-gray-400\"> <div class=\"label-2\">Valid from</div> <div class=\"data-data\"> <div class=\"data-2\">{{validFrom}}</div> </div> </div> <div class=\"data-two-columns-2 border-bottom-gray-400\"> <div class=\"label-2\">Valid until</div> <div class=\"data-data\"> <div class=\"data-2\">{{validUntil}}</div> </div> </div> </div> </div> </div> </body> </html>"
                        param['digitalFacilityRecord']['renderTemplate'][0]['template'] = new_template
                    
                    # Update storage URL
                    if 'storage' in param and 'url' in param['storage']:
                        param['storage']['url'] = param['storage']['url'].replace('/v1/documents', '/api/1.0.0/documents')
                    
                    # Update dlr
                    if 'dlr' in param:
                        if 'dlrAPIUrl' in param['dlr'] and '/api/1.0.0' not in param['dlr']['dlrAPIUrl']:
                            param['dlr']['dlrAPIUrl'] += '/api/1.0.0'
                        if 'linkRegisterPath' in param['dlr'] and param['dlr']['linkRegisterPath'] == '/api/resolver':
                            param['dlr']['linkRegisterPath'] = 'resolver'
    
    # TODO: Validation (commented out)
    # import jsonschema
    # new_schema = requests.get('https://jargon.sh/user/unece/DigitalFacilityRecord/v/0.6.0/artefacts/jsonSchemas/FacilityRecord.json').json()
    # jsonschema.validate(client['components'][0]['props']['data'], new_schema)
    
    # Save upgraded client data
    save_json(client, 'upgraded_client_test_data.json')
    
    print("Upgrade complete. Changes logged to 'versions_changes.log'. Upgraded file saved to 'upgraded_client_test_data.json'.")