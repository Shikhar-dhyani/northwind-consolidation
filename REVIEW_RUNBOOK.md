# 45-minute review runbook

Use the committed source bundle unchanged. Temporary input changes in the tests use
copies. The original bundle remains the basis for the reported control figures.

## Before the call

```bash
git clone https://github.com/Shikhar-dhyani/northwind-consolidation.git
cd northwind-consolidation
python -m pip install -r requirements.txt
python -m consolidation --data data --out output
python -m pytest -q
```

Check the statement status and issues, not just the process exit code. This bundle
intentionally produces partial_blocked statements. Prepare the repository locally;
the runtime consolidation needs no internet, model, credentials or optional PDF packages.

## Suggested walkthrough

| Minutes | Demonstration |
|---|---|
| 0-5 | Explain the group, acquisition period, policy constraints and incomplete inputs. |
| 5-12 | Show architecture: deterministic arithmetic, proposed review agent, no agent ledger authority. |
| 12-20 | Trace revenue and India goodwill/NCI from controls through source/rate rows and postings. |
| 20-28 | Explain JE-006 rejection, duplicate/overlap holds, mapping correction and IC causes. |
| 28-38 | Predict changed inputs, then run selected examples below. |
| 38-45 | Explain actual AI mistakes, current limits, three-month plan and questions. |

## Focused changed-input examples

First say the prediction aloud using CANDIDATE_GUIDE.md, then run:

```bash
python -m pytest tests/test_pipeline.py -q -k resolving_sgd
python -m pytest tests/test_pipeline.py -q -k changed_revenue
python -m pytest tests/test_pipeline.py -q -k unbalanced_input
python -m pytest tests/test_pipeline.py -q -k instruction_memo
python -m pytest tests/test_pipeline.py -q -k monthly_mismatch
```

The SGD rate of 1.7000 is explicitly a synthetic test input, never the original closing
rate or a reported estimate. The sale example supplies that fixture first so it can
assert numerical changes in profit. On the original bundle, the same sale increases
revenue while reported profit remains null because the SGD dependency is unresolved.

## Files to keep open

| Question | Evidence |
|---|---|
| What are the results? | output/control_figures_sd.json and output/control_explanations.json |
| What was excluded and why? | output/journal_decisions.json and output/issues.json |
| Which rows produced this balance? | output/ledger_postings.csv and consolidated_tb.csv |
| How is an elimination balanced? | output/eliminations.csv and validation.json |
| Was a number recomputed independently? | tests/test_pipeline.py and VALIDATION.md |
| How was AI corrected? | Three fix commits in VALIDATION.md and transcripts/ |
| What is future work rather than implemented? | ARCHITECTURE.md page 6 and REFLECTION.md |

Do not claim complete financial statements, independent personal accounting approval,
a deployed LLM review workflow, atomic publication or a remote CI result unless actual
evidence has subsequently established it. Explain the implemented behavior directly.
