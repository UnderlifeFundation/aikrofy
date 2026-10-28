"""
Pipedrive CRM Connector.
"""
from typing import Dict, Any, Optional
from services.crm.base_connector import BaseCRMConnector, CRMAPIError
from services.crm.canonical_models import Contact, Lead, Account, Deal


class PipedriveConnector(BaseCRMConnector):
    """
    Adapter for Pipedrive CRM.
    """

    def __init__(self, crm_url: Optional[str], credentials: Dict[str, Any]):
        url = crm_url or "https://api.pipedrive.com/v1"
        super().__init__(url, credentials)
        self.api_token = credentials.get("api_token")
        self.access_token = credentials.get("access_token")

    def _get_url(self, path: str) -> str:
        if self.api_token:
            # Query parameter authentication
            sep = "&" if "?" in path else "?"
            return f"{self.crm_url}{path}{sep}api_token={self.api_token}"
        return f"{self.crm_url}{path}"

    def _get_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.access_token and not self.api_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers

    def test_connection(self) -> Dict[str, Any]:
        """Test authentication by requesting user info."""
        url = self._get_url("/users/me")
        try:
            resp = self._safe_request("GET", url, headers=self._get_headers())
            if resp.status_code == 200:
                return {"success": True, "crm_name": "Pipedrive CRM"}
            return {"success": False, "error": f"HTTP {resp.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ------------------------------------------------------------------
    # Contact Management (Persons in Pipedrive)
    # ------------------------------------------------------------------

    def get_contact(self, contact_id: str) -> Optional[Contact]:
        url = self._get_url(f"/persons/{contact_id}")
        try:
            resp = self._safe_request("GET", url, headers=self._get_headers())
            data = resp.json().get("data", {})
            if not data:
                return None
            
            # Pipedrive phone and email are arrays of dicts
            email_val = ""
            emails = data.get("email", [])
            if isinstance(emails, list) and emails:
                email_val = emails[0].get("value", "")

            phone_val = ""
            phones = data.get("phone", [])
            if isinstance(phones, list) and phones:
                phone_val = phones[0].get("value", "")

            org_id = ""
            org_obj = data.get("org_id")
            if isinstance(org_obj, dict):
                org_id = str(org_obj.get("value", ""))
            elif org_obj:
                org_id = str(org_obj)

            return Contact(
                id=str(data["id"]),
                first_name=data.get("first_name"),
                last_name=data.get("last_name"),
                email=email_val or "no-email@pipedrive.com",
                phone=phone_val,
                account_id=org_id,
                custom_fields=data
            )
        except CRMAPIError as e:
            if e.status_code == 404:
                return None
            raise e

    def create_contact(self, contact_data: Dict[str, Any]) -> Contact:
        url = self._get_url("/persons")
        payload = {
            "name": f"{contact_data.get('first_name', '')} {contact_data.get('last_name', '')}".strip(),
            "email": contact_data.get("email"),
            "phone": contact_data.get("phone")
        }
        resp = self._safe_request("POST", url, headers=self._get_headers(), json=payload)
        data = resp.json().get("data", {})
        return self.get_contact(str(data["id"]))

    def update_contact(self, contact_id: str, contact_data: Dict[str, Any]) -> Contact:
        url = self._get_url(f"/persons/{contact_id}")
        payload = {}
        if "first_name" in contact_data or "last_name" in contact_data:
            payload["name"] = f"{contact_data.get('first_name', '')} {contact_data.get('last_name', '')}".strip()
        if "email" in contact_data:
            payload["email"] = contact_data["email"]
        if "phone" in contact_data:
            payload["phone"] = contact_data["phone"]

        self._safe_request("PUT", url, headers=self._get_headers(), json=payload)
        return self.get_contact(contact_id)

    # ------------------------------------------------------------------
    # Lead Management
    # ------------------------------------------------------------------

    def get_lead(self, lead_id: str) -> Optional[Lead]:
        url = self._get_url(f"/leads/{lead_id}")
        try:
            resp = self._safe_request("GET", url, headers=self._get_headers())
            data = resp.json().get("data", {})
            if not data:
                return None
            return Lead(
                id=data["id"],
                full_name=data.get("title"),
                email=None,
                source=None,
                status="lead",
                estimated_value=None,
                custom_fields=data
            )
        except CRMAPIError as e:
            if e.status_code == 404:
                return None
            raise e

    def create_lead(self, lead_data: Dict[str, Any]) -> Lead:
        url = self._get_url("/leads")
        payload = {
            "title": lead_data.get("full_name") or "New Lead",
            "person_id": lead_data.get("person_id")
        }
        resp = self._safe_request("POST", url, headers=self._get_headers(), json=payload)
        data = resp.json().get("data", {})
        return Lead(
            id=data["id"],
            full_name=data.get("title"),
            email=None,
            source=None,
            status="lead",
            estimated_value=None,
            custom_fields=data
        )

    def update_lead(self, lead_id: str, lead_data: Dict[str, Any]) -> Lead:
        url = self._get_url(f"/leads/{lead_id}")
        payload = {}
        if "full_name" in lead_data:
            payload["title"] = lead_data["full_name"]
        self._safe_request("PATCH", url, headers=self._get_headers(), json=payload)
        return self.get_lead(lead_id)

    # ------------------------------------------------------------------
    # Account Management (Organizations in Pipedrive)
    # ------------------------------------------------------------------

    def get_account(self, account_id: str) -> Optional[Account]:
        url = self._get_url(f"/organizations/{account_id}")
        try:
            resp = self._safe_request("GET", url, headers=self._get_headers())
            data = resp.json().get("data", {})
            if not data:
                return None
            return Account(
                id=str(data["id"]),
                name=data.get("name") or "",
                domain=None,
                annual_revenue=None,
                industry=None
            )
        except CRMAPIError as e:
            if e.status_code == 404:
                return None
            raise e

    def create_account(self, account_data: Dict[str, Any]) -> Account:
        url = self._get_url("/organizations")
        payload = {
            "name": account_data.get("name")
        }
        resp = self._safe_request("POST", url, headers=self._get_headers(), json=payload)
        data = resp.json().get("data", {})
        return self.get_account(str(data["id"]))

    # ------------------------------------------------------------------
    # Deal / Opportunity Management
    # ------------------------------------------------------------------

    def get_deal(self, deal_id: str) -> Optional[Deal]:
        url = self._get_url(f"/deals/{deal_id}")
        try:
            resp = self._safe_request("GET", url, headers=self._get_headers())
            data = resp.json().get("data", {})
            if not data:
                return None
            return Deal(
                id=str(data["id"]),
                title=data.get("title") or "",
                amount=data.get("value") or "0.0",
                stage=str(data.get("stage_id") or ""),
                custom_fields=data
            )
        except CRMAPIError as e:
            if e.status_code == 404:
                return None
            raise e

    def create_deal(self, deal_data: Dict[str, Any]) -> Deal:
        url = self._get_url("/deals")
        payload = {
            "title": deal_data.get("title"),
            "value": str(deal_data.get("amount", "0.0")),
            "stage_id": deal_data.get("stage")
        }
        resp = self._safe_request("POST", url, headers=self._get_headers(), json=payload)
        data = resp.json().get("data", {})
        return self.get_deal(str(data["id"]))

    def update_deal_stage(self, deal_id: str, new_stage: str) -> Deal:
        url = self._get_url(f"/deals/{deal_id}")
        # Pipedrive stage_id is strictly an integer — convert or raise early
        try:
            stage_id = int(new_stage)
        except (ValueError, TypeError):
            raise ValueError(
                f"Pipedrive stage_id must be an integer, received: {new_stage!r}. "
                "Pass the numeric stage ID from your Pipedrive pipeline settings."
            )
        payload = {"stage_id": stage_id}
        self._safe_request("PUT", url, headers=self._get_headers(), json=payload)
        return self.get_deal(deal_id)
