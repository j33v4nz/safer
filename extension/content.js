const editableSelectors = ["textarea", "[contenteditable='true']", "[role='textbox']"];
const sendSelectors = ["button[type='submit']", "button[aria-label*='Send' i]", "button[data-testid*='send' i]"];
let bypassOnce = false;
let checking = false;

function editable(target) { return target && target.closest(editableSelectors.join(",")); }
function textOf(node) { return node instanceof HTMLTextAreaElement ? node.value : (node?.innerText || "").trim(); }
function notice(message, kind = "info") { let el = document.querySelector("#safer-notice"); if (!el) { el = document.createElement("div"); el.id = "safer-notice"; document.body.append(el); } el.className = kind; el.textContent = message; setTimeout(() => el?.remove(), 5000); }
function inspect(text) { return chrome.runtime.sendMessage({ type: "inspect", text, source: location.hostname }); }

async function authorize(node, retry) {
  const text = textOf(node);
  if (!text || checking) return true;
  checking = true; notice("Safer is checking this prompt…");
  const result = await inspect(text); checking = false;
  if (result.status === "ok" && result.decision === "allow") { document.querySelector("#safer-notice")?.remove(); bypassOnce = true; retry(); return true; }
  if (result.status === "ok") { notice(`Blocked locally: ${Math.round(Math.max(...Object.values(result.scores).map(s => s.probability)) * 100)}% policy risk.`, "block"); return false; }
  if (result.status === "unavailable" && result.failMode === "block") { notice("Blocked: local Safer service is unavailable.", "block"); return false; }
  notice(result.status === "unconfigured" ? "Safer needs setup in extension Options." : "Local guardrail unavailable — warning only.", "warn"); bypassOnce = true; retry(); return true;
}

document.addEventListener("paste", async (event) => { const node = editable(event.target); if (!node || bypassOnce) return; event.preventDefault(); const pasted = event.clipboardData?.getData("text/plain") || ""; const original = textOf(node); const result = await inspect(`${original}\n${pasted}`); if (result.status === "ok" && result.decision === "block") return notice("Paste blocked locally due to guardrail policy.", "block"); if (result.status !== "ok" && result.failMode === "block") return notice("Paste blocked: local guardrail unavailable.", "block"); if (node instanceof HTMLTextAreaElement) { node.setRangeText(pasted, node.selectionStart, node.selectionEnd, "end"); node.dispatchEvent(new InputEvent("input", { bubbles: true, inputType: "insertFromPaste", data: pasted })); } else document.execCommand("insertText", false, pasted); }, true);
document.addEventListener("keydown", (event) => { const node = editable(event.target); if (!node || event.key !== "Enter" || event.shiftKey) return; if (bypassOnce) { bypassOnce = false; return; } event.preventDefault(); authorize(node, () => node.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }))); }, true);
document.addEventListener("click", (event) => { const button = event.target.closest(sendSelectors.join(",")); if (!button) return; if (bypassOnce) { bypassOnce = false; return; } const node = document.querySelector(editableSelectors.join(",")); if (!node || !textOf(node)) return; event.preventDefault(); event.stopImmediatePropagation(); authorize(node, () => button.click()); }, true);
