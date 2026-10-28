"""
Canonical Models - Pydantic V2 schemas for normalized ERP data.

These models define the standard data structures that the PymAI agent layer
consumes, regardless of the ERP source. Each model uses AliasChoices to
automatically map divergent property names from SAP B1, NetSuite, Odoo,
and Dynamics 365 Business Central into a unified schema.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, AliasChoices


class CanonicalCustomer(BaseModel):
    """Normalized customer/business partner record."""
    customer_id: str = Field(
        validation_alias=AliasChoices("customer_id", "CardCode", "id", "partner_id", "customerId"),
        description="Unique identifier for the customer record"
    )
    name: str = Field(
        validation_alias=AliasChoices("name", "CardName", "companyname", "display_name", "displayName"),
        description="Customer's full name or company name"
    )
    email: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("email", "EmailAddress", "email", "email_address"),
        description="Customer's primary email address"
    )
    phone: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("phone", "Phone1", "phone", "phoneNumber"),
        description="Customer's primary phone number"
    )
    tax_id: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("tax_id", "FederalTaxID", "taxIdNum", "vat"),
        description="Tax identification number"
    )
    custom_fields: Dict[str, Any] = Field(
        default={},
        description="Supplementary passthrough fields from the native ERP"
    )


class CanonicalInvoiceLine(BaseModel):
    """Line item detail for invoice transactions."""
    item_code: str = Field(
        validation_alias=AliasChoices("item_code", "ItemCode", "item", "product_id"),
        description="Unique identification code of the item or product"
    )
    description: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("description", "ItemDescription", "description", "name"),
        description="Line item description"
    )
    quantity: float = Field(
        validation_alias=AliasChoices("quantity", "Quantity", "quantity", "qty"),
        description="Physical quantity of units in the transaction"
    )
    unit_price: float = Field(
        validation_alias=AliasChoices("unit_price", "UnitPrice", "rate", "price_unit"),
        description="Net unit price of the line"
    )
    total: Optional[float] = Field(
        default=None,
        validation_alias=AliasChoices("total", "LineTotal", "amount", "price_subtotal"),
        description="Line total amount"
    )


class CanonicalInvoice(BaseModel):
    """Normalized model for issued billing/invoice documents."""
    invoice_id: str = Field(
        validation_alias=AliasChoices("invoice_id", "DocEntry", "id", "id_invoice"),
        description="Primary key or identifier of the document"
    )
    document_number: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("document_number", "DocNum", "tranid", "number"),
        description="Human-readable document number"
    )
    customer_code: str = Field(
        validation_alias=AliasChoices("customer_code", "CardCode", "entity", "partner_id"),
        description="Association code with the customer"
    )
    customer_name: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("customer_name", "CardName", "companyname", "partner_name"),
        description="Customer name for display"
    )
    document_date: str = Field(
        validation_alias=AliasChoices("document_date", "DocDate", "trandate", "invoice_date"),
        description="Date of issuance of the transactional document"
    )
    due_date: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("due_date", "DocDueDate", "duedate", "invoice_date_due"),
        description="Payment due date"
    )
    total_amount: float = Field(
        validation_alias=AliasChoices("total_amount", "DocTotal", "total", "amount_total"),
        description="Gross total amount invoiced"
    )
    currency: Optional[str] = Field(
        default="USD",
        validation_alias=AliasChoices("currency", "DocCurrency", "currency", "currency_id"),
        description="Currency code of the document"
    )
    status: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("status", "DocumentStatus", "status", "state"),
        description="Current document status"
    )
    lines: List[CanonicalInvoiceLine] = Field(
        default=[],
        validation_alias=AliasChoices("lines", "DocumentLines", "item", "invoice_line_ids"),
        description="Collection of detail lines associated with the transaction"
    )
    custom_fields: Dict[str, Any] = Field(
        default={},
        description="User fields or supplementary passthrough data store"
    )


class CanonicalItem(BaseModel):
    """Normalized product/inventory item."""
    item_code: str = Field(
        validation_alias=AliasChoices("item_code", "ItemCode", "itemId", "default_code"),
        description="Unique item/product code"
    )
    name: str = Field(
        validation_alias=AliasChoices("name", "ItemName", "displayName", "name"),
        description="Item name"
    )
    price: Optional[float] = Field(
        default=None,
        validation_alias=AliasChoices("price", "Price", "basePrice", "list_price"),
        description="Standard selling price"
    )
    stock: Optional[float] = Field(
        default=None,
        validation_alias=AliasChoices("stock", "QuantityOnHand", "quantityAvailable", "qty_available"),
        description="Current stock level"
    )
    category: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("category", "ItemsGroupCode", "class", "categ_id"),
        description="Product category"
    )
    custom_fields: Dict[str, Any] = Field(
        default={},
        description="User fields or supplementary passthrough data store"
    )


class CanonicalJournalEntry(BaseModel):
    """Normalized journal/accounting entry."""
    entry_id: str = Field(
        validation_alias=AliasChoices("entry_id", "JdtNum", "id", "id"),
        description="Journal entry identifier"
    )
    date: str = Field(
        validation_alias=AliasChoices("date", "ReferenceDate", "trandate", "date"),
        description="Entry date"
    )
    memo: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("memo", "Memo", "memo", "ref"),
        description="Entry memo/reference"
    )
    total_debit: Optional[float] = Field(
        default=None,
        description="Total debit amount"
    )
    total_credit: Optional[float] = Field(
        default=None,
        description="Total credit amount"
    )
    custom_fields: Dict[str, Any] = Field(
        default={},
        description="User fields or supplementary passthrough data store"
    )
