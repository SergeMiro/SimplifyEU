"""
Document management tools for the Document Manager agent.
Handles document linking, search, and accountant package generation.
"""

import json
import logging
from datetime import datetime
from crewai.tools import tool
from ..db.client import supabase

logger = logging.getLogger(__name__)


@tool("Link document to transaction")
def link_document_to_transaction(
    account_id: str,
    document_id: str,
    transaction_id: str,
    match_confidence: float = 0.0,
) -> str:
    """
    Link a document (invoice/receipt) to a bank transaction.
    document_id: the ID of the uploaded document
    transaction_id: the ID of the matching transaction
    match_confidence: 0.0-1.0 confidence score of the match
    """
    try:
        res = (
            supabase.table("document_links")
            .insert({
                "account_id": account_id,
                "document_id": document_id,
                "transaction_id": transaction_id,
                "match_confidence": match_confidence,
                "verified": False,
            })
            .execute()
        )
        return json.dumps({
            "linked": True,
            "link_id": res.data[0]["id"] if res.data else None,
        })
    except Exception as e:
        logger.error(f"Error linking document: {e}")
        return json.dumps({"linked": False, "error": str(e)})


@tool("Search documents")
def search_documents(account_id: str, query: str) -> str:
    """
    Search for documents by vendor name, amount, or date.
    query: search term (e.g., 'loyer mars 2025', 'EDF', '500 EUR')
    """
    try:
        # Search in invoices table by vendor name
        res = (
            supabase.table("invoices")
            .select("id, filename, vendor_name, total_amount, currency, invoice_date, status")
            .eq("account_id", account_id)
            .ilike("vendor_name", f"%{query}%")
            .order("created_at", desc=True)
            .limit(20)
            .execute()
        )

        results = res.data or []

        # If no results by vendor, try searching by filename
        if not results:
            res = (
                supabase.table("invoices")
                .select("id, filename, vendor_name, total_amount, currency, invoice_date, status")
                .eq("account_id", account_id)
                .ilike("filename", f"%{query}%")
                .order("created_at", desc=True)
                .limit(20)
                .execute()
            )
            results = res.data or []

        return json.dumps({"documents": results, "count": len(results), "query": query})
    except Exception as e:
        logger.error(f"Error searching documents: {e}")
        return json.dumps({"error": str(e), "documents": []})


@tool("Get unlinked documents")
def get_unlinked_documents(account_id: str) -> str:
    """
    Find documents (invoices) that are not yet linked to any bank transaction.
    These need attention — either auto-matching or manual linking.
    """
    try:
        # Get all invoice IDs
        invoices_res = (
            supabase.table("invoices")
            .select("id, filename, vendor_name, total_amount, invoice_date")
            .eq("account_id", account_id)
            .order("created_at", desc=True)
            .execute()
        )

        # Get all linked document IDs
        links_res = (
            supabase.table("document_links")
            .select("document_id")
            .eq("account_id", account_id)
            .execute()
        )

        linked_ids = {link["document_id"] for link in (links_res.data or [])}
        unlinked = [
            inv for inv in (invoices_res.data or []) if inv["id"] not in linked_ids
        ]

        return json.dumps({"unlinked_documents": unlinked, "count": len(unlinked)})
    except Exception as e:
        logger.error(f"Error finding unlinked documents: {e}")
        return json.dumps({"error": str(e), "unlinked_documents": []})


@tool("Generate accountant package")
def generate_accountant_package(
    account_id: str, period_start: str, period_end: str
) -> str:
    """
    Generate a summary package for the accountant (expert-comptable) for a given period.
    Includes: transaction list, linked invoices, unlinked items, and financial summary.
    period_start/period_end: ISO date strings
    """
    try:
        # Fetch invoices for the period
        invoices_res = (
            supabase.table("invoices")
            .select("*")
            .eq("account_id", account_id)
            .gte("invoice_date", period_start)
            .lte("invoice_date", period_end)
            .order("invoice_date", desc=False)
            .execute()
        )

        invoices = invoices_res.data or []

        # Fetch document links
        links_res = (
            supabase.table("document_links")
            .select("*")
            .eq("account_id", account_id)
            .execute()
        )

        linked_ids = {link["document_id"] for link in (links_res.data or [])}

        linked_invoices = [inv for inv in invoices if inv["id"] in linked_ids]
        unlinked_invoices = [inv for inv in invoices if inv["id"] not in linked_ids]

        total_amount = sum(inv.get("total_amount", 0) or 0 for inv in invoices)

        # Fetch analyses for the period
        analyses_res = (
            supabase.table("analyses")
            .select("id, total_transactions, subscriptions_found, potential_savings_eur, created_at")
            .eq("account_id", account_id)
            .eq("status", "completed")
            .gte("created_at", period_start)
            .lte("created_at", period_end)
            .execute()
        )

        package = {
            "period": {"start": period_start, "end": period_end},
            "summary": {
                "total_invoices": len(invoices),
                "linked_invoices": len(linked_invoices),
                "unlinked_invoices": len(unlinked_invoices),
                "total_invoiced_eur": round(total_amount, 2),
                "analyses_count": len(analyses_res.data or []),
            },
            "invoices": invoices,
            "linked_documents": linked_invoices,
            "unlinked_documents": unlinked_invoices,
            "analyses": analyses_res.data or [],
            "generated_at": datetime.utcnow().isoformat(),
            "note": "Ce package est un brouillon généré automatiquement. Vérifiez avec votre expert-comptable.",
        }

        return json.dumps(package)
    except Exception as e:
        logger.error(f"Error generating package: {e}")
        return json.dumps({"error": str(e)})
