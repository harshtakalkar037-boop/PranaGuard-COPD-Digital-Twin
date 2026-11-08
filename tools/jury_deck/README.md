# PranaGuard jury deck — build system

This folder generates the four jury deliverables reproducibly from one source of truth.

## Outputs (repository root)

| File | What it is |
|---|---|
| `PranaGuard_International_Jury_Presentation.pptx` | 5 main slides + 2 appendix slides, fully editable, click-to-reveal animations, complete speaker notes |
| `PranaGuard_International_Jury_Presentation.pdf` | Same 7 pages, print quality, Inter embedded |
| `PranaGuard_5_Minute_Speaker_Script.docx` | Two-presenter script, timings, interactions, handover, evidence table |
| `PranaGuard_Jury_QA_CheatSheet.pdf` | 5 backup cards: 10 jury answers + pushback handling |

## Rebuild

```bash
pip install --break-system-packages python-pptx python-docx pillow pymupdf fonttools brotli
python tools/jury_deck/build.py
```

## How it works

`deck_lib.py` is a single 960 × 540 pt (16:9) layout engine with two backends that read the same
element list, so the PDF and the PPTX are geometrically identical:

* **PDF** — PyMuPDF. Real Inter TTFs from `fonts/` are embedded and the text is laid out with
  `TextWriter`, using measured advance widths. No fallback fonts appear anywhere.
* **PPTX** — python-pptx. Every string is an individual text box with a real run, so nothing is
  baked into an image. Text uses **Arial** with the point size compensated by measured advance
  widths (Inter is ~2–3 % wider), which keeps the PowerPoint rendering aligned with the PDF while
  staying editable and offline-safe on any machine.

PowerPoint timing XML (fade entrances grouped per click) and slide transitions are emitted by
`PptxOut._add_timing` / `_add_transition`.

## Content discipline

* `content.py` — everything visible on the five main slides.
* `script.py` — **the canonical spoken script** (≈766 words ≈ 5:05 at a conversational pace).
  Both the PPTX notes and the DOCX are generated from it, so they can never drift apart.
* `docs.py` — the DOCX and Q&A card builders.
* `notes.py` — appendix notes only (superseded for the five main slides by `script.py`).

Every factual claim is either traced to PranaGuard's own verified documentation or to one of the
seven cited publications (WHO, GOLD, Langsetmo 2008, Hurst 2010, Elliott-Button 2024, the 2025
multicountry survey, and the project docs). No claim of clinical validation, outcome improvement or
regulatory status appears anywhere, including in the speaker notes.

## Verification

```bash
python tools/jury_deck/render_pptx.py PranaGuard_International_Jury_Presentation.pptx /tmp/pptx_check
```

Rasterises the PPTX from its own stored geometry with Arial metrics — an independent check that the
PowerPoint layout matches the PDF.

## Assets

* `assets/hero_panel.jpg` — illustrative patient photograph, colour-graded into the navy palette
  and blended at its left edge. Labelled "illustrative photograph" on the slides.
* `assets/ui_twin_crop.png` — crop of `docs/model-v3/verification/screenshots/desktop-patient.png`,
  the actual running application, synthetic patient PG-0071, replay state v25 (upscaled 2× with a
  light unsharp mask for print).

*Illustrative imagery was produced for this deck. The application screenshots are genuine captures
committed in this repository.*
