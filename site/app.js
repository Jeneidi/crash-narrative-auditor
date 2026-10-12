(() => {
  const $ = (selector) => document.querySelector(selector);
  const escapeHtml = (value) => String(value).replace(/[&<>"']/g, (char) => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[char]));
  const percent = (value) => `${value * 100}%`;
  const runSelect = $("#run-select");
  const runResult = $("#run-result");
  const copyExample = $("#copy-example");
  const highlight = (narrative, evidence) => {
    const spans = [...new Set(evidence.filter(Boolean))].sort((a, b) => b.length - a.length);
    if (!spans.length) return escapeHtml(narrative);
    const pattern = new RegExp(`(${spans.map((span) => span.replace(/[.*+?^${}()|[\\]\\]/g, "\\\\$&")).join("|")})`, "g");
    return escapeHtml(narrative).replace(pattern, "<mark>$1</mark>");
  };
  const renderRun = (run) => {
    const evidence = run.fields.map((field) => field.evidence);
    runResult.innerHTML = `<div class="run-meta">${escapeHtml(run.reporting_entity)} / ${escapeHtml(run.report_id)} / ${escapeHtml(run.submission_date)}</div><div class="narrative-box">${highlight(run.narrative, evidence)}</div><div class="field-list">${run.fields.map((field) => `<div class="field-row"><div class="field-head"><span class="field-label">${escapeHtml(field.label)}</span><span class="chip ${field.agree ? "chip-good" : ""}">${field.agree ? "agrees" : "differs"}</span></div><div class="field-values"><strong>${escapeHtml(field.predicted)}</strong><span class="filed-value">Filed: ${escapeHtml(field.filed)}</span></div><div class="evidence">${field.evidence ? `“${escapeHtml(field.evidence)}”` : "No exact evidence span, model abstained"}</div></div>`).join("")}</div>`;
    copyExample.dataset.copy = run.narrative;
  };
  const renderMetrics = (metrics) => {
    $("#headline-stats").innerHTML = `<div class="stat"><b>${percent(metrics.macro_accuracy)}</b><span>Auditor macro accuracy</span></div><div class="stat"><b>${percent(metrics.baseline_macro_accuracy)}</b><span>Keyword baseline</span></div><div class="stat"><b>${percent(metrics.evidence_exact_rate)}</b><span>Evidence exact rate</span></div><div class="stat"><b>${metrics.seconds_per_report} s</b><span>Measured per report</span></div>`;
    const labels = {crash_partner: "Crash partner", roadway_type: "Roadway type", other_party_movement: "Other party movement", injury_severity: "Injury severity"};
    $("#metric-rows").innerHTML = Object.entries(metrics.fields).map(([key, value]) => `<tr><td>${labels[key]}</td><td>${percent(value.model_accuracy)}</td><td>${percent(value.baseline_accuracy)}</td><td>${percent(value.ci95[0])} to ${percent(value.ci95[1])}</td></tr>`).join("");
    $("#recording-note").textContent = `${metrics.model_rows} held-out reports. ${metrics.recorded_with}. Cash cost per 1,000 reports: $${metrics.cash_cost_per_1000.toFixed(2)} through the subscription CLI.`;
  };
  const load = async () => {
    const [demo, metrics] = await Promise.all([fetch("data/demo.json").then((response) => response.json()), fetch("data/metrics.json").then((response) => response.json())]);
    demo.runs.forEach((run, index) => runSelect.add(new Option(`${run.report_id} / ${run.reporting_entity}`, String(index))));
    renderRun(demo.runs[0]); renderMetrics(metrics);
    runSelect.addEventListener("change", () => renderRun(demo.runs[Number(runSelect.value)]));
  };
  const prompt = (narrative) => `Extract crash_partner, roadway_type, other_party_movement, and injury_severity from this crash narrative. Return strict JSON with each answer plus an evidence span. Use not stated when silent. Narrative: ${narrative}`;
  $("#save-key").addEventListener("click", () => { const key = $("#api-key").value.trim(); if (!key) { $("#live-status").textContent = "Enter a key before saving."; return; } sessionStorage.setItem(`cna-${$("#provider").value}-key`, key); $("#api-key").value = ""; $("#live-status").textContent = "Key saved in this tab's sessionStorage."; });
  $("#run-live").addEventListener("click", async () => { const provider = $("#provider").value; const key = sessionStorage.getItem(`cna-${provider}-key`); const narrative = $("#live-input").value.trim(); if (!key || !narrative) { $("#live-status").textContent = "Save a session key and enter a narrative first."; return; } $("#live-status").textContent = "Running live extraction..."; try { const url = provider === "anthropic" ? "https://api.anthropic.com/v1/messages" : "https://api.openai.com/v1/chat/completions"; const headers = provider === "anthropic" ? {"content-type":"application/json","x-api-key":key,"anthropic-version":"2023-06-01","anthropic-dangerous-direct-browser-access":"true"} : {"content-type":"application/json","authorization":`Bearer ${key}`}; const body = provider === "anthropic" ? {model:"claude-3-5-haiku-latest",max_tokens:800,messages:[{role:"user",content:prompt(narrative)}]} : {model:"gpt-4o-mini",temperature:0,messages:[{role:"user",content:prompt(narrative)}],response_format:{type:"json_object"}}; const response = await fetch(url, {method:"POST", headers, body:JSON.stringify(body)}); if (!response.ok) throw new Error(`Provider returned ${response.status}`); const payload = await response.json(); const text = provider === "anthropic" ? payload.content?.[0]?.text : payload.choices?.[0]?.message?.content; $("#live-status").textContent = text || "Provider returned no text."; } catch (error) { $("#live-status").textContent = `Live run failed: ${error.message}`; } });
  load().catch((error) => { runResult.textContent = `Recorded data failed to load: ${error.message}`; });
})();
