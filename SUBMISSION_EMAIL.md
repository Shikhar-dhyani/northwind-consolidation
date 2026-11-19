# Submission email draft

Reply to the original assignment email thread. This is a prepared draft, not a sent email.

**Subject:** AI Agentic Engineer take-home submission - NWG-D0BC - Shikhar Dhyani

Hi,

Please find my Northwind Group consolidation take-home submission for bundle NWG-D0BC:

Repository: https://github.com/Shikhar-dhyani/northwind-consolidation

The repository is public, so reviewers can access it without an invitation.

The repository contains the architecture, runnable Python prototype, DECISIONS.md,
VALIDATION.md, AI-session records and one-page reflection, with the full commit history.
The architecture and reflection are also available as PDF attachments in the prepared
submission package.

The prototype includes an Azure Foundry Claude agent for evidence inspection and
human-review proposals. The default run uses a labelled offline rules baseline;
live model tool use is opt-in through local configuration. Neither path gives the
model authority over accounting postings or figures.

Run the prototype with:

```bash
python -m consolidation --data data --out output
```

The supplied bundle lacks closing SGD FX and UK acquisition/historical consolidation
evidence. Affected figures are explicitly null with reasons; independently supported
figures remain available. The journal review policy and all assumptions are disclosed.

A separately labelled alternative scenario shows conditional totals and the opening-equity
bridge without replacing the conservative controls. The validation suite contains 82
passing tests, including audit regressions and changed-input checks; default figures
were verified unchanged from fresh clones after each fix.

I look forward to walking through the design, source traceability and input-change
examples in the follow-up session.

Regards,
Shikhar Dhyani
