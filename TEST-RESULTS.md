# Validation results

Validated 4 October 2026, Python 3.12 and Node.js 22+, before creating this archive.

| Check | Result |
| --- | --- |
| Fresh virtual environment and Python dependency installation | Passed |
| `pip check` | No broken requirements |
| Python backend regression/provider/API tests | 91 passed |
| Frontend TypeScript check | Passed |
| Frontend production build | Passed |
| Real Next.js to FastAPI proxy | Passed |
| All three samples through the running frontend proxy | Passed |
| Corrections retain original AI fields | Passed |
| Missing reading key returns JSON rather than HTML/fake results | Passed |
| Empty backend `.env` | Verified, zero bytes |

Gemini and Tavily provider tests used controlled HTTP fixtures, not private credentials or paid calls. The smoke script explicitly disables keys. Actual model access/quota and real handwriting recognition must be checked with your keys. The frontend used installed Node dependencies; a clean Node reinstall and human browser usability review were not part of these checks. These results do not establish clinical accuracy.

Reproduce with the commands in README.md.

## Update validation

Added tests cover bounded 500/502/503/504 recovery, exhausted retries, distinct DNS/TLS/proxy/timeout handling, no repeated quota/authentication calls, safe stage/status logs, proxy configuration, and the no-image connection check. All 91 tests passed. The credential-free check correctly returns provider_unavailable for the intentionally empty environment.

The guidance/sample section was reorganized into a dedicated component, with equal-height panels, larger sample previews, improved contrast and a wrapping footer. Layout review used the supplied screenshot and source; browser rendering was not verified here because the Chromium download failed. Actual Gemini availability on the user's machine remains dependent on its connection and credentials.
