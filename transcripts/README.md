# AI session records

`codex-session.jsonl` is an ordered export of the current session's user-visible messages,
tool calls and returned results. Failed tests, attempted commands, retries and dead ends
remain present. Text is not summarized or cleaned up. Only personal data and recognized
API keys are redacted. `EXPORT_STATUS.json` records its snapshot boundary and coverage.

Internal platform instructions, private reasoning and telemetry are not user-visible
conversation records and are excluded. Tool results may themselves be truncated by
the tool at execution time; the export preserves what the tool actually returned.

`claude-planning.txt` preserves the original planning conversation exactly as pasted
by the candidate. `SESSIONS.json` records its source and SHA-256. No speaker labels,
missing tool records or attachments have been reconstructed. Completeness of the pasted
Claude record is candidate-provided, rather than independently verified against Claude.

`claude-review-pasted-excerpts.jsonl` separately preserves the later review exchanges
that the candidate pasted into this chat, including the audit and remediation discussion.
`CLAUDE_REVIEW_PROVENANCE.json` records their source, hashes and coverage. These are
supplied excerpts, not a complete native Claude review-session export; omitted external
turns cannot be recovered from the Codex log. Add a native export or shared record if
there are additional contributing exchanges outside those supplied here.

The current conversation is still in progress when exported. Refresh after it finishes:

```bash
python scripts/export_transcript.py --source <path-to-original-session.jsonl>
```

Inside the same Codex session, `python scripts/export_transcript.py` can locate the log
from its session identifier. The exporter cannot include its own later result or final
message in the same snapshot; rerun after the session ends for those final records.
Completion is now detected from actual session start/completion events. Completed turns
are counted, and an ongoing turn is explicitly identified with its snapshot boundary.

Both known contributing conversations are represented: the candidate-supplied Claude
planning text and this Codex implementation session. Failed attempts and test failures
remain in the Codex record. Private titles and summaries of unrelated chats returned
during discovery are redacted as personal data; tool calls/results remain in place.
This filtering is now scoped to identified discovery tool results and exact private chat
field values. Ordinary JSON title/summary fields in user messages, AI drafts and other
tools are preserved. The refreshed export restores such material from the original log.
If another AI session contributed, include its original record as well.
