"""
Schemas for Normalized Transactions - Multi-gateway payment integration.
Defines Pydantic models with strict validation rules.

Copyright © 2026 WEBLIFETECH (Jonnathan Peña). All Rights Reserved.
"""
from decimal import Decimal
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, EmailStr, field_validator


class NormalizedTransactionRequest(BaseModel):
    """Normalized payload request for creating charges/intents."""
    amount: Decimal = Field(..., gt=Decimal('0.00'), description="Transactional amount (must be positive)")
    currency: str = Field(default="USD", max_length=3, description="3-character ISO currency code")
    customer_email: Optional[EmailStr] = Field(default=None, description="Customer email address")
    customer_phone: Optional[str] = Field(default=None, description="Customer phone number")
    customer_name: Optional[str] = Field(default=None, description="Customer name")
    description: Optional[str] = Field(default=None, description="Charge description")
    payment_token: Optional[str] = Field(default=None, description="Payment token, source, or card token if direct")
    idempotency_key: str = Field(..., description="Unique key to prevent duplicate charges")
    return_url: Optional[str] = Field(default=None, description="Callback URL for redirect-based payments")
    cancel_url: Optional[str] = Field(default=None, description="Cancel callback URL")

    @field_validator('currency')
    @classmethod
    def validate_currency(cls, v: str) -> str:
        if not v or len(v) != 3:
            raise ValueError("Currency must be exactly a 3-character ISO code")
        return v.upper()


class NormalizedTransactionResponse(BaseModel):
    """Normalized output from any provider adapter."""
    success: bool
    status: str = Field(..., description="Transaction status (pending, authorized, captured, failed, refunded, voided)")
    amount: Decimal
    currency: str
    transaction_id: Optional[str] = Field(default=None, description="Provider transaction ID")
    payment_url: Optional[str] = Field(default=None, description="Redirect URL for user action if redirect-based")
    error_code: Optional[str] = Field(default=None)
    error_message: Optional[str] = Field(default=None)
    raw_response: Dict[str, Any] = Field(default_factory=dict, description="Raw gateway response metadata")
