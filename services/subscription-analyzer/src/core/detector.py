import statistics
import re
import uuid
from collections import defaultdict
from typing import List
from uuid import UUID
from datetime import date, datetime

from ..db.models import Transaction, AnalysisItem
from .classifier import classify_merchant
from difflib import SequenceMatcher

def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()

async def detect_subscriptions(transactions: List[Transaction], analysis_id: UUID) -> List[AnalysisItem]:
    """
    Analyzes transactions to detect potential subscriptions.
    """
    # 1. Normalization & Grouping
    groups = defaultdict(list)

    for tx in transactions:
        desc = tx.description.lower()
        # Remove digits
        desc_norm = re.sub(r'\d+', '', desc)
        # Remove special chars (keep spaces)
        desc_norm = re.sub(r'[^\w\s]', '', desc_norm)
        # Remove extra spaces
        desc_norm = ' '.join(desc_norm.split())

        # Check against existing keys for similarity
        found_key = None
        # Optimization: only check keys starting with same char or short keys
        for key in groups.keys():
            if similar(key, desc_norm) > 0.8: # Threshold
                found_key = key
                break

        if found_key:
            groups[found_key].append(tx)
        else:
            groups[desc_norm].append(tx)

    candidates = []

    for desc_norm, txs in groups.items():
        if len(txs) < 2:
            continue

        # Sort by date
        txs.sort(key=lambda x: x.date)

        amounts = [abs(t.amount) for t in txs]
        avg_amount = statistics.mean(amounts)

        # Filter amount > 20 EUR
        if avg_amount < 20:
             continue

        # Calculate intervals
        dates = [t.date for t in txs]
        intervals = [(dates[i+1] - dates[i]).days for i in range(len(dates)-1)]
        avg_interval = statistics.mean(intervals) if intervals else 0

        frequency = "irregular"
        if 5 <= avg_interval <= 9:
            frequency = "weekly"
        elif 10 <= avg_interval <= 18:
            frequency = "biweekly"
        elif 25 <= avg_interval <= 35:
            frequency = "monthly"
        elif 80 <= avg_interval <= 100:
            frequency = "quarterly"
        elif 335 <= avg_interval <= 395:
            frequency = "annual"

        if frequency == "irregular":
             continue

        # Confidence Scoring
        confidence = 0.5
        if frequency == "monthly":
            confidence += 0.2

        # Stability of amount
        std_dev = statistics.stdev(amounts) if len(amounts) > 1 else 0
        if std_dev / avg_amount < 0.1:
            confidence += 0.1

        # Keywords
        keywords = ["subscription", "membership", "premium", "plan", "recur"]
        if any(k in desc_norm for k in keywords):
            confidence += 0.1

        # Call classifier
        merchant_name = None
        category = None
        try:
            classification = await classify_merchant(desc_norm, avg_amount, frequency)
            if classification.get("is_subscription"):
                confidence += 0.1
                # Adjust confidence based on LLM confidence?
                # classification['confidence'] is 0-1.
                confidence += (classification.get("confidence", 0) * 0.1)

            merchant_name = classification.get("merchant_name")
            category = classification.get("category")
        except Exception as e:
            # Fallback if classifier fails
            print(f"Classifier error: {e}")
            pass

        # Create candidate
        item = AnalysisItem(
            id=uuid.uuid4(),
            analysis_id=analysis_id,
            merchant_descriptor=txs[0].description,
            merchant_name=merchant_name,
            category=category,
            amount_avg=round(avg_amount, 2),
            amount_min=round(min(amounts), 2),
            amount_max=round(max(amounts), 2),
            currency=txs[0].currency,
            frequency=frequency,
            occurrences=len(txs),
            first_seen=dates[0],
            last_seen=dates[-1],
            confidence_score=min(confidence, 1.0),
            is_subscription=(confidence >= 0.7),
            recommendation=f"Detected {frequency} payment. Check if you still need this.",
            tags=[],
            created_at=datetime.now()
        )
        candidates.append(item)

    # Sort by confidence
    candidates.sort(key=lambda x: x.confidence_score or 0, reverse=True)
    return candidates
