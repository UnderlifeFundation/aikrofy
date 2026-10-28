"""
Salesforce CRM Connector.
"""
from typing import Dict, Any, Optional
import logging
from services.crm.base_connector import BaseCRMConnector, CRMAPIError
from services.crm.canonical_models import Contact, Lead, Account, Deal

logger = logging.getLogger(__name__)


class SalesforceConnector(BaseCRMConnector):
    """
    Adapter for Salesforce CRM.
    Uses Salesforce REST API & SOQL.
    """

    def __init__(self, crm_url: Optional[str], credentials: Dict[str, Any]):
        # Salesforce requires instance_url or custom domain
        url = crm_url or credentials.get("instance_url") or "https://login.salesforce.com"
        super().__init__(url, credentials)
        self.access_token = credentials.get("access_token")
        self.client_id = credentials.get("client_id")
        self.client_secret = credentials.get("client_secret")
        self.refresh_token = credentials.get("refresh_token")

    def _refresh_access_token(self):
        """Refresh OAuth 2.0 access token."""
        if not self.refresh_token or not self.client_id or not self.client_secret:
            raise ValueError("Salesforce client credentials or refresh token missing")
        
        # Use login.salesforce.com or test.salesforce.com depending on sandbox or prod
        auth_url = "https://login.salesforce.com/services/oauth2/token"
        payload = {
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token
        }
        import requests
        resp = requests.post(auth_url, data=payload, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        self.access_token = data.get("access_token")
        # Update credentials local store
        self.credentials["access_token"] = self.access_token

    def _get_headers(self) -> Dict[str, str]:
        if not self.access_token:
            self._refresh_access_token()
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

    def _check_limit_headers(self, headers: Dict[str, Any]):
        """Logs Salesforce API limit info from HTTP headers."""
        limit_info = headers.get("Sforce-Limit-Info")
        if limit_info:
            logger.info(f"Salesforce API Limit Info: {limit_info}")

    def test_connection(self) -> Dict[str, Any]:
        """Test connection using a lightweight API query call."""
        url = f"{self.crm_url}/services/data/v57.0/query/?q=SELECT+Id+FROM+Contact+LIMIT+1"
        try:
            resp = self._safe_request("GET", url, headers=self._get_headers())
            self._check_limit_headers(resp.headers)
            if resp.status_code == 200:
                return {"success": True, "crm_name": "Salesforce CRM"}
            return {"success": False, "error": f"HTTP {resp.status_code}"}
        except Exception as e:
            # Try to refresh token and retry once
            try:
                self._refresh_access_token()
                resp = self._safe_request("GET", url, headers=self._get_headers())
                if resp.status_code == 200:
                    return {"success": True, "crm_name": "Salesforce CRM"}
            except Exception as inner_e:
                return {"success": False, "error": f"{str(e)} -> Token refresh error: {str(inner_e)}"}
            return {"success": False, "error": str(e)}

    # ------------------------------------------------------------------
    # Contact Management
    # ------------------------------------------------------------------

    def get_contact(self, contact_id: str) -> Optional[Contact]:
        url = f"{self.crm_url}/services/data/v57.0/sobjects/Contact/{contact_id}"
        try:
            resp = self._safe_request("GET", url, headers=self._get_headers())
            self._check_limit_headers(resp.headers)
            data = resp.json()
            return Contact(
                id=data["Id"],
                first_name=data.get("FirstName"),
                last_name=data.get("LastName"),
                email=data.get("Email") or "",
                phone=data.get("Phone"),
                account_id=data.get("AccountId"),
                custom_fields=data
            )
        except CRMAPIError as e:
            if e.status_code == 404:
                return None
            raise e

    def create_contact(self, contact_data: Dict[str, Any]) -> Contact:
        url = f"{self.crm_url}/services/data/v57.0/sobjects/Contact/"
        payload = {
            "FirstName": contact_data.get("first_name"),
            "LastName": contact_data.get("last_name") or "Unknown",
            "Email": contact_data.get("email"),
            "Phone": contact_data.get("phone")
        }
        resp = self._safe_request("POST", url, headers=self._get_headers(), json=payload)
        self._check_limit_headers(resp.headers)
        data = resp.json()
        return self.get_contact(data["id"])

    def update_contact(self, contact_id: str, contact_data: Dict[str, Any]) -> Contact:
        url = f"{self.crm_url}/services/data/v57.0/sobjects/Contact/{contact_id}"
        payload = {}
        if "first_name" in contact_data:
            payload["FirstName"] = contact_data["first_name"]
        if "last_name" in contact_data:
            payload["LastName"] = contact_data["last_name"]
        if "email" in contact_data:
            payload["Email"] = contact_data["email"]
        if "phone" in contact_data:
            payload["Phone"] = contact_data["phone"]

        resp = self._safe_request("PATCH", url, headers=self._get_headers(), json=payload)
        self._check_limit_headers(resp.headers)
        return self.get_contact(contact_id)

    # ------------------------------------------------------------------
    # Lead Management
    # ------------------------------------------------------------------

    def get_lead(self, lead_id: str) -> Optional[Lead]:
        url = f"{self.crm_url}/services/data/v57.0/sobjects/Lead/{lead_id}"
        try:
            resp = self._safe_request("GET", url, headers=self._get_headers())
            self._check_limit_headers(resp.headers)
            data = resp.json()
            return Lead(
                id=data["Id"],
                full_name=data.get("Name") or f"{data.get('FirstName', '')} {data.get('LastName', '')}".strip(),
                email=data.get("Email"),
                source=data.get("LeadSource"),
                status=data.get("Status") or "New",
                estimated_value=data.get("AnnualRevenue"),
                custom_fields=data
            )
        except CRMAPIError as e:
            if e.status_code == 404:
                return None
            raise e

    def create_lead(self, lead_data: Dict[str, Any]) -> Lead:
        url = f"{self.crm_url}/services/data/v57.0/sobjects/Lead/"
        names = (lead_data.get("full_name") or "").split(" ", 1)
        firstname = names[0] if names else ""
        lastname = names[1] if len(names) > 1 else "Unknown"

        payload = {
            "FirstName": firstname,
            "LastName": lastname,
            "Company": lead_data.get("company_name") or "Self-Employed",
            "Email": lead_data.get("email"),
            "Status": lead_data.get("status") or "Open - Not Contacted"
        }
        resp = self._safe_request("POST", url, headers=self._get_headers(), json=payload)
        self._check_limit_headers(resp.headers)
        data = resp.json()
        return self.get_lead(data["id"])

    def update_lead(self, lead_id: str, lead_data: Dict[str, Any]) -> Lead:
        url = f"{self.crm_url}/services/data/v57.0/sobjects/Lead/{lead_id}"
        payload = {}
        if "status" in lead_data:
            payload["Status"] = lead_data["status"]
        if "full_name" in lead_data:
            names = (lead_data["full_name"] or "").split(" ", 1)
            payload["FirstName"] = names[0] if names else ""
            payload["LastName"] = names[1] if len(names) > 1 else "Unknown"

        resp = self._safe_request("PATCH", url, headers=self._get_headers(), json=payload)
        self._check_limit_headers(resp.headers)
        return self.get_lead(lead_id)

    # ------------------------------------------------------------------
    # Account Management
    # ------------------------------------------------------------------

    def get_account(self, account_id: str) -> Optional[Account]:
        url = f"{self.crm_url}/services/data/v57.0/sobjects/Account/{account_id}"
        try:
            resp = self._safe_request("GET", url, headers=self._get_headers())
            self._check_limit_headers(resp.headers)
            data = resp.json()
            return Account(
                id=data["Id"],
                name=data.get("Name") or "",
                domain=data.get("Website"),
                annual_revenue=data.get("AnnualRevenue"),
                industry=data.get("Industry")
            )
        except CRMAPIError as e:
            if e.status_code == 404:
                return None
            raise e

    def create_account(self, account_data: Dict[str, Any]) -> Account:
        url = f"{self.crm_url}/services/data/v57.0/sobjects/Account/"
        payload = {
            "Name": account_data.get("name"),
            "Website": account_data.get("domain"),
            "AnnualRevenue": str(account_data.get("annual_revenue") or ""),
            "Industry": account_data.get("industry")
        }
        resp = self._safe_request("POST", url, headers=self._get_headers(), json=payload)
        self._check_limit_headers(resp.headers)
        data = resp.json()
        return self.get_account(data["id"])

    # ------------------------------------------------------------------
    # Deal / Opportunity Management
    # ------------------------------------------------------------------

    def get_deal(self, deal_id: str) -> Optional[Deal]:
        url = f"{self.crm_url}/services/data/v57.0/sobjects/Opportunity/{deal_id}"
        try:
            resp = self._safe_request("GET", url, headers=self._get_headers())
            self._check_limit_headers(resp.headers)
            data = resp.json()
            return Deal(
                id=data["Id"],
                title=data.get("Name") or "",
                amount=data.get("Amount") or "0.0",
                stage=data.get("StageName") or "",
                custom_fields=data
            )
        except CRMAPIError as e:
            if e.status_code == 404:
                return None
            raise e

    def create_deal(self, deal_data: Dict[str, Any]) -> Deal:
        url = f"{self.crm_url}/services/data/v57.0/sobjects/Opportunity/"
        payload = {
            "Name": deal_data.get("title"),
            "Amount": str(deal_data.get("amount", "0.0")),
            "StageName": deal_data.get("stage", "Prospecting"),
            "CloseDate": deal_data.get("expected_closing_date") or "2026-12-31"
        }
        resp = self._safe_request("POST", url, headers=self._get_headers(), json=payload)
        self._check_limit_headers(resp.headers)
        data = resp.json()
        return self.get_deal(data["id"])

    def update_deal_stage(self, deal_id: str, new_stage: str) -> Deal:
        url = f"{self.crm_url}/services/data/v57.0/sobjects/Opportunity/{deal_id}"
        payload = {
            "StageName": new_stage
        }
        resp = self._safe_request("PATCH", url, headers=self._get_headers(), json=payload)
        self._check_limit_headers(resp.headers)
        return self.get_deal(deal_id)
