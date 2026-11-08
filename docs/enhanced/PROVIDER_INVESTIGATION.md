# Environmental provider investigation — 2026-11-05

This investigation preceded implementation. No station/provider response is invented.

## Implemented candidate: Open-Meteo
Actual audit requests returned HTTP200 and current timestamps for Pune:
- `https://air-quality-api.open-meteo.com/v1/air-quality` with latitude/longitude, `current=pm2_5,pm10,nitrogen_dioxide,ozone,us_aqi`, `domains=cams_global`, `timezone=UTC`.
- `https://api.open-meteo.com/v1/forecast` with `current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m,wind_direction_10m`, `wind_speed_unit=kmh`, `timezone=UTC`.

These are **modelled atmospheric/weather estimates**, not CPCB monitoring-station observations, medical measurements or personal exposure. `us_aqi` is the U.S. AQI scale, not India's National AQI. No Indian AQI is fabricated or inferred from incomplete pollutant data.

Primary references inspected:
- https://open-meteo.com/en/docs/air-quality-api
- https://open-meteo.com/en/docs
- https://open-meteo.com/en/terms
- https://open-meteo.com/en/licence

The terms page specifies free non-commercial service under600 calls/minute,5000/hour,10000/day and300000/month; CC BY4.0 attribution applies to data. Commercial hosted access requires an appropriate subscription/key. Availability/accuracy are not guaranteed. The implementation caches components for15 minutes, rate-limits retries, uses bounded timeouts and requests only the four configured locations. Optional commercial credentials remain server-side. Exact current retrieval evidence is recorded separately after executing the integrated provider service.

## Not integrated: IMD
Official reference inspected: https://api.imd.gov.in/public/api_reference.html . Its documented current-weather endpoint `https://api.imd.gov.in/api/v1/current_wx` returned **401: API key missing**. No authorized key, station mapping/access agreement, complete rate-limit terms or redistribution license was supplied. Therefore no IMD data are fetched/displayed and no working IMD integration is claimed. Old indexed IMD documentation paths returned404; they are not used in application code. Access and licensing must be verified before implementing an IMD adapter.

## Not integrated: CPCB / Data.gov.in
Catalog investigated: https://www.data.gov.in/resource/real-time-air-quality-index-various-locations . It returned a service-unavailable page here. A request to the published resource endpoint `https://api.data.gov.in/resource/3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69?format=json&limit=1` failed TLS/connection establishment in this environment. No private key was supplied. Endpoint reachability, authorized coverage, current rate limits and applicable redistribution terms could not all be verified, so **no CPCB station integration is implemented** and no station values are substituted. Public third-party examples were used only to identify the resource to investigate, never as fabricated data.

## Fallback and model separation
Use the existing licensed historical city cache when current retrieval is disabled/fails and no recent provider cache exists. Preserve its original2026 dates and unknown fields; do not calculate missing AQI/weather/wind values. Provider component failures are explicit. Neither current snapshots nor simulated device observations alter frozen ML features, model artifacts, evaluation files or the historical cohort. No provider keys/credentials enter frontend code or persisted request URLs.
