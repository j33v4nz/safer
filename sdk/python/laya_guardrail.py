"""Provider-neutral policy gate for Python AI applications and agent frameworks."""
from laya_guard.client import Decision, GuardBlocked, inspect, require_allowed


class Guardrail:
    def __init__(self, *, endpoint: str | None = None, token: str | None = None, source: str = "python-sdk"):
        self.endpoint, self.token, self.source = endpoint, token, source

    def inspect(self, prompt: str) -> Decision:
        return inspect(prompt, endpoint=self.endpoint, token=self.token, source=self.source)

    def require(self, prompt: str) -> dict:
        return require_allowed(prompt, endpoint=self.endpoint, token=self.token, source=self.source)


__all__ = ["Guardrail", "GuardBlocked"]
