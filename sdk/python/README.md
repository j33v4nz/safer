# Python SDK

Install the CLI package first: `pip install -e ../../cli`.

```python
from laya_guardrail import Guardrail

guard = Guardrail(source="support-agent")
guard.require(user_prompt)  # raises GuardBlocked before the provider call
response = client.responses.create(model="...", input=user_prompt)
```

Use the same line before every model call, tool call, or untrusted document ingestion point.
