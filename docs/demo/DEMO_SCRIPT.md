# PranaGuard — timed 20-minute recording script

**Status: script only. No demo video has been recorded or uploaded.** Target duration: 20:00. Rehearse at approximately 140–150 spoken words/minute (about145 is a useful rehearsal target) and perform the indicated clicks while narrating where practical. The script has about2,582 spoken words (about17.8 minutes at145wpm), leaving about2.2 minutes for pauses/actions across the20-minute schedule. Do not speed through the clicks and submit a short video. If finishing a section early, inspect the highlighted real values until the next cue. Confirm the current challenge duration wording; keep the final recording within its accepted range.

All patient records are synthetic. Never claim clinical validation, prospective detection success or a proven effect of an intervention. Read changing scenario values from the actual screen; do not substitute a rehearsed number.

## Before recording
- Complete team/college placeholders in metadata, README and slides. Restart servers after rebuilding models.
- Activate the Python environment; run `python -m scripts.bootstrap --reset`; start FastAPI and Vite using README commands.
- Open the app at `http://127.0.0.1:5173/#overview`, PowerPoint/PDF, a terminal in the repository and `artifacts/demo_case.json`.
- Disable personal notifications, close secrets, set a legible browser zoom and record at 1920×1080 if possible. Use an incognito browser or a clean recording profile.
- Keep a visible timer. The final video should contain the live application, not only slides.

## 00:00–01:20 · Title, identity and safety boundary
**Screen:** presentation slide1, then slide2. Put the actual team and institution on screen only after the owner has supplied them.

**Narration:**
“Welcome to PranaGuard, a body and environment digital twin prototype for COPD exacerbation forecasting. This project was built for the Happiest Health Digital Twin Challenge 2026. Our team and institutional details are shown here once they have been confirmed by the project owner.

The clinical motivation is straightforward. A patient’s respiratory condition changes over time, while environmental context and adherence information also change. A single oxygen reading or a static medical profile does not capture that whole picture. A clinician would need a traceable way to connect those signals and ask what has changed for this particular patient.

Before showing the system, I want to draw a firm safety boundary. Every patient in this demonstration is synthetic. The environmental context is a cached public atmospheric model product. This is not a medical device, it is not clinically validated, and it must not be used to diagnose, triage or recommend treatment. We will show actual model results, including weak performance and a false-positive alert. A functioning digital twin workflow is not the same thing as proven clinical effectiveness.”

**Action/hold:** Point to “synthetic proof of concept” and the project title; hold the safety statement long enough to read. Advance at01:20.

## 01:20–02:50 · Problem, Indian use case and target outputs
**Screen:** slides2–4: problem, horizons, solution.

**Narration:**
“The intended use case is a clinician reviewing a synthetic outpatient COPD cohort. The clinician can inspect a patient’s clinical history, recent physiology, symptoms, activity, sleep and ambient context, then review three separate model-estimated risks. The demonstration locations are Pune, Mumbai, Delhi and Bengaluru. These are locations for public environmental examples, not claims of hospital partnerships or clinical deployment.

The targets are new synthetic onsets in the next twenty-four, forty-eight and seventy-two hours. They are not three copies of one score. Each horizon has its own fitted classifier and calibrator. The labels are stochastic events created by the generator, not real, clinician-adjudicated COPD exacerbations.

The question we are exploring is whether this engineering architecture can maintain a personalized state, update it consistently, expose understandable predictions and preserve a review trail. A future clinically useful system would also have to establish accurate probabilities, useful lead time, manageable alert burden and safe workflows on real, ethically governed data. We have not established those things here. In fact, the seventy-two-hour primary model performs poorly on the held-out synthetic split, and we will inspect that openly.”

**Action/hold:** Highlight the three horizon labels. Do not describe the target horizons as validated warning lead times. Pause at each horizon before proceeding.

## 02:50–04:10 · Actual architecture
**Screen:** slide6 or separate `docs/architecture/PranaGuard_Architecture.pdf`.

**Narration:**
“This diagram reflects the implemented system. The data sources are a reproducible synthetic patient cohort and cached public ambient data. Ingestion and deterministic replay feed validation and causal feature engineering. The twin-state engine maintains the patient-specific baseline, observed current state and immutable version.

The three fitted horizon models and their calibrators produce the actual estimates. Explanations are computed from saved features, alerts are persisted, and what-if simulation creates a separate branch rather than overwriting the patient. SQLite is cross-cutting: it stores versions, replay metadata, alerts, action logs and scenarios. The API layer is FastAPI, with REST endpoints and a WebSocket that tells the React client to refresh actual data.

The diagram’s dashed links matter. Predictions are persisted directly on each update; explanations are calculated on demand. A scenario reads the observed past from the twin, recomputes features and uses the same model bundle. It never receives future realized observations. The frontend uses React and TypeScript with Vite, Tailwind, Recharts and Lucide. It is not a static mockup, and errors are not replaced with invented results.”

**Action/hold:** Trace source → replay → features → state → inference → persistence → API → React. Point to the separate scenario branch and the on-demand explanation label.

## 04:10–05:40 · Data provenance and offline mode
**Screen:** app System & data; show the source table and the cache manifest in the editor.

**Narration:**
“The delivered cohort has one hundred and twenty synthetic patients, sixty days and one hundred and seventy-two thousand, eight hundred hourly rows. There are two hundred and sixty-three stochastic artificial onsets across the full dataset. All clinical and physiological values are synthetic, including missing wearable-style measurements after baseline calibration.

The environmental fields are different. We successfully retrieved eight public API responses, covering air and weather for four cities, with one thousand four hundred and forty hourly timestamps in each response. PM two point five, PM ten, nitrogen dioxide and ozone come from Open-Meteo’s CAMS global model product; temperature and humidity come from its Historical Weather API. The manifest contains the actual URLs, retrieval times and checksums. These are coarse gridded ambient values, not personal exposure or indoor air measurements.

The dates are August first through September twenty-ninth, twenty twenty-six, in UTC. The screen must not be described as current live air quality. The data are attributed under Creative Commons Attribution four point zero, with hosted API access conditions documented separately.

Normal replay and inference make no external data-provider requests. The cache supports an offline demonstration after dependencies are installed. A missing cache causes a clear error unless an explicitly labelled synthetic environmental fallback is chosen.”

**Action/hold:** Show a source URL, retrieval timestamp, date coverage and license. Explain that cache age is assessed against the replay clock, not misrepresented as fresh wall-clock data.

## 05:40–07:20 · Cohort overview and persistent patient twin
**Screen:** Cohort overview → search `PG-0071` → open row → Patient twins.

**Narration:**
“This is the actual clinician dashboard. The cohort count, risk categories, open-alert count and trend chart come from backend responses. The trend is the mean of model estimates in persisted twin versions. The thresholds are prototype conventions, not clinical urgency rules. Search, category filters, pagination and patient selection all operate on the real synthetic cohort response.

I am opening synthetic twin seventy-one, identifier P G zero zero seven one. The banner displays a synthetic label, clinical context, the model category and the saved state version. The three horizon cards show independent calibrated model estimates. None of these numbers is a hardcoded demonstration score.

Below, the baseline is the median of that patient’s first seventy-two observed hours. It is fixed before fitted or evaluated rows. Current oxygen saturation, heart rate, respiratory rate, symptoms and hourly activity are compared with that baseline. A missing current measurement is shown as missing, not replaced visually by a reassuring invented value; the model uses a training-set median and the warning makes that clear.

The history chart displays actual synthetic observations. Historical risk values are present only for versions predicted and persisted during replay. Earlier values that were not predicted remain null. Finally, the version ledger lets me load a saved historical state. This patient-specific state, continued updating, prediction and isolated branching are why we call it a stateful data-driven research twin.”

**Action/hold:** Change the physiology selector, inspect the baseline line, select v1 then Current state, and use Export twin to download the actual JSON. Show the filename and synthetic flag, not any personal files.

## 07:20–08:50 · Deterministic replay and real risk updates
**Screen:** Patient twins; replay toolbar.

**Narration:**
“Replay is controlled by the backend, not an animation of fake numbers. Pressing Play advances one historical hour every two seconds and creates a new version for every patient. The WebSocket invalidates the view, and the frontend reloads the saved state. If the socket is unavailable, a REST refresh provides a fallback.

I will let a small number of updates occur, then pause. We can see the cursor and version change. To make the recorded scenario reproducible, I will reset now. This is a deliberately destructive demonstration operation: the confirmation explains that it clears alerts, actions and scenarios, then recreates twenty-four hours of persisted history. It is not a production medical-record deletion workflow.

The documented starting cursor is hour one thousand and thirty-nine. Now I advance twelve hours in one backend transaction. At hour one thousand and fifty-one, this patient’s actual calibrated seventy-two-hour score is approximately thirty-five point five one percent. That crosses the predeclared thirty-five-percent alert convention.

This example was selected retrospectively because of its high model score across the synthetic cohort. Its synthetic seventy-two-hour label is zero: it is a false positive, not a successful early warning. We use it to demonstrate the workflow honestly, not to claim detection performance.”

**Action/hold:** Play; observe at least two increments; Pause; Reset and accept confirmation; verify1039; click +12h; verify1051 and v37. Briefly show `artifacts/demo_case.json`, including `selected_label_72: 0` and the selection disclaimer.

## 08:50–10:30 · Explainability and calibration caveat
**Screen:** Risk explainability; switch24h/72h; inspect drivers, deviations and audit.

**Narration:**
“This is the deployed model’s explanation, not a manually authored list of risk factors. LightGBM’s native TreeSHAP computes a contribution for every model feature. The top drivers are ranked by absolute contribution. Patient-relative deviations show changes from the fixed personal baseline, and the contribution-change section compares the current saved version with its predecessor.

The units are important. These bars explain the raw, uncalibrated tree log-odds. The base value plus contributions equals the raw margin; an automated numerical test checks that identity. They do not sum to the displayed calibrated probability, and they do not establish clinical causes.

There is an especially serious limitation in this experiment: the fitted seventy-two-hour Platt calibrator has a negative slope. That means it reverses raw tree-score direction. A positive raw-score contribution can therefore correspond to a lower final calibrated risk. The interface calls this out instead of implying that the bar colors give a simple clinical risk story.

We have not silently changed calibration after seeing the test set. This unstable result is retained in the report and model card. It shows why transparent explanations are necessary but not sufficient: a nicely rendered explanation cannot rescue a weak or unstable model. Future development needs new, pre-registered data and proper stability assessment before making any patient-level interpretation.”

**Action/hold:** Switch horizons; inspect one driver’s actual value and raw contribution. Scroll to the additive audit. Read the calibration warning on screen.

## 10:30–12:15 · Alerts, acknowledgement and clinician actions
**Screen:** Care activity; use the alert created at1051.

**Narration:**
“The alert created by the actual model is now stored in SQLite. It references the synthetic patient, the state version, the seventy-two-hour horizon, the score and the replay timestamp. The engine prevents repeated open alerts for the same patient while an unresolved alert already exists.

I can acknowledge the alert and then document a review action. This note is deliberately about a synthetic false positive and does not contain treatment advice. The action category and free-text note are saved with the reviewed twin version and a wall-clock logging timestamp. Acknowledgement and resolution are persisted status transitions, not temporary local checkboxes.

Now I resolve the alert and reload the browser. The resolution and review history remain visible. Resolving an alert does not mean that the patient recovered, and logging an adherence or exposure review does not change physiology or automatically reduce risk. These records are documentation, not a claimed intervention model.

The default workspace is a local synthetic demonstration with authentication disabled. An optional shared admin token can protect write endpoints, but that is not a production clinical identity or permissions system. No real patient information should be entered here. A real deployment would need proper authentication, role-based access, consent, retention policy, secure storage and clinical governance.”

**Action/hold:** Acknowledge → choose Clinical review → enter “Synthetic demonstration: reviewed model false positive. No treatment recommendation.” → Save action → Resolve → reload. Show the persisted record and version.

## 12:15–14:05 · What-if studio, conditional branches and preservation
**Screen:** What-if studio; use current patient; change assumptions and Run backend simulation.

**Narration:**
“The what-if studio is explicitly a conditional sensitivity experiment, not a treatment simulator. We support an ambient PM two point five assumption, an adherence feature assumption and an hourly activity multiplier. The backend validates their ranges. It copies the observed history only up to the current twin state and creates baseline and scenario branches.

Physiology is held constant. PM two point five moves toward the requested assumption over a six-hour transition, PM ten scales proportionally, adherence is set to the selected value, and activity changes steps. The causal trailing-window and personalization features are recalculated. The same actual fitted horizon models produce the projected-time estimates.

I will run this now and read the values from the returned chart rather than promise that an assumption will lower risk. With this weak, non-causal model, reducing ambient pollution can even increase the estimated score. That counterintuitive output must not be described as a biological effect. It illustrates the limitations of model sensitivity and the negative calibration behavior, not evidence against exposure reduction or in favor of any therapy.

At a projected time, a seventy-two-hour estimate refers to the model evaluated at that projected state. It is not cumulative benefit over the original seventy-two hours. The result is stored separately with its assumptions and source version. The preservation indicator is backed by a test and a state comparison: the original patient twin has not been overwritten.”

**Action/hold:** Set a visibly different PM assumption; adjust adherence/activity; run the API calculation; read current baseline/scenario values; switch horizons; reopen the saved scenario. Return to the twin to confirm its source version remains unchanged.

## 14:05–16:20 · Actual evaluation, leakage prevention and negative results
**Screen:** Model validation72h →24h; show ablation table and split protocol.

**Narration:**
“Now we come to the evidence. The split is both patient-disjoint and calendar-time-disjoint: seventy-two training patients, twenty-four calibration patients and twenty-four further test patients at later dates. At least seventy-two hours separate the partitions, keeping future label windows apart. Patient identity, event flags, time indices and future observations are not model features. Personal baselines use only the first seventy-two hours. Imputation and Logistic Regression scaling fit on training only, and Platt calibration fits on calibration only.

The executed training set contains fourteen thousand six hundred and five sampled rows, the calibration set one thousand three hundred and seventy-seven, and the held-out test four thousand six hundred and ninety-nine hourly windows. These are correlated windows, not independent clinical participants. The report includes patient-cluster bootstrap intervals, but there are only five event onsets inside the test window.

For the primary personalized LightGBM model, AUROC is approximately zero point six nine one six at twenty-four hours, zero point six one four four at forty-eight hours, and zero point three nine five one at seventy-two hours. The last result is below chance. Seventy-two-hour AUPRC is zero point zero five nine three, below the zero point zero seven seven three prevalence baseline.

Logistic Regression is better at seventy-two hours, with AUROC zero point six two five three and AUPRC zero point two two eight one. The ablations do not establish a consistent benefit from environment or personalization. At the fixed thirty-five-percent cutoff, the primary models have zero sensitivity in this test set. The seventy-two-hour audit detects zero of five test-window onsets, so there is no meaningful median detected lead time to claim.

The ROC, precision-recall, calibration and confusion matrix views all come from executed predictions. We report these negative findings because synthetic proof-of-concept engineering is not clinical validation, and the interface should never obscure that distinction.”

**Action/hold:** Point to each horizon’s metric; show prevalence, confusion matrix and ablations. Pause on zero true positives and the72h warning rather than quickly skipping them.

## 16:20–18:20 · Technical walkthrough and actual verification
**Screen:** terminal/editor; briefly return to System & data.

**Narration:**
“The backend separates ingestion validation, causal features, fitted-model operations, the twin engine, persistence and API schemas. The same feature code is shared by training, replay and scenario inference. SQLite uses foreign keys and atomic replay transactions. A failed transaction rolls back rather than leaving a cursor ahead of its saved patient states. A checksum ties the dataset to the model bundle.

The reproducible generation and training commands are in the README. Training executes Logistic Regression and four LightGBM input-group experiments at three horizons, fifteen experiments in total. Evaluation can independently recompute the main metrics from the saved test prediction file. The reproducibility check runs generation and training again and compares actual dataset bytes, predictions and metrics.

Our final verification reports contain forty-one passing backend tests, fourteen passing frontend tests and eighteen passing actual Chromium integration checks. The browser tests use the running servers, exercise the primary controls and verify an actual model-generated alert, scenario state isolation, action persistence, export and mobile layout. External browser data-provider requests were blocked, and none were attempted during the offline runtime workflow.

These checks establish software behavior, not clinical safety or efficacy. There is one upstream backend deprecation warning, and the frontend chart bundle remains an optimization opportunity. The system status view shows the real model version, cache provenance, missingness handling and database counts. The API documentation is available locally through FastAPI’s interactive documentation route.”

**Action/hold:** Run `python -m pytest`; show the actual result. Open the saved frontend/browser/reproducibility reports; show source modules and API docs. Do not imply that test counts validate medical predictions.

## 18:20–20:00 · Limitations, roadmap and submission honesty
**Screen:** slides15–16; README checklist/video section.

**Narration:**
“To close, PranaGuard delivers a functional digital twin software workflow: persistent personalized state, hourly updates, three real model outputs, transparent explanations, an auditable alert and review process, isolated conditional scenarios, reproducible experiments and a working React clinician interface.

The limitations are substantial and intentional to disclose. All patient data and labels are synthetic. The generator is not clinically calibrated. Environmental context is coarse and shared by city, not personal exposure. The held-out event count is small, the seventy-two-hour model and calibration are unstable, and the fixed alert threshold misses every held-out onset in this run. Scenario output is not a causal or validated treatment effect. There is no evidence here of reduced hospitalization, clinical lead time or patient benefit.

The next steps are new pre-registered development cohorts, clinically adjudicated outcomes collected under ethical approval, patient/time/site-external prospective validation, calibration and subgroup analysis, trustworthy as-issued environmental feeds, and production-grade identity, privacy and clinical governance. A defensible causal or mechanistic model would be needed before discussing intervention effects.

Finally, submission status must remain honest. The repository must actually be published as public; the owner must supply team and institution details; this recording must actually be uploaded to YouTube as Unlisted; and every final link must be checked signed out. A script or a locally generated presentation does not satisfy the video requirement. Thank you for reviewing both what this prototype implements and what its results do not yet establish.”

**Action/hold:** Show the current checklist and unresolved items. End at20:00 after the safety statement is readable. Verify the actual recording duration and audio before uploading.

## Post-recording evidence to capture
Record final duration, YouTube Unlisted URL, signed-out playback test, actual public repository URL and the commit containing the final README. Update metadata and all placeholders, regenerate the checklist, and only then assess submission readiness.
