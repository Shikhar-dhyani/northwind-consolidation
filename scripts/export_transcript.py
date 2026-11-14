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


def redact_discovery(value):
    """Redact exact private chat fields only in an identified discovery result."""
    private = set()
    decoder = json.JSONDecoder()

    def collect(node):
        if isinstance(node, dict):
            if node.get('kind') in ('codex', 'chatgpt') and node.get('id') != os.environ.get('CODEX_THREAD_ID'):
                private.update(v for k, v in node.items() if k in ('title', 'summary') and isinstance(v, str) and v)
            for item in node.values():
                collect(item)
        elif isinstance(node, list):
            for item in node:
                collect(item)
        elif isinstance(node, str):
            try:
                decoded = json.loads(node)
            except ValueError:
                pass
            else:
                collect(decoded)
                return
            position = 0
            while position < len(node):
                match = re.search(r'[\[{]', node[position:])
                if not match:
                    break
                position += match.start()
                try:
                    parsed, end = decoder.raw_decode(node, position)
                except ValueError:
                    position += 1
                else:
                    collect(parsed)
                    position = end
    collect(value)

    def replace_fields(node):
        if isinstance(node, dict):
            return {k: ('[REDACTED PRIVATE CHAT METADATA]' if k in ('title', 'summary') and isinstance(v, str)
                        and v in private else replace_fields(v)) for k, v in node.items()}
        if isinstance(node, list):
            return [replace_fields(item) for item in node]
        if isinstance(node, str):
            for secret in sorted(private, key=len, reverse=True):
                for ascii_only in (True, False):
                    quote, encoded = '"', json.dumps(secret, ensure_ascii=ascii_only)[1:-1]
                    for _ in range(5):
                        pattern = (re.escape(quote) + r'(?:title|summary)' + re.escape(quote)
                                   + r'\s*:\s*' + re.escape(quote) + r'(?P<value>' + re.escape(encoded)
                                   + ')' + re.escape(quote))
                        node = re.sub(pattern, lambda m: m[0][:m.start('value') - m.start()]
                            + '[REDACTED PRIVATE CHAT METADATA]' + m[0][m.end('value') - m.start():], node)
                        quote = json.dumps(quote)[1:-1]
                        encoded = json.dumps(encoded, ensure_ascii=ascii_only)[1:-1]
            return node
        return node
    return replace_fields(value)


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
    discovery_calls = set()
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
        if item.get('type') in ('custom_tool_call', 'function_call') and (
                'tools.mcp__codex_app__list_threads({' in item.get('input', '')
                or item.get('name', '').endswith('__list_threads')):
            discovery_calls.add(item.get('call_id'))
        visible = (item.get('type') == 'message' and item.get('role') in ('user', 'assistant')
                   and item.get('channel') not in ('analysis', 'summary')) or item.get('type') in VISIBLE_TOOLS
        if not visible:
            excluded['internal_response_item'] += 1
            continue
        payload = {k: v for k, v in item.items() if k != 'internal_chat_message_metadata_passthrough'}
        if item.get('type') in ('custom_tool_call_output', 'function_call_output') and item.get('call_id') in discovery_calls:
            payload = {**payload, 'output': redact_discovery(payload.get('output'))}
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
