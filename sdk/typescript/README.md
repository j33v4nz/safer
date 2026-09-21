# TypeScript SDK

```js
import { requireAllowed } from "@laya/guardrail";

await requireAllowed(userPrompt, { source: "my-agent" });
const response = await provider.responses.create({ input: userPrompt });
```

Call `requireAllowed` before every provider request. It throws `GuardBlocked` when local policy denies the prompt.
