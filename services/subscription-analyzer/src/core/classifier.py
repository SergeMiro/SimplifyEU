import httpx
import json
from ..config import settings

async def classify_merchant(descriptor: str, amount: float, frequency: str) -> dict:
    """
    Calls LLM API (Mistral or Chutes.ai) to classify if transaction is a subscription.
    """
    # Quick mock return if no keys for testing
    if not settings.MISTRAL_API_KEY and not settings.CHUTES_API_KEY:
        # Fallback simple logic
        is_sub = "subscription" in descriptor.lower() or frequency in ["monthly", "annual"]
        return {
            "is_subscription": is_sub,
            "merchant_name": descriptor.title(),
            "category": "Other",
            "confidence": 0.5
        }

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
        url = "https://api.chutes.ai/v1/chat/completions"
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
            return json.loads(content)
        except Exception as e:
            print(f"Mistral API error: {e}")
            # Return safe default
            return {
                "is_subscription": False,
                "merchant_name": descriptor,
                "category": "Unknown",
                "confidence": 0.0
            }
