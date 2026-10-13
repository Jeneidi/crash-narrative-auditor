(() => {
  const $ = (selector) => document.querySelector(selector);
  const escapeHtml = (value) => String(value).replace(/[&<>"']/g, (char) => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[char]));
  const percent = (value) => `${(value * 100).toFixed(1)}%`;
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
    runResult.innerHTML = `<div class="run-meta">${escapeHtml(run.reporting_entity)} / ${escapeHtml(run.report_id)} / ${escapeHtml(run.submission_date)}</div><div class="narrative-box">${highlight(run.narrative, evidence)}</div><div class="field-list">${run.fields.map((field) => `<div class="field-row"><div class="field-head"><span class="field-label">${escapeHtml(field.label)}</span><span class="chip ${field.agree ? "chip-good" : ""}">${field.agree ? "matches filing" : "differs from filing"}</span></div><div class="field-values"><strong>${escapeHtml(field.predicted)}</strong><span class="filed-value">Company filed: ${escapeHtml(field.filed)}</span></div><div class="evidence">${field.evidence ? `“${escapeHtml(field.evidence)}”` : "No quote found, so the AI said “not stated”"}</div></div>`).join("")}</div>`;
    copyExample.dataset.copy = run.narrative;
  };
  const renderMetrics = (metrics) => {
    $("#headline-stats").innerHTML = `<div class="stat"><b>${metrics.answered_slot_count.toLocaleString()}</b><span>Answers found in the stories</span></div><div class="stat"><b>${percent(metrics.answered_slot_accuracy.model)}</b><span>AI matched the filing</span></div><div class="stat"><b>${percent(metrics.answered_slot_accuracy.majority)}</b><span>Always guessing the most common answer</span></div><div class="stat"><b>${percent(metrics.evidence_exact_rate)}</b><span>Quotes found word for word in the story</span></div>`;
    $("#metric-rows").innerHTML = Object.entries(metrics.fields).map(([key, value]) => `<tr><td>${escapeHtml(value.majority_value === undefined ? key : ({crash_partner: "Crash partner", roadway_type: "Roadway type", other_party_movement: "Other party movement", injury_severity: "Injury severity"}[key]))}</td><td>${percent(value.coverage.model)}</td><td>${percent(value.answered_slot_accuracy.model)}</td><td>${percent(value.answered_slot_accuracy.majority)}</td><td>${percent(value.answered_slot_accuracy.keyword)}</td><td>${percent(value.all_rows_accuracy.model)}</td><td>${percent(value.all_rows_accuracy.majority)}</td><td>${percent(value.all_rows_accuracy.keyword)}</td></tr>`).join("");
    $("#recording-note").textContent = `${metrics.model_rows} reports set aside for testing: the newest 30% of reports plus every report from the smallest company. Answers recorded with ${metrics.recorded_with}. Cost per 1,000 reports: $${metrics.cash_cost_per_1000.toFixed(2)}, since it ran on an existing Claude subscription.`;
  };
  const renderReview = (disagreements) => {
    $("#review-list").innerHTML = disagreements.top_pairs.map((pair) => `<article class="review-item"><div class="review-head"><div><p class="mono">${escapeHtml(pair.label)}</p><h3 class="h3">Company filed “${escapeHtml(pair.filed)}”, AI read “${escapeHtml(pair.model)}”</h3></div><span class="chip">${pair.count} flagged</span></div><p class="prose">Example report ${escapeHtml(pair.example.report_id)}: “${escapeHtml(pair.example.narrative)}”</p>${pair.example.evidence ? `<p class="evidence">Quote the AI used as proof: “${escapeHtml(pair.example.evidence)}”</p>` : ""}</article>`).join("");
    $("#review-note").textContent = `${disagreements.disagreement_slots} mismatches are flagged for a person to review, in ${disagreements.pair_count} different combinations of filed answer and AI answer. Each one shown here has one real example.`;
  };
  const load = async () => {
    const [demo, metrics, disagreements] = await Promise.all([fetch("data/demo.json").then((response) => response.json()), fetch("data/metrics.json").then((response) => response.json()), fetch("data/disagreements.json").then((response) => response.json())]);
    demo.runs.forEach((run, index) => runSelect.add(new Option(`${run.report_id} / ${run.reporting_entity}`, String(index))));
    renderRun(demo.runs[0]); renderMetrics(metrics); renderReview(disagreements);
    runSelect.addEventListener("change", () => renderRun(demo.runs[Number(runSelect.value)]));
  };
  const prompt = (narrative) => `Extract crash_partner, roadway_type, other_party_movement, and injury_severity from this crash narrative. Return strict JSON with each answer plus an evidence span. Use not stated when silent. Narrative: ${narrative}`;
  $("#save-key").addEventListener("click", () => { const key = $("#api-key").value.trim(); if (!key) { $("#live-status").textContent = "Paste a key before saving."; return; } sessionStorage.setItem(`cna-${$("#provider").value}-key`, key); $("#api-key").value = ""; $("#live-status").textContent = "Key saved for this browser tab only."; });
  $("#run-live").addEventListener("click", async () => { const provider = $("#provider").value; const key = sessionStorage.getItem(`cna-${provider}-key`); const narrative = $("#live-input").value.trim(); if (!key || !narrative) { $("#live-status").textContent = "Save a key and paste a crash story first."; return; } $("#live-status").textContent = "Reading the story..."; try { const url = provider === "anthropic" ? "https://api.anthropic.com/v1/messages" : "https://api.openai.com/v1/chat/completions"; const headers = provider === "anthropic" ? {"content-type":"application/json","x-api-key":key,"anthropic-version":"2023-06-01","anthropic-dangerous-direct-browser-access":"true"} : {"content-type":"application/json","authorization":`Bearer ${key}`}; const body = provider === "anthropic" ? {model:"claude-3-5-haiku-latest",max_tokens:800,messages:[{role:"user",content:prompt(narrative)}]} : {model:"gpt-4o-mini",temperature:0,messages:[{role:"user",content:prompt(narrative)}],response_format:{type:"json_object"}}; const response = await fetch(url, {method:"POST", headers, body:JSON.stringify(body)}); if (!response.ok) throw new Error(`the AI service returned error ${response.status}`); const payload = await response.json(); const text = provider === "anthropic" ? payload.content?.[0]?.text : payload.choices?.[0]?.message?.content; $("#live-status").textContent = text || "The AI service sent back no text."; } catch (error) { $("#live-status").textContent = `It did not work: ${error.message}`; } });
  load().catch((error) => { runResult.textContent = `The saved examples did not load: ${error.message}`; });
})();
