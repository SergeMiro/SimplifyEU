"""
French tax calendar tools for the Tax Assistant agent.
Generates obligation deadlines based on business type and tax regime.
"""

import json
import logging
from datetime import datetime, date, timedelta
from crewai.tools import tool

logger = logging.getLogger(__name__)

# French tax calendar reference data
MICRO_ENTREPRENEUR_DEADLINES = {
    "monthly": {
        # Declaration of turnover (CA) — due last day of month following the period
        "declaration_ca": {
            "title": "Déclaration de chiffre d'affaires",
            "description": "Déclarez votre CA du mois précédent sur autoentrepreneur.urssaf.fr",
            "service_url": "https://www.autoentrepreneur.urssaf.fr",
            "day_of_month": 30,  # Last day of following month
            "months": list(range(1, 13)),  # Every month
        },
    },
    "quarterly": {
        "declaration_ca_q1": {
            "title": "Déclaration CA - T1 (jan-mar)",
            "description": "Déclarez votre CA du 1er trimestre",
            "service_url": "https://www.autoentrepreneur.urssaf.fr",
            "deadline_month": 4,
            "deadline_day": 30,
        },
        "declaration_ca_q2": {
            "title": "Déclaration CA - T2 (avr-jun)",
            "description": "Déclarez votre CA du 2ème trimestre",
            "service_url": "https://www.autoentrepreneur.urssaf.fr",
            "deadline_month": 7,
            "deadline_day": 31,
        },
        "declaration_ca_q3": {
            "title": "Déclaration CA - T3 (jul-sep)",
            "description": "Déclarez votre CA du 3ème trimestre",
            "service_url": "https://www.autoentrepreneur.urssaf.fr",
            "deadline_month": 10,
            "deadline_day": 31,
        },
        "declaration_ca_q4": {
            "title": "Déclaration CA - T4 (oct-déc)",
            "description": "Déclarez votre CA du 4ème trimestre",
            "service_url": "https://www.autoentrepreneur.urssaf.fr",
            "deadline_month": 1,
            "deadline_day": 31,
        },
    },
}

COMPANY_DEADLINES = {
    "tva_monthly": {
        "title": "Déclaration de TVA (mensuelle)",
        "description": "Déposez votre déclaration CA3 de TVA du mois précédent",
        "service_url": "https://www.impots.gouv.fr/professionnel",
        "day_of_month": 19,  # Generally 19th of following month
        "months": list(range(1, 13)),
    },
    "tva_quarterly": {
        "title": "Déclaration de TVA (trimestrielle)",
        "description": "Déposez votre déclaration CA3 de TVA du trimestre précédent",
        "service_url": "https://www.impots.gouv.fr/professionnel",
        "deadlines": [(4, 19), (7, 19), (10, 19), (1, 19)],
    },
    "is_acompte": {
        "title": "Acompte d'impôt sur les sociétés (IS)",
        "description": "Versement de l'acompte trimestriel d'IS",
        "service_url": "https://www.impots.gouv.fr/professionnel",
        "deadlines": [(3, 15), (6, 15), (9, 15), (12, 15)],
    },
    "annual_accounts": {
        "title": "Dépôt des comptes annuels",
        "description": "Dépôt des comptes annuels au greffe du tribunal de commerce",
        "service_url": "https://www.infogreffe.fr",
        "note": "Dans les 6 mois suivant la clôture de l'exercice",
    },
    "cotisations_sociales": {
        "title": "Cotisations sociales (URSSAF)",
        "description": "Paiement des cotisations sociales",
        "service_url": "https://www.urssaf.fr",
        "frequency": "monthly_or_quarterly",
    },
}

CFE_DEADLINE = {
    "title": "Cotisation Foncière des Entreprises (CFE)",
    "description": "Paiement de la CFE — applicable à toutes les entreprises",
    "service_url": "https://www.impots.gouv.fr/professionnel",
    "deadline_month": 12,
    "deadline_day": 15,
}


@tool("Generate tax calendar")
def generate_tax_calendar(
    business_type: str,
    tax_regime: str,
    declaration_frequency: str,
    tva_applicable: bool,
    year: int = 0,
) -> str:
    """
    Generate a personalized tax obligation calendar based on business profile.
    business_type: micro_entrepreneur, sarl, sas, sasu, ei, eurl
    tax_regime: micro, reel_simplifie, reel_normal
    declaration_frequency: monthly, quarterly
    tva_applicable: whether TVA applies
    year: the year to generate for (0 = current year)
    Returns a list of obligations with deadlines.
    """
    if year == 0:
        year = datetime.utcnow().year

    obligations = []

    if business_type == "micro_entrepreneur":
        # Micro-entrepreneur: turnover declarations
        if declaration_frequency == "monthly":
            deadlines = MICRO_ENTREPRENEUR_DEADLINES["monthly"]
            for key, info in deadlines.items():
                for month in info["months"]:
                    # Deadline is last day of following month
                    deadline_month = month + 1 if month < 12 else 1
                    deadline_year = year if month < 12 else year + 1
                    # Use safe day
                    day = min(info["day_of_month"], 28)
                    obligations.append({
                        "obligation_type": key,
                        "title": f"{info['title']} — {_month_name_fr(month)} {year}",
                        "description": info["description"],
                        "deadline": f"{deadline_year}-{deadline_month:02d}-{day:02d}T23:59:00",
                        "service_url": info["service_url"],
                    })
        else:
            deadlines = MICRO_ENTREPRENEUR_DEADLINES["quarterly"]
            for key, info in deadlines.items():
                dl_year = year if info["deadline_month"] != 1 else year + 1
                day = min(info["deadline_day"], 28)
                obligations.append({
                    "obligation_type": "declaration_ca",
                    "title": info["title"],
                    "description": info["description"],
                    "deadline": f"{dl_year}-{info['deadline_month']:02d}-{day:02d}T23:59:00",
                    "service_url": info["service_url"],
                })
    else:
        # Company types (SARL, SAS, SASU, EI, EURL)
        if tva_applicable:
            if declaration_frequency == "monthly":
                tva = COMPANY_DEADLINES["tva_monthly"]
                for month in tva["months"]:
                    deadline_month = month + 1 if month < 12 else 1
                    deadline_year = year if month < 12 else year + 1
                    obligations.append({
                        "obligation_type": "tva_declaration",
                        "title": f"{tva['title']} — {_month_name_fr(month)} {year}",
                        "description": tva["description"],
                        "deadline": f"{deadline_year}-{deadline_month:02d}-{tva['day_of_month']:02d}T23:59:00",
                        "service_url": tva["service_url"],
                    })
            else:
                tva = COMPANY_DEADLINES["tva_quarterly"]
                for m, d in tva["deadlines"]:
                    dl_year = year if m != 1 else year + 1
                    obligations.append({
                        "obligation_type": "tva_declaration",
                        "title": tva["title"],
                        "description": tva["description"],
                        "deadline": f"{dl_year}-{m:02d}-{d:02d}T23:59:00",
                        "service_url": tva["service_url"],
                    })

        # IS acomptes (for SARL, SAS, SASU)
        if business_type in ("sarl", "sas", "sasu"):
            is_info = COMPANY_DEADLINES["is_acompte"]
            for m, d in is_info["deadlines"]:
                obligations.append({
                    "obligation_type": "is_acompte",
                    "title": is_info["title"],
                    "description": is_info["description"],
                    "deadline": f"{year}-{m:02d}-{d:02d}T23:59:00",
                    "service_url": is_info["service_url"],
                })

        # Annual accounts
        aa = COMPANY_DEADLINES["annual_accounts"]
        obligations.append({
            "obligation_type": "annual_accounts",
            "title": aa["title"],
            "description": aa["description"],
            "deadline": f"{year}-06-30T23:59:00",
            "service_url": aa["service_url"],
        })

        # Cotisations sociales
        cs = COMPANY_DEADLINES["cotisations_sociales"]
        obligations.append({
            "obligation_type": "cotisations_sociales",
            "title": cs["title"],
            "description": cs["description"],
            "deadline": f"{year}-12-31T23:59:00",
            "service_url": cs["service_url"],
        })

    # CFE — applies to everyone
    cfe = CFE_DEADLINE
    obligations.append({
        "obligation_type": "cfe",
        "title": cfe["title"],
        "description": cfe["description"],
        "deadline": f"{year}-{cfe['deadline_month']:02d}-{cfe['deadline_day']:02d}T23:59:00",
        "service_url": cfe["service_url"],
    })

    return json.dumps({
        "obligations": obligations,
        "count": len(obligations),
        "year": year,
        "business_type": business_type,
    })


@tool("Calculate turnover for period")
def calculate_turnover_for_period(account_id: str, period_start: str, period_end: str) -> str:
    """
    Calculate total turnover (chiffre d'affaires) for a given period.
    Sums up income transactions from bank data.
    period_start: ISO date string (e.g., '2025-01-01')
    period_end: ISO date string (e.g., '2025-03-31')
    Returns turnover breakdown.
    """
    try:
        from ..db.client import supabase as db

        # Fetch completed analyses in the period
        analyses_res = (
            db.table("analyses")
            .select("id, total_transactions, subscriptions_found, potential_savings_eur")
            .eq("account_id", account_id)
            .eq("status", "completed")
            .gte("created_at", period_start)
            .lte("created_at", period_end)
            .execute()
        )

        # Fetch income invoices in the period
        invoices_res = (
            db.table("invoices")
            .select("total_amount, currency, invoice_date, vendor_name")
            .eq("account_id", account_id)
            .gte("invoice_date", period_start)
            .lte("invoice_date", period_end)
            .execute()
        )

        total_invoiced = sum(
            inv.get("total_amount", 0) or 0 for inv in (invoices_res.data or [])
        )

        return json.dumps({
            "period_start": period_start,
            "period_end": period_end,
            "total_invoiced_eur": round(total_invoiced, 2),
            "invoice_count": len(invoices_res.data or []),
            "analyses_count": len(analyses_res.data or []),
            "note": "Ce montant est un brouillon basé sur les factures enregistrées. Vérifiez avant déclaration.",
        })
    except Exception as e:
        logger.error(f"Error calculating turnover: {e}")
        return json.dumps({"error": str(e)})


@tool("Check upcoming deadlines")
def check_upcoming_deadlines(account_id: str, days_ahead: int = 14) -> str:
    """
    Check for upcoming tax deadlines within the next N days.
    Returns obligations that are approaching their deadline.
    """
    try:
        from ..db.client import supabase as db

        now = datetime.utcnow()
        cutoff = (now + timedelta(days=days_ahead)).isoformat()

        res = (
            db.table("tax_obligations")
            .select("*")
            .eq("account_id", account_id)
            .in_("status", ["pending", "reminded"])
            .lte("deadline", cutoff)
            .order("deadline", desc=False)
            .execute()
        )

        upcoming = []
        for ob in (res.data or []):
            deadline_dt = datetime.fromisoformat(ob["deadline"].replace("Z", "+00:00"))
            days_remaining = (deadline_dt.replace(tzinfo=None) - now).days
            upcoming.append({
                **ob,
                "days_remaining": days_remaining,
                "is_overdue": days_remaining < 0,
                "is_urgent": days_remaining <= 3,
            })

        return json.dumps({
            "upcoming": upcoming,
            "count": len(upcoming),
            "days_ahead": days_ahead,
        })
    except Exception as e:
        logger.error(f"Error checking deadlines: {e}")
        return json.dumps({"error": str(e), "upcoming": []})


def _month_name_fr(month: int) -> str:
    names = [
        "", "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
        "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre",
    ]
    return names[month] if 1 <= month <= 12 else str(month)
