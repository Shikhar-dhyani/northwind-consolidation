"""Small Azure Foundry Claude Messages adapter; no credentials enter audit logs."""

import json
import os
from pathlib import Path
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class ReviewError(ValueError):
    pass


def configuration(env_file=Path('.env')):
    keys = ('ANTHROPIC_FOUNDRY_API_KEY', 'ANTHROPIC_FOUNDRY_BASE_URL', 'ANTHROPIC_FOUNDRY_MODEL')
    values = {}
    if env_file.is_file():
        for line in env_file.read_text(encoding='utf-8-sig').splitlines():
            if not line.strip() or line.lstrip().startswith('#'):
                continue
            name, separator, value = line.partition('=')
            if separator and name.strip() in keys:
                values[name.strip()] = value.strip().strip('\"\'')
    return {key: os.environ.get(key, values.get(key, '')) for key in keys}


def messages_endpoint(value):
    parsed = urlsplit(value)
    if (parsed.scheme != 'https' or not re.fullmatch(r'[a-z0-9-]+\.services\.ai\.azure\.com', parsed.hostname or '')
            or parsed.username or parsed.password or parsed.port or parsed.query or parsed.fragment):
        raise ReviewError('Configure an HTTPS Azure Foundry resource endpoint without credentials or query parameters')
    if parsed.path.rstrip('/') not in ('', '/anthropic', '/anthropic/v1/messages'):
        raise ReviewError('Expected resource root, /anthropic or /anthropic/v1/messages endpoint')
    return f'https://{parsed.hostname}/anthropic/v1/messages'


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        # Never forward an API key to a redirected destination.
        return None


class FoundryClaude:
    def __init__(self, config=None):
        config = configuration() if config is None else config
        self.key = config['ANTHROPIC_FOUNDRY_API_KEY']
        if not self.key:
            raise ReviewError('Set ANTHROPIC_FOUNDRY_API_KEY in the ignored .env or environment')
        self.endpoint = messages_endpoint(config['ANTHROPIC_FOUNDRY_BASE_URL'])
        self.model = config['ANTHROPIC_FOUNDRY_MODEL']
        if not re.fullmatch(r'[A-Za-z0-9._-]{1,120}', self.model):
            raise ReviewError('Set ANTHROPIC_FOUNDRY_MODEL to the deployed Claude model name')

    def complete(self, system, messages, tools):
        body = json.dumps({'model': self.model, 'system': system, 'messages': messages,
            'tools': tools, 'tool_choice': {'type': 'any', 'disable_parallel_tool_use': True},
            'max_tokens': 4096, 'stream': False}, allow_nan=False).encode('utf-8')
        if len(body) > 240_000:
            raise ReviewError('Review context budget exceeded')
        request = Request(self.endpoint, body, headers={'Content-Type': 'application/json',
            'x-api-key': self.key, 'anthropic-version': '2023-06-01'}, method='POST')
        for attempt in range(3):
            try:
                with build_opener(NoRedirect).open(request, timeout=30) as response:
                    raw = response.read(1_000_001)
                if len(raw) > 1_000_000:
                    raise ReviewError('Provider response exceeds review budget')
                result = json.loads(raw)
                if not isinstance(result, dict) or not isinstance(result.get('content'), list):
                    raise ReviewError('Malformed Claude Messages response')
                return result
            except HTTPError as error:
                status = error.code
                error.close()
                if (status == 429 or status >= 500) and attempt < 2:
                    time.sleep(.25 * 2 ** attempt)
                    continue
                raise ReviewError(f'Azure Claude HTTP {status}; inspect endpoint, deployment, quota and credentials locally') from None
            except (URLError, TimeoutError, OSError):
                if attempt < 2:
                    time.sleep(.25 * 2 ** attempt)
                    continue
                raise ReviewError('Azure Claude network/timeout failure after bounded retries') from None
            except (ValueError, UnicodeError):
                raise ReviewError('Malformed JSON from Azure Claude') from None
