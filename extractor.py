import json
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

from schema import InvoiceSchema
from config import MODEL_NAME, GROQ_API_KEY


llm = ChatGroq(
    model=MODEL_NAME,
    api_key=GROQ_API_KEY,
    temperature=0
)

# ROOT CAUSE FIX: Groq's function-calling backend is unreliable with
# with_structured_output() and throws BadRequestError (tool_use_failed).
# Solution: prompt the model to return plain JSON and parse it manually.

FIELDS = [
    "invoice_number",
    "invoice_date",
    "due_date",
    "customer_name",
    "vendor_name",
    "subtotal",
    "tax_amount",
    "total_amount",
    "currency",
]

SYSTEM_PROMPT = """You are an invoice data extractor.
Extract the requested fields from the invoice text and return ONLY a valid JSON object.
Do not include any explanation, markdown, or code fences — just raw JSON.
If a field is not found, use the string "NA"."""


def fill_missing_fields(data: dict) -> dict:
    """Ensure all expected fields are present, defaulting to 'NA'."""
    for field in FIELDS:
        if not data.get(field):
            data[field] = "NA"
    return data


def extract_invoice_fields(invoice_text: str) -> dict:
    prompt = f"""Extract the following fields from the invoice below and return a JSON object:

Fields:
- invoice_number
- invoice_date
- due_date
- customer_name
- vendor_name
- subtotal
- tax_amount
- total_amount
- currency

Invoice text:
{invoice_text}
"""

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=prompt)
    ]

    response = llm.invoke(messages)
    raw = response.content.strip()

    # Strip markdown code fences if the model adds them despite instructions
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # If parsing fails, return all NA rather than crashing the whole batch
        data = {field: "NA" for field in FIELDS}

    # Validate through Pydantic schema and return as dict
    validated = InvoiceSchema(**fill_missing_fields(data))
    return validated.model_dump()