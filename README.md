# PranaGuard — Patient-Specific COPD Digital-Twin Workspace

**Happiest Health Digital Twin Challenge 2026 · Engineering prototype and research submission**  
**Institution:** Pune Institute of Computer Technology (PICT), Pune

> PranaGuard is a synthetic-data research prototype combining longitudinal patient-twin replay, experimental multi-horizon risk visibility, model-study evidence, environmental context, and connected doctor–patient care workflows. It makes data coverage, model versions, provenance, assumptions and review actions inspectable; it does not make autonomous clinical decisions.

<p align="center">
  <a href="https://prana-guard-copd-digital-twin.vercel.app"><strong>Open live demo</strong></a> ·
  <a href="https://pranaguard-api.onrender.com/api/health"><strong>Backend health</strong></a> ·
  <a href="https://github.com/harshtakalkar037-boop/PranaGuard-COPD-Digital-Twin"><strong>Source repository</strong></a>
</p>

> [!CAUTION]
> **Research demonstration only. Not a medical device. Not clinically validated.** All patient identities and records are synthetic. Model outputs are experimental estimates on generated data and must not be used for diagnosis, triage, prescribing, treatment, emergency decisions, or claims of patient benefit. No real patient, hospital/EHR, or certified medical-device integration is provided.

---

## 1. The problem we are exploring

COPD status can change over time. A single measurement may not describe the context of a person's symptoms, daily records, baseline, or environmental conditions.

PranaGuard explores whether a patient-specific digital-twin workspace can make longitudinal signals, experimental risk estimates, model evidence, and care-team review easier to inspect in one connected experience. The prototype demonstrates that workflow on a frozen synthetic research cohort; it does not demonstrate reliable prediction of real COPD exacerbations or improved clinical outcomes.

## 2. What makes PranaGuard different

- **Stateful twin, not just a static dashboard:** replayable, versioned patient states and longitudinal history.
- **Visible research evidence:** model versions, experiment comparisons, evaluation results, limitations, and provenance are surfaced rather than hidden behind one score.
- **Connected doctor and patient workflows:** patient-submitted records can be reviewed by an assigned doctor; doctor-shared documents and follow-ups appear in the linked patient account.
- **Server-side access rules:** role and patient-assignment checks are enforced by the API, not only by hiding interface elements.
- **Honest missing-data handling:** surfaces show coverage, freshness, completeness, and empty states rather than inventing values.
- **Environmental context is separate from model inference:** optional city context is displayed separately and is not silently inserted into the frozen model inputs.
- **Additive evolution:** care-workspace and v6 capabilities extend the original twin, replay, alert, and study-explorer experience.

## 3. Live prototype and submission resources

| Resource | Link |
|---|---|
| Live web application | [PranaGuard dashboard](https://prana-guard-copd-digital-twin.vercel.app) |
| Backend health endpoint | [API health](https://pranaguard-api.onrender.com/api/health) |
| FastAPI interactive docs | [API docs](https://pranaguard-api.onrender.com/docs) |
| Source code | [GitHub repository](https://github.com/harshtakalkar037-boop/PranaGuard-COPD-Digital-Twin) |
| Doctor–patient delivery report | [DOCTOR_PATIENT_DELIVERY.md](docs/DOCTOR_PATIENT_DELIVERY.md) |
| v6 implementation report | [ENHANCEMENT_IMPLEMENTATION_REPORT.md](docs/ENHANCEMENT_IMPLEMENTATION_REPORT.md) |
| v6 acceptance evidence | [V6_ACCEPTANCE.md](docs/v6-verification/V6_ACCEPTANCE.md) |

The public frontend is hosted on Vercel and the FastAPI backend on Render. The currently audited Render API uses the Free plan and a local SQLite file. **Do not assume user-created demo records survive service restarts, redeployments, or filesystem resets.** This hosting configuration is for demonstration only and must never receive real patient information.

## 4. Jury walkthrough: recommended 5–7 minute flow

1. **Start at login.** Explain that the accounts are fictional demo identities and that the app has separate doctor and patient experiences.
2. **Open the doctor workspace.** Show grouped navigation, the synthetic patient directory, search, and the Care Action Centre.
3. **Open a patient profile.** Review the twin overview, baseline, historical state, sputum information, care plan, review history, and model-risk context.
4. **Explain risk evidence carefully.** Show 24/48/72-hour replay-model outputs with timestamps, model version, input completeness, freshness, review status, and explanation limitations. Do not call these clinically validated probabilities.
5. **Demonstrate the connected patient account.** Sign out and sign in as the linked patient. Add or inspect a daily wellbeing entry, sputum diary, and medication-adherence report.
6. **Return to the doctor account.** Show the same patient-submitted record, mark it reviewed, and demonstrate the audit trail.
7. **Show doctor-to-patient actions.** Share a fictional document or follow-up instruction, then show the linked patient view and authorized document access.
8. **Finish with Insights and Study Explorer.** Highlight date filters, honest missing-data states, experiment comparisons, and explicit model limitations.

### Demo identities

These are public synthetic demonstration credentials, not production credentials. Passwords may be overridden with environment variables before the first database seed.

| Username | Demo password | Experience |
|---|---|---|
| `dr-atlas` | `prana-atlas-demo` | Doctor account with synthetic cohort |
| `dr-nova` | `prana-nova-demo` | Empty doctor panel for assignment/isolation demonstration |
| `pat-pg0071` | `prana-patient-demo` | Patient account linked to synthetic patient PG-0071 |

Sessions use bearer tokens, PBKDF2 password hashes, and a 12-hour expiry. This is demo-grade authentication, not production identity management.

## 5. Feature set

### 5.1 Original digital-twin and research dashboard

- Frozen synthetic cohort with **120 patient profiles and 3,000 stored twin/window states**.
- Cohort overview, patient search, risk categories, and patient-specific views.
- Longitudinal twin-state history, versioned replay, and live dashboard updates through WebSockets.
- Baseline/current-state inspection, signal trends, and missingness/freshness context.
- Model inference and explanation surfaces for the frozen baseline pipeline.
- Scenario studio for conditional PM2.5, adherence, and activity assumptions.
- Persisted alerts, acknowledgement/resolution workflow, and clinician action notes.
- Data-integrity checks, cohort/model fingerprints, provenance manifests, and reproducible artifacts.

The frozen cohort is read-only research data. Demo write flows are designed to touch workspace tables, not rewrite the frozen scientific dataset.

### 5.2 Model-study and evidence explorer

- Versioned experiment history, gates, rollups, ablations, top-five summaries, leaderboard, scatter plots, and model comparisons.
- Experiment v2 (6-hour personalized) is rejected and retained as evidence, not presented as active.
- Experiment v3 (`pg48-v3-multiseed`) is an active experimental 48-hour early-warning model with its own frozen-gate evidence.
- v4 evidence, gap analysis, final selection report, and TreeSHAP cache are retained and integrity-checked.
- v5 study explorer presents frozen-versus-active comparisons without overwriting prior study results.

### 5.3 Clinician workspace and connected patient experience

- Signed-in clinician workspace, unified patient directory, onboarding, patient 360° profile, and persisted Care Action Centre review workflow.
- Patient daily wellbeing log, sputum diary, and medication adherence with audited corrections.
- Doctor-reviewed flags, clinical document upload/share with SHA-256 provenance, follow-up instructions, and uniform audit trail.
- Patient home summary and patient insights for symptoms/breathlessness/cough, replay breathing rate, sleep, activity, hydration, adherence, and wellbeing.
- 7/30/90-day and custom date filters, with explicit empty states where replay data is unavailable.
- Exactly three patient navigation items: Patient Home, My Health Records, and Clinical Documents.

### 5.4 v6: doctor risk visibility and patient insights

- Doctor risk cards for 24/48/72-hour horizons, including prediction timestamp, model version, data completeness, freshness, and review status.
- 72-hour watchlist and patient-profile Model Risk tab, plus timestamped prediction history.
- Feature-contribution view reuses the existing frozen engine explanation path.
- Patient insights and home summaries are data-backed and preserve honest missing-data states.
- Patient sessions are blocked with HTTP 403 from doctor-only prediction endpoints.
- All risk outputs are labelled as experimental synthetic-data estimates and not intended for diagnosis, triage, or treatment decisions.

## 6. Architecture and technology

| Layer | Technology |
|---|---|
| Frontend | React, TypeScript, Vite, Tailwind CSS, Recharts, Lucide React |
| Backend/API | Python, FastAPI, Uvicorn, Pydantic |
| Data and ML | pandas, NumPy, scikit-learn, LightGBM, joblib |
| Persistence | SQLite, WAL, foreign keys, transactional writes, additive migrations |
| Communication | REST API and WebSockets |
| Testing | pytest, Vitest, React Testing Library, Playwright Chromium |

```text
backend/app/
  main.py, engine.py, store.py      frozen research API and twin engine
  enhanced/                         registry, alerts, devices, environment, evidence
  workspace/                        authentication, directory, patient profile, care workflows
  migrations/                       additive, checksummed database migrations
models_store/, baseline_outcomes/   frozen model artifacts and baseline evidence
experiments-v2…v4, docs/model*/      versioned studies and evaluation artifacts
frontend/src/
  pages/                            original dashboard and research pages
  pages-enhanced/                   study and model-science pages
  workspace/                        login, directory, profile, Care Action Centre
docs/                               implementation reports and verification evidence
```

## 7. Data, model methodology, and interpretation

- The research cohort contains 120 synthetic patient profiles and 3,000 synthetic window states. These records do not represent real people.
- The frozen baseline model is `pg-synthetic-v1`. Its runtime scores are raw replay-model outputs and must not be described as calibrated clinical probabilities.
- The separate `pg48-v3-multiseed` experiment is a synthetic-only 48-hour study model. Do not conflate its evaluation with the frozen baseline runtime.
- The v6 prediction-history feature records timestamped outputs and model/state versions; it does not modify historical raw scores.
- Environmental context is optional, city-level gridded/modelled information. USAQI is not CPCB/Indian NAQI; environmental context is not a personal exposure measurement and is not a frozen-model input.
- What-if scenarios are conditional sensitivity analyses, not validated disease trajectories, causal intervention effects, or treatment recommendations.
- TreeSHAP/model explanations describe model associations, not causation. A lower model score is not evidence that an intervention improves health.

## 8. Validation, tests, and verification evidence

Latest recorded v6 verification (2026-11-07):

| Check | Recorded result |
|---|---:|
| Backend pytest suite | **151 passed** |
| Frontend Vitest suite | **78 passed** |
| TypeScript check | Clean |
| Production frontend build | Passed |
| Doctor–patient real-browser round trip | **14/14 passed** |
| Workspace browser regression | **15/15 passed** |
| v6 risk/insights browser verification | **7/7 passed** |
| Clean extraction setup and test verification | Passed |

Evidence files:
- [v6 acceptance matrix](docs/v6-verification/V6_ACCEPTANCE.md)
- [Doctor–patient browser results](docs/doctor-patient-verification/BROWSER_DOCTOR_PATIENT.json)
- [Workspace browser results](docs/workspace-verification/BROWSER_WORKSPACE.json)
- [v6 browser results](docs/v6-verification/V6_BROWSER_RESULTS.json)

These are recorded software tests and browser checks on synthetic data. They are **not** independent clinical validation, prospective evaluation, regulatory verification, or evidence of patient benefit. Re-run the suites against the exact commit used for final submission.

## 9. Security, privacy, and limitations

### Implemented demo safeguards

- PBKDF2-hashed demo passwords and expiring bearer sessions.
- Doctor assignment scoping and patient-own-record scoping enforced in backend services.
- Doctor-only risk endpoints reject patient sessions.
- Document type/size/signature checks, SHA-256 provenance, and authorized document downloads.
- Audited record corrections and actor-attributed workflow actions.
- Additive, checksummed, transactional database migrations.
- No real patient records or credentials are included in the project dataset.

### Limitations reviewers should know

- No real patient data, clinician-adjudicated labels, prospective cohort, or external clinical validation.
- No medical-device certification, hospital/EHR integration, or real wearable telemetry.
- Demo authentication is not production-grade identity/RBAC or a regulated clinical access system.
- No claim of HIPAA/GDPR or other healthcare regulatory compliance is made.
- Current Render Free service uses local SQLite storage; hosted writes are not guaranteed durable. Do not enter real patient information.
- Environmental sources are gridded/modelled products, not personal exposure measurements.
- What-if scenarios are noncausal sensitivity analyses; explanations are associations, not causation.

Before any real-world study, the project would require ethics review, informed consent, governed longitudinal COPD data, clinician-adjudicated outcomes, prospective multi-site evaluation, subgroup and calibration assessment, secure identity/access management, clinical oversight, and a validated safety process.

## 10. Local setup

### Prerequisites

- Python 3.11 or newer (v6 verification used Python 3.13).
- Node.js 20 or newer and npm.
- Git.

### Install

```bash
git clone https://github.com/harshtakalkar037-boop/PranaGuard-COPD-Digital-Twin.git
cd PranaGuard-COPD-Digital-Twin
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
npm --prefix frontend ci
```

### Start the backend

```bash
.venv/bin/python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

### Start the frontend in a second terminal

```bash
npm --prefix frontend run dev
```

Open [http://127.0.0.1:5173](http://127.0.0.1:5173). Vite proxies API requests and WebSockets to the local FastAPI service. Use a single Uvicorn worker; distributed replay coordination is not implemented.

### Useful verification commands

```bash
.venv/bin/python -m pytest backend/tests/ -q
npm --prefix frontend test
npm --prefix frontend run build
.venv/bin/python -m scripts.browser_verify_workspace
.venv/bin/python -m scripts.browser_verify_doctor_patient
.venv/bin/python -m scripts.browser_verify_v6
```

Use a disposable database copy for risky tests or reset/bootstrap commands. Never run reset or data-generation commands against a database whose demo actions you need to preserve.

## 11. Configuration reference

| Variable | Purpose |
|---|---|
| `PRANAGUARD_DB` | SQLite database path; use a copy for experiments |
| `PRANAGUARD_DEMO_DOCTOR_PASSWORD` | First-seed password override for `dr-atlas` |
| `PRANAGUARD_DEMO_DOCTOR2_PASSWORD` | First-seed password override for `dr-nova` |
| `PRANAGUARD_DEMO_PATIENT_PASSWORD` | First-seed password override for `pat-pg0071` |
| `PRANAGUARD_LIVE_ENV_ENABLED` | Opt-in live city environment integration; disabled by default |
| `PRANAGUARD_ENV_TTL_SECONDS` | Environment cache lifetime |
| `PRANAGUARD_ENV_RETRY_SECONDS` | Environment provider retry interval |
| `PRANAGUARD_ENV_TIMEOUT_SECONDS` | Environment provider timeout |
| `OPEN_METEO_API_KEY` | Optional provider key, if required by the selected provider |
| `PRANAGUARD_DEVICE_SECRET` | Optional device-simulator secret |
| `PRANAGUARD_ADMIN_TOKEN` | Optional shared demo admin token for protected legacy write routes |
| `PRANAGUARD_CORS_ORIGINS` | Comma-separated allowed frontend origins |

Set secrets only in the backend environment. Do not commit `.env`, credentials, tokens, or private keys. Demo password overrides apply when demo users are first seeded; changing an environment variable after account creation does not automatically rewrite the stored password.

## 12. Team and institution

- **Challenge:** Happiest Health Digital Twin Challenge 2026.
- **Institution:** Pune Institute of Computer Technology (PICT), Pune.
- **Team lead / original submission repository owner:** Anuja Naik.
- **Engineering, frontend/backend implementation, and documentation:** Harsh Takalkar.
- **Clinical advisor:** None claimed.

Please ensure the final challenge submission uses the official complete team roster and role wording agreed by the team.

## 13. Future work

1. Move hosted writable records to managed persistent storage with backups, migration testing, and controlled access.
2. Improve identity, authorization, secret management, audit retention, and deployment hardening before any sensitive-data use.
3. Evaluate model stability on new, pre-registered synthetic cohorts without tuning against the existing test set.
4. Seek ethically approved access to governed longitudinal COPD data and clinician-adjudicated outcomes.
5. Conduct prospective, multi-site evaluation of calibration, uncertainty, fairness, missingness, and useful lead time.
6. Integrate validated devices or EHR systems only with appropriate security, consent, interoperability, and governance.
7. Develop and validate any mechanistic or causal response model before making intervention-effect claims.

## 14. License and attribution

Refer to the repository [LICENSE](LICENSE) and [third-party notices](docs/THIRD_PARTY_LICENSES.md) for code, synthetic data, cached environmental products, dependencies, and asset terms. Environmental-provider attribution does not imply endorsement.

---

<p align="center">
  <strong>PranaGuard</strong><br/>
  Patient-specific digital-twin research workspace · Synthetic data only · No clinical validation
</p>
