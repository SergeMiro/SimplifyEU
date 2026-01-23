# Subscription Leak Detector

Microservice for detecting unused subscriptions from bank statements.

## Features
- **CSV Parsing**: Parses bank statements (CSV).
- **Subscription Detection**: Clustering algorithm + Frequency analysis.
- **AI Classification**: Uses Mistral API to classify merchants and categories.
- **Reporting**: Generates PDF reports with findings.

## Tech Stack
- **Language**: Python 3.11+
- **Framework**: FastAPI
- **Database**: Supabase (PostgreSQL)
- **AI**: Mistral API
- **PDF**: ReportLab

## Setup

### Prerequisites
- Docker & Docker Compose
- Supabase Project (URL & Key)
- Mistral API Key

### Environment Variables
Create `.env` file in `services/subscription-analyzer`:
```bash
SUPABASE_URL=your_url
SUPABASE_KEY=your_key
MISTRAL_API_KEY=your_mistral_key
REDIS_URL=redis://redis:6379/0
```

### Running with Docker
The service is part of the root `docker-compose.yml`.
```bash
docker-compose up --build subscription-analyzer
```
Service will be available at `http://localhost:8001`.

### Local Development
```bash
cd services/subscription-analyzer
pip install -r requirements.txt
uvicorn src.main:app --reload --port 8001
```

## API Endpoints

### POST /v1/analyses
Upload a CSV file for analysis.
- Headers: `X-API-Key`, `X-Account-ID`, `X-User-ID`
- Body: `file` (multipart/form-data)

### POST /v1/analyses/{id}/run
Start the analysis process (async).

### GET /v1/analyses/{id}
Get analysis status and results.

### GET /v1/analyses/{id}/report
Download PDF report.

## Testing
```bash
# Set environment variables for testing
export SUPABASE_URL=mock
export SUPABASE_KEY=mock
export MISTRAL_API_KEY=mock
export REDIS_URL=mock
pytest
```
