# Submission package - NWG-D0BC

## Six required deliverables

| Requirement | Repository artifact | Status |
|---|---|---|
| Architecture, maximum six pages | ARCHITECTURE.md; optional output/pdf/ARCHITECTURE.pdf | Six-page PDF rendered and visually checked. |
| Working prototype and full history | consolidation/, data/, README.md, tests/, Git history | One-command outputs; independent and changed-input checks. |
| 5-7 decisions | DECISIONS.md | Seven decisions with context, choices, alternatives, reasons, trade-offs and AI contribution. |
| Validation, independent figures and at least three AI mistakes/fix commits | VALIDATION.md | Three actual mistakes/fix commits plus independent financial oracles. |
| AI-session records | transcripts/ | Partial records of one continuous Claude session and visible Codex record. Complete native Claude coverage remains unavailable; provenance and snapshot boundary are explicit. |
| One-page reflection | REFLECTION.md; optional output/pdf/REFLECTION.pdf | One-page PDF rendered and visually checked. |

The missing SGD closing rate and UK historical acquisition/equity evidence are disclosed
financial blockers. The brief explicitly permits null with reasons. No external value or
invented company answer has been inserted to make the figures appear complete.

## Build the review archive

Run financial outputs on their own with the README command. To build the additional
submission archive from a clean committed checkout:

```bash
python -m pip install -r requirements.txt
python scripts/prepare_submission.py
```

Optional PDF attachments:

```bash
python -m pip install -r requirements-docs.txt
python scripts/render_submission_pdfs.py
python scripts/prepare_submission.py --require-pdfs
```

The packager runs the tests, checks original source bytes and transcript hashes, reruns
the accounting engine, verifies a full-history Git bundle, and writes:

- output/submission/northwind-consolidation-NWG-D0BC.zip
- output/submission/northwind-consolidation.bundle
- output/submission/BUILD_REPORT.json

The archive includes committed source, documentation, AI records, generated financial
outputs, any rendered PDF attachments and the Git bundle. Original history is preserved.
The report records the exact source commit, tests, controls and transcript coverage.
PDF generation is optional and is not a dependency of the financial run.

## Transcript boundary

The planning text and transcripts/claude-review-pasted-excerpts.jsonl are partial pieces
of one continuous Claude session, **Assignment explanation**. The audit itself ran in
Codex, and its findings were pasted into Claude. Inspection of the matching desktop
task's menu and the File menu found no conversation share/export command. A complete
native Claude record was not obtained; this remains a transcript-deliverable limitation.
See transcripts/README.md and SESSIONS.json for the exact coverage and observed reason.

Claude planning is preserved exactly as provided by the candidate; its completeness is
not independently verified against Claude. The Codex export includes completed turns
and the active turn through its stated boundary. To include the current turn's final
records after the chat ends, refresh the export from the original local session log:

```bash
python scripts/export_transcript.py --source <path-to-original-session.jsonl>
git add transcripts
git commit -m "docs: refresh completed AI session record"
python scripts/prepare_submission.py --require-pdfs
```

The exporter detects completion from real session events. It no longer labels every
export incomplete unconditionally. It retains failed tests and dead ends and redacts
only personal data, recognized secrets and private unrelated chat metadata.

## Delivery and follow-up

SUBMISSION_EMAIL.md contains the prepared reply. No email has been sent by the agent.
Send it through the original assignment thread, using the repository link and bundle ID
NWG-D0BC. Attach the architecture/reflection PDFs if using attachments; they are also
included in the prepared archive. Provide reviewer access if the repository is private.

For offline history review, clone the extracted Git bundle:

```bash
git clone northwind-consolidation.bundle review-clone
cd review-clone
python -m consolidation --data data --out output
```

CANDIDATE_GUIDE.md contains the answer explanations. REVIEW_RUNBOOK.md provides
the live walkthrough. Neither supplies missing company evidence or represents a
separate human accounting sign-off.
