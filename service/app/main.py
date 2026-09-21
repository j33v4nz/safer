from __future__ import annotations

import asyncio
import hmac
import os
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

import laya
from fastapi import FastAPI, Header, HTTPException, Request, status
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

from .questions import GUARD_QUESTIONS, POLICY_VERSION

TOKEN = os.environ.get("SAFER_TOKEN", os.environ.get("LAYA_GUARD_TOKEN", ""))
BLOCK_THRESHOLD = float(os.environ.get("SAFER_BLOCK_THRESHOLD", os.environ.get("LAYA_GUARD_BLOCK_THRESHOLD", "0.80")))
MAX_PROMPT_CHARS = int(os.environ.get("SAFER_MAX_PROMPT_CHARS", os.environ.get("LAYA_GUARD_MAX_PROMPT_CHARS", "12000")))


@dataclass
class Runtime:
    router: Any | None = None
    loaded: bool = False


runtime = Runtime()


@asynccontextmanager
async def lifespan(_: FastAPI):
    if not TOKEN or len(TOKEN) < 24:
        raise RuntimeError("SAFER_TOKEN must be set to a random secret of at least 24 characters")
    # Preloading is intentional: changing language can otherwise trigger expensive model reloads.
    runtime.router = laya.Router(preload=True, max_loaded=2)
    runtime.loaded = True
    yield
    if runtime.router is not None:
        runtime.router.unload()


app = FastAPI(title="Safer", version=POLICY_VERSION, lifespan=lifespan, docs_url=None, redoc_url=None)
# The bearer-like local token remains the authorization boundary; CORS only enables extension fetches.
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET", "POST"], allow_headers=["Content-Type", "X-Safer-Token"])


class InspectRequest(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_PROMPT_CHARS)
    source: str = Field(default="unknown", max_length=80)

    @field_validator("text")
    @classmethod
    def reject_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("text must not be blank")
        return value


class Score(BaseModel):
    probability: float = Field(ge=0, le=1)


class InspectResponse(BaseModel):
    decision: str
    threshold: float
    policy_version: str
    scores: dict[str, Score]
    routing: dict[str, Any]
    latency_ms: int


def _authorized(token: str | None) -> bool:
    return bool(token and hmac.compare_digest(token, TOKEN))


def _probability(answer: dict[str, Any]) -> float:
    """Accept the classifier's `noul` primitive and reject malformed model output."""
    value = answer.get("noul")
    if isinstance(value, (int, float)) and 0 <= value <= 1:
        return float(value)
    raise ValueError("Safer classifier returned an invalid probability")


def _predict(text: str) -> dict[str, Any]:
    if runtime.router is None:
        raise RuntimeError("router is unavailable")
    return runtime.router.predict({"prompt": text}, GUARD_QUESTIONS)


@app.get("/healthz")
async def health() -> dict[str, Any]:
    return {"ready": runtime.loaded, "policy_version": POLICY_VERSION}


@app.post("/v1/inspect", response_model=InspectResponse)
async def inspect(payload: InspectRequest, request: Request, x_safer_token: str | None = Header(default=None)) -> InspectResponse:
    if request.client is None or request.client.host not in {"127.0.0.1", "::1"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="loopback clients only")
    if not _authorized(x_safer_token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid local guard token")

    started = time.perf_counter()
    try:
        result = await asyncio.wait_for(run_in_threadpool(_predict, payload.text), timeout=8)
        answers = result["answers"]
        scores = {name: Score(probability=_probability(answers[name])) for name in GUARD_QUESTIONS}
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="invalid classifier response") from exc
    except TimeoutError as exc:
        raise HTTPException(status_code=503, detail="local classifier timeout") from exc

    decision = "block" if max(score.probability for score in scores.values()) >= BLOCK_THRESHOLD else "allow"
    return InspectResponse(decision=decision, threshold=BLOCK_THRESHOLD, policy_version=POLICY_VERSION, scores=scores, routing=result.get("routing", {}), latency_ms=round((time.perf_counter() - started) * 1000))
