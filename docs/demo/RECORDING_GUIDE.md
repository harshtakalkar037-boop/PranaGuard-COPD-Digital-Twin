# Recording and reproducible scenario guide

## Required deliverable still pending
An actual 15–20 minute demo uploaded to YouTube as **Unlisted**, with its actual URL in the README. This directory contains preparation materials only; no recording/upload has been completed. Confirm the latest official duration wording before recording; target20 minutes here.

## Before recording
1. Fill actual team/institution fields in `submission_metadata.json`; regenerate documentation and update slide1.
2. Install dependencies, initialize the bundled demo, start one FastAPI worker and the Vite frontend using the root README.
3. Use OBS Studio or the operating system screen recorder. These are human recording options, not application dependencies.
4. Set recording to1920×1080 if possible,30fps, microphone enabled; record a20-second sample and listen before the full take.
5. Record a clean browser profile with readable zoom. Close personal tabs/notifications. Never show tokens, account credentials or private records.
6. Place slides, architecture PDF, terminal and app on the same recording workspace. Keep a timer visible off-capture.

## Deterministic live scenario
```bash
python -m scripts.replay pause
python -m scripts.replay reset
python -m scripts.replay status
```
- The initial cursor is1039 and the primed current version25. Focus `PG-0071` (Synthetic twin071, Delhi).
- Check independent risk outputs, current missing-field warning, baseline/physiology, observation gaps, version1 and Current state.
- Play/pause briefly to demonstrate timed updates, then reset to1039 again.
- Advance +12h to1051. Actual72h probability is0.3551213864930386, current state version37; an actual model-generated alert is persisted.
- **This is a retrospective maximum-score example across the full synthetic cohort, label72=0, hence a false positive.** It is not a held-out detection success or clinical early warning. Keep `artifacts/demo_case.json` available to verify that statement.
- Acknowledge, record “Synthetic demonstration: reviewed model false positive. No treatment recommendation.”, resolve and reload. Explain that resolving does not assert recovery.
- Run a scenario at the current saved version. Read the actual returned baseline/scenario values, not a scripted promised reduction. Reopen the saved scenario and show original state preservation.
- Show actual evaluation, all ablations, below-chance72h discrimination, negative calibration slope, zero primary sensitivity at.35 and zero detected held-out onsets.
- End with provenance, tests, security limitations and pending submission tasks.

## Technical walkthrough commands
```bash
python -m pytest
npm --prefix frontend test -- --reporter=verbose
python -m scripts.evaluate
# Optional, considerably longer; run before recording and show its report:
python -m scripts.verify_reproducibility
```
Use `http://127.0.0.1:8000/docs` for API schemas. Source walkthrough: validation.py → features.py → ml.py → engine.py → store.py → main.py → frontend/src/App.tsx. Show source files, not secrets.

## Offline proof
Install dependencies before disconnecting external internet. The runtime uses local cohort/cache/model/SQLite files only. The browser integration report blocked external HTTP and observed no external requests. Do not claim the optional external API refresh or first-time package installation works without internet.

## Final output and upload
Export an actual MP4 with audible narration; review start/middle/end and exact duration. Upload to the owner's YouTube channel as **Unlisted** (not Private), wait for processing, then open the actual URL signed out. Add the URL and duration to metadata and README; verify playback without permissions. Do not paste a placeholder as a completed video. This environment did not have authorized YouTube publishing access.
