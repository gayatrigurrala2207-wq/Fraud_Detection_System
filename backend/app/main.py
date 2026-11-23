"""FastAPI entry point: `python -m uvicorn app.main:app --reload` from backend/."""

import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import VERSION, get_settings
from app.replay import ReplayWorker
from app.routes import cases, dataset, health, insights, overview, replay, settings, transactions


@asynccontextmanager
async def lifespan(app: FastAPI):
    worker = ReplayWorker(get_settings())
    app.state.worker = worker
    task = asyncio.create_task(worker.run())
    yield
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task


app = FastAPI(title="FraudShield API", version=VERSION, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(get_settings().cors_origins),
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
for module in (health, dataset, settings, overview, transactions, cases, insights, replay):
    app.include_router(module.router, prefix="/api")
