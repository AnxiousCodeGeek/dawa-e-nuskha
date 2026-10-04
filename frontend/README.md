# Frontend

React/Next.js interface retaining the approved hero, welcome screen, logo, Urdu typography, accessibility controls, source viewer, correction flow and encrypted device history.

Install from the project root with `npm install`; run `npm run dev` and open http://localhost:3000. Start the Python backend separately on port 8000. `next.config.ts` proxies `/api/*` to that backend and extends the proxy timeout for streamed analysis. There are no Next.js prescription API handlers.

`shared/schema.ts` supplies frontend types/validators and export formatting. `services/quality.ts` supplies a preliminary browser preview check; the Python backend recomputes real-image metrics independently. These are presentation/client helpers, not a TypeScript AI backend.

Use `npm run typecheck` and `npm run build`; `npm start` serves the production build. Static-only hosting cannot proxy and run the full application. Keep all keys in `backend/.env`, never in `NEXT_PUBLIC_` fields or frontend code.

Assets include the approved Dawa-e-Nuskha logo, synthetic samples and self-hosted Noto Nastaliq Urdu with its license. No personal prescription images are bundled. See the root README for two-terminal setup and the setup smoke test.
