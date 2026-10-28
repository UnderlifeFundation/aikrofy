"""
Microsoft Dynamics 365 CRM Connector.
"""
from typing import Dict, Any, Optional
from services.crm.base_connector import BaseCRMConnector, CRMAPIError
from services.crm.canonical_models import Contact, Lead, Account, Deal


class DynamicsConnector(BaseCRMConnector):
    """
    Adapter for Microsoft Dynamics 365 Customer Engagement.
    Uses Web API (Dataverse OData v4).
    """

    def __init__(self, crm_url: Optional[str], credentials: Dict[str, Any]):
        # Dataverse Web API endpoint
        url = crm_url or credentials.get("environment_url") or "https://myorg.api.crm.dynamics.com"
        # Append Web API base suffix if missing
        if not url.endswith("/api/data/v9.2"):
            url = f"{url.rstrip('/')}/api/data/v9.2"
        super().__init__(url, credentials)
        self.access_token = credentials.get("access_token")

    def _get_headers(self) -> Dict[str, str]:
        if not self.access_token:
            raise ValueError("Microsoft Dynamics access token is missing")
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "OData-MaxVersion": "4.0",
            "OData-Version": "4.0",
            "Accept": "application/json"
        }

    def test_connection(self) -> Dict[str, Any]:
        """Test connection by requesting WhoAmI system function."""
        url = f"{self.crm_url}/WhoAmI"
        try:
            resp = self._safe_request("GET", url, headers=self._get_headers())
            if resp.status_code == 200:
                return {"success": True, "crm_name": "Microsoft Dynamics 365"}
            return {"success": False, "error": f"HTTP {resp.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ------------------------------------------------------------------
    # Contact Management
    # ------------------------------------------------------------------

    def get_contact(self, contact_id: str) -> Optional[Contact]:
        url = f"{self.crm_url}/contacts({contact_id})?$select=contactid,firstname,lastname,emailaddress1,telephone1,_parentcustomerid_value"
        try:
            resp = self._safe_request("GET", url, headers=self._get_headers())
            data = resp.json()
            return Contact(
                id=data["contactid"],
                first_name=data.get("firstname"),
                last_name=data.get("lastname"),
                email=data.get("emailaddress1") or "no-email@dynamics.com",
                phone=data.get("telephone1"),
                account_id=data.get("_parentcustomerid_value"),
                custom_fields=data
            )
        except CRMAPIError as e:
            if e.status_code == 404:
                return None
            raise e

    def create_contact(self, contact_data: Dict[str, Any]) -> Contact:
        url = f"{self.crm_url}/contacts"
        payload = {
            "firstname": contact_data.get("first_name"),
            "lastname": contact_data.get("last_name") or "Unknown",
            "emailaddress1": contact_data.get("email"),
            "telephone1": contact_data.get("phone")
        }
        resp = self._safe_request("POST", url, headers=self._get_headers(), json=payload)
        # OData v4 POST returns 204 No Content with OData-EntityId header
        entity_id = resp.headers.get("OData-EntityId", "")
        # Parse GUID out of OData-EntityId url, e.g. contacts(guid)
        import re
        match = re.search(r"\((.*?)\)", entity_id)
        guid = match.group(1) if match else ""
        return self.get_contact(guid)

    def update_contact(self, contact_id: str, contact_data: Dict[str, Any]) -> Contact:
        url = f"{self.crm_url}/contacts({contact_id})"
        payload = {}
        if "first_name" in contact_data:
            payload["firstname"] = contact_data["first_name"]
        if "last_name" in contact_data:
            payload["lastname"] = contact_data["last_name"]
        if "email" in contact_data:
            payload["emailaddress1"] = contact_data["email"]
        if "phone" in contact_data:
            payload["telephone1"] = contact_data["phone"]

        self._safe_request("PATCH", url, headers=self._get_headers(), json=payload)
        return self.get_contact(contact_id)

    # ------------------------------------------------------------------
    # Lead Management
    # ------------------------------------------------------------------

    def get_lead(self, lead_id: str) -> Optional[Lead]:
        url = f"{self.crm_url}/leads({lead_id})?$select=leadid,fullname,emailaddress1,subject,statuscode,estimatedvalue"
        try:
            resp = self._safe_request("GET", url, headers=self._get_headers())
            data = resp.json()
            return Lead(
                id=data["leadid"],
                full_name=data.get("fullname"),
                email=data.get("emailaddress1"),
                source=data.get("subject"),
                status=str(data.get("statuscode")),
                estimated_value=data.get("estimatedvalue"),
                custom_fields=data
            )
        except CRMAPIError as e:
            if e.status_code == 404:
                return None
            raise e

    def create_lead(self, lead_data: Dict[str, Any]) -> Lead:
        url = f"{self.crm_url}/leads"
        _full_name = (lead_data.get("full_name") or "")
        _name_parts = _full_name.split(" ", 1)
        payload = {
            "subject": lead_data.get("source") or "Web Chat Conversation Lead",
            "firstname": _name_parts[0] if _name_parts else "",
            "lastname": _name_parts[1] if len(_name_parts) > 1 else "Unknown",
            "emailaddress1": lead_data.get("email"),
            "estimatedvalue": lead_data.get("estimated_value")
        }
        resp = self._safe_request("POST", url, headers=self._get_headers(), json=payload)
        entity_id = resp.headers.get("OData-EntityId", "")
        import re
        match = re.search(r"\((.*?)\)", entity_id)
        guid = match.group(1) if match else ""
        return self.get_lead(guid)

    def update_lead(self, lead_id: str, lead_data: Dict[str, Any]) -> Lead:
        url = f"{self.crm_url}/leads({lead_id})"
        payload = {}
        if "status" in lead_data:
            # Dynamics uses integer statuscode values
            try:
                payload["statuscode"] = int(lead_data["status"])
            except (ValueError, TypeError):
                payload["statuscode"] = 1
        if "full_name" in lead_data:
            names = (lead_data["full_name"] or "").split(" ", 1)
            payload["firstname"] = names[0] if names else ""
            payload["lastname"] = names[1] if len(names) > 1 else "Unknown"

        self._safe_request("PATCH", url, headers=self._get_headers(), json=payload)
        return self.get_lead(lead_id)

    # ------------------------------------------------------------------
    # Account Management
    # ------------------------------------------------------------------

    def get_account(self, account_id: str) -> Optional[Account]:
        url = f"{self.crm_url}/accounts({account_id})?$select=accountid,name,websiteurl,revenue,industrycode"
        try:
            resp = self._safe_request("GET", url, headers=self._get_headers())
            data = resp.json()
            return Account(
                id=data["accountid"],
                name=data.get("name") or "",
                domain=data.get("websiteurl"),
                annual_revenue=data.get("revenue"),
                industry=str(data.get("industrycode"))
            )
        except CRMAPIError as e:
            if e.status_code == 404:
                return None
            raise e

    def create_account(self, account_data: Dict[str, Any]) -> Account:
        url = f"{self.crm_url}/accounts"
        payload = {
            "name": account_data.get("name"),
            "websiteurl": account_data.get("domain"),
            "revenue": account_data.get("annual_revenue"),
            "industrycode": int(account_data["industry"]) if isinstance(account_data.get("industry"), str) and account_data["industry"].isdigit() else None
        }
        resp = self._safe_request("POST", url, headers=self._get_headers(), json=payload)
        entity_id = resp.headers.get("OData-EntityId", "")
        import re
        match = re.search(r"\((.*?)\)", entity_id)
        guid = match.group(1) if match else ""
        return self.get_account(guid)

    # ------------------------------------------------------------------
    # Deal / Opportunity Management
    # ------------------------------------------------------------------

    def get_deal(self, deal_id: str) -> Optional[Deal]:
        url = f"{self.crm_url}/opportunities({deal_id})?$select=opportunityid,name,estimatedvalue,stepname"
        try:
            resp = self._safe_request("GET", url, headers=self._get_headers())
            data = resp.json()
            return Deal(
                id=data["opportunityid"],
                title=data.get("name") or "",
                amount=data.get("estimatedvalue") or "0.0",
                stage=data.get("stepname") or "",
                custom_fields=data
            )
        except CRMAPIError as e:
            if e.status_code == 404:
                return None
            raise e

    def create_deal(self, deal_data: Dict[str, Any]) -> Deal:
        url = f"{self.crm_url}/opportunities"
        payload = {
            "name": deal_data.get("title"),
            "estimatedvalue": deal_data.get("amount"),
            "stepname": deal_data.get("stage") or "Qualify"
        }
        resp = self._safe_request("POST", url, headers=self._get_headers(), json=payload)
        entity_id = resp.headers.get("OData-EntityId", "")
        import re
        match = re.search(r"\((.*?)\)", entity_id)
        guid = match.group(1) if match else ""
        return self.get_deal(guid)

    def update_deal_stage(self, deal_id: str, new_stage: str) -> Deal:
        url = f"{self.crm_url}/opportunities({deal_id})"
        payload = {
            "stepname": new_stage
        }
        self._safe_request("PATCH", url, headers=self._get_headers(), json=payload)
        return self.get_deal(deal_id)
