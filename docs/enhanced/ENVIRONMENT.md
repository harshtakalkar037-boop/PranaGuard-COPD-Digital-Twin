# India environmental context — opt-in external models, explicit fallback

## Provider and scope
The implemented provider is Open-Meteo's current air-quality and weather APIs. Real integrated requests succeeded for Pune, Mumbai, Delhi and Bengaluru; exact source/valid/retrieved times and results are retained in`verification/LIVE_PROVIDER_VERIFICATION.json`and`live-context-*.json`. Those files are **dated evidence**, not production current-data fallbacks.

The city registry is centralized in`backend/app/enhanced/settings.py:CITIES`; frontend city menus load it from the API. Add a new city with independently verified coverage/terms and a historical cache strategy; do not guess a station ID or accept arbitrary URLs from clients.

- Air: PM2.5,PM10,NO₂,O₃ and **U.S. AQI** from the CAMS global model domain.
- Weather:2m temperature, relative humidity, WMO weather code,10m wind speed/direction where returned.
- Every component/metric identifies source/type, unit, valid time, retrieval time, freshness/missingness and city-grid scope. Grid coordinates can differ from the requested city-centre point.
- These are modelled estimates, not CPCB station observations, certified patient measurements or personal-exposure estimates. U.S. AQI is **not** Indian NAQI; no Indian AQI is computed from incomplete fields.
- Current context never enters the frozen ML frame. Historical model inputs still use only the original licensed historical caches/data.

## Configuration
Default:`PRANAGUARD_LIVE_ENV_ENABLED=false`. Historical replay and inference remain offline-ready.

For an authorized non-commercial demo, set backend`.env`:

```dotenv
PRANAGUARD_LIVE_ENV_ENABLED=true
PRANAGUARD_ENV_TTL_SECONDS=900
PRANAGUARD_ENV_RETRY_SECONDS=300
PRANAGUARD_ENV_TIMEOUT_SECONDS=8
```

Restart the backend after configuration changes. The normal free endpoints require no key. Optional`OPEN_METEO_API_KEY`is backend-only and switches to documented customer hosts; paid-account access was not externally tested. Do not use free non-commercial hosting for a commercial service without the appropriate agreement.

## Cache, rate control and errors
- Independent air/weather entries in SQLite; original provider values are preserved as returned after timestamp/unit/numeric validation.
- Default15min TTL; minimum5min TTL/request interval, including forced refresh. A single4-city instance is thereby bounded below the documented free daily request ceiling under these defaults/clamps; shared provider IP/rate limits can still cause429.
- Failure backoff:5,10,20,40,then60min capped, with numeric`Retry-After`honoured for longer delays up to24h. It is not an automatic tight-loop retry. A user refresh during cooldown returns the explicit cache/fallback, not a fake new retrieval timestamp.
- Concurrent same-city requests share a lock. Hostnames are fixed to provider domains; no user URL/SSRF proxy is offered. Timeout is bounded, redirects disabled. Provider exceptions expose only exception class/HTTP status, never response bodies or URLs containing keys.
- A provider valid time older than3h is explicitly stale, even if HTTP200. A stale-data-quality notice is created.
- A failed component does not erase a successful component.

Fallback chain: fresh current/cache → stale last-current cache with error → checksum-verified original historical cache with original dates → explicit unavailable/null fields. When requests are disabled, any current cache is labelled stale; otherwise the historical cache is used. The historical files do **not** contain U.S. AQI, current weather codes or wind; these remain missing rather than fabricated.

## Attribution and access investigation
Primary docs/terms inspected:
- https://open-meteo.com/en/docs/air-quality-api
- https://open-meteo.com/en/docs
- https://open-meteo.com/en/terms
- https://open-meteo.com/en/licence

Data attribution is visible in the UI and source ledger: Open-Meteo, Copernicus Atmosphere Monitoring Service and weather-model providers; data CC BY4.0. Free non-commercial limits documented at audit:600/min,5000/hour,10000/day,300000/month. Provider availability/accuracy is not guaranteed. Preserve attribution when redistributing dated response evidence.

IMD's official documented current endpoint returned401/API key missing; no authorized key was supplied. CPCB/Data.gov.in coverage/access/licensing could not all be verified in this environment. They are listed **not integrated**, not silently replaced or misrepresented as connected. See`PROVIDER_INVESTIGATION.md`.

## Notification rule
Modelled PM2.5≥35µg/m³ or U.S.AQI≥100 can create a city-linked environmental notice for fresh context only. This is an explicitly unvalidated demonstration rule, not a verified COPD trigger or personal-exposure/clinical threshold. No email or emergency action occurs automatically.
