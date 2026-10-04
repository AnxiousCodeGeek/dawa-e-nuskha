"""FastAPI API. Start from project root: python -m uvicorn backend.main:app."""
import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import ValidationError
from .agent import stream_agent
from .catalog import Catalog
from .config import Settings
from .context import Context
from .errors import MESSAGES
from .images import prepare_image
from .model import AnalyzeInput, CorrectInput, Correction
from .providers import Providers
from .tools import patient_summary

log = logging.getLogger('prescription.events')


async def read_json(request: Request, limit=4_500_000):
    if request.headers.get('content-encoding', 'identity') != 'identity':
        raise ValueError('Unsupported body encoding')
    if not request.headers.get('content-type', '').lower().startswith('application/json'):
        raise ValueError('Expected JSON')
    data = bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data) > limit:
            raise ValueError('Body too large')
    return json.loads(data)


def create_app(settings=None, *, transport=None, rate_limit=20):
    settings = settings or Settings.from_env()
    providers, catalog = Providers(settings, transport), Catalog()
    app = FastAPI(title='Dawa-e-Nuskha API', version='2.0.0')
    app.state.settings, app.state.providers, app.state.catalog = settings, providers, catalog
    buckets = {}
    app.add_middleware(CORSMiddleware, allow_origins=list(settings.allowed_origins),
                       allow_methods=['GET', 'POST'], allow_headers=['Content-Type'], allow_credentials=False)

    @app.middleware('http')
    async def security(request: Request, call_next):
        if request.method not in ('GET', 'HEAD', 'OPTIONS'):
            origin = request.headers.get('origin')
            if origin and origin not in settings.allowed_origins:
                return JSONResponse({'error': 'This request could not be accepted.'}, status_code=403)
            host = request.client.host if request.client else 'local'
            now = time.monotonic()
            if len(buckets) >= 2000:
                buckets.clear()
            count, started = buckets.get(host, (0, now))
            if now-started >= 60:
                count, started = 0, now
            if count >= rate_limit:
                return JSONResponse({'error': 'Please wait a minute before trying again.'}, status_code=429)
            buckets[host] = count+1, started
            try:
                if int(request.headers.get('content-length', '0')) > 4_500_000:
                    return JSONResponse({'error': 'Please choose a smaller image.'}, status_code=413)
            except ValueError:
                return JSONResponse({'error': 'Invalid request.'}, status_code=400)
        response = await call_next(request)
        response.headers.update({'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff',
                                 'Referrer-Policy': 'no-referrer', 'X-Frame-Options': 'DENY'})
        return response

    @app.get('/api/health')
    async def health():
        return {'status': 'ok', 'backend': 'python'}

    @app.get('/api/settings/provider')
    async def provider_status():
        return {'configured': bool(settings.gemini_key), 'canConfigure': False}

    @app.get('/api/settings/search')
    async def search_status():
        return {'configured': bool(settings.tavily_key), 'canConfigure': False, 'catalog_records': len(catalog.records)}

    @app.api_route('/api/settings/{kind}', methods=['POST', 'DELETE'])
    async def disabled_settings(kind: str):
        return JSONResponse({'error': 'Configure API keys in backend/.env and restart the Python backend.'}, status_code=403)

    @app.post('/api/prescription/analyze')
    async def analyze(request: Request):
        try:
            input = AnalyzeInput.model_validate(await read_json(request))
            processed, metrics = None, None
            if input.image:
                processed, metrics = await asyncio.to_thread(prepare_image, input.image)
        except (ValueError, ValidationError, TypeError):
            return JSONResponse({'error': 'Choose a valid JPEG, PNG or WEBP image or a sample.'}, status_code=400)
        if not input.sample and not settings.gemini_key:
            return JSONResponse({'error': MESSAGES['provider_unavailable'], 'code': 'provider_unavailable'}, status_code=503)
        context = Context(input, settings, providers, catalog, image=processed, metrics=metrics)
        return StreamingResponse(stream_agent(context), media_type='application/x-ndjson',
                                 headers={'Cache-Control': 'no-store', 'X-Accel-Buffering': 'no'})

    @app.post('/api/prescription/correct')
    async def correct(request: Request):
        try:
            data = CorrectInput.model_validate(await read_json(request, 500_000))
            result = data.prescription
            medication = next((m for m in result.medications if m.id == data.medication_id), None)
            if medication is None or len(result.user_corrections)+len(data.values) > 300:
                raise ValueError('Invalid correction')
            for field, value in data.values.items():
                result.user_corrections.append(Correction(medication_id=medication.id, field=field,
                    ai_value=medication.fields[field].value, user_value=value,
                    created_at=datetime.now(timezone.utc).isoformat(), confirmed=data.confirm))
            medication.verification_status = 'confirmed' if data.confirm else 'unresolved'
            result.summary = patient_summary(result)
            log.info(json.dumps({'event': 'user_corrected', 'fields': len(data.values)}))
            return {'result': result.model_dump(mode='json')}
        except (ValueError, ValidationError, TypeError):
            return JSONResponse({'error': 'Your changes could not be saved. Please try again.'}, status_code=400)

    return app


app = create_app()
