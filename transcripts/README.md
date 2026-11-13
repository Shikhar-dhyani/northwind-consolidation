# AI session records

`codex-session.jsonl` is an ordered export of the current session's user-visible messages,
tool calls and returned results. Failed tests, attempted commands, retries and dead ends
remain present. Text is not summarized or cleaned up. Only personal data and recognized
API keys are redacted. `EXPORT_STATUS.json` records its snapshot boundary and coverage.

Internal platform instructions, private reasoning and telemetry are not user-visible
conversation records and are excluded. Tool results may themselves be truncated by
the tool at execution time; the export preserves what the tool actually returned.

The current conversation is still in progress when exported. Refresh after it finishes:

```bash
python scripts/export_transcript.py --source <path-to-original-session.jsonl>
```

Inside the same Codex session, `python scripts/export_transcript.py` can locate the log
from its session identifier. The exporter cannot include its own later result or final
message in the same snapshot; rerun after the session ends for those final records.
The coverage flag deliberately remains incomplete until reviewed after that refresh.

**Earlier sessions are missing.** The supplied handoff describes prior AI planning,
but contains no full earlier session export. Add those original exports or shared links
here before submission; a handoff is not a replacement transcript. No reconstructed
conversation has been presented as an original session. This is the remaining packaging
requirement even though the local prototype and supporting documents are present.
