# Third-party data and asset licenses

## Project code and original documents
MIT; see the root [LICENSE](../LICENSE). No clinical efficacy warranty is provided. Models and original documentation are distributed with the code under MIT; source-data attribution obligations remain applicable.

## Synthetic patient data
All profiles, physiology, symptoms, adherence, sleep, activity and outcome labels are procedurally generated. They do not represent identifiable people. Original synthetic patient fields are dedicated under [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/). The combined longitudinal file also includes CC BY 4.0 environmental fields, so retain the attribution below when redistributing that file. The synthetic disease generator is not medically validated.

## Environmental fields and cached API responses
Data provided by [Open-Meteo](https://open-meteo.com/), using the [Copernicus Atmosphere Monitoring Service global atmospheric composition forecasts](https://ads.atmosphere.copernicus.eu/datasets/cams-global-atmospheric-composition-forecasts?tab=overview) and historical weather products. API data are offered under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/); the [Open-Meteo license](https://open-meteo.com/en/licence) requires attribution and indication of modifications. Retain provider credits. No endorsement is implied.

Raw JSON responses are unmodified. The longitudinal file renames fields, joins UTC timestamps and aligns shared city-level fields with synthetic patient hours. No individual exposure measurement is implied. Exact request URLs, retrieval times, sample counts, source names and SHA-256 checksums are in [the cache manifest](../data/environment/manifest.json).

Hosted API access terms are distinct from data redistribution rights: free endpoint access is for non-commercial fair use. Commercial API service use requires the appropriate subscription. See https://open-meteo.com/en/terms and https://open-meteo.com/en/pricing . Open-Meteo **server source code** has an AGPL license; this repository only calls its public APIs and does not copy that server code.

## Frontend assets and libraries
No stock images, commercial assets, external webfonts or restricted datasets are included. All screenshots are from the actual running PranaGuard application. Diagrams are original editable vector shapes. System font stacks are used, not bundled font binaries.

- React / React DOM: MIT.
- Vite, Tailwind CSS, Recharts, Lucide React, Vitest and Testing Library: MIT (retain notices from installed dependencies).
- FastAPI, Pydantic, pandas, NumPy, scikit-learn, LightGBM, SHAP, Uvicorn and joblib: their upstream permissive licenses apply to their packages (MIT, BSD variants and PSF as applicable).
- SQLite: public domain.
- Build-time python-pptx: MIT; ReportLab: BSD-style; Playwright: Apache-2.0.
- PyMuPDF is a build-time **AGPL/commercial-license** dependency, not part of the application runtime. Its source is not copied into the repository. Review its licensing if embedding/distributing that tool or modifying its use. LibreOffice is used externally for PDF conversion under its upstream licensing.

Dependency code is not vendored. Package manifests and the npm lockfile are included. These notices do not replace a formal legal review for commercial/regulated deployment.
