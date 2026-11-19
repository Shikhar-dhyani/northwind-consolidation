# AI session records

Actual Azure Foundry Claude application runs are preserved in runtime_claude/. These
are separate from the development conversations. The first two attempts failed (step
budget and final-request timeout); the third completed with 11 advisory proposals.
Each folder contains the unedited review report, tool transcript and checksum provenance.
Model prose remains unverified and includes a documented unnecessary UK-date request.

`codex-session.jsonl` is an ordered export of the current session's user-visible messages,
tool calls and returned results. Failed tests, attempted commands, retries and dead ends
remain present. Text is not summarized or cleaned up. Only personal data and recognized
API keys are redacted. `EXPORT_STATUS.json` records its snapshot boundary and coverage.

Internal platform instructions, private reasoning and telemetry are not user-visible
conversation records and are excluded. Tool results may themselves be truncated by
the tool at execution time; the export preserves what the tool actually returned.

There is **one continuous Claude session**, titled **Assignment explanation**. It covers
the assignment explanation, accounting primers, README, handoff, opening-equity review,
scenario discussion, audit prioritisation and closing checks. The actual audit ran in
Codex; the candidate pasted its findings into that same Claude session. There is no
separate Claude audit conversation.
Session ID supplied by the candidate: `cse_01SVCqfToLJucCuuiuraUBt7`.

`claude-planning.txt` preserves the initial text exactly as pasted by the candidate.
`SESSIONS.json` records its source and SHA-256. No speaker labels, missing tool records
or attachments have been reconstructed.

`claude-review-pasted-excerpts.jsonl` separately preserves the later review exchanges
that the candidate pasted into this chat, including the audit and remediation discussion.
`CLAUDE_REVIEW_PROVENANCE.json` records their source, hashes and coverage. Its six
excerpts include the closing clarification of the session's scope. Both Claude files
contain supplied text from the same session.

The current conversation is still in progress when exported. Refresh after it finishes:

```bash
python scripts/export_transcript.py --source <path-to-original-session.jsonl>
```

Inside the same Codex session, `python scripts/export_transcript.py` can locate the log
from its session identifier. The exporter cannot include its own later result or final
message in the same snapshot; rerun after the session ends for those final records.
Completion is now detected from actual session start/completion events. Completed turns
are counted, and an ongoing turn is explicitly identified with its snapshot boundary.

The two known contributing sessions are represented: partial records of the single
Claude session and this Codex implementation session. Failed attempts and test failures
remain in the Codex record. Private titles and summaries of unrelated chats returned
during discovery are redacted as personal data; tool calls/results remain in place.
This filtering is now scoped to identified discovery tool results and exact private chat
field values. Ordinary JSON title/summary fields in user messages, AI drafts and other
tools are preserved. Unrelated chat/project labels exposed in Claude's sidebar during
the export check are redacted only in the corresponding UI results; the assignment task
and its messages remain present. The refreshed export restores other material from the original log.
If another AI session contributed, include its original record as well.
