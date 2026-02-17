# Invoice Duplicate Detector

Intelligent duplicate invoice detection using OCR, fuzzy matching, and weighted
similarity scoring.

## Architecture

```
src/
├── main.py              # FastAPI app entry point
├── config.py            # Pydantic settings (OCR, weights, thresholds)
├── api/v1/
│   ├── invoices.py      # Upload, process, list, delete invoices
│   └── duplicates.py    # Duplicate pairs CRUD + bulk actions + stats
├── auth/
│   └── api_key.py       # API key authentication (bcrypt)
├── core/
│   ├── pdf_extractor.py    # Dual PDF extraction + magic-byte validation
│   ├── ocr_processor.py    # Tesseract OCR with retry + backoff
│   ├── invoice_parser.py   # Multi-language regex parser (EN/FR/DE/IT)
│   ├── fuzzy_matcher.py    # Text/amount/date fuzzy comparison
│   └── similarity.py       # Weighted scoring engine
├── db/
│   ├── client.py        # Supabase singleton
│   └── models.py        # Pydantic models
└── utils/
    └── logger.py        # Structured logging
```

## Quick Start

```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your Supabase credentials

uvicorn src.main:app --reload --port 8002

python -m pytest tests/ -v
```

## API Endpoints

| Method | Path                         | Description                |
| ------ | ---------------------------- | -------------------------- |
| GET    | `/health`                    | Health check               |
| POST   | `/v1/invoices/upload`        | Upload invoice (PDF/image) |
| GET    | `/v1/invoices`               | List invoices (paginated)  |
| GET    | `/v1/invoices/{id}`          | Get invoice details        |
| DELETE | `/v1/invoices/{id}`          | Delete invoice             |
| GET    | `/v1/duplicates`             | List duplicate pairs       |
| GET    | `/v1/duplicates/{id}`        | Get duplicate pair details |
| PATCH  | `/v1/duplicates/{id}`        | Review (confirm/dismiss)   |
| POST   | `/v1/duplicates/bulk-action` | Bulk confirm/dismiss       |
| GET    | `/v1/duplicates/stats`       | Detection statistics       |

## Duplicate Detection Pipeline

1. **Upload** → file validated (extension, size, magic bytes)
2. **Dedup** → SHA-256 hash check for exact duplicates
3. **Extract** → pdfplumber → PyPDF2 → Tesseract OCR fallback
4. **Parse** → regex extraction (invoice#, amount, vendor, date, line items)
5. **Score** → weighted similarity against all existing invoices
6. **Flag** → pairs exceeding threshold (default 0.85) saved as duplicates

## Configurable Weights

| Field          | Default Weight |
| -------------- | -------------- |
| Invoice Number | 0.30           |
| Amount         | 0.25           |
| Vendor Name    | 0.20           |
| Date           | 0.15           |
| Line Items     | 0.10           |
