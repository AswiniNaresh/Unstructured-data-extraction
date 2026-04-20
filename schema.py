from pydantic import BaseModel, Field, field_validator
from pydantic import ConfigDict
from typing import Any


class InvoiceSchema(BaseModel):
    # Preserve the field declaration order in all dict/JSON outputs
    model_config = ConfigDict(populate_by_name=True)

    invoice_number: str = Field(default="NA")
    invoice_date: str = Field(default="NA")
    due_date: str = Field(default="NA")
    customer_name: str = Field(default="NA")
    vendor_name: str = Field(default="NA")
    subtotal: str = Field(default="NA")
    tax_amount: str = Field(default="NA")
    total_amount: str = Field(default="NA")
    currency: str = Field(default="NA")

    @field_validator(
        "invoice_number", "invoice_date", "due_date",
        "customer_name", "vendor_name", "subtotal",
        "tax_amount", "total_amount", "currency",
        mode="before"
    )
    @classmethod
    def coerce_to_str(cls, v: Any) -> str:
        if v is None:
            return "NA"
        return str(v)