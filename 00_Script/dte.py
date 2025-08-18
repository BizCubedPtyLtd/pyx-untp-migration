

# ---------- DPP Transformer ----------
class DPPTransformer(CredentialTransformer):
    def transform(self) -> Dict[str, Any]:
        # Apply general migrations
        self.component = GeneralMigrator.migrate_general_v_050_to_v_060(self.component)
        
        # Placeholder for DPP-specific migrations (add based on migration guide)
        data = self.component["props"]["data"]
        # Example: Update schema URL to v0.6.0
        schema = self.component["props"]["schema"]
        schema["url"] = schema["url"].replace("/v/0.5.0/", "/v/0.6.0/")
        
        # Clean and flatten as needed
        self._clean_identifier_list(data, ['type', '@context', 'issuer'])
        self._flatten_credential_subject(data, 'credentialSubject')
        
        return self.component
    


# ---------- DCC Transformer ----------
class DCCTransformer(CredentialTransformer):
    def transform(self) -> Dict[str, Any]:
        # Apply general migrations
        self.component = GeneralMigrator.migrate_general_v_050_to_v_060(self.component)
        
        # Placeholder for DCC-specific migrations (add based on migration guide)
        data = self.component["props"]["data"]
        # Example: Update schema URL to v0.6.0
        schema = self.component["props"]["schema"]
        schema["url"] = schema["url"].replace("/v/0.5.0/", "/v/0.6.0/")
        
        # Clean and flatten as needed
        self._clean_identifier_list(data, ['type', '@context', 'issuer'])
        self._flatten_credential_subject(data, 'credentialSubject')
        
        return self.component
    