
from typing import Dict, Any, List

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