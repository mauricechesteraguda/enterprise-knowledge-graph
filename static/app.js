(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const escapeHtml = (value) => String(value ?? "").replace(/[&<>'"]/g, (char) => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;","\"":"&quot;"}[char]));
  const setStatus = (id, text, state = "pending") => { const node = $(id); node.textContent = text; node.className = `status ${state}`; };
  const fetchJson = async (url, options = {}) => { const response = await fetch(url, options); const body = await response.json().catch(() => ({})); if (!response.ok) throw new Error(body?.error?.code || "request_failed"); return body; };
  const renderCards = (target, items) => { const node = $(target); node.innerHTML = items.map((item) => `<div class="card"><small>${escapeHtml(item.label)}</small><strong>${escapeHtml(item.value)}</strong></div>`).join(""); node.setAttribute("aria-busy", "false"); };
  async function loadHealth() { // type-10052026-Maurice: Render safe, bounded operational state.
    try { const data = await fetchJson("/v1/health"); const required = data.required || {}; const optional = data.optional || {}; renderCards("health-cards", [{label:"Graph",value:required.graph || "unknown"},{label:"Vector",value:optional.vector || "degraded"},{label:"LLM",value:optional.llm || "degraded"},{label:"Data as of",value:data.data_as_of || "unknown"}]); setStatus("health-status", data.status === "ok" ? "Healthy" : "Degraded", data.status === "ok" ? "ok" : "warn"); } catch (error) { renderCards("health-cards", [{label:"API",value:"Unavailable"}]); setStatus("health-status", "Unavailable", "error"); }
  }
  async function loadStats() { // type-10052026-Maurice: Show only numeric aggregate counters.
    try { const data = await fetchJson("/v1/stats"); const stats = data.stats || {}; const items = Object.entries(stats).slice(0, 8).map(([label, value]) => ({label, value})); renderCards("stats-cards", items.length ? items : [{label:"Snapshot",value:"No counters"}]); setStatus("stats-status", "Loaded", "ok"); } catch (error) { renderCards("stats-cards", [{label:"Snapshot",value:"Unavailable"}]); setStatus("stats-status", "Unavailable", "error"); }
  }
  async function ask() { // type-10052026-Maurice: Keep prompt content in the request body and out of logs.
    const question = $("question").value.trim(); if (!question) { $("ask-message").textContent = "Enter a question or choose a sample."; return; }
    $("ask").disabled = true; $("answer-card").hidden = true; setStatus("answer-status", "Thinking", "pending"); $("ask-message").textContent = "";
    try { const data = await fetchJson("/v1/ask", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({question})}); const evidence = data.evidence || data.linked_entities || []; $("answer-card").innerHTML = `<h3>${escapeHtml(data.grounding_status || "Grounded answer")}</h3><p>${escapeHtml(data.answer || "No answer returned.")}</p><div class="evidence"><strong>Evidence</strong><p>${evidence.length ? evidence.map(escapeHtml).join(" · ") : "Evidence snapshot: " + escapeHtml(data.evidence_snapshot_id || "not available")}</p></div>`; $("answer-card").hidden = false; setStatus("answer-status", "Complete", "ok"); } catch (error) { $("ask-message").textContent = error.message === "unsupported_question" ? "This question is outside the supported graph catalog." : "The answer service is unavailable. Try again."; setStatus("answer-status", "Could not answer", "error"); } finally { $("ask").disabled = false; }
  }
  const savedTheme = localStorage.getItem("kg-theme");
  const themeToggle = $("theme-toggle");
  const setTheme = (theme) => { document.documentElement.dataset.theme = theme; const light = theme === "light"; themeToggle.textContent = light ? "Use dark mode" : "Use light mode"; themeToggle.setAttribute("aria-pressed", String(light)); localStorage.setItem("kg-theme", theme); };
  setTheme(savedTheme || (window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark"));
  themeToggle.addEventListener("click", () => setTheme(document.documentElement.dataset.theme === "light" ? "dark" : "light"));
  $("sample-question").addEventListener("change", (event) => { if (event.target.value) $("question").value = event.target.value; });
  $("question").addEventListener("keydown", (event) => { if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) { event.preventDefault(); ask(); } });
  $("ask").addEventListener("click", ask); loadHealth(); loadStats();
})();
