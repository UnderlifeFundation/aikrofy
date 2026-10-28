"""
Dynamic CRM Schema Mapping Engine - Runtime validation and Code-First LLM mapper.

Enables clients to connect custom DBs/APIs by compiling schemas at runtime and utilizing
AI to dynamically map fields to our canonical CRM format.
"""
import os
import json
import logging
from typing import Any, Dict, Type, Union, Optional
from pydantic import BaseModel, create_model, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

logger = logging.getLogger(__name__)


class CustomCRMMappingEngine:
    """
    Compiles Pydantic V2 models dynamically from JSON Schemas,
    and uses LLMs to automatically resolve mappings for custom/in-house databases.
    """

    @staticmethod
    def compile_schema(schema_name: str, json_schema_dict: Dict[str, Any]) -> Type[BaseModel]:
        """Compile a Pydantic model from a JSON Schema definition at runtime."""
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

            if metadata.get("nullable", False):
                python_type = Union[python_type, None]

            field_description = metadata.get("description", f"Dynamic attribute {field_name}")
            is_required = field_name in required

            default_val = ... if is_required else metadata.get("default", None)
            dynamic_fields[field_name] = (
                python_type,
                Field(default=default_val, description=field_description)
            )

        return create_model(schema_name, __base__=BaseModel, **dynamic_fields)

    @staticmethod
    def generate_mapping_with_llm(
        raw_json_sample: Dict[str, Any], 
        canonical_entity: str, 
        api_key: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Uses an LLM to dynamically generate dot-notation paths mapping a raw JSON sample 
        to the target canonical CRM entity properties.

        Args:
            raw_json_sample: Dict containing a sample payload from the custom system.
            canonical_entity: One of 'Contact', 'Lead', 'Account', 'Deal'.
            api_key: Optional client OpenAI key.

        Returns:
            Dict mapping: canonical_field_name -> raw_json_path (dot notation)
        """
        resolved_key = api_key or os.getenv("OPENAI_API_KEY")
        if not resolved_key:
            logger.warning("No OpenAI API key resolved for custom mapping generator. Returning empty mapping.")
            return {}

        # Define canonical entity schemas for the LLM
        entity_schemas = {
            "Contact": {
                "id": "Unique identifier of the contact in the raw system",
                "first_name": "First name of the person",
                "last_name": "Last name of the person",
                "email": "Primary email address",
                "phone": "Phone number",
                "account_id": "ID of the associated company/account, if any"
            },
            "Lead": {
                "id": "Unique identifier of the lead",
                "full_name": "Full name of the lead",
                "email": "Email address of the lead",
                "source": "Marketing source or medium (e.g. facebook, web)",
                "status": "Lead qualification stage (e.g. New, Contacted, Qualified)",
                "estimated_value": "Estimated budget or contract value (number)"
            },
            "Account": {
                "id": "Unique identifier of the company/account",
                "name": "Organization or company name",
                "domain": "Domain or website of the company",
                "annual_revenue": "Annual revenue amount (number)",
                "industry": "Industry or vertical"
            },
            "Deal": {
                "id": "Unique identifier of the deal/opportunity",
                "title": "Name or title of the opportunity",
                "account_id": "ID of the associated account/company",
                "stage": "Pipeline stage of the deal",
                "amount": "Value of the deal (number)",
                "probability": "Win probability percentage/factor (0.0 to 1.0)",
                "expected_closing_date": "Date when deal is expected to close"
            }
        }

        target_schema = entity_schemas.get(canonical_entity)
        if not target_schema:
            raise ValueError(f"Invalid canonical entity: {canonical_entity}")

        system_msg = SystemMessage(
            content=(
                "You are an expert integration engineer. Your task is to inspect a sample raw JSON payload "
                "from a proprietary API or database and map its properties to a standardized canonical CRM schema. "
                "Output ONLY a valid JSON object where the keys are canonical field names, and the values are "
                "dot-notation paths representing where to extract that value from the raw JSON payload. "
                "Do not include any markdown fences or explanation. "
                "Example output: {\"first_name\": \"data.user.fname\", \"email\": \"data.user.contacts.email_addr\"}"
            )
        )

        user_content = {
            "canonical_entity": canonical_entity,
            "target_fields_to_resolve": target_schema,
            "raw_json_payload_sample": raw_json_sample
        }
        human_msg = HumanMessage(content=json.dumps(user_content, indent=2))

        try:
            # We use gpt-5-nano as a robust fallback
            model_name = "gpt-5-nano"
            llm = ChatOpenAI(
                model=model_name,
                api_key=resolved_key,
                temperature=0.0
            )
            response = llm.invoke([system_msg, human_msg])
            text_response = response.content.strip()
            # Handle potential markdown wrappers if returned
            if text_response.startswith("```json"):
                text_response = text_response.split("```json", 1)[1].rsplit("```", 1)[0].strip()
            elif text_response.startswith("```"):
                text_response = text_response.split("```", 1)[1].rsplit("```", 1)[0].strip()

            return json.loads(text_response)
        except Exception as e:
            logger.error(f"Error generating dynamic mapping: {e}")
            return {}

    @staticmethod
    def apply_mapping(raw_response: Dict[str, Any], mapping_rules: Dict[str, str]) -> Dict[str, Any]:
        """
        Apply resolved mapping rules to extract canonical fields from raw data.
        """
        result: Dict[str, Any] = {}
        custom_fields: Dict[str, Any] = {}

        for canonical_key, raw_path in mapping_rules.items():
            value = _extract_nested(raw_response, raw_path)
            if value is not None:
                result[canonical_key] = value

        # Any fields not mapped but present can be saved into custom_fields passthrough
        for k, v in raw_response.items():
            if k not in mapping_rules.values() and not isinstance(v, (dict, list)):
                custom_fields[k] = v

        if custom_fields:
            result["custom_fields"] = custom_fields

        return result


def _extract_nested(data: Dict[str, Any], path: str) -> Any:
    """Extract a value from a nested dictionary using dot-notation path."""
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
