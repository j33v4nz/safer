from __future__ import annotations

import json
import os
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class GuardBlocked(RuntimeError):
    """Raised before an unsafe prompt is passed to a model provider."""


@dataclass(frozen=True)
class Decision:
    allowed: bool
    payload: dict


def inspect(text: str, *, endpoint: str | None = None, token: str | None = None, source: str = "cli", timeout: float = 9) -> Decision:
    endpoint = (endpoint or os.environ.get("LAYA_GUARD_ENDPOINT", "http://127.0.0.1:8787")).rstrip("/")
    token = token or os.environ.get("LAYA_GUARD_TOKEN")
    if not token:
        raise RuntimeError("LAYA_GUARD_TOKEN is required")
    request = Request(f"{endpoint}/v1/inspect", data=json.dumps({"text": text, "source": source}).encode(), headers={"Content-Type": "application/json", "X-Laya-Guard-Token": token}, method="POST")
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read())
    except (HTTPError, URLError) as exc:
        raise RuntimeError(f"local Safer service is unavailable: {exc}") from exc
    return Decision(allowed=payload.get("decision") == "allow", payload=payload)


def require_allowed(text: str, **kwargs: object) -> dict:
    decision = inspect(text, **kwargs)
    if not decision.allowed:
        scores = decision.payload.get("scores", {})
        highest = max((item.get("probability", 0) for item in scores.values()), default=0)
        raise GuardBlocked(f"prompt blocked by local policy (highest risk {highest:.0%})")
    return decision.payload
