"""Check Gemini without uploading medical data or printing keys.
Run from the project root: python -m backend.scripts.check_provider
"""
import asyncio
import json
import logging
import os
from backend.config import Settings
from backend.errors import AnalysisError, error_event
from backend.providers import Providers

async def check(settings, *, transport=None):
    info = {'configured': bool(settings.gemini_key), 'model': settings.gemini_model,
            'httpx_trust_env': settings.httpx_trust_env,
            'proxy_env_present': any(bool(os.getenv(n)) for n in ('HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'http_proxy', 'https_proxy', 'all_proxy')),
            'custom_ca_env_present': any(bool(os.getenv(n)) for n in ('SSL_CERT_FILE', 'SSL_CERT_DIR'))}
    if not settings.gemini_key:
        return info | {'ok': False, 'code': 'provider_unavailable',
                       'message': 'Set GEMINI_API_KEY in backend/.env and restart the backend.'}
    try:
        response = await Providers(settings, transport).gemini({
            'contents': [{'role': 'user', 'parts': [{'text': 'Reply only with OK. Connection test, no medical data.'}]}],
            'generationConfig': {'temperature': 0, 'maxOutputTokens': 64}}, 'provider')
        if not response.get('candidates'):
            raise AnalysisError('provider_request', 'provider')
        return info | {'ok': True, 'message': 'Gemini is reachable with this key and model. No prescription was sent.'}
    except AnalysisError as error:
        event = error_event(error)
        return info | {'ok': False, 'code': event['code'], 'message': event['message'], **error.safe_details()}

if __name__ == '__main__':
    logging.basicConfig(level=logging.WARNING, format='%(message)s')
    result = asyncio.run(check(Settings.from_env()))
    print(json.dumps(result, indent=2, ensure_ascii=False))
    raise SystemExit(0 if result['ok'] else 1)
