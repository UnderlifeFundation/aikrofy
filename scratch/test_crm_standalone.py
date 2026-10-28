"""
CRM stand-alone integration test script.
Validates connectors initialization, canonical mapping structures, and custom mapper.
"""
import sys
import os

# Append backend directory to system path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../backend')))

from services.crm.canonical_models import Contact, Lead, Account, Deal
from services.crm.hubspot_connector import HubSpotConnector
from services.crm.salesforce_connector import SalesforceConnector
from services.crm.pipedrive_connector import PipedriveConnector
from services.crm.zoho_connector import ZohoCRMConnector
from services.crm.dynamics_connector import DynamicsConnector
from services.crm.custom_mapper import CustomCRMMappingEngine


def test_connectors_init():
    print("Testing connectors initialization...")
    
    # 1. HubSpot
    hs = HubSpotConnector(None, {"access_token": "hs_test_token"})
    assert hs.crm_url == "https://api.hubapi.com"
    print("✓ HubSpot initialized successfully.")

    # 2. Salesforce
    sf = SalesforceConnector(None, {
        "client_id": "sf_client",
        "client_secret": "sf_secret",
        "refresh_token": "sf_refresh",
        "instance_url": "https://test.salesforce.com"
    })
    assert sf.crm_url == "https://test.salesforce.com"
    print("✓ Salesforce initialized successfully.")

    # 3. Pipedrive
    pd = PipedriveConnector(None, {"api_token": "pd_token"})
    assert pd.crm_url == "https://api.pipedrive.com/v1"
    print("✓ Pipedrive initialized successfully.")

    # 4. Zoho
    zh = ZohoCRMConnector(None, {"access_token": "zh_token", "region": ".eu"})
    assert zh.crm_url == "https://www.zohoapis.eu/crm/v3"
    print("✓ Zoho initialized successfully.")

    # 5. Dynamics 365
    dy = DynamicsConnector(None, {
        "access_token": "dy_token",
        "environment_url": "https://company.crm4.dynamics.com"
    })
    assert dy.crm_url == "https://company.crm4.dynamics.com/api/data/v9.2"
    print("✓ Dynamics 365 initialized successfully.")


def test_custom_mapper():
    print("Testing Custom CRM Mapper...")
    
    # Compile dynamic model schema test
    schema_dict = {
        "properties": {
            "first_name": {"type": "string", "description": "Given name"},
            "age": {"type": "integer", "description": "Years of life", "default": 18}
        },
        "required": ["first_name"]
    }
    
    DynamicContactModel = CustomCRMMappingEngine.compile_schema("DynamicContact", schema_dict)
    instance = DynamicContactModel(first_name="John")
    assert instance.first_name == "John"
    assert instance.age == 18
    print("✓ Custom compiled schema validated successfully.")

    # Test static mapping application
    raw_response = {
        "person": {
            "fname": "Sarah",
            "lname": "Connor"
        },
        "contacts": [
            {"type": "email", "value": "sarah@sky.net"}
        ]
    }
    
    mapping_rules = {
        "first_name": "person.fname",
        "last_name": "person.lname"
    }
    
    mapped_data = CustomCRMMappingEngine.apply_mapping(raw_response, mapping_rules)
    assert mapped_data["first_name"] == "Sarah"
    assert mapped_data["last_name"] == "Connor"
    print("✓ Custom mapping engine transformation validated successfully.")


if __name__ == "__main__":
    try:
        test_connectors_init()
        test_custom_mapper()
        print("\nALL CRM STANDALONE INTEGRATION TESTS PASSED SUCCESSFULLY! 🎉")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
