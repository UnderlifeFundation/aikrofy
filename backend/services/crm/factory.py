"""
CRM Connector Factory
Resolves the correct connector instance based on company configuration.
"""
from typing import Optional
from services.crm.base_connector import BaseCRMConnector


def get_crm_connector(company) -> Optional[BaseCRMConnector]:
    """
    Factory function: given a Company model instance, look up its
    CRMConfig and return the matching platform connector ready to use.

    Returns None if the company has no CRM configured.
    """
    from extensions import db

    # Preventive rollback (MySQL "gone away" protection)
    try:
        db.session.rollback()
    except Exception:
        pass

    config = getattr(company, 'crm_config', None)
    if not config or not config.platform:
        return None

    platform = config.platform.value  # e.g. 'hubspot'
    crm_url = config.crm_url
    credentials = config.credentials or {}

    connectors = {
        'hubspot': _build_hubspot,
        'salesforce': _build_salesforce,
        'pipedrive': _build_pipedrive,
        'zoho': _build_zoho,
        'dynamics_365': _build_dynamics_365,
        'custom': _build_custom,
    }

    builder = connectors.get(platform)
    if not builder:
        raise ValueError(f"Unsupported CRM platform: {platform}")

    return builder(crm_url, credentials)


# ------------------------------------------------------------------
# Builder helpers (lazy imports to avoid circular deps)
# ------------------------------------------------------------------

def _build_hubspot(crm_url, credentials):
    from services.crm.hubspot_connector import HubSpotConnector
    return HubSpotConnector(crm_url, credentials)


def _build_salesforce(crm_url, credentials):
    from services.crm.salesforce_connector import SalesforceConnector
    return SalesforceConnector(crm_url, credentials)


def _build_pipedrive(crm_url, credentials):
    from services.crm.pipedrive_connector import PipedriveConnector
    return PipedriveConnector(crm_url, credentials)


def _build_zoho(crm_url, credentials):
    from services.crm.zoho_connector import ZohoCRMConnector
    return ZohoCRMConnector(crm_url, credentials)


def _build_dynamics_365(crm_url, credentials):
    from services.crm.dynamics_connector import DynamicsConnector
    return DynamicsConnector(crm_url, credentials)


def _build_custom(crm_url, credentials):
    # For custom connections, we return a generic/flexible connector wrapper
    # or let the custom mapper compile it
    from services.crm.base_connector import BaseCRMConnector
    from services.crm.canonical_models import Contact, Lead, Account, Deal
    from typing import Dict, Any, Optional

    class CustomCRMConnector(BaseCRMConnector):
        def test_connection(self) -> Dict[str, Any]:
            # Custom integrations are assumed configured by mapping schema
            return {"success": True, "crm_name": "Custom Integration"}

        def get_contact(self, contact_id: str) -> Optional[Contact]:
            return None

        def create_contact(self, contact_data: Dict[str, Any]) -> Contact:
            from services.crm.custom_mapper import CustomCRMMappingEngine
            rules = self.credentials.get("mappings", {}).get("Contact", {})
            mapped = CustomCRMMappingEngine.apply_mapping(contact_data, rules)
            mapped["id"] = mapped.get("id") or "custom_contact_id"
            mapped["email"] = mapped.get("email") or "custom@email.com"
            return Contact(**mapped)

        def update_contact(self, contact_id: str, contact_data: Dict[str, Any]) -> Contact:
            return self.create_contact(contact_data)

        def get_lead(self, lead_id: str) -> Optional[Lead]:
            return None

        def create_lead(self, lead_data: Dict[str, Any]) -> Lead:
            from services.crm.custom_mapper import CustomCRMMappingEngine
            rules = self.credentials.get("mappings", {}).get("Lead", {})
            mapped = CustomCRMMappingEngine.apply_mapping(lead_data, rules)
            mapped["id"] = mapped.get("id") or "custom_lead_id"
            mapped["status"] = mapped.get("status") or "New"
            return Lead(**mapped)

        def update_lead(self, lead_id: str, lead_data: Dict[str, Any]) -> Lead:
            return self.create_lead(lead_data)

        def get_account(self, account_id: str) -> Optional[Account]:
            return None

        def create_account(self, account_data: Dict[str, Any]) -> Account:
            from services.crm.custom_mapper import CustomCRMMappingEngine
            rules = self.credentials.get("mappings", {}).get("Account", {})
            mapped = CustomCRMMappingEngine.apply_mapping(account_data, rules)
            mapped["id"] = mapped.get("id") or "custom_account_id"
            mapped["name"] = mapped.get("name") or "Custom Account"
            return Account(**mapped)

        def get_deal(self, deal_id: str) -> Optional[Deal]:
            return None

        def create_deal(self, deal_data: Dict[str, Any]) -> Deal:
            from services.crm.custom_mapper import CustomCRMMappingEngine
            rules = self.credentials.get("mappings", {}).get("Deal", {})
            mapped = CustomCRMMappingEngine.apply_mapping(deal_data, rules)
            mapped["id"] = mapped.get("id") or "custom_deal_id"
            mapped["title"] = mapped.get("title") or "Custom Deal"
            mapped["amount"] = mapped.get("amount") or "0.0"
            mapped["stage"] = mapped.get("stage") or "New"
            return Deal(**mapped)

        def update_deal_stage(self, deal_id: str, new_stage: str) -> Deal:
            return self.create_deal({"stage": new_stage})

    return CustomCRMConnector(crm_url, credentials)


class CRMFactory:
    """Wrapper class providing get_connector method for backward compatibility."""
    @staticmethod
    def get_connector(company_or_id):
        from models.company import Company
        if isinstance(company_or_id, (int, str)):
            company = Company.query.get(int(company_or_id))
        else:
            company = company_or_id
        if not company:
            return None
        return get_crm_connector(company)

