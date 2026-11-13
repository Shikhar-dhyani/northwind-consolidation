"""Export user-visible Codex messages/tool records without rewriting dead ends.

Run again after the session ends for a complete snapshot. Internal system/developer
instructions, private reasoning and app telemetry are not conversation exports.
"""

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re

VISIBLE_TOOLS = {'function_call', 'function_call_output', 'custom_tool_call', 'custom_tool_call_output'}


def redact_private_fields(text):
    for depth in reversed(range(4)):
        slashes = 2 ** depth - 1
        quote = '\\' * slashes + '"'
        pattern = (re.escape(quote) + r'(?:title|summary)' + re.escape(quote)
                   + r'\s*:\s*' + re.escape(quote))
        pieces, cursor = [], 0
        for match in re.finditer(pattern, text):
            if match.start() < cursor:
                continue
            end = match.end()
            while end < len(text):
                if text[end] == '"':
                    before = end - 1
                    while before >= 0 and text[before] == '\\':
                        before -= 1
                    count = end - before - 1
                    if count % (2 ** (depth + 1)) == slashes:
                        pieces.extend((text[cursor:match.end()], '[REDACTED PRIVATE CHAT METADATA]'))
                        cursor = end - slashes
                        break
                end += 1
        pieces.append(text[cursor:])
        text = ''.join(pieces)
    return text


def redact(value):
    if isinstance(value, str):
        home = str(Path.home())
        for prefix in (home.replace('\\', '\\\\'), home, home.replace('\\', '/')):
            value = value.replace(prefix, 'C:/Users/[REDACTED]')
        value = value.replace('Shikhar Dhyani', '[REDACTED NAME]')
        value = re.sub(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}', '[REDACTED EMAIL]', value)
        value = re.sub(r'\bsk-[A-Za-z0-9_-]{16,}\b', '[REDACTED API KEY]', value)
        # Chat discovery can return private, unrelated conversation metadata. Keep
        # the calls/results and their ordering, but redact these personal fields.
        return redact_private_fields(value)
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, dict):
        return {key: redact(item) for key, item in value.items()}
    return value


def capture_planning(records, folder):
    """Preserve the candidate-supplied Claude conversation, without inferred roles."""
    for record in records:
        item = record.get('payload', {})
        if record.get('type') != 'response_item' or item.get('role') != 'user':
            continue
        content = item.get('content', [])
        blocks = [{'text': content}] if isinstance(content, str) else content
        for block in blocks:
            text = block.get('text', '')
            opening, closing = '<send_user_message_question_reply>', '</send_user_message_question_reply>'
            if opening not in text or closing not in text:
                continue
            replies = json.loads(text.split(opening, 1)[1].split(closing, 1)[0])
            for reply in replies:
                answer = reply.get('answer', '')
                if 'claude , and here is the orignal conversation' not in answer:
                    continue
                # No formatting, speaker reconstruction, trimming, or paraphrasing.
                raw = answer.encode('utf-8')
                path = folder / 'claude-planning.txt'
                if path.exists() and path.read_bytes() != raw:
                    raise ValueError('Existing Claude transcript differs; preserve it before adding another version')
                path.write_bytes(raw)
                registry = {'sessions': [{
                    'id': 'claude-planning', 'path': path.name,
                    'sha256': hashlib.sha256(raw).hexdigest(),
                    'provenance': 'Original conversation text supplied by the candidate in this chat',
                    'received_timestamp': record.get('timestamp'),
                    'format': 'Verbatim pasted text; speaker labels, original attachments and native tool records were not separately supplied',
                    'completeness': 'Candidate-provided record; not independently verified against Claude',
                }]}
                (folder / 'SESSIONS.json').write_text(json.dumps(registry, indent=2) + '\n', encoding='utf-8')


def export(source: Path, target: Path):
    included, excluded = [], Counter()
    records = [json.loads(line) for line in source.read_text(encoding='utf-8').splitlines()]
    target.parent.mkdir(parents=True, exist_ok=True)
    capture_planning(records, target.parent)
    active, completed_turns = False, 0
    for record in records:
        if record.get('type') == 'event_msg':
            kind = record['payload'].get('type')
            if kind == 'task_started':
                active = True
            elif kind == 'task_complete':
                active = False
                completed_turns += 1
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
    target.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in included), encoding='utf-8')
    registry_path = target.parent / 'SESSIONS.json'
    registry = json.loads(registry_path.read_text()) if registry_path.exists() else {'sessions': []}
    prior = bool(registry['sessions']) and all((target.parent / s['path']).is_file() for s in registry['sessions'])
    status = {'source_session': source.name, 'last_record_timestamp': included[-1]['timestamp'] if included else None,
              'exported_records': len(included), 'current_session_complete': not active,
              'completed_turns': completed_turns, 'active_turn_included_through_snapshot': active,
              'earlier_planning_sessions_available': prior,
              'redactions': ['personal home path', 'candidate name', 'email addresses', 'recognized API keys',
                             'private chat titles and summaries returned by discovery'],
              'excluded_internal_record_counts': dict(excluded),
              'note': 'Visible messages and tool calls/results in original order, including mistakes. '
                      'Completion is detected from session events. An active turn is captured through the snapshot '
                      'boundary; rerun after it finishes to include its final records. See SESSIONS.json for prior-session provenance.'}
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
    print(f'Exported {status["exported_records"]} visible records to {args.out}; '
          f'completed turns: {status["completed_turns"]}; active turn: {status["active_turn_included_through_snapshot"]}.')


if __name__ == '__main__':
    main()
