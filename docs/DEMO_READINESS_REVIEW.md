# PranaGuard demo-readiness review

Review date: 2026-11-06. This is a **synthetic-data research demonstration**, not a production or clinical-readiness approval. No existing cohort database or model was reset or regenerated. Testing used disposable SQLite databases and uploads, with synthetic provisioning enabled only for the test. The normal secure portal preview remained separate.

## Findings and fixes

- The stylesheet named Inter but the application did not provide the font, so browsers without a local copy could silently fall back. Inter Variable is now bundled locally and loaded by the application; the browser reported the font loaded.
- Daily-care progress and plan summaries could briefly show zero activity or no guidance/target while the corresponding request was loading or had failed. They now show loading or error states instead. The requested food, hydration, absent-target and exercise notices are preserved with the exact requested apostrophes. Three regression tests cover the notices and loading/error behavior.
- No new features or visual redesign were introduced.

## Page and responsive sweep

Real headless Chromium, synthetic signed-in accounts and screenshots were used at 1440×900 (desktop), 768×1024 (tablet) and 390×844 (mobile). Automated navigation and screenshot capture passed for each view below at each size: 66 captures total. The sweep detected no document-level horizontal overflow, uncaught page errors or visible portal error messages in these states. It checked computed palette values for sidebar `#103b34`, active item `#28594b`, primary button `#1b6b55`, background `#f6f8f7`, text `#203e36`, and loaded Inter Variable. Mobile navigation is a horizontally scrollable strip. Automated screenshots are not a substitute for manual inspection of every screen, device, browser, interaction, loading condition or accessibility need; representative landing, doctor, patient, tablet and mobile captures were also visually inspected.

| Area | Views captured at all three sizes |
| --- | --- |
| Public | Landing, doctor login, patient login |
| Doctor | Home, My Patients, Care Action Centre, Sputum Monitoring, Patient Activity & Adherence, Care Plans, Add Patient, Notifications, Environment, Research tools |
| Patient | Home, My Health, Symptom Check-in, Sputum Diary, My Daily Care Plan, Upload Documents, My Care Plan, Notifications, My Profile |

Representative synthetic captures: [desktop doctor care action centre](screenshots/review/desktop-doctor-care-action-centre.png), [tablet patient daily care](screenshots/review/tablet-patient-daily-care.png), [mobile patient check-in](screenshots/review/mobile-patient-checkin.png), [mobile landing](screenshots/review/mobile-landing.png). The full screenshot set and machine-readable sweep results were also saved as a separate workspace ZIP; they contain synthetic demo data only, not onboarding credentials.

## Functional verification

- The existing Chromium E2E was rerun after the fixes against a fresh disposable database: doctor sign-in, assigned synthetic account provisioning, one-time temporary credential, forced password change, care-plan creation/update, sputum observation and private image review, symptom check-in, breakfast/lunch/dinner, water and activity, notifications/read navigation, and patient-to-other-record and doctor-to-unassigned-record denials passed.
- Additional real-browser checks confirmed the assigned doctor sees all three meals, water and activity; type, date and review-status filters; shared activity review and notification; symptom review with shared follow-up; a research prediction horizon and scenario; and patient PDF upload visible to the assigned doctor. The safety text and absent-target, loading and error states were checked by frontend tests. The browser checked configured-target safety content, not every empty/error state at every viewport.
- Backend tests: **95 passed**, Python 3.11 with compatible independently resolved dependencies; one upstream Starlette TestClient deprecation warning. Frontend: **41 passed**, production build passed, npm audit reported **0 vulnerabilities** (moderate threshold). The final browser E2E passed after the changes.
- This is not an exhaustive test of every button, file type, filter combination, notification trigger, failure path, browser or assistive technology. File authorization and other negative cases have additional backend tests, but this is not a penetration test. The original charts, replay, device and data-source pages remain in separately isolated unsafe legacy demo mode rather than the protected doctor portal; they were covered by existing tests, not by this new portal page sweep.

## Environment and remaining limitations

Python 3.12 was not installed. A Python 3.12 source-build attempt found missing SQLite, zlib, OpenSSL and libffi development dependencies, so it was stopped; the exact Python 3.12 `requirements-lock.txt` environment was **not** installed or tested. A previous prebuilt-runtime download also failed TLS. Repeat the locked install and backend suite in a suitable Python 3.12 CI environment before relying on it.

The prior [completion report](COMPLETION_REPORT.md) describes important remaining constraints: synthetic-only use, no clinical validation, rate limiting/MFA/security hardening and independent review required, request-body limits needed upstream, session-storage XSS exposure, and bounded history/notification lists. Never expose predictable demo credentials or the unsafe legacy mode publicly or use them for real patients. The browser review does not certify the application for production or medical use.
