from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api.v1 import analyses
from .utils.logger import setup_logger

logger = setup_logger("subscription-analyzer")

app = FastAPI(
    title="Subscription Leak Detector",
    description="Microservice for analyzing bank statements to detect subscriptions.",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analyses.router, prefix="/v1", tags=["analyses"])

@app.get("/health")
def health_check():
    return {"status": "ok"}
