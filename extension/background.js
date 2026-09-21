const defaults = { endpoint: "http://127.0.0.1:8787", token: "", failMode: "warn" };

async function settings() {
  return { ...defaults, ...(await chrome.storage.local.get(defaults)) };
}

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message.type !== "inspect" || typeof message.text !== "string") return;
  (async () => {
    const config = await settings();
    if (!config.token) return sendResponse({ status: "unconfigured" });
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 9000);
    try {
      const response = await fetch(`${config.endpoint.replace(/\/$/, "")}/v1/inspect`, {
        method: "POST", signal: controller.signal,
        headers: { "Content-Type": "application/json", "X-Safer-Token": config.token },
        body: JSON.stringify({ text: message.text, source: message.source || location.hostname })
      });
      if (!response.ok) throw new Error(`service responded ${response.status}`);
      sendResponse({ status: "ok", ...(await response.json()) });
    } catch (_error) {
      sendResponse({ status: "unavailable", failMode: config.failMode });
    } finally { clearTimeout(timeout); }
  })();
  return true;
});
