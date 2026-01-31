# 🧪 Microservices Testing Guide

This guide contains instructions and commands for testing the various microservices within the SimplifyEU ecosystem.

---

## 🔍 Subscription Leak Detector

This service analyzes bank statements (CSV/Excel) to find hidden subscriptions using AI.

### 📁 Test Data Location
All synthetic test files are located in:
`services/subscription-analyzer/tests/test_data/`

### 🛠 How to Test

#### 1. Quick Demo (For Clients)
Use the lightweight CSV with 26 transactions to show immediate results.
- **File:** `services/subscription-analyzer/tests/test_data/simple_test.csv`
- **Action:** Upload via the Dashboard UI at `/dashboard/services/subscription-detector`.

#### 2. Stress Test / Full Analysis
Use the full dataset with 240+ transactions covering a 3-month period.
- **File:** `services/subscription-analyzer/tests/test_data/test_statement.csv` (or `.xlsx`)
- **Action:** Upload via the Dashboard UI.

#### 3. Generate New Data
If you need more data or different patterns, run the generator script:
```bash
cd services/subscription-analyzer/tests/test_data
python generate_test_data.py
```

### 📡 Manual API Testing (cURL)

You can test the backend microservice directly using cURL commands. Ensure the service is running on port 8001.

#### 1. Health Check
```bash
curl -X GET http://localhost:8001/health
```

#### 2. Upload and Analyze CSV
Replace `[ACCOUNT_ID]` and `[USER_ID]` with valid UUIDs from your Supabase setup.
```bash
curl -X POST http://localhost:8001/v1/analyses \
  -H "X-API-Key: sk_test_123" \
  -H "X-Account-ID: [ACCOUNT_ID]" \
  -H "X-User-ID: [USER_ID]" \
  -F "file=@services/subscription-analyzer/tests/test_data/simple_test.csv"
```

#### 3. Run Analysis Task
```bash
curl -X POST http://localhost:8001/v1/analyses/[ANALYSIS_ID]/run \
  -H "X-API-Key: sk_test_123" \
  -H "X-Account-ID: [ACCOUNT_ID]"
```

---

## 🤖 AI Lab (Test Interface)

Standard interface for testing LLM responses and streaming.

### 🛠 How to Test
- **URL:** `/ai-test`
- **Action:** Enter prompts like "Explain subscription leak detection" and observe the real-time streaming response.
- **Backend:** This proxies requests through the `apps/web/api/ai-test` route to Chutes AI.

---

*Note: Always use synthetic data for testing to remain GDPR compliant. Never use real client bank statements in development.*
