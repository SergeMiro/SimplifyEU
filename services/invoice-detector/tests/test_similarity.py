"""
Tests for fuzzy matching and similarity scoring.
"""
import pytest
from src.core.fuzzy_matcher import (
    fuzzy_text_similarity,
    exact_match,
    amount_similarity,
    date_similarity,
)
from src.core.similarity import compute_similarity_score


class TestFuzzyTextSimilarity:
    """Test fuzzy text comparison."""

    def test_identical_strings(self):
        assert fuzzy_text_similarity("hello world", "hello world") == 1.0

    def test_case_insensitive(self):
        score = fuzzy_text_similarity("ACME Corp", "acme corp")
        assert score >= 0.9

    def test_reordered_words(self):
        score = fuzzy_text_similarity("Acme Corp EU", "EU Acme Corp")
        assert score >= 0.8

    def test_completely_different(self):
        score = fuzzy_text_similarity("Apple Inc", "Microsoft Corp")
        assert score < 0.5

    def test_none_handling(self):
        assert fuzzy_text_similarity(None, "test") == 0.0
        assert fuzzy_text_similarity("test", None) == 0.0
        assert fuzzy_text_similarity(None, None) == 0.0

    def test_empty_strings(self):
        assert fuzzy_text_similarity("", "test") == 0.0


class TestExactMatch:
    """Test exact match."""

    def test_exact(self):
        assert exact_match("INV-001", "INV-001") == 1.0

    def test_case_insensitive(self):
        assert exact_match("inv-001", "INV-001") == 1.0

    def test_different(self):
        assert exact_match("INV-001", "INV-002") == 0.0

    def test_none(self):
        assert exact_match(None, "test") == 0.0


class TestAmountSimilarity:
    """Test amount comparison."""

    def test_exact_match(self):
        assert amount_similarity(1234.56, 1234.56) == 1.0

    def test_within_tolerance(self):
        score = amount_similarity(1234.56, 1234.57)
        assert score >= 0.9

    def test_five_percent_diff(self):
        score = amount_similarity(100.0, 104.0)
        assert score >= 0.7

    def test_completely_different(self):
        score = amount_similarity(100.0, 500.0)
        assert score == 0.0

    def test_none_handling(self):
        assert amount_similarity(None, 100.0) == 0.0
        assert amount_similarity(100.0, None) == 0.0


class TestDateSimilarity:
    """Test date comparison."""

    def test_same_date(self):
        assert date_similarity("15/01/2026", "15/01/2026") == 1.0

    def test_different_separators(self):
        score = date_similarity("15/01/2026", "15-01-2026")
        assert score == 1.0

    def test_different_dates(self):
        score = date_similarity("15/01/2026", "20/06/2026")
        assert score < 0.5

    def test_none_handling(self):
        assert date_similarity(None, "15/01/2026") == 0.0


class TestComputeSimilarityScore:
    """Test the weighted similarity engine."""

    def test_identical_invoices(self, sample_invoice_a, sample_invoice_b):
        result = compute_similarity_score(sample_invoice_a, sample_invoice_b)
        assert result["total_score"] >= 0.85
        assert result["is_duplicate"] is True

    def test_different_invoices(self, sample_invoice_a, sample_invoice_c):
        result = compute_similarity_score(sample_invoice_a, sample_invoice_c)
        assert result["total_score"] < 0.85
        assert result["is_duplicate"] is False

    def test_same_hash_gives_perfect(self, sample_invoice_a):
        copy = {**sample_invoice_a, "id": "inv-copy"}
        result = compute_similarity_score(sample_invoice_a, copy)
        assert result["total_score"] == 1.0

    def test_result_structure(self, sample_invoice_a, sample_invoice_b):
        result = compute_similarity_score(sample_invoice_a, sample_invoice_b)
        assert "total_score" in result
        assert "field_scores" in result
        assert "is_duplicate" in result
        assert "invoice_number" in result["field_scores"]
        assert "amount" in result["field_scores"]
        assert "vendor" in result["field_scores"]

    def test_empty_invoices(self):
        result = compute_similarity_score({}, {})
        assert result["total_score"] == 0.0
        assert result["is_duplicate"] is False
