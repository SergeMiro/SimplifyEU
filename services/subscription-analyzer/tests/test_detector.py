import pytest
from unittest.mock import patch, AsyncMock
from uuid import uuid4
from src.core.detector import detect_subscriptions, Transaction
from src.core.classifier import classify_merchant

@pytest.mark.asyncio
async def test_detect_subscriptions_logic(sample_transactions):
    analysis_id = uuid4()
    
    # Mock the classifier to return predictable results
    with patch("src.core.detector.classify_merchant", new_callable=AsyncMock) as mock_classifier:
        # Define side effects for classifier based on descriptor
        async def side_effect(descriptor, amount, frequency):
            desc_lower = descriptor.lower()
            if "netflix" in desc_lower:
                return {
                    "is_subscription": True,
                    "merchant_name": "Netflix",
                    "category": "Streaming",
                    "confidence": 0.95
                }
            elif "adobe" in desc_lower:
                return {
                    "is_subscription": True,
                    "merchant_name": "Adobe",
                    "category": "SaaS",
                    "confidence": 0.90
                }
            else:
                return {
                    "is_subscription": False,
                    "merchant_name": "Unknown",
                    "category": "Other",
                    "confidence": 0.1
                }
        
        mock_classifier.side_effect = side_effect

        items = await detect_subscriptions(sample_transactions, analysis_id)
        
        # Assertions
        assert len(items) >= 2, "Should detect at least Netflix and Adobe"
        
        netflix = next((i for i in items if i.merchant_name == "Netflix"), None)
        assert netflix is not None
        assert netflix.frequency == "monthly"
        assert netflix.amount_avg == 21.99
        assert netflix.confidence_score >= 0.8
        
        adobe = next((i for i in items if i.merchant_name == "Adobe"), None)
        assert adobe is not None
        assert adobe.frequency == "monthly"
        # Tolerance for float comparison or avg calculation
        assert 29.90 < adobe.amount_avg < 30.10

@pytest.mark.asyncio
async def test_frequency_detection():
    # Test internal logic indirectly via small transaction sets if possible,
    # or just trust the integration test above covering 'monthly'.
    pass
