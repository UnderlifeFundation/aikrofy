"""
HubSpot CRM Connector.
"""
from typing import Dict, Any, Optional
from services.crm.base_connector import BaseCRMConnector, CRMAPIError
from services.crm.canonical_models import Contact, Lead, Account, Deal


class HubSpotConnector(BaseCRMConnector):
    """
    Adapter for HubSpot CRM.
    Uses HubSpot v3 API.
    """

    def __init__(self, crm_url: Optional[str], credentials: Dict[str, Any]):
        # HubSpot doesn't require crm_url as it's a fixed SaaS API, but we support default
        url = crm_url or "https://api.hubapi.com"
        super().__init__(url, credentials)
        self.access_token = credentials.get("access_token")

    def _get_headers(self) -> Dict[str, str]:
        if not self.access_token:
            raise ValueError("HubSpot access token is missing")
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

    def test_connection(self) -> Dict[str, Any]:
        """Test authentication using a lightweight API call to fetch contacts."""
        url = f"{self.crm_url}/crm/v3/objects/contacts?limit=1"
        try:
            resp = self._safe_request("GET", url, headers=self._get_headers())
            if resp.status_code == 200:
                return {"success": True, "crm_name": "HubSpot CRM"}
            return {"success": False, "error": f"HTTP {resp.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ------------------------------------------------------------------
    # Contact Management
    # ------------------------------------------------------------------

    def get_contact(self, contact_id: str) -> Optional[Contact]:
        url = f"{self.crm_url}/crm/v3/objects/contacts/{contact_id}?properties=firstname,lastname,email,phone,associatedcompanyid"
        try:
            resp = self._safe_request("GET", url, headers=self._get_headers())
            data = resp.json()
            props = data.get("properties", {})
            return Contact(
                id=data["id"],
                first_name=props.get("firstname"),
                last_name=props.get("lastname"),
                email=props.get("email") or "",
                phone=props.get("phone"),
                account_id=props.get("associatedcompanyid"),
                custom_fields=props
            )
        except CRMAPIError as e:
            if e.status_code == 404:
                return None
            raise e

    def create_contact(self, contact_data: Dict[str, Any]) -> Contact:
        url = f"{self.crm_url}/crm/v3/objects/contacts"
        payload = {
            "properties": {
                "firstname": contact_data.get("first_name"),
                "lastname": contact_data.get("last_name"),
                "email": contact_data.get("email"),
                "phone": contact_data.get("phone")
            }
        }
        resp = self._safe_request("POST", url, headers=self._get_headers(), json=payload)
        data = resp.json()
        props = data.get("properties", {})
        return Contact(
            id=data["id"],
            first_name=props.get("firstname"),
            last_name=props.get("lastname"),
            email=props.get("email") or "",
            phone=props.get("phone"),
            account_id=props.get("associatedcompanyid"),
            custom_fields=props
        )

    def update_contact(self, contact_id: str, contact_data: Dict[str, Any]) -> Contact:
        url = f"{self.crm_url}/crm/v3/objects/contacts/{contact_id}"
        properties = {}
        if "first_name" in contact_data:
            properties["firstname"] = contact_data["first_name"]
        if "last_name" in contact_data:
            properties["lastname"] = contact_data["last_name"]
        if "email" in contact_data:
            properties["email"] = contact_data["email"]
        if "phone" in contact_data:
            properties["phone"] = contact_data["phone"]

        payload = {"properties": properties}
        resp = self._safe_request("PATCH", url, headers=self._get_headers(), json=payload)
        data = resp.json()
        props = data.get("properties", {})
        return Contact(
            id=data["id"],
            first_name=props.get("firstname"),
            last_name=props.get("lastname"),
            email=props.get("email") or "",
            phone=props.get("phone"),
            account_id=props.get("associatedcompanyid"),
            custom_fields=props
        )

    # ------------------------------------------------------------------
    # Lead Management
    # ------------------------------------------------------------------

    def get_lead(self, lead_id: str) -> Optional[Lead]:
        # HubSpot does not have a separate 'Lead' object natively in v3 standard;
        # leads are generally Contacts with lifecyclestage = 'lead' or 'prospect'.
        url = f"{self.crm_url}/crm/v3/objects/contacts/{lead_id}?properties=firstname,lastname,email,phone,hs_lead_status,lifecyclestage"
        try:
            resp = self._safe_request("GET", url, headers=self._get_headers())
            data = resp.json()
            props = data.get("properties", {})
            return Lead(
                id=data["id"],
                full_name=f"{props.get('firstname', '')} {props.get('lastname', '')}".strip(),
                email=props.get("email"),
                source=props.get("hs_analytics_source"),
                status=props.get("hs_lead_status") or props.get("lifecyclestage") or "new",
                estimated_value=None,
                custom_fields=props
            )
        except CRMAPIError as e:
            if e.status_code == 404:
                return None
            raise e

    def create_lead(self, lead_data: Dict[str, Any]) -> Lead:
        url = f"{self.crm_url}/crm/v3/objects/contacts"
        names = (lead_data.get("full_name") or "").split(" ", 1)
        firstname = names[0] if names else ""
        lastname = names[1] if len(names) > 1 else ""

        payload = {
            "properties": {
                "firstname": firstname,
                "lastname": lastname,
                "email": lead_data.get("email"),
                "hs_lead_status": lead_data.get("status", "NEW"),
                "lifecyclestage": "lead"
            }
        }
        resp = self._safe_request("POST", url, headers=self._get_headers(), json=payload)
        data = resp.json()
        props = data.get("properties", {})
        return Lead(
            id=data["id"],
            full_name=f"{props.get('firstname', '')} {props.get('lastname', '')}".strip(),
            email=props.get("email"),
            source=props.get("hs_analytics_source"),
            status=props.get("hs_lead_status") or props.get("lifecyclestage") or "new",
            estimated_value=None,
            custom_fields=props
        )

    def update_lead(self, lead_id: str, lead_data: Dict[str, Any]) -> Lead:
        url = f"{self.crm_url}/crm/v3/objects/contacts/{lead_id}"
        properties = {}
        if "status" in lead_data:
            properties["hs_lead_status"] = lead_data["status"]
        if "full_name" in lead_data:
            names = (lead_data["full_name"] or "").split(" ", 1)
            properties["firstname"] = names[0] if names else ""
            properties["lastname"] = names[1] if len(names) > 1 else ""

        payload = {"properties": properties}
        resp = self._safe_request("PATCH", url, headers=self._get_headers(), json=payload)
        data = resp.json()
        props = data.get("properties", {})
        return Lead(
            id=data["id"],
            full_name=f"{props.get('firstname', '')} {props.get('lastname', '')}".strip(),
            email=props.get("email"),
            source=props.get("hs_analytics_source"),
            status=props.get("hs_lead_status") or props.get("lifecyclestage") or "new",
            estimated_value=None,
            custom_fields=props
        )

    # ------------------------------------------------------------------
    # Account Management
    # ------------------------------------------------------------------

    def get_account(self, account_id: str) -> Optional[Account]:
        url = f"{self.crm_url}/crm/v3/objects/companies/{account_id}?properties=name,domain,annualrevenue,industry"
        try:
            resp = self._safe_request("GET", url, headers=self._get_headers())
            data = resp.json()
            props = data.get("properties", {})
            return Account(
                id=data["id"],
                name=props.get("name") or "",
                domain=props.get("domain"),
                annual_revenue=props.get("annualrevenue"),
                industry=props.get("industry")
            )
        except CRMAPIError as e:
            if e.status_code == 404:
                return None
            raise e

    def create_account(self, account_data: Dict[str, Any]) -> Account:
        url = f"{self.crm_url}/crm/v3/objects/companies"
        payload = {
            "properties": {
                "name": account_data.get("name"),
                "domain": account_data.get("domain"),
                "annualrevenue": str(account_data.get("annual_revenue") or ""),
                "industry": account_data.get("industry")
            }
        }
        resp = self._safe_request("POST", url, headers=self._get_headers(), json=payload)
        data = resp.json()
        props = data.get("properties", {})
        return Account(
            id=data["id"],
            name=props.get("name") or "",
            domain=props.get("domain"),
            annual_revenue=props.get("annualrevenue"),
            industry=props.get("industry")
        )

    # ------------------------------------------------------------------
    # Deal / Opportunity Management
    # ------------------------------------------------------------------

    def get_deal(self, deal_id: str) -> Optional[Deal]:
        url = f"{self.crm_url}/crm/v3/objects/deals/{deal_id}?properties=dealname,amount,dealstage,pipeline"
        try:
            resp = self._safe_request("GET", url, headers=self._get_headers())
            data = resp.json()
            props = data.get("properties", {})
            return Deal(
                id=data["id"],
                title=props.get("dealname") or "",
                amount=props.get("amount") or "0.0",
                stage=props.get("dealstage") or "",
                custom_fields=props
            )
        except CRMAPIError as e:
            if e.status_code == 404:
                return None
            raise e

    def create_deal(self, deal_data: Dict[str, Any]) -> Deal:
        url = f"{self.crm_url}/crm/v3/objects/deals"
        payload = {
            "properties": {
                "dealname": deal_data.get("title"),
                "amount": str(deal_data.get("amount", "0.0")),
                "dealstage": deal_data.get("stage", "appointmentscheduled")
            }
        }
        resp = self._safe_request("POST", url, headers=self._get_headers(), json=payload)
        data = resp.json()
        props = data.get("properties", {})
        return Deal(
            id=data["id"],
            title=props.get("dealname") or "",
            amount=props.get("amount") or "0.0",
            stage=props.get("dealstage") or "",
            custom_fields=props
        )

    def update_deal_stage(self, deal_id: str, new_stage: str) -> Deal:
        url = f"{self.crm_url}/crm/v3/objects/deals/{deal_id}"
        payload = {
            "properties": {
                "dealstage": new_stage
            }
        }
        resp = self._safe_request("PATCH", url, headers=self._get_headers(), json=payload)
        data = resp.json()
        props = data.get("properties", {})
        return Deal(
            id=data["id"],
            title=props.get("dealname") or "",
            amount=props.get("amount") or "0.0",
            stage=props.get("dealstage") or "",
            custom_fields=props
        )

    # ------------------------------------------------------------------
    # Conversations Inbox & Custom Channels (2026-03 API)
    # ------------------------------------------------------------------

    def create_visitor_token(self, email: str, first_name: str = None, last_name: str = None) -> Dict[str, Any]:
        """
        Generate a visitor identification token for the web chat widget.
        API: POST /visitor-identification/2026-03/tokens/create
        """
        url = f"{self.crm_url}/visitor-identification/2026-03/tokens/create"
        payload = {
            "email": email,
            "firstName": first_name or "",
            "lastName": last_name or "",
            "hsCustomerAgentContext": {}
        }
        resp = self._safe_request("POST", url, headers=self._get_headers(), json=payload)
        return resp.json()

    def publish_custom_channel_message(
        self,
        channel_id: str,
        thread_id: str,
        message_text: str,
        sender_identifier: str,
        sender_name: str,
        is_whatsapp: bool = True,
        direction: str = "INCOMING",
        idempotency_id: str = None
    ) -> Dict[str, Any]:
        """
        Publish a WhatsApp or Telegram message to a registered HubSpot custom channel.
        API: POST /conversations/2026-03/custom-channels/{channelId}/messages
        """
        url = f"{self.crm_url}/conversations/2026-03/custom-channels/{channel_id}/messages"
        sender_type = "HS_PHONE_NUMBER" if is_whatsapp else "CHANNEL_SPECIFIC_OPAQUE_ID"
        recipient_type = "CHANNEL_SPECIFIC_OPAQUE_ID"

        # Import datetime locally to avoid namespace issue if not imported at top
        from datetime import datetime

        payload = {
            "text": message_text,
            "channelAccountId": "default_account_pym",
            "messageDirection": direction,
            "integrationThreadId": thread_id,
            "senders": [
                {
                    "deliveryIdentifier": {
                        "type": sender_type,
                        "value": sender_identifier
                    },
                    "name": sender_name or "Usuario"
                }
            ],
            "recipients": [
                {
                    "deliveryIdentifier": {
                        "type": recipient_type,
                        "value": "pym_system_receiver"
                    }
                }
            ],
            "timestamp": datetime.utcnow().isoformat() + "Z" if direction == "INCOMING" else None
        }

        if idempotency_id:
            payload["integrationIdempotencyId"] = idempotency_id

        resp = self._safe_request("POST", url, headers=self._get_headers(), json=payload)
        return resp.json()

