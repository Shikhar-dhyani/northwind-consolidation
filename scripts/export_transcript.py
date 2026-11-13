"""Export user-visible Codex messages/tool records without rewriting dead ends.

Run again after the session ends for a complete snapshot. Internal system/developer
instructions, private reasoning and app telemetry are not conversation exports.
"""

import argparse
from collections import Counter
import json
import os
from pathlib import Path
import re

VISIBLE_TOOLS = {'function_call', 'function_call_output', 'custom_tool_call', 'custom_tool_call_output'}


def redact(value):
    if isinstance(value, str):
        home = str(Path.home())
        for prefix in (home.replace('\\', '\\\\'), home, home.replace('\\', '/')):
            value = value.replace(prefix, 'C:/Users/[REDACTED]')
        value = value.replace('Shikhar Dhyani', '[REDACTED NAME]')
        value = re.sub(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}', '[REDACTED EMAIL]', value)
        value = re.sub(r'\bsk-[A-Za-z0-9_-]{16,}\b', '[REDACTED API KEY]', value)
        return value
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, dict):
        return {key: redact(item) for key, item in value.items()}
    return value


def export(source: Path, target: Path):
    included, excluded = [], Counter()
    for line in source.read_text(encoding='utf-8').splitlines():
        record = json.loads(line)
        if record.get('type') != 'response_item':
            excluded[record.get('type', 'unknown')] += 1
            continue
        item = record['payload']
        visible = (item.get('type') == 'message' and item.get('role') in ('user', 'assistant')
                   and item.get('channel') not in ('analysis', 'summary')) or item.get('type') in VISIBLE_TOOLS
        if not visible:
            excluded['internal_response_item'] += 1
            continue
        payload = {k: v for k, v in item.items() if k != 'internal_chat_message_metadata_passthrough'}
        included.append(redact({'timestamp': record.get('timestamp'), 'type': 'response_item', 'payload': payload}))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in included), encoding='utf-8')
    status = {'source_session': source.name, 'last_record_timestamp': included[-1]['timestamp'] if included else None,
              'exported_records': len(included), 'current_session_complete': False,
              'earlier_planning_sessions_available': False,
              'redactions': ['personal home path', 'candidate name', 'email addresses', 'recognized API keys'],
              'excluded_internal_record_counts': dict(excluded),
              'note': 'Visible messages and tool calls/results in original order, including mistakes. '
                      'Snapshot taken during the session; refresh after completion. Earlier planning exports still required.'}
    (target.parent / 'EXPORT_STATUS.json').write_text(json.dumps(status, indent=2) + '\n', encoding='utf-8')
    return status


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path)
    parser.add_argument('--out', type=Path, default=Path('transcripts/codex-session.jsonl'))
    args = parser.parse_args()
    source = args.source
    if source is None:
        session = os.environ.get('CODEX_SESSION_ID')
        if not session:
            parser.error('Provide --source with the session JSONL path')
        matches = list((Path.home() / '.codex/sessions').rglob(f'*{session}*.jsonl'))
        if len(matches) != 1:
            parser.error('Cannot identify a unique current session; provide --source')
        source = matches[0]
    status = export(source, args.out)
    print(f'Exported {status["exported_records"]} visible records to {args.out}; session snapshot remains incomplete.')


if __name__ == '__main__':
    main()
