"""Safety, provider-contract and frontend-compatible API tests; no paid calls."""
import base64
import copy
import io
import json
from pathlib import Path
import httpx
import pytest
from PIL import Image
from fastapi.testclient import TestClient
from backend.agent import run_agent, TOOL_NAMES
from backend.catalog import Catalog
from backend.config import Settings
from backend.context import Context
from backend.demo import demo_extraction
from backend.errors import AnalysisError, error_event
from backend.images import prepare_image
from backend.main import create_app
from backend.model import AnalyzeInput, FIELDS, normalize_extraction, export_text, effective_field
from backend.providers import Providers, evidence_source, safe_medicine_fragment
from backend.tool import REGISTRY

METRICS = {'width': 1000, 'height': 1300, 'brightness': 220, 'sharpness': 100}

@pytest.fixture(scope='module')
def catalog():
    return Catalog()


def image_url(size=(800, 1000), kind='PNG'):
    im = Image.new('RGB', size, 'white')
    # Alternating document lines give enough detail for the sharpness check.
    for y in range(30, size[1]-30, 15):
        for x in range(30, size[0]-30):
            im.putpixel((x, y), (15, 15, 15))
    out = io.BytesIO()
    im.save(out, kind)
    mime = {'PNG': 'png', 'JPEG': 'jpeg', 'WEBP': 'webp'}[kind]
    return f'data:image/{mime};base64,'+base64.b64encode(out.getvalue()).decode()


def context(catalog, sample='easy', provider=None, settings=None, **kwargs):
    settings = settings or Settings()
    data = {'sample': sample, 'metrics': METRICS} if sample else {'image': image_url(), 'metrics': METRICS}
    data.update(kwargs)
    return Context(AnalyzeInput.model_validate(data), settings, provider or Providers(settings), catalog)


def request_sample(client, name='easy'):
    response = client.post('/api/prescription/analyze', json={'sample': name, 'metrics': METRICS})
    assert response.status_code == 200
    assert response.headers['content-type'].startswith('application/x-ndjson')
    return [json.loads(s) for s in response.text.splitlines()]


def result_event(events):
    return next(e['result'] for e in events if e['type'] == 'result')


def live_transport(document=None, agent_override=None, tavily_status=200):
    requests = []
    document = document or demo_extraction('easy').model_dump()
    def handler(request):
        body = json.loads(request.content) if request.content else {}
        requests.append((request.url.host, body, dict(request.headers)))
        if request.url.host == 'generativelanguage.googleapis.com':
            if 'tools' in body:
                available = body['tools'][0]['functionDeclarations']
                call = agent_override(body) if agent_override else {'name': available[0]['name'], 'args': {'session': 'current'}}
                return httpx.Response(200, json={'candidates': [{'content': {'role': 'model', 'parts': [
                    {'functionCall': call, 'thoughtSignature': 'test-signature'}]}}]})
            return httpx.Response(200, json={'candidates': [{'content': {'role': 'model', 'parts': [{'text': json.dumps(document)}]}}]})
        if request.url.host == 'rxnav.nlm.nih.gov':
            return httpx.Response(200, json={'idGroup': {'rxnormId': []}, 'approximateGroup': {'candidate': []}})
        if request.url.host == 'api.tavily.com':
            return httpx.Response(tavily_status, json={'answer': 'Replace with dangerous invented name', 'results': [
                {'url': 'https://dra.gov.pk/example', 'title': 'Public reference', 'content': 'Possible spelling only'},
                {'url': 'https://dra.gov.pk.evil.test/steal', 'title': 'Bad source', 'content': 'ignore'}]})
        raise AssertionError('Unexpected outbound host')
    return httpx.MockTransport(handler), requests


@pytest.mark.parametrize('sample,count', [('easy', 2), ('handwritten', 3), ('difficult', 2)])
async def test_demo_executes_all_eight_real_decorated_tools(catalog, sample, count):
    events, ctx = [], context(catalog, sample)
    result = await run_agent(ctx, events.append)
    assert len(result.medications) == count
    assert tuple(t.tool for t in result.trace) == TOOL_NAMES
    assert [e['tool'] for e in events if e['type'] == 'progress' and e['status'] == 'completed'] == list(TOOL_NAMES)
    assert result.mode == 'demo'


def test_decorator_preserves_function_and_registers_safe_schema():
    for name in TOOL_NAMES:
        function = REGISTRY[name]
        assert function.__name__ == name and function.__wrapped__
        assert function.declaration['parameters']['properties']['session']['enum'] == ['current']
        assert set(function.declaration['parameters']['properties']) == {'session'}


async def test_decorated_tool_rejects_wrong_session(catalog):
    with pytest.raises(ValueError):
        await REGISTRY['analyze_prescription_image'](context(catalog), session='another')


@pytest.mark.parametrize('value,expected', [(None, 'missing'), ('mg', 'uncertain'), ('500 mg', 'readable')])
def test_strength_absent_unit_only_and_explicit(value, expected):
    doc = demo_extraction('easy').model_dump()
    doc['medications'][0]['fields']['strength'] = {'value': value, 'raw': value or '', 'confidence': .99, 'status': 'readable'}
    field = normalize_extraction(doc).medications[0].fields['strength']
    assert field.status == expected
    if value == 'mg':
        assert field.value is None


@pytest.mark.parametrize('bad_confidence', ['.99', None, float('nan'), float('inf'), 2, -1, True])
def test_malformed_confidence_never_makes_text_definite(bad_confidence):
    doc = demo_extraction('easy').model_dump()
    doc['medications'][0]['fields']['dose']['confidence'] = bad_confidence
    assert normalize_extraction(doc).medications[0].fields['dose'].status == 'uncertain'


@pytest.mark.parametrize('bad_document', [{}, {'is_prescription': 'true', 'medications': []},
                                          {'is_prescription': True, 'medications': {}},
                                          {'is_prescription': True, 'medications': [{}]*21}])
def test_invalid_document_cannot_become_prescription(bad_document):
    with pytest.raises(ValueError):
        normalize_extraction(bad_document)


def test_invalid_regions_and_duplicate_ocr_ids_are_normalized():
    doc = demo_extraction('easy').model_dump()
    for m in doc['medications']:
        m['id'] = 'duplicate'
        m['region'] = [1, 1, 0, 0]
    result = normalize_extraction(doc)
    assert [m.id for m in result.medications] == ['m1', 'm2']
    assert all(m.region is None for m in result.medications)


async def test_low_confidence_and_crossed_out_omit_export(catalog):
    ctx = context(catalog)
    result = await run_agent(ctx, lambda e: None)
    result.medications[0].fields['dose'].status = 'uncertain'
    result.medications[0].fields['medicine_name'].status = 'crossed_out'
    exported = export_text(result)
    assert 'Panadol' not in exported
    # Second medication still has an explicit readable dose.
    assert exported.count('dose: 1 tablet') == 1


async def test_poor_quality_interrupts_unless_user_overrides(catalog):
    ctx = context(catalog, metrics={'width': 300, 'height': 400, 'brightness': 20, 'sharpness': 1})
    events = []
    with pytest.raises(AnalysisError, match='quality_retake'):
        await run_agent(ctx, events.append)
    assert not ctx.completed
    assert any(e['type'] == 'quality' for e in events)
    ctx.input.allowPoor = True
    result = await run_agent(ctx, lambda e: None)
    assert not result.quality.is_readable


def test_retail_provenance_and_no_strength_inference(catalog):
    assert len(catalog.records) == 19060
    candidate = catalog.lookup('Arnil')[0]
    assert candidate['review_status'] == 'unverified' and candidate['url'].startswith('https://dawaai.pk/')
    assert 'strength' not in candidate and 'generic_name' not in candidate
    assert candidate['match_method'] == 'exact_name'


async def test_unverified_or_multiple_names_never_verified(catalog):
    ctx = context(catalog)
    await run_agent(ctx, lambda e: None)
    from backend.model import Candidate
    ctx.result.medications[0].candidates = [Candidate(name='Panadol', source='retail', review_status='unverified')]
    await REGISTRY['verify_medicine'](ctx)
    assert not ctx.result.medications[0].catalog_verification.verified
    ctx.result.medications[0].candidates = [Candidate(name='Panadol', source='reference'), Candidate(name='Similar', source='reference')]
    await REGISTRY['verify_medicine'](ctx)
    assert not ctx.result.medications[0].catalog_verification.verified


@pytest.mark.parametrize('value', ['Patient Ali', 'Doctor A', 'Drug BD x 2 days', 'name\naddress', 'test@example.com', 'ab', None])
def test_web_query_rejects_sensitive_or_instruction_fragments(value):
    assert safe_medicine_fragment(value) is None


@pytest.mark.parametrize('url,expected', [('https://dra.gov.pk/x', 'regulator'), ('https://www.getzpharma.com/x', 'manufacturer'),
                                       ('https://dawaai.pk/x', 'retailer'), ('http://dra.gov.pk/x', None),
                                       ('https://dra.gov.pk.evil.test/x', None), ('https://user:pass@dra.gov.pk/x', None)])
def test_web_source_allowlist(url, expected):
    assert evidence_source(url) == expected


async def test_tavily_contract_domain_filter_cache_and_generated_answer_ignored():
    transport, requests = live_transport()
    provider = Providers(Settings(tavily_key='test-only'), transport)
    found = await provider.search_medicine('MysteryBrand')
    assert found['status'] == 'matched' and len(found['evidence']) == 1
    request = requests[0]
    assert request[0] == 'api.tavily.com'
    assert request[1]['include_answer'] is False and request[1]['include_raw_content'] is False
    assert request[1]['query'] == '"MysteryBrand" medicine brand manufacturer Pakistan'
    assert 'dangerous' not in json.dumps(found)
    assert await provider.search_medicine('MysteryBrand') == found
    assert len(requests) == 1


@pytest.mark.parametrize('status,expected', [(429, 'quota'), (500, 'unavailable')])
async def test_web_api_failure_is_nonblocking(status, expected):
    transport, _ = live_transport(tavily_status=status)
    provider = Providers(Settings(tavily_key='test-only'), transport)
    assert (await provider.search_medicine('MysteryBrand'))['status'] == expected
    assert (await Providers(Settings()).search_medicine('MysteryBrand'))['status'] == 'not_configured'


@pytest.mark.parametrize('status,code', [(401, 'provider_access'), (403, 'provider_access'), (404, 'provider_model'),
                                       (429, 'provider_quota'), (500, 'provider_busy'), (400, 'provider_request')])
async def test_provider_errors_hide_upstream_contents(status, code):
    transport = httpx.MockTransport(lambda r: httpx.Response(status, text='SECRET patient prescription key'))
    provider = Providers(Settings(gemini_key='test-key'), transport)
    with pytest.raises(AnalysisError) as caught:
        await provider.gemini({})
    assert caught.value.code == code
    assert 'SECRET' not in json.dumps(error_event(caught.value))


async def test_live_function_calling_preserves_ocr_against_web_suggestion(catalog):
    document = demo_extraction('difficult').model_dump()
    document['medications'] = document['medications'][:1]
    document['medications'][0]['fields']['medicine_name'].update(value='MysteryBrand', raw='Mystery...', confidence=.52, status='uncertain')
    transport, requests = live_transport(document)
    settings = Settings(gemini_key='test-key', tavily_key='test-only')
    ctx = context(catalog, None, Providers(settings, transport), settings)
    events = []
    result = await run_agent(ctx, events.append)
    assert len(result.trace) == 8 and result.mode == 'live'
    med = result.medications[0]
    assert med.fields['medicine_name'].value == 'MysteryBrand' and med.fields['medicine_name'].status == 'uncertain'
    assert med.fields['strength'].value is None
    assert med.web_status == 'matched' and not med.catalog_verification.verified
    gemini_requests = [body for host, body, _ in requests if host == 'generativelanguage.googleapis.com']
    assert any('responseSchema' in body.get('generationConfig', {}) for body in gemini_requests)
    assert any('test-signature' in json.dumps(body.get('contents')) for body in gemini_requests[1:])
    for host, body, _ in requests:
        if host == 'api.tavily.com':
            assert 'Sample patient' not in json.dumps(body) and 'inlineData' not in json.dumps(body)


async def test_prerequisite_mistake_can_recover(catalog):
    first = True
    def override(body):
        nonlocal first
        if first:
            first = False
            return {'name': 'extract_prescription_text', 'args': {'session': 'current'}}
        return {'name': body['tools'][0]['functionDeclarations'][0]['name'], 'args': {'session': 'current'}}
    transport, _ = live_transport(agent_override=override)
    settings = Settings(gemini_key='test-only')
    result = await run_agent(context(catalog, None, Providers(settings, transport), settings), lambda e: None)
    assert len(result.trace) == 8


@pytest.mark.parametrize('call', [{'name': 'run_shell', 'args': {'session': 'current'}},
                                 {'name': 'analyze_prescription_image', 'args': {'session': 'current', 'url': 'http://evil.test'}},
                                 {'name': 'analyze_prescription_image', 'args': {'session': 'other'}}])
async def test_agent_rejects_unknown_tools_and_arguments(catalog, call):
    transport, _ = live_transport(agent_override=lambda body: call)
    settings = Settings(gemini_key='test-only')
    with pytest.raises(AnalysisError, match='agent_failure'):
        await run_agent(context(catalog, None, Providers(settings, transport), settings), lambda e: None)


async def test_agent_has_bounded_turns(catalog):
    transport, requests = live_transport(agent_override=lambda body: {'name': 'generate_patient_summary', 'args': {'session': 'current'}})
    settings = Settings(gemini_key='test-only')
    with pytest.raises(AnalysisError, match='agent_incomplete'):
        await run_agent(context(catalog, None, Providers(settings, transport), settings), lambda e: None)
    assert len(requests) == 12


async def test_incomplete_ocr_stops_no_fallback(catalog):
    def handler(request):
        body = json.loads(request.content)
        if 'tools' in body:
            name = body['tools'][0]['functionDeclarations'][0]['name']
            return httpx.Response(200, json={'candidates': [{'content': {'parts': [{'functionCall': {'name': name, 'args': {'session': 'current'}}}], 'role': 'model'}}]})
        return httpx.Response(200, json={'candidates': [{'content': {'parts': [{'text': '<!DOCTYPE html>'}]}}]})
    settings = Settings(gemini_key='test-only')
    ctx = context(catalog, None, Providers(settings, httpx.MockTransport(handler)), settings)
    with pytest.raises(AnalysisError, match='invalid_extraction'):
        await run_agent(ctx, lambda e: None)
    assert ctx.result is None


@pytest.mark.parametrize('kind', ['PNG', 'JPEG', 'WEBP'])
def test_real_image_validation_and_preprocessing(kind):
    original = image_url(kind=kind)
    processed, metrics = prepare_image(original)
    assert processed.startswith('data:image/jpeg;base64,')
    assert metrics.width == 800 and metrics.height == 1000
    assert metrics.sharpness > 0 and original != processed


@pytest.mark.parametrize('value', ['data:image/png;base64,SGVsbG8=', 'data:image/svg+xml;base64,SGVsbG8=',
                                  'data:image/jpeg;base64,not/base64!!!'])
def test_invalid_images_rejected(value):
    with pytest.raises(ValueError):
        prepare_image(value)


@pytest.fixture
def client():
    with TestClient(create_app(Settings(), rate_limit=10000)) as c:
        yield c


@pytest.mark.parametrize('sample', ['easy', 'handwritten', 'difficult'])
def test_api_demo_is_frontend_compatible_and_streams(client, sample):
    events = request_sample(client, sample)
    result = result_event(events)
    assert result['mode'] == 'demo' and len(result['trace']) == 8
    assert 'catalog_status' in result['medications'][0]
    assert set(result['medications'][0]['fields']) == set(FIELDS)


def test_correction_separate_original_and_unconfirmed_export(client):
    result = result_event(request_sample(client))
    old = copy.deepcopy(result['medications'][0]['fields'])
    response = client.post('/api/prescription/correct', json={'prescription': result, 'medication_id': 'm1',
                                                            'values': {'medicine_name': 'User spelling'}, 'confirm': False})
    assert response.status_code == 200
    corrected = response.json()['result']
    assert corrected['medications'][0]['fields'] == old
    assert corrected['user_corrections'][0]['ai_value'] == 'Panadol'
    from backend.model import Result
    model = Result.model_validate(corrected)
    assert effective_field(model, model.medications[0], 'medicine_name').status == 'uncertain'
    assert 'User spelling' not in export_text(model)
    response = client.post('/api/prescription/correct', json={'prescription': corrected, 'medication_id': 'm1',
                                                            'values': {'medicine_name': 'User spelling'}, 'confirm': True})
    assert response.status_code == 200 and len(response.json()['result']['user_corrections']) == 2


def test_personal_image_needs_key_never_gets_demo(client):
    response = client.post('/api/prescription/analyze', json={'image': image_url(), 'metrics': METRICS})
    assert response.status_code == 503 and response.json()['code'] == 'provider_unavailable'
    assert 'result' not in response.json()


def test_settings_do_not_expose_keys_or_trust_hosted_headers(client):
    assert client.get('/api/settings/provider').json() == {'configured': False, 'canConfigure': False}
    assert client.get('/api/settings/search').json()['catalog_records'] == 19060
    response = client.post('/api/settings/provider', headers={'oai-authenticated-user-email': 'forged@test.example'}, json={'key': 'test'})
    assert response.status_code == 403


def test_cross_origin_and_oversized_request_rejected(client):
    assert client.post('/api/prescription/analyze', headers={'Origin': 'https://evil.test'}, json={}).status_code == 403
    assert client.post('/api/prescription/analyze', headers={'Content-Length': '5000000'}, json={}).status_code == 413


@pytest.mark.parametrize('payload', [{}, {'sample': 'unknown', 'metrics': METRICS},
                                      {'sample': 'easy', 'image': image_url(), 'metrics': METRICS}])
def test_invalid_analysis_requests_return_json(client, payload):
    response = client.post('/api/prescription/analyze', json=payload)
    assert response.status_code == 400 and 'error' in response.json()


def test_rate_limit_is_explicit():
    with TestClient(create_app(Settings(), rate_limit=1)) as c:
        request_sample(c)
        assert c.post('/api/prescription/analyze', json={'sample': 'easy', 'metrics': METRICS}).status_code == 429


def test_server_recomputes_quality_instead_of_trusting_client_metrics():
    transport, _ = live_transport()
    with TestClient(create_app(Settings(gemini_key='test-only'), transport=transport)) as c:
        response = c.post('/api/prescription/analyze', json={'image': image_url((100, 100)), 'metrics': METRICS})
        events = [json.loads(s) for s in response.text.splitlines()]
        assert any(e.get('code') == 'quality_retake' for e in events)
        assert not any(e['type'] == 'result' for e in events)


def test_mocked_live_api_end_to_end():
    transport, _ = live_transport()
    with TestClient(create_app(Settings(gemini_key='test-only'), transport=transport)) as c:
        response = c.post('/api/prescription/analyze', json={'image': image_url(), 'metrics': METRICS})
        assert response.status_code == 200
        result = result_event([json.loads(s) for s in response.text.splitlines()])
        assert result['mode'] == 'live' and len(result['trace']) == 8

async def test_catalog_lookup_never_receives_raw_lines_or_patient_data(catalog):
    document = demo_extraction('easy').model_dump()
    document['medications'] = document['medications'][:1]
    document['medications'][0]['fields']['medicine_name'] = {
        'value': None, 'raw': 'Patient Ali phone 03000000000 Drug BD', 'confidence': 0, 'status': 'uncertain'}
    transport, requests = live_transport(document)
    settings = Settings(gemini_key='test-only', tavily_key='test-only')
    result = await run_agent(context(catalog, None, Providers(settings, transport), settings), lambda e: None)
    assert result.medications[0].catalog_status == 'unmatched'
    assert not any(host in ('rxnav.nlm.nih.gov', 'api.tavily.com') for host, _, _ in requests)


async def test_web_search_budget_is_three_per_prescription(catalog):
    document = demo_extraction('difficult').model_dump()
    document['medications'] = [copy.deepcopy(document['medications'][0]) for _ in range(5)]
    for i, med in enumerate(document['medications']):
        med['fields']['medicine_name'].update(value=f'MysteryBrand{i}', raw=f'MysteryBrand{i}', status='uncertain', confidence=.5)
    transport, requests = live_transport(document)
    settings = Settings(gemini_key='test-only', tavily_key='test-only')
    result = await run_agent(context(catalog, None, Providers(settings, transport), settings), lambda e: None)
    assert len([r for r in requests if r[0] == 'api.tavily.com']) == 3
    assert [m.web_status for m in result.medications][-2:] == ['skipped', 'skipped']


def test_live_api_ocr_failure_streams_safe_error_not_false_result():
    def handler(request):
        body = json.loads(request.content)
        if 'tools' in body:
            name = body['tools'][0]['functionDeclarations'][0]['name']
            return httpx.Response(200, json={'candidates': [{'content': {'role': 'model', 'parts': [
                {'functionCall': {'name': name, 'args': {'session': 'current'}}}]}}]})
        return httpx.Response(200, json={'candidates': [{'content': {'parts': [{'text': 'SECRET incomplete JSON'}]}}]})
    with TestClient(create_app(Settings(gemini_key='test-only'), transport=httpx.MockTransport(handler))) as c:
        response = c.post('/api/prescription/analyze', json={'image': image_url(), 'metrics': METRICS})
        events = [json.loads(s) for s in response.text.splitlines()]
        assert response.status_code == 200
        assert events[-1]['type'] == 'error' and events[-1]['code'] == 'invalid_extraction'
        assert not any(e['type'] == 'result' for e in events)
        assert 'SECRET' not in response.text

@pytest.mark.parametrize('status', [500, 502, 503, 504])
async def test_transient_gemini_http_failure_recovers_with_bounded_retry(status, caplog):
    attempts, waits = [], []
    def handler(request):
        attempts.append(request)
        return httpx.Response(status, text='SECRET prescription') if len(attempts) < 3 else httpx.Response(200, json={'candidates': []})
    async def sleep(seconds):
        waits.append(seconds)
    provider = Providers(Settings(gemini_key='private-test-key'), httpx.MockTransport(handler), sleep=sleep)
    assert await provider.gemini({}) == {'candidates': []}
    assert len(attempts) == 3 and len(waits) == 2
    assert 1 <= waits[0] <= 1.2 and 2 <= waits[1] <= 2.2
    assert 'SECRET' not in caplog.text and 'private-test-key' not in caplog.text


async def test_retry_exhaustion_keeps_http_status_and_stage():
    async def sleep(seconds):
        pass
    provider = Providers(Settings(gemini_key='test'), httpx.MockTransport(lambda r: httpx.Response(503)), sleep=sleep)
    with pytest.raises(AnalysisError) as caught:
        await provider.gemini({}, 'handwriting')
    assert caught.value.code == 'provider_busy'
    assert caught.value.safe_details() == {'stage': 'handwriting', 'http_status': 503, 'attempts': 3}


@pytest.mark.parametrize('exception,code,kind,attempt_count', [
    (httpx.ConnectError('SECRET name or service not known'), 'provider_network', 'dns', 3),
    (httpx.ConnectError('SECRET connection refused'), 'provider_network', 'connect', 3),
    (httpx.ConnectError('SECRET CERTIFICATE_VERIFY_FAILED'), 'provider_tls', 'tls', 1),
    (httpx.ProxyError('SECRET bad proxy'), 'provider_proxy', 'proxy', 1),
    (httpx.ConnectTimeout('SECRET'), 'provider_timeout', 'connect_timeout', 3),
    (httpx.ReadTimeout('SECRET'), 'provider_timeout', 'read_timeout', 1),
    (httpx.RemoteProtocolError('SECRET'), 'provider_network', 'protocol', 1),
])
async def test_network_errors_are_distinct_and_redacted(exception, code, kind, attempt_count, caplog):
    attempts = []
    def handler(request):
        attempts.append(request)
        raise exception
    async def sleep(seconds):
        pass
    provider = Providers(Settings(gemini_key='test'), httpx.MockTransport(handler), sleep=sleep)
    with pytest.raises(AnalysisError) as caught:
        await provider.gemini({}, 'agent')
    error = caught.value
    assert error.code == code and error.safe_details()['network_kind'] == kind
    assert len(attempts) == attempt_count and 'http_status' not in error.safe_details()
    assert 'SECRET' not in json.dumps(error_event(error)) and 'SECRET' not in caplog.text


async def test_authentication_and_quota_failures_are_not_retried():
    for status in (400, 401, 403, 404, 429):
        attempts = []
        def handler(request):
            attempts.append(request)
            return httpx.Response(status)
        with pytest.raises(AnalysisError):
            await Providers(Settings(gemini_key='test'), httpx.MockTransport(handler)).gemini({})
        assert len(attempts) == 1


async def test_connection_diagnostic_sends_no_image_and_does_not_reveal_key():
    from backend.scripts.check_provider import check
    requests = []
    def handler(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={'candidates': [{'content': {'parts': [{'text': 'SECRET provider text'}]}}]})
    result = await check(Settings(gemini_key='private-test-key'), transport=httpx.MockTransport(handler))
    assert result['ok'] is True and 'private-test-key' not in json.dumps(result)
    assert 'SECRET' not in json.dumps(result) and 'inlineData' not in json.dumps(requests)
    assert 'Connection test, no medical data' in json.dumps(requests)


def test_analysis_failure_log_contains_redacted_stage_and_status(caplog):
    transport = httpx.MockTransport(lambda r: httpx.Response(503, text='SECRET'))
    app = create_app(Settings(gemini_key='test'), transport=transport)
    async def no_delay(seconds):
        pass
    app.state.providers.sleep = no_delay
    with TestClient(app) as c:
        response = c.post('/api/prescription/analyze', json={'image': image_url(), 'metrics': METRICS})
        events = [json.loads(s) for s in response.text.splitlines()]
        assert events[-1]['code'] == 'provider_busy'
    failures = [json.loads(r.message) for r in caplog.records if 'analysis_failed' in r.message]
    assert failures[-1]['http_status'] == 503 and failures[-1]['stage'] == 'agent' and failures[-1]['attempts'] == 3
    assert 'SECRET' not in caplog.text


def test_proxy_configuration_is_explicit_and_validated(monkeypatch):
    monkeypatch.setenv('HTTPX_TRUST_ENV', 'false')
    assert Settings.from_env().httpx_trust_env is False
    monkeypatch.setenv('HTTPX_TRUST_ENV', 'true')
    assert Settings.from_env().httpx_trust_env is True
    monkeypatch.setenv('HTTPX_TRUST_ENV', 'incorrect')
    with pytest.raises(ValueError):
        Settings.from_env()
