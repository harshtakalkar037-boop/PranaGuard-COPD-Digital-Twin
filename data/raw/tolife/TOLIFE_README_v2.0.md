# TOLIFE Clinical Study A — v2.0 dataset note (provenance record)

**No raw TOLIFE data ships in this repository.** This file documents where the derived research
artifacts in `backend/app/research/artifacts/` came from, plus the semantics the corrected v7
experiment relies on. See `docs/research-models/DOWNLOAD_INSTRUCTIONS.md` to obtain the dataset.

- Record: <https://zenodo.org/records/23263785> (version v2.0) — CC-BY-4.0
- DOI: `10.5281/zenodo.23263785`
- API file URLs: `https://zenodo.org/api/records/23263785/files/index.zip/content`, `…/files/README.md/content`

## Semantics used by the v7 research module

- **Participants**: 86 coded kit identities (e.g. `GER-001`), rendered in-app only as `tolife:<kit>`;
  never joined to platform `PG-` patient identities.
- **Observed channels** (kept): daily SpO₂, sleep heart-rate mean, PPG RMSSD (ms), walked distance (m),
  sleep efficiency (%), session FEV₁ (L), environment aggregates when available.
- **Model-estimated symptom channels (EXCLUDED from predictors and from the research view)**: the
  study-provided model-estimated CAT/CCQ/mMRC classes — they are model outputs, not measurements, and
  including them caused same-day label leakage in the superseded v1 probe.
- **Exacerbation register**: 80 entries / 42 unique participants / 0 missing dates. After the v7 audit:
  42 events inside the observed monitoring frame; 32 with any valid measured day in the prior 7 days;
  30 evaluable (in-frame AND prior-7d valid). Day 0 = register onset date; negative relative days precede onset.
- **Derived deliverables shipped here (REAL_DERIVED)**: `event_register_audit.json`,
  `tolife_horizon_results.json`, `tolife_research_series.json`, `tolife_participants_research.json`.

Citation (as requested by the licence notice): TOLIFE consortium, *Clinical Study A dataset*, Zenodo v2.0.
