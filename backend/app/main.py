"""FastAPI entry point: `python -m uvicorn app.main:app --reload` from backend/."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import VERSION, get_settings
from app.routes import dataset, health, settings

app = FastAPI(title="FraudShield API", version=VERSION)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(get_settings().cors_origins),
    allow_methods=["GET"],
    allow_headers=["*"],
)
for module in (health, dataset, settings):
    app.include_router(module.router, prefix="/api")
