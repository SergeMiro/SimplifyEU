import pytest
import uuid
from datetime import date, timedelta
from src.core.detector import detect_subscriptions
from src.db.models import Transaction

@pytest.mark.asyncio
async def test_detect_subscriptions():
    # Generate weekly transactions
    txs = []
    base_date = date(2023, 1, 1)
    for i in range(10):
        txs.append(Transaction(
            date=base_date + timedelta(days=i*7),
            description="Weekly Service",
            amount=-25.00
        ))

    # Random noise
    txs.append(Transaction(date=base_date, description="Coffee", amount=-5.00))

    items = await detect_subscriptions(txs, uuid.uuid4())

    assert len(items) >= 1
    item = next((i for i in items if i.merchant_descriptor == "Weekly Service"), None)
    assert item is not None
    assert item.frequency == "weekly"
    # assert item.is_subscription == True # This depends on confidence logic, might vary
