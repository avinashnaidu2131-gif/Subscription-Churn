"""
FastAPI application entrypoint.

Loads the pre-trained model artifact at startup (produced by
scripts/train_pipeline.py) and mounts the /optimize-retry, /decline-codes,
and /bank-patterns routes.

Run:
    python scripts/train_pipeline.py      # trains + saves the model once
    uvicorn app.api.main:app --reload     # then serve the API
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config import MODEL_PATH
from app.ml.model import RetryModel
from app.state import set_model

app = FastAPI(
    title="FT-04 Subscription Churn Retry Optimizer",
    description=(
        "Categorizes decline codes, maps issuing-bank/network patterns, and "
        "predicts the optimal localized gateway + datetime to retry a failed charge."
    ),
    version="0.1.0",
)

# Enable CORS for Vercel, localhost, and external integrations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.on_event("startup")
def load_model() -> None:
    if not MODEL_PATH.exists():
        print(
            f"[Startup] WARNING: no model artifact at {MODEL_PATH}. "
            f"Run `python scripts/train_pipeline.py` first, then restart the server."
        )
        return
    model = RetryModel().load(MODEL_PATH)
    set_model(model)
