# Crash Narrative Auditor

An evidence-backed extraction benchmark that turns autonomous driving logs into four structured crash fields with verbatim quotes, then scores the result against NHTSA's filed columns.

Live demo: https://crash-narrative-auditor.mjeneidi.com

## The problem

Autonomous-vehicle teams triage free-text crash narratives for anomaly detection, root cause analysis, perception failures and long-tail scenarios. A useful extraction tool must answer `not stated` when a narrative is silent, preserve the exact evidence span, and make its evaluation visible. The same schema can support battery incident review and IoT telematics without hiding label noise behind a polished interface.

## The result

On the 1,196 field values the narratives actually state, the extractor matches the filed value 81.2% versus 40.6% for majority guessing on the same values, abstains on the rest, and every evidence quote is checked (99.9% exact).

The favorable majority baseline is computed from the most common filed value in these same test rows. Keyword and majority results below are evaluated on the same answered slots as the model, with all-row accuracy retained for transparency.

| Field | Coverage | Model answered | Majority answered | Keyword answered | Model all rows | Majority all rows | Keyword all rows |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Crash partner | 98.9% | 96.4% | 29.8% | 75.2% | 95.3% | 30.0% | 74.3% |
| Roadway type | 57.4% | 63.9% | 59.2% | 38.0% | 36.7% | 73.4% | 22.3% |
| Other party movement | 82.2% | 75.9% | 26.3% | 16.2% | 66.4% | 28.4% | 15.5% |
| Injury severity | 30.9% | 78.8% | 78.8% | 11.7% | 24.3% | 85.6% | 4.3% |

Roadway type and injury severity barely beat or tie majority on answered slots because one filed category dominates each field, and narratives rarely state property damage. Measured runtime was 3.78 seconds per report. Cash cost per 1,000 reports was $0.00 through the Claude Code subscription CLI.

## How it works

1. Load the public NHTSA Standing General Order ADS CSV with pandas.
2. Split by report submission month: newest 30%, plus every report from the smallest reporting entity.
3. Ask Claude Haiku 5.5 for four enumerated fields and a verbatim evidence span for each.
4. Validate with Pydantic, exact substring checks and a deterministic keyword baseline.
5. Compare answered-slot and all-row accuracy with bootstrap 95% confidence intervals, then queue disagreements for human review.

## Data and license

The source is the [NHTSA Standing General Order ADS incident CSV](https://static.nhtsa.gov/odi/ffdd/sgo-2021-01/SGO-2021-01_Incident_Reports_ADS.csv), a US government public-domain dataset. The build fetched 2,581,860 bytes and parsed 1,478 narrative rows on 2026-10-12. Raw data is ignored locally and can be restored with `scripts/download_data.py`.

## Evaluation method

The structured columns are a useful built-in answer key, not perfect truth. The headline metric is exact accuracy over the 1,196 field slots where the model answered. The majority baseline is the most common filed value per field computed on the test rows, which makes it a favorable comparison. Keyword and majority accuracy on answered slots use the same rows as the model. The model output is recorded from Claude Haiku 5.5 via Claude Code on 2026-10-12, cached in batches, and never calls `api.openai.com`. A queue of 50 model versus filed disagreements plus the most common filed/model pairs is included for human review. It is not presented as a completed hand check.

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
