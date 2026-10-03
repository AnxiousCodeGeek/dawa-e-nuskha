# Dawa-e-Nuskha

An accessible AI-assisted prescription reader with a **Python/FastAPI backend** and **React/Next.js frontend**. Upload a prescription, inspect its reading beside the source image, and review uncertain fields without overwriting the original AI interpretation.

> AI-assisted transcription — verify against the original prescription. The app does not diagnose, prescribe or alter medication instructions.

## Features

- Optional camera or upload/gallery; three explicit synthetic demo samples.
- Real Gemini function-calling agent with eight decorated Python tools.
- Structured transcription, source regions, uncertainty and separate user corrections.
- Local Pakistani medicine-name candidates, RxNorm fallback and optional Tavily web evidence.
- English/Urdu, licensed self-hosted Urdu font, adjustable text, high contrast and voice.
- Encrypted local history, deletion, copy/share and print/save as PDF.

## Setup

Requirements: Python 3.11+, Node.js 22.13+ and npm. From the project root:

```bash
python -m venv .venv
```

Activate `.venv` with `source .venv/bin/activate` on macOS/Linux, `.venv\Scripts\Activate.ps1` in Windows PowerShell, or `.venv\Scripts\activate.bat` in Windows Command Prompt.

```bash
python -m pip install -r backend/requirements-dev.txt
npm install
```

The supplied `backend/.env` is empty. Add your own keys:

```dotenv
GEMINI_API_KEY=your_key
GEMINI_MODEL=gemini-2.5-flash
TAVILY_API_KEY=your_optional_key
OPENAI_API_KEY=your_optional_key
```

Gemini is implemented; Tavily is optional; OpenAI is reserved for a future adapter. Restart the backend after edits. Never commit `.env` or expose keys through `NEXT_PUBLIC_`.

Run the backend in one terminal:

```bash
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

Run the frontend in another:

```bash
npm run dev
```

Open http://localhost:3000. The frontend proxies `/api/*` to FastAPI. Samples work without keys; real uploads require Gemini. API documentation: http://127.0.0.1:8000/docs.

## How the agent works

`backend/agent.py` runs a bounded Gemini function-calling loop. `backend/tools.py` contains normal Python functions registered with the project's `@tool` decorator from `backend/tool.py`. The decorator supplies names, descriptions, prerequisites and function declarations; the agent calls the actual decorated functions.

The tools check image quality, extract handwriting, structure fields, identify medicine candidates, retrieve optional web evidence, check reference identity, flag inconsistencies and generate a faithful summary. The model receives only session-bound tool arguments. Unknown tools/arguments are rejected, prerequisites are enforced, and progress/results are streamed as NDJSON. `backend/model.py` validates structured data and preserves uncertainty.

Catalog matches cannot verify handwriting or infer doses. User corrections remain separate from the original reading. The catalog is not automatically updated by reviewing a prescription. Samples use declared fixtures through the same tool interfaces, never as fallback results for uploaded images.

## Checks

```bash
python -m pytest backend/tests -q
npm run typecheck
npm run build
python backend/scripts/smoke_setup.py
```

The smoke script requires ports 8000 and 3000 to be free; it starts/stops both real servers and disables API keys for its tests. The delivered version passed **75 Python tests**, frontend type checking, the production build and two-server integration checks. Provider contracts are tested with controlled HTTP fixtures; actual paid Gemini/Tavily calls require your credentials. These checks do not establish clinical OCR accuracy.

## Privacy and scope

No API keys or personal prescriptions are included. Personal images are sent to the configured reading provider after consent. Web/catalog queries use bounded medicine names; web references never silently rewrite medical fields. Optional prescription history is encrypted locally rather than stored on the server.

The 19,060-row catalog is user-supplied unverified retail data. Review its licensing/currentness before redistribution. This standalone edition has no application authentication: configure HTTPS, access controls and durable abuse protection before public deployment. An overall open-source license has not been selected; font licensing is included. See `README.md` for complete setup, architecture, privacy and limitations.
