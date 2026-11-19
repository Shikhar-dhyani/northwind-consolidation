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
the default accounting/offline-review run needs no internet, model credentials or optional PDF packages.

## Suggested walkthrough

| Minutes | Demonstration |
|---|---|
| 0-5 | Explain the group, acquisition period, policy constraints and incomplete inputs. |
| 5-12 | Show architecture: deterministic arithmetic, implemented Claude review agent, no agent ledger authority. |
| 12-20 | Trace revenue and India goodwill/NCI from controls through source/rate rows and postings. |
| 20-28 | Explain JE-006 rejection, duplicate/overlap holds, mapping correction and IC causes. |
| 28-38 | Predict changed inputs, then run selected examples below. |
| 38-45 | Explain actual AI mistakes, current limits, three-month plan and questions. |

## Agent demonstration

Open AGENT_REVIEW.md, consolidation/review.py and consolidation/claude_foundry.py.
Show review_report.json and agent_trace.json: mode, model, evidence calls, rejected
proposals and pending human review. The default baseline is offline rules, not a model.
With the ignored .env configured, run the same command with --review live for actual
Azure Claude tool use. Predict that financial controls do not change. A missing key,
provider error or exhausted agent budget yields review status failed and CLI exit 3;
valid accounting outputs remain available. Do not present protocol fixtures as a live run.

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

Before the session, reread these paths and explain their boundaries without relying
on the transcript:

- consolidation/journals.py: parsed dates and net-account fingerprints, prospective
  accrual balances, and the distinction between rejection and review holds.
- consolidation/scenarios.py: conditional opening-equity bridge, the explicit whitelist
  of unknowns covered by A1/A1.gross/A2, and rejection of other unquantified dependencies.
- consolidation/publication.py: complete staged generations, directory swaps, Windows
  lock retries, and failure-result invalidation. Know the documented OS/concurrency limits.
- consolidation/reporting.py: final rounding, null reasons, posting provenance and output schemas.

For journal changes, predict both classification and the amount effect. Removing held
JE-019 changes the held count but no amounts. Removing posted JE-014 lets the otherwise
identical JE-019 become the retained audit accrual, so the expense is still recorded once.
Increasing both legs of a valid US expense/accrual journal by USD 1,000 changes translated
expense by 1,000 / 1.278 and the liability by 1,000 / 1.253; changing only one leg instead
rejects the whole now-unbalanced journal, not just its difference. Default group profit remains null until SGD closing
FX is supplied; NCI is unaffected by a parent-only expense change.

GitHub Actions runs the suite and the one-command consolidation on clean Linux CI
runners for Python 3.11 and 3.14. Those automated checks complement a fresh local clone;
they do not replace your own rehearsal on another computer before the live session.

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
