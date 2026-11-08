# Download & Repro Instructions — External Research Datasets (v7)

The platform ZIP is a complete runnable project. It does **not** redistribute the two external raw datasets (they are CC-BY-4.0; re-hosting copies is unnecessary), and it never ships v6 restricted/generated raw twin data beyond what v6 already documents.

## 1. Cough-COPD(CC) — Zenodo 14881818 (CC-BY-4.0)

- Record page: <https://zenodo.org/records/14881818> (v2, 2025-02-17; creators: USTC & Hangzhou slan-health).
- Direct file download (RAR, md5 `63094082465da311b478951fdf882853`):
  `https://zenodo.org/records/14881818/api/records/14881818/files/Cough-COPD(CC).rar/content`
  (or via the API: `https://zenodo.org/api/records/14881818` → `files[0].links.self`).
- Extraction: RarLab **unrar** 7.12 (static Linux binary: `https://www.rarlab.com/rar/rarlinux-x64-712.tar.gz`). The binary is a build tool only — it is not part of the shipped ZIP.
- The shipped artifact (`backend/app/research/artifacts/cough_model.joblib` + `cough_model_eval.json` + `cough_dataset_index.json`) was produced from an 853-file publisher split. Raw audio is not in the repo.

## 2. TOLIFE Clinical Study A v2.0 — Zenodo 23263785 (CC-BY-4.0)

- Record page: <https://zenodo.org/records/23263785>; DOI `10.5281/zenodo.23263785`.
- API file URLs: `https://zenodo.org/api/records/23263785/files/index.zip/content` and `…/files/README.md/content`.
- Semantics used by the corrected experiment are recorded in `data/raw/tolife/TOLIFE_README_v2.0.md` (shipped). The derived research views (`event_register_audit.json`, `tolife_horizon_results.json`, `tolife_research_series.json`, `tolife_participants_research.json`) are shipped under `backend/app/research/artifacts/`; raw participant-level parquet/wearable payloads are **not** redistributed.

## 3. Rebuild the research artifacts locally (optional)

With the two datasets downloaded into `research_v1/pranaguard-unified-copd-dataset/` (or set `RESEARCH_ROOT` to your processed tree):

```bash
cd backend
pip install -r requirements.txt          # scikit-learn==1.9.1 numpy==2.5.4 pandas==3.0.6 are pinned
python scripts/research_tolife_horizons.py     # RESEARCH_ROOT/RESEARCH_OUT env vars override defaults
python scripts/research_train_cough_artifact.py
```

Regeneration is byte-deterministic against the shipped artifacts (cough model joblib 4,570,809 bytes; AUROC 0.9316 / sensitivity 0.578; TOLIFE audit 80/42/30; horizons 0.355/0.389/0.393 under the pinned runtime).

## 4. Run the platform

```bash
pip install -r requirements.txt
uvicorn backend.app.main:create_app --factory --host 0.0.0.0 --port 8000
# new shell
cd frontend && npm install && npm run dev   # or npm run build && npm run preview
```

Sign in with any v6 demo login (documented in `docs/DOCTOR_PATIENT_DELIVERY.md`). Open **Research models** in the navigation for the three model cards.
