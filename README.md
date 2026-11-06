# PranaGuard — Patient-Specific COPD Digital Twin

## Enhanced ZIP edition (2026-11-05)

Built **only in an isolated copy of the user-supplied fork** [`harshtakalkar037-boop/PranaGuard-COPD-Digital-Twin`](https://github.com/harshtakalkar037-boop/PranaGuard-COPD-Digital-Twin), based on commit `95a4e2b00fcb2d9df7210c6b87ecba171a0c4e91`. No push, deployment or modification of either remote/original workspace is claimed. The URLs and submission presentation below describe the original project, **not a deployment of these enhancements**.

**New:** searchable fictional-patient registry and profiles; 72-hour onboarding gates; four generic simulated device types with authenticated/idempotent ingestion; opt-in current city context; notification/read/review history; fixed-recipient demo SMTP test; record-level provenance. Original colours, fonts, shared cards/components and all scientific artifacts are preserved.

| Capability | Actual status |
|---|---|
| Fictional registration, profiles, review/history | Implemented; additive SQLite migrations; original 120-patient cohort preserved |
| Device integration | Software simulations only, backend-generated through validated REST ingestion; no hardware compatibility claim |
| New-patient predictions | **Not enabled.** 72h observation coverage is required; device-only streams still lack the compatible full evaluated feature frame. No manufactured probabilities |
| Current environment | Actual Open-Meteo/CAMS requests verified for Pune/Mumbai/Delhi/Bengaluru; default is explicit historical fallback until enabled |
| AQI | Actual provider U.S. AQI; **not CPCB Indian NAQI**; city-model context, not personal exposure |
| Notifications and reviews | Implemented; legacy model alerts retained and bidirectionally linked; demo rules only |
| Email | Disabled by default; preview/outbox and explicit SMTP test supported; actual localhost SMTP capture tested; no external inbox-delivery claim |
| CPCB, IMD, real hardware, clinical use | Not integrated/validated; planned only |

Start from the ZIP using [section 12](#12-run-locally). **Do not run reset, training or data-generation commands to install the enhancement.** The ZIP includes the copied original synthetic SQLite snapshot with 3000 saved states. First boot applies only additive schema migrations; registration and monitoring persist across restarts. Active simulations intentionally do not auto-resume.

- [Audit and implementation plan](docs/enhanced/AUDIT_AND_PLAN.md)
- [Feature status and boundaries](docs/enhanced/FEATURE_STATUS.md)
- [Patients, migrations and safe backup](docs/enhanced/PATIENTS_AND_MIGRATIONS.md)
- [Simulated device guide](docs/enhanced/DEVICE_INTEGRATION.md)
- [Environment guide](docs/enhanced/ENVIRONMENT.md) and [actual provider investigation](docs/enhanced/PROVIDER_INVESTIGATION.md)
- [Notifications and email guide](docs/enhanced/NOTIFICATIONS.md)
- [Enhancement API reference](docs/enhanced/API_ENHANCED.md)
- [Executed verification and handover](docs/enhanced/VERIFICATION.md)

---

**Happiest Health Digital Twin Challenge 2026 | Prototype & Code Submission**

> **PranaGuard explores how a patient-specific digital twin could combine physiological trends, symptoms, patient history and ambient environmental context to estimate COPD exacerbation risk at 24-, 48- and 72-hour horizons—with inspectable explanations and what-if scenarios.**

**Live demo:** https://pranaguard-copd-dashboard.vercel.app  
**Backend health:** https://pranaguard-copd-api.onrender.com/api/health  
**Public source code:** https://github.com/anuja-naik/PranaGuard-COPD-Digital-Twin

> **Important:** This is a research prototype using synthetic patient records. It is not a medical device, is not clinically validated, and must not be used for diagnosis, triage, prescribing, treatment, or emergency decisions. The 72-hour LightGBM result is below chance; the model results do not establish clinical usefulness or patient benefit.

---

## 1. Team and institution

- **Project:** PranaGuard — Patient-Specific COPD Digital Twin
- **Challenge:** Happiest Health Digital Twin Challenge 2026
- **Team lead / repository owner:** Anuja Naik
- **Institution:** Pune Institute of Computer Technology (PICT), Pune
- **Team member:** Harsh Takalkar — Frontend, backend and documentation.
- **Clinical advisor:** None claimed.

## 2. Problem statement

Chronic obstructive pulmonary disease (COPD) exacerbations can lead to worsening symptoms, emergency visits and hospitalisation. A useful early-warning workflow would need to consider a patient's own baseline and changing measurements alongside symptoms, history and environmental context—not simply display an isolated reading.

PranaGuard is an engineering research prototype that demonstrates this workflow on a synthetic cohort. It is designed to make the state of each digital twin, the estimated risk, contributing model features, data provenance and scenario assumptions inspectable. It does **not** prove that its predictions can reliably forecast real COPD exacerbations.

## 3. Proposed healthcare use case

A clinician-facing research dashboard can be used to:

1. Review a synthetic COPD cohort and identify patient twins with elevated model-estimated risk.
2. Open an individual twin and inspect baseline and current measurements.
3. Compare estimated 24-, 48- and 72-hour risk horizons.
4. Review model drivers and their changes between persisted twin states.
5. Inspect alerts and record review actions in the demonstration workflow.
6. Explore conditional scenarios for ambient PM2.5, adherence and activity assumptions without modifying the original twin.
7. Review data freshness, missing fields, validation metrics and limitations.

The demo uses four illustrative Indian locations: Pune, Mumbai, Delhi and Bengaluru. It does not ingest real patients, connect to a hospital/EHR or medical device, or provide clinical advice.

## 4. Live prototype

- **Dashboard:** https://pranaguard-copd-dashboard.vercel.app
- **Backend health check:** https://pranaguard-copd-api.onrender.com/api/health
- **API route reference:** [docs/API.md](docs/API.md)
- **Architecture:** [PDF](docs/architecture/PranaGuard_Architecture.pdf) · [Editable PPTX](docs/architecture/PranaGuard_Architecture.pptx) · [SVG](docs/architecture/PranaGuard_Architecture.svg)
- **Project presentation:** [16-slide PPTX](docs/presentation/PranaGuard_Digital_Twin_Challenge_2026.pptx) · [PDF](docs/presentation/PranaGuard_Digital_Twin_Challenge_2026.pdf)
- **Technical report:** [Markdown](docs/TECHNICAL_REPORT.md) · [PDF](docs/PranaGuard_Technical_Report.pdf)

The hosted API health response reports that the service is running and that its data are synthetic. Free hosting may take time to wake after inactivity. The application is a demonstration environment, not a production clinical service.

## 5. Key features implemented

- **Persistent patient twins:** 120 synthetic profiles with 60 days of hourly longitudinal data.
- **Cohort overview:** risk categories, patient search and cohort-level summaries.
- **Multi-horizon prediction:** separate models for 24-, 48- and 72-hour horizons.
- **Explainability:** native LightGBM TreeSHAP for the tree model, with limitations of calibration and interpretation documented.
- **State history:** versioned hourly twin states stored in SQLite.
- **What-if studio:** conditional scenario branches for PM2.5, adherence and activity assumptions.
- **Alerts and review actions:** persisted demonstration alerts, acknowledgement/resolution and action logs.
- **Data provenance:** source manifest, freshness and missingness reporting.
- **Reproducible artifacts:** model evaluation outputs, split manifest, synthetic-data generator, tests, architecture diagrams and presentation files.

This is a **stateful, data-driven research twin**. It is not a validated mechanistic lung model, treatment controller or causal simulator.

## 6. Technical stack

| Component | Technology |
|---|---|
| Frontend | React, TypeScript, Vite, Tailwind CSS, Recharts, Lucide React |
| Backend/API | Python, FastAPI, Uvicorn, Pydantic |
| Data and ML | pandas, NumPy, scikit-learn, LightGBM, joblib |
| Explainability | Native LightGBM TreeSHAP; reference-perturbation fallback documented for non-tree models |
| Persistence | SQLite with WAL, foreign keys and transactional writes |
| Communication | REST API and WebSockets |
| Tests | pytest, Vitest, React Testing Library, Playwright Chromium |
| Deliverables | Editable PowerPoint, PDF exports, SVG architecture diagram and technical documentation |

## 7. Data sources and synthetic-data disclosure

The cohort contains **120 synthetic patients, 60 days, 172,800 hourly rows and 263 generated event onsets**. Patient profiles, physiological/wearable-style measurements, symptoms, adherence and outcomes are synthetic and do not represent real people. The data generator uses seed 2026; it is not a validated physiological COPD simulator.

Ambient PM2.5, PM10, NO2, ozone, temperature and humidity are drawn from eight cached city-level public API responses covering 1 August–29 September 2026 UTC. They are historical/modelled environmental products, not personal exposure measurements or live conditions. No future environmental observations are supplied to a forecast or scenario branch.

- [Data provenance](docs/DATA_PROVENANCE.md)
- [Environmental cache manifest](data/environment/manifest.json)
- [Synthetic-data generation manifest](data/generation_manifest.json)
- [Third-party licenses](docs/THIRD_PARTY_LICENSES.md)

Environmental data attribution: Open-Meteo/CAMS and historical weather products. See the provenance manifest and license notes for exact sources and terms. Provider attribution does not imply endorsement.

## 8. AI/ML methodology

Logistic Regression is the baseline and LightGBM is the primary deployed tree model. Separate binary classifiers estimate each horizon, with a separate Platt logistic calibrator per horizon.

For an eligible synthetic patient-hour *t*, the horizon label is 1 when a new generated event onset occurs in the following 24, 48 or 72 hours. These are generated labels, not clinician-adjudicated COPD exacerbations.

### Leakage controls

- Patient-disjoint and calendar-time-disjoint train, calibration and test partitions: 72 / 24 / 24 patients.
- A minimum 72-hour purge between partitions to prevent future label intervals crossing partition boundaries.
- Patient baselines use only the initial 72-hour warm-up period.
- Trailing windows and past differences are causal; no centered windows, backward filling or future outcomes are used as features.
- Imputation/scaling are fitted on training data only; calibration uses a disjoint calibration partition.
- Hyperparameters and the demonstration alert cutoff were fixed rather than tuned against the test set.

Details: [methodology](docs/METHODOLOGY.md), [split manifest](artifacts/split_manifest.json), [evaluation report](artifacts/evaluation.md).

## 9. Actual model results and limitations

The following metrics are from the executed held-out experiment. They are included as-is, including the negative findings.

| Model | Horizon | AUROC | AUPRC | Brier score |
|---|---:|---:|---:|---:|
| LightGBM | 24h | 0.6916 | 0.0882 | 0.0279 |
| LightGBM | 48h | 0.6144 | 0.0968 | 0.0557 |
| LightGBM | 72h | 0.3951 | 0.0593 | 0.0853 |
| Logistic Regression | 24h | 0.6619 | 0.1993 | 0.0260 |
| Logistic Regression | 48h | 0.6285 | 0.1841 | 0.0537 |
| Logistic Regression | 72h | 0.6253 | 0.2281 | 0.0800 |

**Interpretation and negative findings**

- LightGBM's 72-hour AUROC is **0.3951**, below chance; its AUPRC is **0.0593**, below the 0.0773 prevalence baseline.
- Logistic Regression performs better than LightGBM at 72 hours (AUROC 0.6253, AUPRC 0.2281).
- At the fixed 0.35 demonstration threshold, all three primary LightGBM horizon models have zero sensitivity on this test set.
- The 72-hour alert audit detected **0 of 5** held-out synthetic onsets. A median lead time cannot be established.
- The negative 72-hour calibration slope can reverse the direction implied by raw tree scores. TreeSHAP values explain raw model scores, not the calibrated probability directly.
- The small number of held-out onsets, correlated hourly windows and shared city-level environmental variables make estimates unstable.

These results measure learnability on a generated dataset and demonstrate the software workflow. They do **not** establish clinical validity, useful prospective warning, reduced hospitalisation, treatment efficacy or patient benefit.

Supporting files: [15-experiment evaluation](artifacts/evaluation.md), [machine-readable evaluation](artifacts/evaluation.json), [metrics CSV](artifacts/metrics.csv), [saved test predictions](artifacts/test_predictions.csv.gz), [metric verification](artifacts/evaluation_verification.json), [limitations](docs/LIMITATIONS.md).

## 10. Explainability and what-if scenarios

TreeSHAP contributions are calculated for the raw LightGBM tree score; they do not sum to the final calibrated probability. Explanations are associations, not causal effects.

The scenario studio supports conditional assumptions for PM2.5, adherence and activity. It recalculates features over projected hours while preserving the original twin and stores the scenario separately. The paths are **sensitivity analyses, not validated disease trajectories or treatment-effect estimates**. A lower model score must not be interpreted as evidence that an intervention improves health.

## 11. Architecture and repository contents

```text
backend/app/                 FastAPI, features, inference, validation, twin engine and SQLite
backend/tests/               Backend and scientific-integrity tests
frontend/src/                React dashboard, API client, charts and UI tests
scripts/                     Data generation, training, evaluation, replay and verification
artifacts/                   Fitted models, metrics, predictions and split metadata
data/environment/            Cached public environmental data and provenance
data/                         Synthetic longitudinal dataset and patient profiles
docs/architecture/           PDF, PPTX and SVG architecture diagrams
docs/presentation/           Editable presentation and PDF export
docs/screenshots/             Screenshots from the running application
docs/demo/                    Demo recording guide and checklist
docs/verification/            Test outputs, reproducibility and artifact audits
submission_metadata.json     Submission metadata
```

## 12. Run locally

Tested with Python 3.13, Node.js 20 and npm. The ZIP includes a preserved synthetic SQLite snapshot; the application can also initialize a new database without training. No database server is required.

```bash
# Extract the delivered PranaGuard-Enhanced.zip first. The remote fork does not contain these local enhancements.
cd PranaGuard-Enhanced

python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
npm --prefix frontend ci
python -m scripts.bootstrap
```

Start the backend from the repository root:

```bash
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

In a second terminal, from the repository root:

```bash
npm --prefix frontend run dev
```

Open http://127.0.0.1:5173. Vite proxies API requests and WebSockets to the local FastAPI server. Use a single Uvicorn worker; distributed replay coordination is not implemented.

**Historical research reproduction only (not enhancement setup):** the commands below rewrite protected data/model/evaluation files. Run them only in a separate disposable copy, never in this preserved enhanced working directory. No retraining/regeneration was performed for this enhancement. To reproduce the original pipeline using the bundled cache:

```bash
python -m scripts.generate_data --seed 2026 --patients 120 --days 60
python -m scripts.train
python -m scripts.select_demo
python -m scripts.evaluate
python -m scripts.bootstrap --reset
```

**Caution:** an explicit replay reset recreates active original-cohort twin versions. Source alerts/actions/scenarios are archived before deletion; new registrations, monitoring records and their reviews are preserved. Normal setup does not reset anything. Do not regenerate data/models while the server is running.

## 13. Tests and verification

The original project's historical verification reported (the original reports are retained unchanged):

- 41 backend tests passed
- 14 frontend tests passed
- 18 Chromium integration checks passed
- Production frontend build passed

Reports: [backend tests](docs/verification/backend-tests.txt), [frontend tests](docs/verification/frontend-tests.txt), [browser verification](docs/verification/browser-verification.json), [clean setup](docs/verification/clean-setup.json).

These are historical project test results, not independent clinical validation. Enhanced-edition executed results and exact commands are in [docs/enhanced/VERIFICATION.md](docs/enhanced/VERIFICATION.md). Re-run tests in a throwaway verification database rather than resetting your working dataset.

## 14. Demo video

**Recorded demo:** [Watch PranaGuard — Digital Twin Challenge 2026](https://youtu.be/G_IQ4HrpZsA)

Please verify before final submission that the video is set to **Unlisted**, plays when opened in a signed-out/incognito browser, and meets the challenge's required **15–20 minute** duration. The link is included here as provided; YouTube visibility and duration have not been independently confirmed.

- [20-minute demo script](docs/demo/DEMO_SCRIPT.md)
- [Recording guide](docs/demo/RECORDING_GUIDE.md)
- [Upload checklist](docs/demo/UPLOAD_CHECKLIST.md)
- [Video status notes](docs/demo/VIDEO_STATUS.md)

## 15. Open-source license

Project code, original documents and model bundle are released under the [MIT License](LICENSE). Synthetic patient fields are CC0 1.0. Cached environmental data retain their applicable CC BY 4.0 attribution. Third-party dependency and asset details are listed in [THIRD_PARTY_LICENSES.md](docs/THIRD_PARTY_LICENSES.md).

## 16. Privacy, safety and future work

**Research demonstration only. Not a medical device. No clinical validation. Not for clinical decision-making.**

All displayed patient records are synthetic. The public demo is not suitable for real patient data. Read-only data and the WebSocket are publicly accessible; the optional shared admin token protects writes only and is not production-grade identity or role-based access control. The system does not provide a clinical consent workflow, certified device ingestion, regulated audit retention or a guarantee of encryption at rest.

Before any real-world study, the project would require ethics review, informed consent, clinician-adjudicated outcomes, appropriately governed longitudinal data, prospective multi-site evaluation, subgroup and calibration assessment, secure identity/access management, clinical oversight and a validated safety process.

### Roadmap

1. Evaluate stability on new, pre-registered synthetic cohorts without tuning against the current test set.
2. Establish ethically approved access to longitudinal COPD data and clinician-adjudicated outcomes.
3. Conduct prospective, multi-site validation and assess calibration, uncertainty, fairness, missingness and useful lead time.
4. Add properly authenticated device/EHR ingestion and personal exposure estimates only under suitable governance.
5. Develop and validate any causal/mechanistic response model before making claims about intervention effects.

---
