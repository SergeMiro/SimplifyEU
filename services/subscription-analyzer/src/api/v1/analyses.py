from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, BackgroundTasks, status, Header
from typing import List, Optional
from uuid import UUID
import uuid
from datetime import datetime
import io
import httpx

from ...auth.api_key import get_current_account
from ...db.client import supabase
from ...db.models import Analysis, AnalysisItem
from ...core.csv_parser import parse_csv
from ...core.detector import detect_subscriptions
from ...core.pdf_generator import generate_pdf_report

router = APIRouter()

async def run_analysis_task(analysis_id: str, account_id: str, file_content: bytes):
    try:
        # Update status
        supabase.table("analyses").update({"status": "processing"}).eq("id", analysis_id).execute()

        # Parse
        transactions = parse_csv(file_content)

        # Detect
        items = await detect_subscriptions(transactions, UUID(analysis_id))

        # Save Items
        items_data = []
        for item in items:
            data = item.model_dump(exclude={"id", "created_at"})
            data['analysis_id'] = str(data['analysis_id'])
            data['first_seen'] = data['first_seen'].isoformat()
            data['last_seen'] = data['last_seen'].isoformat()
            items_data.append(data)

        if items_data:
            supabase.table("analysis_items").insert(items_data).execute()

        # Calc stats
        total_tx = len(transactions)
        subs_found = len([i for i in items if i.is_subscription])
        savings = sum([i.amount_avg for i in items if i.is_subscription])

        # Update Analysis
        supabase.table("analyses").update({
            "status": "completed",
            "total_transactions": total_tx,
            "subscriptions_found": subs_found,
            "potential_savings_eur": savings,
            "completed_at": datetime.now().isoformat()
        }).eq("id", analysis_id).execute()

    except Exception as e:
        print(f"Analysis failed: {e}")
        supabase.table("analyses").update({
            "status": "failed",
            "error_message": str(e)
        }).eq("id", analysis_id).execute()

@router.post("/analyses", status_code=201)
async def create_analysis(
    file: UploadFile = File(...),
    account_id: str = Depends(get_current_account),
    user_id: str = Header(..., alias="X-User-ID")
):
    if not file.filename.endswith(('.csv', '.txt')):
        raise HTTPException(400, "Only CSV files are allowed")

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(400, "File too large")

    # Upload to Supabase Storage (Private)
    file_path = f"{account_id}/{uuid.uuid4()}_{file.filename}"
    try:
        # Upload
        res = supabase.storage.from_("uploads").upload(file_path, content)
        # We DO NOT generate public URL for privacy.
        # We store the path.
    except Exception as e:
        print(f"Storage upload error: {e}")
        raise HTTPException(500, "Failed to upload file")

    # Create Record
    new_analysis = {
        "account_id": account_id,
        "user_id": user_id,
        "status": "pending",
        "filename": file.filename,
        "file_url": file_path, # Storing path
        "source_type": "csv"
    }

    res = supabase.table("analyses").insert(new_analysis).execute()
    if not res.data:
        raise HTTPException(500, "Failed to create analysis record")

    analysis_id = res.data[0]['id']

    return {"analysis_id": analysis_id, "status": "pending"}

@router.post("/analyses/{analysis_id}/run")
async def run_analysis(
    analysis_id: str,
    background_tasks: BackgroundTasks,
    account_id: str = Depends(get_current_account)
):
    # Verify ownership
    res = supabase.table("analyses").select("*").eq("id", analysis_id).eq("account_id", account_id).execute()
    if not res.data:
        raise HTTPException(404, "Analysis not found")

    analysis = res.data[0]
    if analysis['status'] == 'processing':
        return {"status": "processing", "message": "Already running"}

    # Download file content
    content = None
    try:
        path = analysis.get('file_url')
        if not path:
             raise HTTPException(400, "No file associated")

        # Check if legacy public URL
        if path.startswith("http"):
             async with httpx.AsyncClient() as client:
                resp = await client.get(path)
                if resp.status_code == 200:
                    content = resp.content
                else:
                    raise HTTPException(400, "Could not retrieve file content")
        else:
            # Download from storage using path
            content = supabase.storage.from_("uploads").download(path)

    except Exception as e:
        print(f"Download error: {e}")
        raise HTTPException(400, "Could not retrieve file content")

    background_tasks.add_task(run_analysis_task, analysis_id, account_id, content)

    return {"status": "processing", "message": "Analysis started"}

@router.get("/analyses/{analysis_id}")
async def get_analysis(
    analysis_id: str,
    account_id: str = Depends(get_current_account)
):
    res = supabase.table("analyses").select("*").eq("id", analysis_id).eq("account_id", account_id).execute()
    if not res.data:
        raise HTTPException(404, "Analysis not found")

    analysis = res.data[0]

    # Get items
    items_res = supabase.table("analysis_items").select("*").eq("analysis_id", analysis_id).execute()
    items = items_res.data

    return {**analysis, "items": items}

@router.get("/analyses")
async def list_analyses(
    page: int = 1,
    limit: int = 20,
    account_id: str = Depends(get_current_account)
):
    start = (page - 1) * limit
    end = start + limit - 1

    res = supabase.table("analyses").select("*", count="exact")\
        .eq("account_id", account_id)\
        .order("created_at", desc=True)\
        .range(start, end)\
        .execute()

    return {
        "data": res.data,
        "total": res.count,
        "page": page
    }

@router.get("/analyses/{analysis_id}/report")
async def get_report(
    analysis_id: str,
    account_id: str = Depends(get_current_account)
):
    # Fetch analysis and items
    res = supabase.table("analyses").select("*").eq("id", analysis_id).eq("account_id", account_id).execute()
    if not res.data:
        raise HTTPException(404, "Analysis not found")

    analysis_data = res.data[0]
    analysis = Analysis(**analysis_data)

    items_res = supabase.table("analysis_items").select("*").eq("analysis_id", analysis_id).execute()
    items = [AnalysisItem(**i) for i in items_res.data]

    pdf_bytes = generate_pdf_report(analysis, items)

    # Upload report to storage (Private)
    report_path = f"{account_id}/{analysis_id}.pdf"
    try:
        supabase.storage.from_("reports").upload(report_path, pdf_bytes, file_options={"content-type": "application/pdf", "upsert": "true"})
        # Store path, not public URL
        supabase.table("analyses").update({"report_url": report_path}).eq("id", analysis_id).execute()
    except Exception as e:
        print(f"Report upload error: {e}")
        # Continue to return bytes

    # Return Content directly (Secure)
    from fastapi.responses import Response
    return Response(content=pdf_bytes, media_type="application/pdf")

@router.delete("/analyses/{analysis_id}")
async def delete_analysis(
    analysis_id: str,
    account_id: str = Depends(get_current_account)
):
    res = supabase.table("analyses").delete().eq("id", analysis_id).eq("account_id", account_id).execute()
    if not res.data:
        raise HTTPException(404, "Analysis not found")

    return {"message": "Analysis deleted"}
