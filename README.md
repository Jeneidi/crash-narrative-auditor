# Crash Narrative Auditor

An evidence-backed extraction benchmark that turns autonomous driving logs into four structured crash fields with verbatim quotes, then scores the result against NHTSA's filed columns.

Live demo: https://crash-narrative-auditor.mjeneidi.com

## The problem

Autonomous-vehicle teams triage free-text crash narratives for anomaly detection, root cause analysis, perception failures and long-tail scenarios. A useful extraction tool must answer `not stated` when a narrative is silent, preserve the exact evidence span, and make its evaluation visible. The same schema can support battery incident review and IoT telematics without hiding label noise behind a polished interface.

## The result

On 444 held-out reports from the NHTSA ADS incident CSV, the auditor reached 55.68693693693694% macro accuracy versus 29.11036036036036% for a keyword and regex baseline. Evidence quotes were exact narrative substrings for 99.88738738738738% of fields, and non-abstained accuracy was 81.18729096989966%. Measured runtime was 3.7754842342342343 seconds per report. Cash cost per 1,000 reports was $0.00 through the Claude Code subscription CLI.

Per-field model accuracy versus baseline: crash partner 95.27027027027027% versus 74.32432432432432%, roadway type 36.711711711711715% versus 22.2972972972973%, other party movement 66.44144144144144% versus 15.54054054054054%, and injury severity 24.324324324324326% versus 4.2792792792792795%.

## How it works

1. Load the public NHTSA Standing General Order ADS CSV with pandas.
2. Split by report submission month: newest 30%, plus every report from the smallest reporting entity.
3. Ask Claude Haiku 5.5 for four enumerated fields and a verbatim evidence span for each.
4. Validate with Pydantic, exact substring checks and a deterministic keyword baseline.
5. Compare field accuracy with bootstrap 95% confidence intervals and queue disagreements for review.

## Data and license

The source is the [NHTSA Standing General Order ADS incident CSV](https://static.nhtsa.gov/odi/ffdd/sgo-2021-01/SGO-2021-01_Incident_Reports_ADS.csv), a US government public-domain dataset. The build fetched 2,581,860 bytes and parsed 1,478 narrative rows on 2026-10-12. Raw data is ignored locally and can be restored with `scripts/download_data.py`.

## Evaluation method

The structured columns are a useful built-in answer key, not perfect truth. The headline metric is macro average of exact per-field accuracy across crash partner, roadway type, other party pre-crash movement and highest injury severity alleged. The baseline uses transparent keyword and regex-style aliases. The model output is recorded from Claude Haiku 5.5 via Claude Code on 2026-10-12, cached in batches, and never calls `api.openai.com`. A queue of 50 model versus filed disagreements is included for human review. It is not presented as a completed hand check.

## How to run

```bash
uv venv .venv --python 3.11
uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/python scripts/download_data.py
.venv/bin/python scripts/prepare_data.py
.venv/bin/python scripts/run_baseline.py
.venv/bin/python scripts/run_llm_eval.py
.venv/bin/python scripts/evaluate.py
.venv/bin/python scripts/build_site_data.py
.venv/bin/pytest -q
cd site && python3 -m http.server 8000 --bind 127.0.0.1
```

The test gate is `.venv/bin/pytest -q`. The site is plain HTML, CSS and JavaScript with no build step. A BYOK mode stores a provider key only in `sessionStorage` and sends it only to the selected provider.

## Limitations

Waymo is the majority of the source rows, so the result may not generalize across manufacturers. Filed structured fields can be wrong or incomplete, especially when the narrative uses `Other, see Narrative` or leaves a field blank. The 50 disagreement records are queued for a human hand check, but no hand check was claimed or completed during this build. The live BYOK mode is not used for the recorded metrics. The static demo shows 20 recorded held-out reports.

## Credits

NHTSA for the public data, the Project Site Kit for the static site foundation, and Claude Haiku 5.5 through Claude Code for the recorded extraction run.
