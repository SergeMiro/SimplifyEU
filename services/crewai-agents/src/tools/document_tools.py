"""
Document management tools for the Document Manager agent.
Handles document linking, search, and accountant package generation.

NOTE: these tools query the core `invoices` table (Stripe billing). The original
code selected detector-only columns (vendor_name, total_amount, invoice_date,
filename) from `invoices`; those columns do not exist on that table (they live on
`detector_invoices`). That mismatch pre-dates this migration; the queries below
use the real `invoices` columns so they execute, and the JSON shapes are
preserved where the data exists.
"""

import json
import logging
from datetime import datetime
from crewai.tools import tool
from sqlalchemy import select
from ..db.session import SessionLocal
from ..db.orm import (
    DocumentLink as DocumentLinkRow,
    Invoice as InvoiceRow,
)

logger = logging.getLogger(__name__)


def _invoice_to_dict(inv: InvoiceRow) -> dict:
    return {
        "id": str(inv.id),
        "account_id": str(inv.account_id),
        "stripe_invoice_id": inv.stripe_invoice_id,
        "amount": float(inv.amount) if inv.amount is not None else None,
        "currency": inv.currency,
        "status": inv.status,
        "pdf_url": inv.pdf_url,
        "created_at": inv.created_at.isoformat() if inv.created_at else None,
    }


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
        with SessionLocal() as db:
            row = DocumentLinkRow(
                account_id=account_id,
                document_id=document_id,
                transaction_id=transaction_id,
                match_confidence=match_confidence,
                verified=False,
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return json.dumps({
                "linked": True,
                "link_id": str(row.id),
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
        with SessionLocal() as db:
            rows = db.scalars(
                select(InvoiceRow)
                .where(InvoiceRow.account_id == account_id)
                .order_by(InvoiceRow.created_at.desc())
                .limit(20)
            ).all()

            results = [_invoice_to_dict(r) for r in rows]
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
        with SessionLocal() as db:
            # Get all invoices
            invoices = db.scalars(
                select(InvoiceRow)
                .where(InvoiceRow.account_id == account_id)
                .order_by(InvoiceRow.created_at.desc())
            ).all()

            # Get all linked document IDs
            linked_ids = {
                str(doc_id)
                for doc_id in db.scalars(
                    select(DocumentLinkRow.document_id).where(
                        DocumentLinkRow.account_id == account_id
                    )
                ).all()
            }

            unlinked = [
                _invoice_to_dict(inv)
                for inv in invoices
                if str(inv.id) not in linked_ids
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
        with SessionLocal() as db:
            # Fetch invoices for the period (by created_at; invoice_date does not
            # exist on the core invoices table — see module note).
            invoices_rows = db.scalars(
                select(InvoiceRow)
                .where(InvoiceRow.account_id == account_id)
                .where(InvoiceRow.created_at >= period_start)
                .where(InvoiceRow.created_at <= period_end)
                .order_by(InvoiceRow.created_at.asc())
            ).all()

            invoices = [_invoice_to_dict(r) for r in invoices_rows]

            # Fetch document links
            linked_ids = {
                str(doc_id)
                for doc_id in db.scalars(
                    select(DocumentLinkRow.document_id).where(
                        DocumentLinkRow.account_id == account_id
                    )
                ).all()
            }

            linked_invoices = [inv for inv in invoices if inv["id"] in linked_ids]
            unlinked_invoices = [inv for inv in invoices if inv["id"] not in linked_ids]

            total_amount = sum(inv.get("amount", 0) or 0 for inv in invoices)

            package = {
                "period": {"start": period_start, "end": period_end},
                "summary": {
                    "total_invoices": len(invoices),
                    "linked_invoices": len(linked_invoices),
                    "unlinked_invoices": len(unlinked_invoices),
                    "total_invoiced_eur": round(total_amount, 2),
                },
                "invoices": invoices,
                "linked_documents": linked_invoices,
                "unlinked_documents": unlinked_invoices,
                "generated_at": datetime.utcnow().isoformat(),
                "note": "Ce package est un brouillon généré automatiquement. Vérifiez avec votre expert-comptable.",
            }

            return json.dumps(package)
    except Exception as e:
        logger.error(f"Error generating package: {e}")
        return json.dumps({"error": str(e)})
