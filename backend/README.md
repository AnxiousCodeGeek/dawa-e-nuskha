# Python backend

FastAPI, Pydantic and async HTTPX implementation. There are no TypeScript backend modules or trained model weights.

| File | Role |
| --- | --- |
| `agent.py` | Bounded function-calling orchestration and NDJSON stream |
| `tools.py` | Eight `@tool`-decorated functions |
| `tool.py` | Decorator, function registry and provider declarations |
| `model.py` | Typed schema, normalization, corrections and safe export |
| `main.py` | HTTP endpoints, request limits and status |
| `providers.py` | Gemini, Tavily and RxNorm adapters |
| `images.py` | Signature checks, bounded decoding and image metrics/preprocessing |
| `catalog.py`, `data/` | Retail reference candidates and provenance |
| `context.py` | Temporary analysis state |
| `config.py`, `.env` | Server configuration; `.env` is deliberately empty |
| `tests/`, `scripts/` | Python tests and real two-server setup test |

From the project root, activate a virtual environment, install `backend/requirements-dev.txt`, then run `python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload`. Add your own Gemini and optional Tavily keys to `.env` and restart. OpenAI is reserved, not implemented.

Run `python -m pytest backend/tests -q`. After installing/building the frontend, stop existing servers and run `python backend/scripts/smoke_setup.py`. The smoke test disables keys and starts both processes itself.

The `@tool` decorator is project-owned and invokes ordinary Python functions. Server-only context carries credentials and the image. The LLM can pass only `session="current"`; the agent validates that argument and tool prerequisites.

No prescription database or API-key browser administration is included. Keys come from the environment. Local catalog rows are unverified retail references, and web evidence does not confirm a transcription. See the root README for privacy and deployment limits.

Connection check: `python -m backend.scripts.check_provider`. This sends only a small text probe if a key is configured. HTTPX proxy settings remain enabled by default; configure `HTTPX_TRUST_ENV` deliberately as described in the root README. TLS verification is never disabled. Logs contain safe stages/status/category only, with bounded retries for connection errors and selected 5xx responses.
