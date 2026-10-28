"""
Zoho CRM Connector.
"""
from typing import Dict, Any, Optional
from services.crm.base_connector import BaseCRMConnector, CRMAPIError
from services.crm.canonical_models import Contact, Lead, Account, Deal


class ZohoCRMConnector(BaseCRMConnector):
    """
    Adapter for Zoho CRM.
    Supports regional API endpoint domains.
    """

    def __init__(self, crm_url: Optional[str], credentials: Dict[str, Any]):
        # Zoho endpoints differ by region: .com, .eu, .in, etc.
        region = credentials.get("region", ".com")
        url = crm_url or f"https://www.zohoapis{region}/crm/v3"
        super().__init__(url, credentials)
        self.access_token = credentials.get("access_token")

    def _get_headers(self) -> Dict[str, str]:
        if not self.access_token:
            raise ValueError("Zoho access token missing")
        return {
            "Authorization": f"Zoho-oauthtoken {self.access_token}",
            "Content-Type": "application/json"
        }

    def test_connection(self) -> Dict[str, Any]:
        """Test connection via lightweight users lookup endpoint."""
        url = f"{self.crm_url}/users?type=ActiveUsers"
        try:
            resp = self._safe_request("GET", url, headers=self._get_headers())
            if resp.status_code == 200:
                return {"success": True, "crm_name": "Zoho CRM"}
            return {"success": False, "error": f"HTTP {resp.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ------------------------------------------------------------------
    # Contact Management
    # ------------------------------------------------------------------

    def get_contact(self, contact_id: str) -> Optional[Contact]:
        url = f"{self.crm_url}/Contacts/{contact_id}"
        try:
            resp = self._safe_request("GET", url, headers=self._get_headers())
            res_data = resp.json().get("data", [])
            if not res_data:
                return None
            data = res_data[0]
            return Contact(
                id=data["id"],
                first_name=data.get("First_Name"),
                last_name=data.get("Last_Name"),
                email=data.get("Email") or "",
                phone=data.get("Phone"),
                account_id=data.get("Account_Name", {}).get("id") if data.get("Account_Name") else None,
                custom_fields=data
            )
        except CRMAPIError as e:
            if e.status_code in (404, 204):
                return None
            raise e

    def create_contact(self, contact_data: Dict[str, Any]) -> Contact:
        url = f"{self.crm_url}/Contacts"
        payload = {
            "data": [{
                "First_Name": contact_data.get("first_name"),
                "Last_Name": contact_data.get("last_name") or "Unknown",
                "Email": contact_data.get("email"),
                "Phone": contact_data.get("phone")
            }]
        }
        resp = self._safe_request("POST", url, headers=self._get_headers(), json=payload)
        res_data = resp.json().get("data", [])
        return self.get_contact(res_data[0]["details"]["id"])

    def update_contact(self, contact_id: str, contact_data: Dict[str, Any]) -> Contact:
        url = f"{self.crm_url}/Contacts/{contact_id}"
        properties = {}
        if "first_name" in contact_data:
            properties["First_Name"] = contact_data["first_name"]
        if "last_name" in contact_data:
            properties["Last_Name"] = contact_data["last_name"]
        if "email" in contact_data:
            properties["Email"] = contact_data["email"]
        if "phone" in contact_data:
            properties["Phone"] = contact_data["phone"]

        payload = {"data": [properties]}
        self._safe_request("PUT", url, headers=self._get_headers(), json=payload)
        return self.get_contact(contact_id)

    # ------------------------------------------------------------------
    # Lead Management
    # ------------------------------------------------------------------

    def get_lead(self, lead_id: str) -> Optional[Lead]:
        url = f"{self.crm_url}/Leads/{lead_id}"
        try:
            resp = self._safe_request("GET", url, headers=self._get_headers())
            res_data = resp.json().get("data", [])
            if not res_data:
                return None
            data = res_data[0]
            return Lead(
                id=data["id"],
                full_name=data.get("Full_Name") or f"{data.get('First_Name', '')} {data.get('Last_Name', '')}".strip(),
                email=data.get("Email"),
                source=data.get("Lead_Source"),
                status=data.get("Lead_Status") or "New",
                estimated_value=data.get("Annual_Revenue"),
                custom_fields=data
            )
        except CRMAPIError as e:
            if e.status_code in (404, 204):
                return None
            raise e

    def create_lead(self, lead_data: Dict[str, Any]) -> Lead:
        url = f"{self.crm_url}/Leads"
        names = (lead_data.get("full_name") or "").split(" ", 1)
        firstname = names[0] if names else ""
        lastname = names[1] if len(names) > 1 else "Unknown"

        payload = {
            "data": [{
                "First_Name": firstname,
                "Last_Name": lastname,
                "Company": lead_data.get("company_name") or "Self",
                "Email": lead_data.get("email"),
                "Lead_Status": lead_data.get("status") or "New"
            }]
        }
        resp = self._safe_request("POST", url, headers=self._get_headers(), json=payload)
        res_data = resp.json().get("data", [])
        return self.get_lead(res_data[0]["details"]["id"])

    def update_lead(self, lead_id: str, lead_data: Dict[str, Any]) -> Lead:
        url = f"{self.crm_url}/Leads/{lead_id}"
        properties = {}
        if "status" in lead_data:
            properties["Lead_Status"] = lead_data["status"]
        if "full_name" in lead_data:
            names = (lead_data["full_name"] or "").split(" ", 1)
            properties["First_Name"] = names[0] if names else ""
            properties["Last_Name"] = names[1] if len(names) > 1 else "Unknown"

        payload = {"data": [properties]}
        self._safe_request("PUT", url, headers=self._get_headers(), json=payload)
        return self.get_lead(lead_id)

    # ------------------------------------------------------------------
    # Account Management
    # ------------------------------------------------------------------

    def get_account(self, account_id: str) -> Optional[Account]:
        url = f"{self.crm_url}/Accounts/{account_id}"
        try:
            resp = self._safe_request("GET", url, headers=self._get_headers())
            res_data = resp.json().get("data", [])
            if not res_data:
                return None
            data = res_data[0]
            return Account(
                id=data["id"],
                name=data.get("Account_Name") or "",
                domain=data.get("Website"),
                annual_revenue=data.get("Annual_Revenue"),
                industry=data.get("Industry")
            )
        except CRMAPIError as e:
            if e.status_code in (404, 204):
                return None
            raise e

    def create_account(self, account_data: Dict[str, Any]) -> Account:
        url = f"{self.crm_url}/Accounts"
        payload = {
            "data": [{
                "Account_Name": account_data.get("name"),
                "Website": account_data.get("domain"),
                "Annual_Revenue": account_data.get("annual_revenue"),
                "Industry": account_data.get("industry")
            }]
        }
        resp = self._safe_request("POST", url, headers=self._get_headers(), json=payload)
        res_data = resp.json().get("data", [])
        return self.get_account(res_data[0]["details"]["id"])

    # ------------------------------------------------------------------
    # Deal / Opportunity Management
    # ------------------------------------------------------------------

    def get_deal(self, deal_id: str) -> Optional[Deal]:
        url = f"{self.crm_url}/Deals/{deal_id}"
        try:
            resp = self._safe_request("GET", url, headers=self._get_headers())
            res_data = resp.json().get("data", [])
            if not res_data:
                return None
            data = res_data[0]
            return Deal(
                id=data["id"],
                title=data.get("Deal_Name") or "",
                amount=data.get("Amount") or "0.0",
                stage=data.get("Stage") or "",
                custom_fields=data
            )
        except CRMAPIError as e:
            if e.status_code in (404, 204):
                return None
            raise e

    def create_deal(self, deal_data: Dict[str, Any]) -> Deal:
        url = f"{self.crm_url}/Deals"
        payload = {
            "data": [{
                "Deal_Name": deal_data.get("title"),
                "Amount": deal_data.get("amount"),
                "Stage": deal_data.get("stage") or "Qualification",
                "Closing_Date": deal_data.get("expected_closing_date") or "2026-12-31"
            }]
        }
        resp = self._safe_request("POST", url, headers=self._get_headers(), json=payload)
        res_data = resp.json().get("data", [])
        return self.get_deal(res_data[0]["details"]["id"])

    def update_deal_stage(self, deal_id: str, new_stage: str) -> Deal:
        url = f"{self.crm_url}/Deals/{deal_id}"
        payload = {
            "data": [{
                "Stage": new_stage
            }]
        }
        self._safe_request("PUT", url, headers=self._get_headers(), json=payload)
        return self.get_deal(deal_id)
