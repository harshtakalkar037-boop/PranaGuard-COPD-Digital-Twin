# Artifact and application QA notes

## What was actually reviewed
- Actual Chromium screenshots of all seven views plus a390px mobile patient view were decoded and visually inspected, not generated as a mockup.
- All16 PowerPoint slides were rendered from the actual LibreOffice PDF export and visually reviewed in a slide overview. Representative content/evaluation/architecture pages were inspected at larger scale.
- The separate architecture PDF was rendered and inspected for node labels, arrow direction, readable paths and complete capability coverage. The editable PPTX uses native vector shapes/text, not a flattened diagram picture.
- The technical report PDF was opened with PyMuPDF; page text includes actual metric values and limitations. It is5 pages in this build.
- Every substantial native PowerPoint paragraph/table cell was compared against the corresponding exported PDF page. All native shapes and extracted PDF spans were checked for page overflow; screenshots were decoded. Final machine results are in artifact-verification.json.

## Readability and interpretation
Main slide titles/body/results are editable and legible; small footers/module labels are supplementary. Screenshots are actual UI images and can be zoomed; key model results are repeated in readable native tables rather than relying on screenshot text. Full-size separate architecture artifacts are available for the detailed diagram. No file-existence-only check is treated as proof of readable content.

The UI explicitly distinguishes synthetic patients, historical ambient data, missing measurements, independent horizon estimates, raw TreeSHAP log-odds, non-causal scenarios and weak72h calibration. The false-positive example is disclosed in the recording package and slides. A retained negative Platt slope is a scientific limitation, not masked as a deployment success.

## Scope of verification
Local artifact checks do not establish GitHub public visibility or YouTube playback. Those remain pending. Automated text/bounds checks cannot prove every semantic aspect of design; visual review supplements them. Software test success is not medical validation. Do not infer production readiness from this QA report.
