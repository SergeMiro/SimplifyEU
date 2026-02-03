import httpx
import json
import logging
from ..config import settings
from .cache import cache_get, cache_set, generate_cache_key

logger = logging.getLogger(__name__)


async def classify_merchant(descriptor: str, amount: float, frequency: str) -> dict:
    """
    Calls LLM API (Mistral or Chutes.ai) to classify if transaction is a subscription.
    Results are cached for 24 hours to reduce API costs.
    """
    # Generate cache key based on input parameters
    cache_key = generate_cache_key(
        prompt=f"{descriptor}|{amount}|{frequency}",
        model=settings.LLM_PROVIDER,
        temperature=0.0
    )
    
    # Check cache first
    cached_result = cache_get(cache_key)
    if cached_result:
        logger.debug(f"[CLASSIFIER] Cache HIT for: {descriptor[:30]}...")
        return cached_result
    
    # Quick mock return if no keys for testing
    if not settings.MISTRAL_API_KEY and not settings.CHUTES_API_KEY:
        # Fallback simple logic
        is_sub = "subscription" in descriptor.lower() or frequency in ["monthly", "annual"]
        result = {
            "is_subscription": is_sub,
            "merchant_name": descriptor.title(),
            "category": "Other",
            "confidence": 0.5
        }
        cache_set(cache_key, result)
        return result

    prompt = f"""
You are a financial analyst. Analyze this recurring transaction:
- Descriptor: "{descriptor}"
- Amount: €{amount}
- Frequency: {frequency}

Determine:
1. Is this likely a subscription? (yes/no)
2. What is the probable merchant name? (guess if unclear)
3. Category: SaaS, Streaming, Cloud, Telecom, Utilities, Insurance, Other
4. Your confidence (0-1)

Respond in JSON:
{{
  "is_subscription": bool,
  "merchant_name": "string",
  "category": "string",
  "confidence": float
}}
"""

    if settings.LLM_PROVIDER == "chutes":
        url = f"{settings.CHUTES_BASE_URL.rstrip('/')}/chat/completions"
        api_key = settings.CHUTES_API_KEY
        model = settings.CHUTES_MODEL
    else:
        url = "https://api.mistral.ai/v1/chat/completions"
        api_key = settings.MISTRAL_API_KEY
        model = "mistral-small-latest"

    async with httpx.AsyncClient() as client:
        try:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": model,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "response_format": {"type": "json_object"}
            }
            
            response = await client.post(url, headers=headers, json=payload, timeout=20.0)
            response.raise_for_status()
            data = response.json()
            content = data['choices'][0]['message']['content']
            result = json.loads(content)
            
            # Cache successful result
            cache_set(cache_key, result)
            logger.debug(f"[CLASSIFIER] Cached result for: {descriptor[:30]}...")
            
            return result
        except Exception as e:
            logger.warning(f"[CLASSIFIER] LLM API error: {e}")
            # Return safe default (don't cache errors)
            return {
                "is_subscription": False,
                "merchant_name": descriptor,
                "category": "Unknown",
                "confidence": 0.0
            }

