"""
Invoice data parser — extracts structured data from raw text.
Uses regex patterns optimized for European invoice formats.
"""
import re
import logging
from typing import Optional

from ..db.models import InvoiceParsedData

logger = logging.getLogger(__name__)

# ── Regex patterns for field extraction ──────

# Invoice number patterns
INVOICE_NUM_PATTERNS = [
    r"(?:Invoice|Facture|Rechnung|Fattura)\s*(?:No\.?|Number|#|N°|Nr\.?)\s*[:\-]?\s*([A-Z0-9\-\/\.]+)",
    r"(?:INV|FAC|RE)\s*[\-\/]?\s*(\d[\d\-\/\.]+)",
    r"(?:Nº|No\.?)\s*[:\-]?\s*(\d[\d\-\/\.]+)",
]

# Amount patterns (European: 1.234,56 or 1 234,56 or standard: 1,234.56)
AMOUNT_PATTERNS = [
    r"(?:Total|Montant\s*TTC|Gesamt|Totale|Grand\s*Total|Amount\s*Due)\s*[:\-]?\s*€?\s*([\d\s]+[\.,]\d{2})",
    r"€\s*([\d\s]+[\.,]\d{2})",
    r"([\d\s]+[\.,]\d{2})\s*€",
    r"EUR\s*([\d\s]+[\.,]\d{2})",
]

# Date patterns (DD/MM/YYYY, DD.MM.YYYY, YYYY-MM-DD)
DATE_PATTERNS = [
    r"(?:Date|Datum|Data)\s*[:\-]?\s*(\d{1,2}[\/\.\-]\d{1,2}[\/\.\-]\d{2,4})",
    r"(\d{4}[\-]\d{2}[\-]\d{2})",
    r"(\d{1,2}[\/\.]\d{1,2}[\/\.]\d{4})",
]

# Due date
DUE_DATE_PATTERNS = [
    r"(?:Due\s*Date|Échéance|Fällig|Scadenza)\s*[:\-]?\s*(\d{1,2}[\/\.\-]\d{1,2}[\/\.\-]\d{2,4})",
]

# Vendor patterns
VENDOR_PATTERNS = [
    r"(?:From|Sender|Émetteur|Absender|Société)\s*[:\-]?\s*(.+?)(?:\n|$)",
]

# Currency patterns
CURRENCY_PATTERNS = [
    r"(?:Currency|Devise|Währung)\s*[:\-]?\s*(EUR|USD|GBP|CHF)",
    r"(€|EUR)",
    r"(\$|USD)",
    r"(£|GBP)",
]


def parse_invoice_text(raw_text: str) -> InvoiceParsedData:
    """
    Parse raw text and extract structured invoice fields.
    Returns InvoiceParsedData with all extracted fields.
    """
    if not raw_text or not raw_text.strip():
        return InvoiceParsedData(raw_text=raw_text or "")

    text = raw_text.strip()

    invoice_number = _extract_first_match(text, INVOICE_NUM_PATTERNS)
    total_amount = _parse_amount(_extract_first_match(text, AMOUNT_PATTERNS))
    invoice_date = _extract_first_match(text, DATE_PATTERNS)
    due_date = _extract_first_match(text, DUE_DATE_PATTERNS)
    vendor_name = _extract_vendor(text)
    currency = _detect_currency(text)
    line_items = _extract_line_items(text)

    parsed = InvoiceParsedData(
        invoice_number=invoice_number,
        vendor_name=vendor_name,
        invoice_date=invoice_date,
        due_date=due_date,
        total_amount=total_amount,
        currency=currency,
        line_items=line_items,
        raw_text=text,
    )

    logger.info(
        f"Parsed invoice: number={invoice_number}, amount={total_amount}, "
        f"vendor={vendor_name}, date={invoice_date}"
    )

    return parsed


def _extract_first_match(text: str, patterns: list[str]) -> Optional[str]:
    """Try each pattern and return the first match."""
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            return match.group(1).strip()
    return None


def _parse_amount(amount_str: Optional[str]) -> Optional[float]:
    """
    Parse a European or standard amount string to float.
    Handles: 1.234,56 → 1234.56  |  1,234.56 → 1234.56  |  1 234,56 → 1234.56
    """
    if not amount_str:
        return None

    try:
        # Remove spaces
        cleaned = amount_str.replace(" ", "")

        # European format: 1.234,56 → comma is decimal separator
        if "," in cleaned and "." in cleaned:
            if cleaned.rindex(",") > cleaned.rindex("."):
                # European: 1.234,56
                cleaned = cleaned.replace(".", "").replace(",", ".")
            else:
                # Standard: 1,234.56
                cleaned = cleaned.replace(",", "")
        elif "," in cleaned:
            # Could be 1234,56 (European) or 1,234 (thousands separator)
            parts = cleaned.split(",")
            if len(parts) == 2 and len(parts[1]) == 2:
                # European decimal: 1234,56
                cleaned = cleaned.replace(",", ".")
            else:
                # Thousands separator
                cleaned = cleaned.replace(",", "")

        return round(float(cleaned), 2)
    except (ValueError, TypeError) as e:
        logger.debug(f"Failed to parse amount '{amount_str}': {e}")
        return None


def _extract_vendor(text: str) -> Optional[str]:
    """Extract vendor name from invoice text."""
    # Try explicit patterns first
    vendor = _extract_first_match(text, VENDOR_PATTERNS)
    if vendor:
        return vendor[:200]  # Truncate

    # Heuristic: first line of the document is often the company name
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if lines:
        first_line = lines[0]
        # Skip if it looks like an invoice number or date
        if not re.match(r"^\d", first_line) and len(first_line) < 100:
            return first_line

    return None


def _detect_currency(text: str) -> str:
    """Detect currency from text, default EUR."""
    if "€" in text or "EUR" in text.upper():
        return "EUR"
    if "$" in text or "USD" in text.upper():
        return "USD"
    if "£" in text or "GBP" in text.upper():
        return "GBP"
    if "CHF" in text.upper():
        return "CHF"
    return "EUR"


def _extract_line_items(text: str) -> list[dict]:
    """
    Heuristic extraction of line items.
    Looks for rows with quantity × description × amount patterns.
    """
    items = []
    # Pattern: quantity | description | amount
    pattern = r"(\d+)\s+(.{5,50}?)\s+([\d\s]+[\.,]\d{2})"

    for match in re.finditer(pattern, text):
        qty = match.group(1)
        desc = match.group(2).strip()
        amount = _parse_amount(match.group(3))

        if amount and desc:
            items.append({
                "quantity": int(qty),
                "description": desc,
                "amount": amount,
            })

    return items[:50]  # Limit to 50 items
