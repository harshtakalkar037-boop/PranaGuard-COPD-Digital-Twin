# Data provenance and access

## Real versus synthetic

| Component | Provenance | Meaning |
|---|---|---|
| Patient profiles and clinical history | Synthetic, seed 2026 | No real people, no hospital/EHR records |
| Physiology, wearable-style values, sleep, activity | Synthetic stochastic process | Not device measurements |
| Symptoms, adherence and outcome onsets | Synthetic | Not clinician-adjudicated exacerbations |
| Ambient PM2.5, PM10, NO2, O3 | Cached public Open-Meteo / CAMS global model product | Gridded ambient concentration, not personal exposure |
| Temperature and humidity | Open-Meteo Historical Weather API | Historical model/reanalysis context, not patient sensors |
| Model predictions and explanations | Executed fitted models | Synthetic proof-of-concept estimates |
| What-if trajectories | Recomputed model inference on projected feature paths | Non-causal sensitivity; no proven intervention effect |

The delivered cohort is 120 patients × 60 days × 24 hours = 172,800 rows from 2026-08-01 through 2026-09-29 UTC. There are 263 stochastic synthetic event onsets across the entire dataset, not 263 real exacerbations. Check [generation_manifest.json](../data/generation_manifest.json) for the actual seed and checksum.

## Public sources verified and cached

- Air quality documentation: https://open-meteo.com/en/docs/air-quality-api
- Air endpoint: https://air-quality-api.open-meteo.com/v1/air-quality
- Weather documentation: https://open-meteo.com/en/docs/historical-weather-api
- Weather endpoint: https://archive-api.open-meteo.com/v1/archive
- License: https://open-meteo.com/en/licence and https://creativecommons.org/licenses/by/4.0/
- Hosted access conditions: https://open-meteo.com/en/terms and https://open-meteo.com/en/pricing
- Upstream CAMS product: https://ads.atmosphere.copernicus.eu/datasets/cams-global-atmospheric-composition-forecasts?tab=overview

Four demonstration locations are used: Pune (18.5204, 73.8567), Mumbai (19.0760, 72.8777), Delhi (28.6139, 77.2090), Bengaluru (12.9716, 77.5946). Eight successful API responses (air + weather per location), each with 1,440 hourly timestamps, were retrieved during this build. Exact URLs and access timestamps are recorded rather than guessed in [environment/manifest.json](../data/environment/manifest.json).

Open-Meteo documents CAMS global data at approximately 0.4° (~45 km) resolution and 3-hourly source resolution, exposed as hourly API values. These data cannot resolve indoor pollutants, travel, occupational exposure or actual inhaled dose. The cache is historical and MUST NOT be described as today's air quality. UTC is used throughout the application; no implicit Indian-local-time conversion is made.

## Transformations and restrictions

Raw responses are saved without alteration and verified by SHA-256. Generation joins UTC timestamps, renames fields and aligns ambient values to each city's synthetic profiles. Subject-level clinical inputs are synthetic. Missing wearable readings are generated independently at about 1.2% for four fields after baseline calibration; their exact realized counts are in the data. Ambient data are not backward-filled. Cache gaps cause a clear error.

`python -m scripts.fetch_environment` is an explicit network operation. Normal application startup, replay, training from the bundled cache and inference work offline. The cache is included under CC BY 4.0 with attribution; no restricted clinical dataset is redistributed.

If there is no cache, generation fails by default. `--allow-synthetic-environment` explicitly permits a labelled synthetic environmental fallback. It does not silently pretend generated values are real. The default 60-day generator requires 60 days of cache. Date-range/coverage mismatch is an error rather than recycling real dates without disclosure.

Historical atmospheric products may be revised and are not archived, as-issued production forecasts. Features only use current/past timestamps, but this experiment is retrospective and cannot establish as-of operational availability. No future realized environmental trajectory is supplied to prediction or scenario inference.


## Enhanced edition: separate monitoring/current-context ledger

The original frozen data/model/evaluation provenance above is unchanged. Enhanced registration fields and symptom/adherence entries are explicitly fictional manual demo data; device observations are backend software simulations, never physical measurements. Current Open-Meteo/CAMS air/weather is independently retrieved modelled city-grid context, cached with valid/retrieved timestamps and per-component freshness/error/missingness. Its U.S. AQI is not CPCB Indian NAQI. CPCB/IMD are not integrated.

The dedicated **Data sources** screen and `/api/enhanced/provenance` expose record-level source/type/unit/timestamps/freshness/patient/missingness and whether a record is an original historical model input. New streams/current context are excluded from frozen ML features. Historical fallback preserves original2026 dates and absent AQI/weather/wind fields as null. See [environment](enhanced/ENVIRONMENT.md), [devices](enhanced/DEVICE_INTEGRATION.md), [onboarding/migrations](enhanced/PATIENTS_AND_MIGRATIONS.md) and [provider investigation](enhanced/PROVIDER_INVESTIGATION.md). Dated API responses under `docs/enhanced/verification/` are actual verification evidence, not fabricated or hardcoded production fallback data.

## v7 research modules: external real datasets (additive)

Two public, permissively licensed datasets were added as separate research views. They are
never merged with the frozen synthetic cohort and never touch the twin feature store.

- **Cough-COPD (CC)** — Zenodo record 14881818 (v2, 2025-02-17), CC-BY-4.0, creators USTC +
  Hangzhou slan-health. The single `Cough-COPD(CC).rar` archive (md5
  63094082465da311b478951fdf882853) was extracted offline (unrar binary not bundled;
  documented on the record page). Labels kept verbatim from `train/`/`test/` folder names —
  no labels were invented. The platform ships only a filename/class/split index (853 rows)
  plus a calibrated research model artifact; raw audio is **not** redistributed. No
  participant identifiers exist in the publication, so participant independence is reported
  as unverifiable, and inference uploads are hashed, never stored.
- **TOLIFE Clinical Study A** — Zenodo record 23263785 v2.0, CC-BY-4.0. Processed
  participant-day aggregates (8,821 days / 86 coded participants) and an 80-entry
  exacerbation register were re-audited here: 42 events fall inside observed device frames,
  32 have any valid measurements in the prior 7 days (30 both). Study-provided
  model-estimated CAT/CCQ/mMRC classes are treated as derived estimates, NOT ground truth,
  and are excluded from predictors and charts. The platform ships coded IDs only
  (`tolife:<kit>`), derived aggregates and evaluation results; raw study tables are not
  redistributed. Horizon metrics (24/48/72h) are reported below chance — exploratory only.

Evidence classes are preserved across models: REAL_OBSERVED (measured) → REAL_DERIVED
(estimated/fitted) → and the pre-existing SYNTHETIC_GENERATED twin cohort, kept disjoint.
