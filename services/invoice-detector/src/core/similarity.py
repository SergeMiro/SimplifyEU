"""
Similarity scoring engine — computes overall duplicate probability
using configurable weighted scoring across multiple invoice fields.
"""
import logging
from typing import Optional

from ..config import settings
from .fuzzy_matcher import (
    fuzzy_text_similarity,
    exact_match,
    amount_similarity,
    date_similarity,
)

logger = logging.getLogger(__name__)


def compute_similarity_score(
    invoice_a: dict,
    invoice_b: dict,
) -> dict:
    """
    Compute a weighted similarity score between two invoices.

    Returns a dict with:
    - total_score: weighted average (0.0-1.0)
    - field_scores: individual field scores
    - is_duplicate: whether total_score exceeds threshold
    """
    field_scores = {}

    # 1. Invoice Number (exact or near-exact)
    field_scores["invoice_number"] = exact_match(
        invoice_a.get("invoice_number"),
        invoice_b.get("invoice_number"),
    )

    # 2. Total Amount
    field_scores["amount"] = amount_similarity(
        invoice_a.get("total_amount"),
        invoice_b.get("total_amount"),
    )

    # 3. Invoice Date
    field_scores["date"] = date_similarity(
        invoice_a.get("invoice_date"),
        invoice_b.get("invoice_date"),
    )

    # 4. Vendor Name (fuzzy)
    field_scores["vendor"] = fuzzy_text_similarity(
        invoice_a.get("vendor_name"),
        invoice_b.get("vendor_name"),
    )

    # 5. Line Items (compare descriptions)
    field_scores["line_items"] = _compare_line_items(
        invoice_a.get("line_items", []),
        invoice_b.get("line_items", []),
    )

    # Weighted total
    weighted_score = (
        field_scores["invoice_number"] * settings.WEIGHT_INVOICE_NUMBER
        + field_scores["amount"] * settings.WEIGHT_AMOUNT
        + field_scores["date"] * settings.WEIGHT_DATE
        + field_scores["vendor"] * settings.WEIGHT_VENDOR
        + field_scores["line_items"] * settings.WEIGHT_LINE_ITEMS
    )

    # Bonus: identical invoice number is a very strong signal
    if field_scores["invoice_number"] == 1.0 and field_scores["amount"] >= 0.9:
        weighted_score = max(weighted_score, 0.95)

    # Bonus: identical file hash (checked separately, but handle if passed)
    if invoice_a.get("file_hash") and invoice_a.get("file_hash") == invoice_b.get("file_hash"):
        weighted_score = 1.0

    total_score = round(min(weighted_score, 1.0), 4)
    is_duplicate = total_score >= settings.DUPLICATE_THRESHOLD

    logger.info(
        f"Similarity: {total_score:.4f} (threshold={settings.DUPLICATE_THRESHOLD}) "
        f"→ {'DUPLICATE' if is_duplicate else 'unique'}"
    )

    return {
        "total_score": total_score,
        "field_scores": field_scores,
        "is_duplicate": is_duplicate,
    }


def _compare_line_items(items_a: list, items_b: list) -> float:
    """
    Compare line items between two invoices.
    Uses fuzzy matching on descriptions and exact match on amounts.
    """
    if not items_a or not items_b:
        return 0.0

    matches = 0
    used = set()

    for item_a in items_a:
        best_score = 0.0
        best_idx = -1

        for idx, item_b in enumerate(items_b):
            if idx in used:
                continue

            desc_sim = fuzzy_text_similarity(
                item_a.get("description", ""),
                item_b.get("description", ""),
            )
            amt_sim = amount_similarity(
                item_a.get("amount"),
                item_b.get("amount"),
            )

            combined = desc_sim * 0.6 + amt_sim * 0.4
            if combined > best_score:
                best_score = combined
                best_idx = idx

        if best_score >= 0.7 and best_idx >= 0:
            matches += 1
            used.add(best_idx)

    total_items = max(len(items_a), len(items_b))
    return round(matches / total_items, 4) if total_items > 0 else 0.0
