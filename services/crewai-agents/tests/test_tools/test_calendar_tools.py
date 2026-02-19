"""Tests for the French tax calendar tools."""

import json
import pytest
from src.tools.calendar_tools import generate_tax_calendar, _month_name_fr


class TestGenerateTaxCalendar:
    """Test suite for tax calendar generation."""

    def test_micro_entrepreneur_quarterly(self):
        """Test calendar generation for micro-entrepreneur with quarterly declarations."""
        result = generate_tax_calendar.run(
            business_type="micro_entrepreneur",
            tax_regime="micro",
            declaration_frequency="quarterly",
            tva_applicable=False,
            year=2025,
        )
        data = json.loads(result)

        assert data["business_type"] == "micro_entrepreneur"
        assert data["year"] == 2025
        assert data["count"] > 0

        # Should have quarterly declarations + CFE
        obligation_types = [o["obligation_type"] for o in data["obligations"]]
        assert "declaration_ca" in obligation_types
        assert "cfe" in obligation_types

    def test_micro_entrepreneur_monthly(self):
        """Test calendar generation for micro-entrepreneur with monthly declarations."""
        result = generate_tax_calendar.run(
            business_type="micro_entrepreneur",
            tax_regime="micro",
            declaration_frequency="monthly",
            tva_applicable=False,
            year=2025,
        )
        data = json.loads(result)

        # Should have 12 monthly declarations + CFE = 13
        assert data["count"] == 13

    def test_sarl_with_tva_monthly(self):
        """Test calendar generation for SARL with monthly TVA."""
        result = generate_tax_calendar.run(
            business_type="sarl",
            tax_regime="reel_simplifie",
            declaration_frequency="monthly",
            tva_applicable=True,
            year=2025,
        )
        data = json.loads(result)

        obligation_types = [o["obligation_type"] for o in data["obligations"]]

        # Should include TVA, IS acomptes, annual accounts, cotisations, CFE
        assert "tva_declaration" in obligation_types
        assert "is_acompte" in obligation_types
        assert "annual_accounts" in obligation_types
        assert "cotisations_sociales" in obligation_types
        assert "cfe" in obligation_types

    def test_sas_with_tva_quarterly(self):
        """Test calendar generation for SAS with quarterly TVA."""
        result = generate_tax_calendar.run(
            business_type="sas",
            tax_regime="reel_normal",
            declaration_frequency="quarterly",
            tva_applicable=True,
            year=2025,
        )
        data = json.loads(result)

        obligation_types = [o["obligation_type"] for o in data["obligations"]]
        assert "tva_declaration" in obligation_types
        assert "is_acompte" in obligation_types

    def test_ei_without_tva(self):
        """Test calendar generation for EI without TVA."""
        result = generate_tax_calendar.run(
            business_type="ei",
            tax_regime="reel_simplifie",
            declaration_frequency="monthly",
            tva_applicable=False,
            year=2025,
        )
        data = json.loads(result)

        obligation_types = [o["obligation_type"] for o in data["obligations"]]

        # EI without TVA should not have TVA declarations or IS acomptes
        assert "tva_declaration" not in obligation_types
        assert "is_acompte" not in obligation_types
        # But should have annual accounts, cotisations, CFE
        assert "annual_accounts" in obligation_types
        assert "cfe" in obligation_types

    def test_deadlines_have_valid_format(self):
        """Test that all deadlines are valid ISO datetime strings."""
        result = generate_tax_calendar.run(
            business_type="micro_entrepreneur",
            tax_regime="micro",
            declaration_frequency="quarterly",
            tva_applicable=False,
            year=2025,
        )
        data = json.loads(result)

        for obligation in data["obligations"]:
            assert "deadline" in obligation
            assert "T" in obligation["deadline"]
            # Basic format check: YYYY-MM-DDTHH:MM:SS
            parts = obligation["deadline"].split("T")
            assert len(parts) == 2
            date_parts = parts[0].split("-")
            assert len(date_parts) == 3

    def test_obligations_have_service_url(self):
        """Test that obligations include service URLs."""
        result = generate_tax_calendar.run(
            business_type="micro_entrepreneur",
            tax_regime="micro",
            declaration_frequency="quarterly",
            tva_applicable=False,
            year=2025,
        )
        data = json.loads(result)

        for obligation in data["obligations"]:
            assert "service_url" in obligation
            assert obligation["service_url"].startswith("https://")

    def test_default_year_is_current(self):
        """Test that year=0 defaults to the current year."""
        from datetime import datetime
        result = generate_tax_calendar.run(
            business_type="micro_entrepreneur",
            tax_regime="micro",
            declaration_frequency="quarterly",
            tva_applicable=False,
            year=0,
        )
        data = json.loads(result)
        assert data["year"] == datetime.utcnow().year


class TestMonthNameFr:
    """Test French month name helper."""

    def test_valid_months(self):
        assert _month_name_fr(1) == "Janvier"
        assert _month_name_fr(6) == "Juin"
        assert _month_name_fr(12) == "Décembre"

    def test_invalid_month(self):
        assert _month_name_fr(0) == "0"
        assert _month_name_fr(13) == "13"
