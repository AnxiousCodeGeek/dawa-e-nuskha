"""Boot both real servers and test the Next.js -> Python setup without paid calls.

Run after npm run build: python backend/scripts/smoke_setup.py
Requires ports 8000 and 3000 to be free. Keys are explicitly disabled for this test.
"""
import base64
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
BASE = 'http://localhost:3000'
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def request(path, data=None):
    req = urllib.request.Request(BASE+path, data=json.dumps(data).encode() if data is not None else None,
        headers={'Content-Type': 'application/json', 'Origin': BASE})
    try:
        with OPENER.open(req, timeout=20) as response:
            return response.status, response.headers, response.read().decode()
    except urllib.error.HTTPError as error:
        return error.code, error.headers, error.read().decode()


def main():
    node = shutil.which('node')
    next_cli = next((p for p in (ROOT/'node_modules/next/dist/bin/next', ROOT/'frontend/node_modules/next/dist/bin/next') if p.exists()), None)
    if not node or next_cli is None or not (ROOT/'frontend/.next/BUILD_ID').exists():
        raise SystemExit('First run npm install and npm run build from the project root.')
    environment = os.environ.copy()
    for name in ('GEMINI_API_KEY', 'TAVILY_API_KEY', 'OPENAI_API_KEY'):
        environment[name] = ''
    environment['ALLOWED_ORIGINS'] = 'http://localhost:3000,http://127.0.0.1:3000'
    processes = []
    with tempfile.TemporaryFile() as logs:
        try:
            processes.append(subprocess.Popen([sys.executable, '-m', 'uvicorn', 'backend.main:app',
                '--host', '127.0.0.1', '--port', '8000', '--no-access-log'], cwd=ROOT,
                env=environment, stdout=logs, stderr=logs))
            processes.append(subprocess.Popen([node, str(next_cli), 'start', '-H', '127.0.0.1', '-p', '3000'],
                cwd=ROOT/'frontend', env=environment, stdout=logs, stderr=logs))
            deadline = time.monotonic()+30
            while time.monotonic() < deadline:
                if any(p.poll() is not None for p in processes):
                    raise AssertionError('Could not start both servers. Check that ports 8000 and 3000 are free.')
                try:
                    status, _, text = request('/api/health')
                    if status == 200 and json.loads(text).get('backend') == 'python':
                        break
                except (urllib.error.URLError, TimeoutError, ValueError):
                    pass
                time.sleep(.1)
            else:
                raise AssertionError('Python proxy did not become ready.')
            print('Real Next.js -> Python health proxy: passed')
            status, _, text = request('/')
            assert status == 200 and 'Dawa-e-Nuskha' in text
            print('Production homepage: passed')
            for sample, count in [('easy', 2), ('handwritten', 3), ('difficult', 2)]:
                status, headers, text = request('/api/prescription/analyze', {
                    'sample': sample, 'metrics': {'width': 1000, 'height': 1300, 'brightness': 220, 'sharpness': 100}})
                assert status == 200 and headers['content-type'].startswith('application/x-ndjson')
                events = [json.loads(s) for s in text.splitlines()]
                result = next(e['result'] for e in events if e['type'] == 'result')
                assert len(result['medications']) == count and len(result['trace']) == 8
                if sample == 'easy':
                    saved = result
                print(f'{sample} sample through real frontend proxy: passed')
            status, _, text = request('/api/prescription/correct', {'prescription': saved,
                'medication_id': saved['medications'][0]['id'], 'values': {'medicine_name': 'Reviewed sample'}, 'confirm': True})
            updated = json.loads(text)['result']
            assert status == 200 and updated['user_corrections'][-1]['user_value'] == 'Reviewed sample'
            assert updated['medications'][0]['fields']['medicine_name']['value'] == 'Panadol'
            print('Correction and original reading preservation: passed')
            out = io.BytesIO()
            Image.new('RGB', (700, 900), 'white').save(out, 'PNG')
            status, _, text = request('/api/prescription/analyze', {'image': 'data:image/png;base64,'+
                base64.b64encode(out.getvalue()).decode(),
                'metrics': {'width': 700, 'height': 900, 'brightness': 220, 'sharpness': 100}})
            assert status == 503 and json.loads(text)['code'] == 'provider_unavailable'
            print('Missing provider returns JSON, never HTML or fake extraction: passed')
        finally:
            for process in reversed(processes):
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()


if __name__ == '__main__':
    main()
