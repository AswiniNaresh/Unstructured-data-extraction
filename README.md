# Invoice Data Extractor

A Flask-based REST API that extracts structured data from unstructured invoice documents (`.docx`) using a Groq-hosted LLM (LLaMA 3 70B). It handles multi-invoice documents, normalizes all fields, and returns clean, ordered JSON.

---

## Table of Contents

- [Project Structure](#project-structure)
- [Approach](#approach)
- [Setup](#setup)
- [Running the API](#running-the-api)
- [API Reference](#api-reference)
- [Example Response](#example-response)
- [Design Decisions & Bug Fixes](#design-decisions--bug-fixes)

---

## Project Structure

```
├── app.py              # Flask application and route definitions
├── extractor.py        # LLM invocation and JSON parsing logic
├── utils.py            # DOCX text extraction and invoice splitting
├── schema.py           # Pydantic model for structured output validation
├── config.py           # Environment variable loading (API key, model name)
├── requirements.txt    # Python dependencies
└── .env                # API keys (not committed to version control)
```

---

## Approach

The pipeline has four stages: **Extract → Split → LLM → Validate**.

```
.docx file
    │
    ▼
┌─────────────────────────────┐
│  Stage 1: Text Extraction   │  utils.py → extract_text_from_docx()
│  Read table cells from docx │
└─────────────┬───────────────┘
              │  List of raw text blocks
              ▼
┌─────────────────────────────┐
│  Stage 2: Invoice Splitting │  utils.py → split_invoices()
│  Filter valid invoice chunks│
└─────────────┬───────────────┘
              │  List of invoice strings
              ▼
┌─────────────────────────────┐
│  Stage 3: LLM Extraction    │  extractor.py → extract_invoice_fields()
│  Groq LLaMA 3 70B → JSON   │
└─────────────┬───────────────┘
              │  Raw JSON string
              ▼
┌─────────────────────────────┐
│  Stage 4: Validation        │  schema.py → InvoiceSchema (Pydantic)
│  Coerce types, fill missing │
└─────────────┬───────────────┘
              │
              ▼
        Structured JSON Response
```

### Stage 1 — Text Extraction (`utils.py`)

`python-docx` is used to open the `.docx` file. A critical insight here is that Word documents can store content in two places: **paragraphs** and **tables**. The original code only read paragraphs, which returned empty strings for this document because all invoice data was embedded inside table cells.

The fixed extractor reads both:

```python
# Paragraphs (top-level text)
for para in doc.paragraphs:
    parts.append(para.text.strip())

# Table cells (where invoice data actually lives)
for table in doc.tables:
    for row in table.rows:
        for cell in row.cells:
            parts.append(cell.text.strip())
```

This returns a list of text blocks — one per table cell — rather than a single joined string.

### Stage 2 — Invoice Splitting (`utils.py`)

Since each table cell already represents one invoice, no complex splitting logic is needed. The function simply filters out any blocks shorter than 100 characters, which removes header rows, blank cells, or metadata that are not real invoices:

```python
def split_invoices(text):
    return [chunk for chunk in text if len(chunk.strip()) > 100]
```

### Stage 3 — LLM Field Extraction (`extractor.py`)

Each invoice text block is sent individually to the Groq API (LLaMA 3 70B). Rather than using LangChain's `with_structured_output()` — which relies on Groq's function-calling backend and is unreliable, throwing `tool_use_failed` errors — the model is prompted via a **system message** to return plain JSON directly:

```python
SYSTEM_PROMPT = """You are an invoice data extractor.
Extract the requested fields from the invoice text and return ONLY a valid JSON object.
Do not include any explanation, markdown, or code fences — just raw JSON.
If a field is not found, use the string "NA"."""
```

The response is then:

1. **Stripped** of any accidental markdown code fences (` ```json ... ``` `)
2. **Parsed** with `json.loads()`
3. **Fallback-safe** — if JSON parsing fails for any invoice, that invoice returns all `"NA"` values instead of crashing the entire batch

### Stage 4 — Validation & Normalization (`schema.py`)

The parsed dict is passed into a Pydantic `InvoiceSchema` model which does three things:

**Coerce numeric types to strings** — LLMs sometimes return amounts as floats (e.g. `2820.0`). A `field_validator` with `mode="before"` converts any value to `str` before Pydantic's type check runs:

```python
@field_validator("subtotal", "tax_amount", "total_amount", ..., mode="before")
@classmethod
def coerce_to_str(cls, v: Any) -> str:
    if v is None:
        return "NA"
    return str(v)
```

**Fill missing fields** — any field the LLM skips is defaulted to `"NA"` by `fill_missing_fields()` before the schema is instantiated.

**Preserve field order** — `model_dump()` (Pydantic v2) is used instead of the deprecated `.dict()`, and `ConfigDict` ensures the output always follows the exact field declaration order in the schema.

---

## Setup

### 1. Clone and install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment variables

Rename `_env` to `.env`:

```bash
mv _env .env
```

Your `.env` file should contain:

```env
GROQ_API_KEY=your_groq_api_key_here
```

Get a free API key at [console.groq.com](https://console.groq.com).

### 3. Place your invoice document

Put your `.docx` file in the project root. The document can contain multiple invoices — each stored as a table cell.

---

## Running the API

```bash
python app.py
```

The server starts at `http://127.0.0.1:5000`.

---

## API Reference

### `POST /extract-invoices`

Accepts a `.docx` file upload and returns structured invoice data for all invoices found in the document.

**Request**

| Parameter | Type | Description |
|-----------|------|-------------|
| `file` | `multipart/form-data` | The `.docx` invoice document |

**cURL Example**

```bash
curl -X POST http://127.0.0.1:5000/extract-invoices \
  -F "file=@InvoiceData.docx"
```

**Postman Example**

- Method: `POST`
- URL: `http://127.0.0.1:5000/extract-invoices`
- Body → `form-data` → Key: `file`, Type: `File`, Value: *(select your .docx)*

**Error Response**

```json
{ "error": "No file uploaded" }
```

---

## Example Response

```json
{
  "invoices": [
    {
      "invoice_number": "#612345",
      "invoice_date": "MARCH.06.2024",
      "due_date": "5 July 2025",
      "customer_name": "Helena Paquet",
      "vendor_name": "Borcelle Catering Services",
      "subtotal": "$500",
      "tax_amount": "10%",
      "total_amount": "$1000",
      "currency": "USD"
    },
    {
      "invoice_number": "INV-00001",
      "invoice_date": "01/01/2023",
      "due_date": "NA",
      "customer_name": "ABC Corporation",
      "vendor_name": "NA",
      "subtotal": "NA",
      "tax_amount": "NA",
      "total_amount": "$625.00",
      "currency": "USD"
    }
  ]
}
```

Fields always appear in this order: `invoice_number`, `invoice_date`, `due_date`, `customer_name`, `vendor_name`, `subtotal`, `tax_amount`, `total_amount`, `currency`.

---

## Design Decisions & Bug Fixes

| File | Issue | Fix |
|------|-------|-----|
| `utils.py` | Only read `doc.paragraphs` — missed all table cell content | Added table iteration to read all cell text |
| `utils.py` | Splitting on `"INVOICE"` keyword was fragile and data-dependent | Replaced with cell-based splitting since each cell is one invoice |
| `extractor.py` | `with_structured_output()` caused Groq `tool_use_failed` 400 errors | Switched to plain `llm.invoke()` with JSON system prompt and manual `json.loads()` |
| `extractor.py` | `fill_missing_fields()` recursed infinitely into itself | Changed `return fill_missing_fields(result)` to `return data` |
| `extractor.py` | `extract_invoice_fields()` never returned its result | Added `return` statement |
| `schema.py` | Pydantic v2 rejected float values in `str` fields | Added `field_validator` with `mode="before"` to coerce all values to `str` |
| `schema.py` | Field order not preserved in output dict | Added `ConfigDict` and switched to `model_dump()` |
| `app.py` | `app.run()` was called inside the route handler | Moved to `if __name__ == "__main__"` block |
| `app.py` | Route never called `split_invoices` or `extract_invoice_fields` | Added full processing pipeline and JSON response |
| `config.py` | `load_dotenv()` couldn't find `_env` file | Added explicit `dotenv_path` and documented rename to `.env` |

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `flask` | REST API server |
| `python-docx` | Reading `.docx` files including table cells |
| `langchain` | LLM message abstractions |
| `langchain-groq` | Groq API client for LangChain |
| `pydantic` | Data validation and schema enforcement |
| `python-dotenv` | Loading API keys from `.env` file |
