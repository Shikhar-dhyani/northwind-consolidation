# Implemented exception-review agent

One agent surrounds the deterministic engine; there are no independent accounting
agents per entity. Claude on Azure Foundry chooses evidence tools and drafts review
proposals. It does not calculate or approve the financial statements.

## Run modes

```powershell
python -m consolidation --data data --out output
python -m consolidation --data data --out output --review live
python -m consolidation --data data --out output --review off
```

The first command uses a deterministic offline rules baseline through the same tool
broker. It requires no network and explicitly reports llm_called=false. It is not a
mock model presented as AI. Live mode uses the real Messages HTTP client. Off disables
review. All modes preserve required accounting filenames and supported figures.

## Local Azure configuration

Copy .env.example to .env only if a local .env does not already exist. Set:

```text
ANTHROPIC_FOUNDRY_API_KEY=your-private-key
ANTHROPIC_FOUNDRY_BASE_URL=https://YOUR-RESOURCE.services.ai.azure.com/anthropic/v1/messages
ANTHROPIC_FOUNDRY_MODEL=your-deployed-Claude-model-name
```

The model must exist in your resource. The template's claude-sonnet-4-6 can be changed.
The base URL also accepts the resource root or /anthropic; the adapter normalizes the
Messages path. Process environment overrides .env. The small loader supports simple
KEY=value assignments and surrounding quotes, without shell expansion. Never commit
.env or paste the key in chat. The local endpoint supplied by the candidate is kept
only in the ignored .env. No OpenAI API key or SDK is used.

## Actual agent loop

1. Accounting finishes and writes a staged, source-hashed result generation.
2. The review broker selects root-cause cases: missing FX, UK history, injected memo,
   mapping classification, sub-ledger discrepancies and held journals. All other issues
   remain in issues.json; this is not an assertion that a model reviewed every issue.
3. Claude receives case IDs/codes and the tool contract, not whole trial balances.
4. Claude selects get_case, read_evidence or get_control. Tool results contain bounded
   excerpts and provenance. Source bytes must match the accounting input manifest.
5. Claude calls submit_review. Local checks require exactly one proposal per selected
   case, permitted actions, inspected citations and valid mapping targets. Rejected tool
   calls return errors to Claude, allowing correction within the remaining budget.
   Excerpts are decoded from the same bytes that were hashed; the chart is verified
   too. Submission rechecks every input so changed evidence cannot yield accepted
   proposals against the old accounting run. OS-level immutable snapshots remain future work.
6. Valid proposals are saved as pending_human_review. The financial output is unchanged.
7. A human obtains supporting evidence, reviews corrections and reruns the full engine.
   There is no automatic approval, source rewrite or persistent override application.

| Tool | Authority |
|---|---|
| get_case | Read a selected issue and up to three bounded source excerpts |
| read_evidence | Read another reference already belonging to selected case evidence |
| get_control | Read a computed control with its source references and reasons |
| submit_review | Queue request_evidence, propose_mapping or explain_only proposals |

No shell, filesystem-write, journal-posting, email or arbitrary network tool is exposed.
Input instructions such as JE-006's memo remain untrusted data. Capability checks
remain effective even if the model follows the memo or invents a tool. No proposal can
change a journal disposition, unblock a control or supply an assumed rate to the engine.
Citation validation proves a reference was inspected, not that the model's prose or
accounting interpretation is correct. Finance review remains necessary.

## Output, budgets and failures

review_report.json records mode, configured model, response receipt, source hashes,
selected case IDs, proposals and status. agent_trace.json retains returned model text,
tool calls/results and validation feedback; private reasoning and API headers are not
recorded. It is separate from the development transcript in transcripts/.

The loop permits 20 model steps, one tool call per step, 4,096 output tokens per request,
a bounded context and response size. Once all cases have been inspected, the final
three steps force submit_review, reserving room for validation corrections rather than
unbounded extra evidence collection. HTTP requests have a 90-second timeout and at
most three attempts for transient failures; authentication failures and timed-out
generations are not automatically retried to avoid duplicate generation charges.
Redirects are refused to avoid forwarding a key. Endpoint validation accepts only the
Azure Foundry HTTPS resource form. Error bodies and credentials are not logged.

Missing configuration, model refusal/malformed output or budget exhaustion publishes an
explicit failed review with no accepted proposals. CLI exit 3 distinguishes that from
accounting failure (exit 2). Accounting failure skips the agent and replaces stale
review outputs with blocked artifacts. Code 0 can still include disclosed financial nulls.

## Validation and live smoke test

tests/test_review.py exercises real tool dispatch, source-manifest checks, prompt-injected
evidence, a forbidden posting attempt, invented citations, corrective feedback, finite
JSON, credential redaction, retries and CLI failure semantics. The scripted Claude
fixture is a protocol test double, not an actual model call or model-quality evaluation.
A credentialed Azure run with configured model claude-sonnet-4-6 completed with 18
model responses and 11 pending human-review proposals. Original financial controls
were unchanged. Actual unedited reports and tool transcripts are preserved under
transcripts/runtime_claude/: the first run exhausted its retrieval budget, the second
timed out on final generation, and the third completed after the bounded fixes.
PROVENANCE.json records checksums and quality notes. The model incorrectly described
the UK acquisition date as absent even though entities.csv supplies it; protocol success
does not validate all prose. Human review must correct that unnecessary request.

The submission packager intentionally regenerates the offline baseline. A live trace
should be preserved separately before repackaging if it is needed as review evidence.

## API references

- [Microsoft: Claude deployment and Messages requests](https://learn.microsoft.com/en-us/azure/foundry/foundry-models/how-to/use-foundry-models-claude)
- [Anthropic: Claude on Microsoft Foundry](https://platform.claude.com/docs/en/build-with-claude/claude-in-microsoft-foundry)
- [Anthropic: tool definitions and tool-use results](https://platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools)
