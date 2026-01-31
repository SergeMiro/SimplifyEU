import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from datetime import datetime, timedelta
from src.core.detector import Transaction

@pytest.fixture
def sample_transactions():
    """Generates a list of sample transactions with some subscriptions"""
    base_date = datetime.now()
    txns = []
    
    # Subscription: Netflix (Monthly)
    for i in range(3):
        txns.append(Transaction(
            date=(base_date - timedelta(days=30*i)).date(),
            description="Netflix.com",
            amount=21.99,
            currency="EUR"
        ))

    # Subscription: Adobe (Monthly, slight variation in amount)
    for i in range(3):
        txns.append(Transaction(
            date=(base_date - timedelta(days=30*i)).date(),
            description="Adobe Creative Cloud",
            amount=29.99 if i == 0 else 30.00, # slight variance
            currency="EUR"
        ))
        
    # Random One-off: Restaurant
    txns.append(Transaction(
        date=base_date.date(),
        description="Local Restaurant",
        amount=45.50,
        currency="EUR"
    ))
    
    return txns
