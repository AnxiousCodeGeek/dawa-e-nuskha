# Dawa-e-Nuskha — Python backend edition

An accessible English/Urdu application that reads and organizes prescriptions, shows the original image beside the extracted information, and keeps human corrections separate from the AI interpretation.

**AI-assisted transcription — verify against the original prescription.** It does not diagnose, prescribe, substitute medicines or change a doctor's instructions. Verify unclear medicine names, strengths and instructions with a doctor or pharmacist.

## What is included

Two source folders: **`backend/`** is a real Python/FastAPI implementation, and **`frontend/`** is the existing React/Next.js interface. There is no TypeScript backend, subprocess bridge to an old agent, or trained `.pt` checkpoint. The agent is implemented in `backend/agent.py`, with decorated functions in `backend/tools.py` and models in `backend/model.py`.

The approved UI, logo, Urdu font, samples, accessibility settings, source-region viewer, review flow and encrypted local history are retained. The published website has not been modified by this download.

## Requirements

- Python **3.11 or newer**; this package was tested with Python 3.12.
- Node.js **22.13 or newer** and npm.
- Gemini API access/quota for personal-image analysis.
- Optional Tavily API access for medicine-name web evidence.
- Ports **8000** (Python API) and **3000** (frontend) available locally.

## Setup

Extract the ZIP and open a terminal in the `dawa-e-nuskha` project root.

### 1. Install the Python backend

```bash
python -m venv .venv
```

Activate the environment:

| System | Command |
| --- | --- |
| macOS / Linux | `source .venv/bin/activate` |
| Windows PowerShell | `.venv\Scripts\Activate.ps1` |
| Windows Command Prompt | `.venv\Scripts\activate.bat` |

```bash
python -m pip install -r backend/requirements-dev.txt
```

This installs the backend and its tests. For only runtime dependencies, use `backend/requirements.txt`. `backend/requirements-lock.txt` records the complete Python package versions used for the delivered checks.

If your system names Python `python3`, use it in place of `python` when creating the environment. After activation, `python` refers to that environment.

### 2. Add your keys

`backend/.env` is supplied **completely empty**. Add your own values:

```dotenv
GEMINI_API_KEY=your_gemini_key
GEMINI_MODEL=gemini-2.5-flash
TAVILY_API_KEY=your_optional_tavily_key
OPENAI_API_KEY=your_optional_openai_key
```

Gemini is the implemented vision and agent provider. Tavily is optional. OpenAI is reserved for a future adapter; supplying its key does **not** enable an OpenAI pipeline in this edition. Select a Gemini model that your Google project can access.

The Python backend loads this file with `python-dotenv`; existing server environment variables take precedence. Restart the Python server after changing keys. Never commit `.env`, put keys in frontend components or use `NEXT_PUBLIC_` for secrets.

Samples work with an empty `.env`. Real uploads return a clear configuration error until Gemini is connected.

### 3. Start the Python API — terminal 1

From the project root, with the virtual environment activated:

```bash
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

Health endpoint: http://127.0.0.1:8000/api/health  
Interactive API documentation: http://127.0.0.1:8000/docs

### 4. Start the frontend — terminal 2

From the project root:

```bash
npm install
npm run dev
```

Open **http://localhost:3000**. Next.js proxies `/api/*` to the Python server at `http://127.0.0.1:8000`, including streaming responses. The frontend contains no prescription-reading backend implementation.

Keep both terminals running. The camera is optional: upload/gallery work without camera permission. `/owner/setup` explains file-based configuration rather than accepting private keys in a browser form.

## Project layout

| Path | Purpose |
| --- | --- |
| `backend/main.py` | FastAPI endpoints, request boundaries, status and rate limiting |
| `backend/agent.py` | Bounded tool-calling agent, progress stream and cancellation |
| `backend/tools.py` | Eight decorated Python tool functions |
| `backend/tool.py` | The `@tool` decorator, registry and Gemini function declarations |
| `backend/model.py` | Pydantic schemas, conservative normalization, corrections and safe export |
| `backend/context.py` | Temporary session state supplied internally to tools |
| `backend/providers.py` | Async Gemini, Tavily and RxNorm HTTP adapters |
| `backend/catalog.py` | Exact and similar-spelling retail catalog lookup |
| `backend/images.py` | Image validation, metrics, EXIF orientation and processed copy |
| `backend/demo.py` | Declared synthetic fixtures; never a live-image fallback |
| `backend/config.py`, `backend/.env` | Server configuration and your empty key file |
| `backend/data/` | 19,060 retail catalog rows and provenance manifest |
| `backend/tests/` | Python regression and mocked-provider integration tests |
| `backend/scripts/smoke_setup.py` | Starts both real servers and verifies the proxy/setup |
| `frontend/app/` | Workspace, styles and setup explanation page |
| `frontend/components/` | Hero, welcome screen, image viewer, medicine cards and reusable UI |
| `frontend/services/` | Browser image preprocessing, streaming client and local encrypted history |
| `frontend/shared/schema.ts` | Frontend data types/validators; not an AI backend |
| `frontend/i18n/`, `frontend/public/` | English/Urdu copy, approved logo, samples and licensed fonts |

## Decorated tools and agent behavior

The functions are organized as real Python tools:

```python
from .tool import tool

@tool(requires=('analyze_prescription_image',))
async def extract_prescription_text(context):
    """Extract the image while preserving uncertainty."""
    context.extraction = await context.providers.extract(context.image)
```

`@tool` is a small project-owned decorator, not a cosmetic marker or a dependency on LangChain. It preserves the function, registers its name/docstring/prerequisites, creates its provider function declaration and exposes an async invocation wrapper. The agent invokes this registered function. The model can pass only `session="current"`; it cannot provide arbitrary Python, URLs, keys or image data as tool arguments.

The live Gemini agent may call registered tools across multiple turns. Prerequisites prevent out-of-order execution, unknown names/arguments are rejected, and the run is bounded to 12 model turns and a 180-second overall timeout. Responses preserve provider content, including thought signatures, in the conversation history. A closed client stream cancels the analysis task.

| Tool | Purpose |
| --- | --- |
| `analyze_prescription_image` | Check resolution, brightness and sharpness; request a retake or explicit override |
| `extract_prescription_text` | Gemini image transcription with a structured response schema |
| `structure_prescription` | Build typed data without filling missing fields |
| `identify_medicine` | Local catalog candidates, then RxNorm fallback |
| `search_medicine_web` | Optional Tavily evidence from bounded medicine-name queries |
| `verify_medicine` | Check reference identity without claiming to verify handwriting or dosage |
| `check_prescription_consistency` | Flag unreadable, missing, crossed-out or duplicate fields |
| `generate_patient_summary` | Produce a faithful summary from readable fields |

Samples execute the same decorated tool sequence with explicit fixtures. Personal images never silently receive sample results.

## Uncertainty and human review

Low-confidence readings stay uncertain. Missing fields stay missing. When a unit such as `mg` is visible but its number is unreadable, strength is uncertain, not absent. A catalog or web candidate never rewrites the extracted medicine name, changes its confidence, invents a strength or becomes treatment advice.

User changes are appended to `user_corrections`, with the original AI field preserved. User confirmation is not clinical verification and does not update the shared catalog. Unconfirmed/crossed-out fields are omitted from export.

## API

| Endpoint | Response |
| --- | --- |
| `GET /api/health` | Python API health |
| `POST /api/prescription/analyze` | NDJSON progress, quality warning, structured result or safe error |
| `POST /api/prescription/correct` | Snapshot with separate corrections |
| `GET /api/settings/provider` | Gemini configured status, never the key |
| `GET /api/settings/search` | Tavily status and catalog row count |

Browser-based settings writes are disabled. There is no server-side prescription-history database. Optional device history is encrypted in the user's browser.

## Run the checks

With the Python environment activated, from the project root:

```bash
python -m pytest backend/tests -q
npm run typecheck
npm run build
python backend/scripts/smoke_setup.py
```

Stop development servers first: the smoke script requires ports 8000 and 3000 to be free. It starts and stops both servers itself, explicitly disables API keys for its checks, and makes no paid provider calls. It verifies the production homepage, real frontend-to-Python proxy, all three samples, streamed results, correction preservation and a JSON missing-provider error.

The delivered version passed **91 Python tests**, frontend type checking, a production build and the real two-server smoke test. The tests include mocked live Gemini function calling/OCR, Tavily contracts/failure behavior, catalog provenance, uncertainty, input validation, image decoding, correction preservation and server-side quality checks. Python dependencies were installed in a fresh virtual environment. The frontend build used the installed Node dependencies.

**Actual paid Gemini/Tavily calls are not validated with your credentials.** Connect your keys, verify quotas and evaluate consented real images against professionally checked ground truth before relying on handwriting recognition. The checks are not clinical certification, calibrated OCR accuracy or browser usability testing.

## Troubleshooting the Gemini connection

A `POST /api/prescription/analyze 200 OK` log means the NDJSON stream opened. It does not mean the agent finished successfully. The final stream event can still report an upstream error. Repeated `GET /api/settings/provider 200 OK` entries are normal status reads, not Gemini connection tests.

The earlier `provider_busy` code covered both network exceptions and Gemini 5xx responses. This update distinguishes them and logs only safe diagnostics: stage, HTTP status, attempt count and a network category. It never logs keys, provider payloads or prescription contents.

With the Python environment activated, run from the project root:

```bash
python -m backend.scripts.check_provider
```

This makes a small Gemini text-generation connection test when a key is configured; it sends no prescription image or patient information. Its JSON output contains no API key. You can share that output when asking for help. An empty `.env` returns `provider_unavailable` without making a provider request.

| Code | Meaning / next step |
| --- | --- |
| `provider_busy` + `http_status: 500/502/503/504` | Gemini returned a temporary server error. The app now retries with bounded exponential backoff, at most three attempts. If it persists, retry later. |
| `provider_network` + `network_kind: dns/connect` | Python could not establish the connection. Check internet access, DNS/firewall and whether `generativelanguage.googleapis.com` is reachable from the backend machine. |
| `provider_tls` | Certificate verification failed. Check trusted CA certificates, system time and network inspection. If a legitimate custom CA is needed, configure `SSL_CERT_FILE`; never disable certificate verification. |
| `provider_proxy` | A configured proxy failed. Check `HTTP_PROXY`, `HTTPS_PROXY` and `ALL_PROXY` settings. |
| `provider_timeout` | The connection or response exceeded its timeout. Check the `network_kind` and retry after checking connectivity. |
| `provider_access` | Check the Gemini API key and project/model access. |
| `provider_quota` | Check Gemini quota/billing. The app does not repeatedly retry this error. |
| `provider_model` | Set a Gemini model your project can access, then restart. |

HTTPX respects proxy/certificate environment settings by default. If this machine has an unintended proxy configured and direct internet access is allowed, add `HTTPX_TRUST_ENV=false` to `backend/.env` and restart. This ignores environment proxy settings **and custom CA environment settings**; leave it `true` when the network requires those settings. TLS verification remains enabled in both modes.

Only connection-establishment failures and selected HTTP 5xx responses are retried. Authentication, model, quota, certificate, proxy, read-timeout and malformed extraction errors are not repeatedly retried. No result is fabricated after failure.

## Updating from the previous Python ZIP

Keep a private backup of your existing `backend/.env` before replacing the source folders. This ZIP supplies an empty `.env`; restore your own key file afterward, then restart both processes. Retain your existing Node/Python dependency installations if their versions match, or install using the README commands. The local history key and data format are unchanged.

## Production run

Build once with `npm run build`. In separate terminals:

```bash
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

```bash
npm start
```

The frontend rewrite targets local port 8000. If you move the API to another host/port, update `frontend/next.config.ts` and rebuild. For a different frontend origin, set `ALLOWED_ORIGINS` in the backend environment to an explicit comma-separated allowlist.

Both supplied commands bind to loopback for local use. This standalone edition has **no application authentication**. Before internet deployment, configure authentication/access controls, HTTPS, durable rate limiting, provider/data policies and an appropriate sensitive-data security review. Static-only hosting cannot run this stack.

## Privacy, catalog and limitations

The original image stays in the browser; a processed copy is prepared for reading. The Python server validates image signatures, decodes bounded JPEG/PNG/WEBP data, recomputes quality metrics for real uploads, applies EXIF orientation and mild preprocessing, and retains no prescription after the session. It does not automatically solve arbitrary rotation, perspective or clipped pages.

Images go to Gemini after user consent. Catalog/web lookups use bounded medicine-name values, not raw prescription lines or patient metadata. Tavily uses allowed regulator/manufacturer/retail domains, generated answers are disabled, results are filtered again, searches are limited to three per prescription and public evidence has a best-effort in-memory cache. Provider policies still need review.

The bundled catalog is a **user-supplied, unverified retail dataset**, not a regulator-approved medicine list. The source manifest retains provenance; licensing, freshness and professional review are required before broader redistribution. Ingredient and prescribed-strength mappings are not inferred. RxNorm is US-centric.

Optional local history uses AES-GCM/PBKDF2 and a user-created passphrase. A forgotten passphrase cannot be recovered. Clearing browser data removes local history; exported files are outside the app's deletion controls. Some secondary UI copy remains English, voice availability varies by browser, and confidence is uncalibrated. The working name has not received legal trademark clearance.

## Provider references

- [Gemini function calling](https://ai.google.dev/gemini-api/docs/function-calling)
- [Gemini generateContent API](https://ai.google.dev/api/generate-content)
- [Tavily Search API](https://docs.tavily.com/documentation/api-reference/endpoint/search)
- [FastAPI testing](https://fastapi.tiangolo.com/tutorial/testing/)

See `README-GITHUB.md` for a concise repository-facing README, plus the backend/frontend README files for module details. Select an appropriate overall repository license and resolve source-data licensing before publishing publicly; the included Urdu font carries its own license.
