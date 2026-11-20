# Final submission email draft

Reply on the original assignment thread. If it already has a subject, retain it.
This draft has not been sent.

Attach these generated PDFs before sending:

- `output/pdf/ARCHITECTURE.pdf` (six pages)
- `output/pdf/REFLECTION.pdf` (one page)

The prepared ZIP is optional: `output/submission/northwind-consolidation-NWG-D0BC.zip`.

---

**Subject:** AI Agentic Engineer take-home submission - NWG-D0BC - Shikhar Dhyani

Hi,

Please find my Northwind Group consolidation take-home submission for bundle **NWG-D0BC**.

Repository: https://github.com/Shikhar-dhyani/northwind-consolidation

The repository is public and includes the runnable prototype, architecture, seven design
decisions, validation evidence, AI-session records and one-page reflection, with the
full commit history. PDF copies of the architecture and reflection accompany this submission.

The implementation combines a deterministic accounting engine with a bounded Claude
review agent on Azure Foundry. The agent inspects evidence and proposes actions for
human review; it cannot post journals or change financial figures. Actual live-run
traces, including failed attempts and the completed review, are preserved in the repository.

From a fresh clone, generate the outputs with:

```bash
python -m consolidation --data data --out output
```

This default run requires no credentials and uses a labelled offline review baseline.
Add `--review live` for Claude tool use with the local configuration described in the README.

Validation includes **85 passing tests**, **64 financial runtime checks**, independent
recomputations and changed-input regressions. Six control figures remain null where
the supplied closing SGD rate or historical UK consolidation evidence is insufficient;
the reasons and a separately labelled conditional scenario are included.

I look forward to discussing the architecture, tracing the figures to source rows and
demonstrating input changes in the follow-up session.

Regards,
Shikhar Dhyani
