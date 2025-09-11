import json
from pathlib import Path
from typing import Dict, Any, List

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
class DCCTransformer(CredentialTransformer):
    def transform(self) -> Dict[str, Any]:
        # 3. Party Structure Changes:
        '''issuedToParty simplified from an Identifier reference to an inline object structure, removing idScheme.
        Similar simplifications applied to assessedOrganisation and auditor properties within the assessment array.
        '''
        issuedtoparty = new_credential_subject.get('issuedToParty', {})
        if "type" in issuedtoparty:
            del new_credential_subject['issuedToParty']["type"]
        if "idScheme" in new_credential_subject:
            del new_credential_subject["issuedToParty"]["idScheme"]
        # new_credential_subject["issuedToParty"] = issuedtoparty


        assessments = new_credential_subject.get('assessment', [])
        for assessment in assessment:
            assessedOrganisation = assessment.get('assessedOrganisation', {})
            if "type" in assessedOrganisation:
                del assessedOrganisation["type"]
            if "idScheme" in assessedOrganisation:
                del assessedOrganisation["idScheme"]
            assessment["assessedOrganisation"] = assessedOrganisation
            auditor = assessment.get('auditor', {})
            if "type" in auditor:
                del auditor["type"]
            if "idScheme" in auditor:
                del auditor["idScheme"]
            assessment["auditor"] = auditor
