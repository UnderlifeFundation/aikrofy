"""
Canonical Models - Pydantic V2 schemas for normalized CRM data.

These models define the standard data structures that the PymAI agent layer
consumes, regardless of the CRM source. Each model uses AliasChoices to
automatically map divergent property names from HubSpot, Salesforce, Pipedrive,
Zoho, and Dynamics 365 into a unified schema.
"""
import decimal
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, AliasChoices


class Contact(BaseModel):
    """Normalized contact record."""
    id: str = Field(
        ..., 
        validation_alias=AliasChoices("id", "contact_id", "vid", "contactId"),
        description="Unique global ID provided by the CRM abstraction layer."
    )
    first_name: Optional[str] = Field(
        None, 
        validation_alias=AliasChoices("first_name", "firstname", "first_name", "firstName"),
        description="First name of the contact."
    )
    last_name: Optional[str] = Field(
        None, 
        validation_alias=AliasChoices("last_name", "lastname", "last_name", "lastName"),
        description="Last name of the contact."
    )
    email: str = Field(
        ..., 
        validation_alias=AliasChoices("email", "email_address", "emailAddress"),
        description="Email address of the contact."
    )
    phone: Optional[str] = Field(
        None, 
        validation_alias=AliasChoices("phone", "phoneNumber", "mobilephone", "phone_number"),
        description="Primary phone number in E.164 format."
    )
    account_id: Optional[str] = Field(
        None, 
        validation_alias=AliasChoices("account_id", "company_id", "associated_company_id", "accountId", "companyId"),
        description="ID of the company/account this contact belongs to."
    )
    custom_fields: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Tenant-specific custom fields and metadata."
    )


class Lead(BaseModel):
    """Normalized lead record."""
    id: str = Field(
        ..., 
        validation_alias=AliasChoices("id", "lead_id", "leadId"),
        description="Unique global ID of the lead."
    )
    full_name: Optional[str] = Field(
        None, 
        validation_alias=AliasChoices("full_name", "fullname", "name", "fullName"),
        description="Full name of the lead."
    )
    email: Optional[str] = Field(
        None, 
        validation_alias=AliasChoices("email", "email_address", "emailAddress"),
        description="Lead contact email."
    )
    source: Optional[str] = Field(
        None, 
        validation_alias=AliasChoices("source", "lead_source", "leadSource", "utm_source"),
        description="Marketing source or acquisition channel."
    )
    status: str = Field(
        ..., 
        validation_alias=AliasChoices("status", "lead_status", "leadStatus", "state"),
        description="Qualification stage of the lead in the pipeline."
    )
    estimated_value: Optional[float] = Field(
        None, 
        validation_alias=AliasChoices("estimated_value", "estimatedvalue", "amount", "budget", "estimatedValue"),
        description="Potential estimated value of the lead."
    )
    custom_fields: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Tenant-specific custom fields."
    )


class Account(BaseModel):
    """Normalized account/company record."""
    id: str = Field(
        ..., 
        validation_alias=AliasChoices("id", "account_id", "company_id", "companyId", "accountId"),
        description="Unique global ID of the account/company."
    )
    name: str = Field(
        ..., 
        validation_alias=AliasChoices("name", "company_name", "companyName"),
        description="Legal or commercial name of the account/company."
    )
    domain: Optional[str] = Field(
        None, 
        validation_alias=AliasChoices("domain", "website", "url"),
        description="Primary internet domain of the organization."
    )
    annual_revenue: Optional[decimal.Decimal] = Field(
        None, 
        validation_alias=AliasChoices("annual_revenue", "annualrevenue", "revenue"),
        description="Annual revenue formatted strictly as a decimal."
    )
    industry: Optional[str] = Field(
        None, 
        validation_alias=AliasChoices("industry", "sector"),
        description="Economic sector or business vertical."
    )
    associated_contacts: List[str] = Field(
        default_factory=list, 
        description="List of associated contact IDs."
    )
    custom_fields: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Tenant-specific custom fields."
    )


class Deal(BaseModel):
    """Normalized deal/opportunity record."""
    id: str = Field(
        ..., 
        validation_alias=AliasChoices("id", "deal_id", "opportunity_id", "dealId", "opportunityId"),
        description="Unique ID of the deal."
    )
    title: str = Field(
        ..., 
        validation_alias=AliasChoices("title", "deal_name", "name", "dealName"),
        description="Name or title of the sales opportunity."
    )
    account_id: Optional[str] = Field(
        None, 
        validation_alias=AliasChoices("account_id", "company_id", "companyId", "accountId"),
        description="Associated account/company ID."
    )
    stage: str = Field(
        ..., 
        validation_alias=AliasChoices("stage", "deal_stage", "dealStage", "pipeline_stage"),
        description="Stage in the sales pipeline."
    )
    amount: decimal.Decimal = Field(
        ..., 
        validation_alias=AliasChoices("amount", "value", "deal_value"),
        description="Financial value of the deal, strictly represented as Decimal."
    )
    probability: Optional[float] = Field(
        None, 
        validation_alias=AliasChoices("probability", "deal_probability", "stage_probability"),
        description="Estimated success probability (0.0 to 1.0)."
    )
    expected_closing_date: Optional[str] = Field(
        None, 
        validation_alias=AliasChoices("expected_closing_date", "closedate", "close_date", "expectedClosingDate"),
        description="Projected closing date in ISO 8601 (YYYY-MM-DD)."
    )
    custom_fields: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Tenant-specific custom fields."
    )
