"""
Dynamic Schema Mapping Engine - Runtime Pydantic V2 model compiler.

Reads client ERP configuration, compiles in-memory validation models using
Pydantic's create_model, and validates inputs dynamically. This enables
standardization of proprietary or heavily-customized ERP APIs via JSON
Schema definitions stored in the database.
"""
import json
from typing import Any, Dict, Type, Union, Optional
from pydantic import BaseModel, create_model, Field


class CustomERPAdaptationEngine:
    """
    Compiles Pydantic V2 models dynamically from JSON Schemas stored in
    the database to validate data flows from custom ERPs.

    Implements the three-level override hierarchy:
    1. Platform-level mapping (standard driver rules)
    2. Environment override (sandbox/production adjustments)
    3. Account override (tenant-specific custom field injection)
    """

    @staticmethod
    def compile_schema(schema_name: str, json_schema_dict: Dict[str, Any]) -> Type:
        """
        Compile a Pydantic model from a JSON Schema definition at runtime.

        Args:
            schema_name: Name for the generated model class.
            json_schema_dict: A JSON Schema dictionary with 'properties' and 'required'.

        Returns:
            A dynamically created Pydantic BaseModel subclass.
        """
        properties = json_schema_dict.get("properties", {})
        required = json_schema_dict.get("required", [])

        type_mapping = {
            "string": str,
            "integer": int,
            "number": float,
            "boolean": bool,
            "object": dict,
            "array": list
        }

        dynamic_fields: Dict[str, Any] = {}
        for field_name, metadata in properties.items():
            json_type = metadata.get("type", "string")
            python_type = type_mapping.get(json_type, Any)

            # Handle nullable or combined-type fields
            if metadata.get("nullable", False):
                python_type = Union[python_type, None]

            field_description = metadata.get("description", f"Dynamic attribute {field_name}")
            is_required = field_name in required

            # Instantiate the field with descriptive metadata for the AI agent
            default_val = ... if is_required else metadata.get("default", None)
            dynamic_fields[field_name] = (
                python_type,
                Field(default=default_val, description=field_description)
            )

        # Return the dynamically compiled model
        return create_model(schema_name, __base__=BaseModel, **dynamic_fields)

    @staticmethod
    def apply_mapping(
        raw_response: Dict[str, Any],
        platform_rules: Optional[Dict[str, str]] = None,
        environment_overrides: Optional[Dict[str, str]] = None,
        account_overrides: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Apply the three-level override hierarchy to transform a native ERP
        response into a canonical payload.

        Each rule dict maps: canonical_field_name -> native_field_path

        Args:
            raw_response: The raw JSON response from the ERP API.
            platform_rules: Level 1 - Standard platform transformations.
            environment_overrides: Level 2 - Sandbox/production adjustments.
            account_overrides: Level 3 - Tenant-specific custom field extraction.

        Returns:
            A normalized dictionary ready for canonical model validation.
        """
        result: Dict[str, Any] = {}
        custom_fields: Dict[str, Any] = {}

        # Level 1: Platform-level mapping
        if platform_rules:
            for canonical_key, native_path in platform_rules.items():
                value = _extract_nested(raw_response, native_path)
                if value is not None:
                    result[canonical_key] = value

        # Level 2: Environment overrides
        if environment_overrides:
            for canonical_key, native_path in environment_overrides.items():
                value = _extract_nested(raw_response, native_path)
                if value is not None:
                    result[canonical_key] = value

        # Level 3: Account-level custom field injection
        if account_overrides:
            for custom_key, native_path in account_overrides.items():
                value = _extract_nested(raw_response, native_path)
                if value is not None:
                    custom_fields[custom_key] = value

        if custom_fields:
            result["custom_fields"] = custom_fields

        return result


def _extract_nested(data: Dict[str, Any], path: str) -> Any:
    """
    Extract a value from a nested dictionary using dot-notation path.
    Example: 'address.city' extracts data['address']['city'].
    """
    keys = path.split(".")
    current = data
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key)
        else:
            return None
        if current is None:
            return None
    return current
