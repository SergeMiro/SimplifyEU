"""
Fuzzy string matching utilities for comparing invoice fields.
"""
import logging
from typing import Optional

from fuzzywuzzy import fuzz

logger = logging.getLogger(__name__)


def fuzzy_text_similarity(a: Optional[str], b: Optional[str]) -> float:
    """
    Compare two text strings using fuzzy matching.
    Returns a score between 0.0 and 1.0.
    """
    if not a or not b:
        return 0.0

    a_clean = _normalize(a)
    b_clean = _normalize(b)

    if not a_clean or not b_clean:
        return 0.0

    # Use token_sort_ratio for order-independent comparison
    score = fuzz.token_sort_ratio(a_clean, b_clean) / 100.0
    return round(score, 4)


def exact_match(a: Optional[str], b: Optional[str]) -> float:
    """Exact match after normalization. Returns 1.0 or 0.0."""
    if not a or not b:
        return 0.0
    return 1.0 if _normalize(a) == _normalize(b) else 0.0


def amount_similarity(a: Optional[float], b: Optional[float], tolerance: float = 0.01) -> float:
    """
    Compare two monetary amounts.
    Returns 1.0 for exact match, scaled score for near-matches.
    """
    if a is None or b is None:
        return 0.0

    if a == b:
        return 1.0

    if a == 0 and b == 0:
        return 1.0

    max_val = max(abs(a), abs(b))
    if max_val == 0:
        return 1.0

    diff = abs(a - b)
    relative_diff = diff / max_val

    # Within tolerance → perfect match
    if relative_diff <= tolerance:
        return 1.0

    # Within 5% → high similarity
    if relative_diff <= 0.05:
        return 0.9

    # Scale down logarithmically
    if relative_diff <= 0.10:
        return 0.7

    if relative_diff <= 0.20:
        return 0.3

    return 0.0


def date_similarity(a: Optional[str], b: Optional[str]) -> float:
    """
    Compare two date strings.
    Returns 1.0 for exact match, partial scores for close dates.
    """
    if not a or not b:
        return 0.0

    # Normalize separators
    a_norm = a.replace("/", "-").replace(".", "-").strip()
    b_norm = b.replace("/", "-").replace(".", "-").strip()

    if a_norm == b_norm:
        return 1.0

    # Try parsing to compare actual dates
    try:
        from datetime import datetime

        formats = ["%d-%m-%Y", "%Y-%m-%d", "%d-%m-%y", "%m-%d-%Y"]
        date_a = _try_parse_date(a_norm, formats)
        date_b = _try_parse_date(b_norm, formats)

        if date_a and date_b:
            diff_days = abs((date_a - date_b).days)
            if diff_days == 0:
                return 1.0
            elif diff_days <= 1:
                return 0.9
            elif diff_days <= 7:
                return 0.5
            elif diff_days <= 30:
                return 0.2
        return 0.0
    except Exception:
        return 0.0


def _try_parse_date(date_str: str, formats: list[str]):
    """Try multiple date formats and return first successful parse."""
    from datetime import datetime
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None


def _normalize(text: str) -> str:
    """Normalize text for comparison: lowercase, strip, collapse whitespace."""
    import re
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    return text
