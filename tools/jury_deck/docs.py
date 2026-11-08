# -*- coding: utf-8 -*-
"""Companion documents: the two-presenter script (DOCX) and the jury Q&A card (PDF)."""
from __future__ import annotations

import os
from datetime import date

from deck_lib import (CYAN, CYAN_DEEP, LIGHT_BG, LINE, MUTED, MUTED_DIM, NAVY, PANEL, WHITE,
                      Canvas, PdfOut, face)
from draw import MARGIN, wrap_multi
from content import A1
import script

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor


# --------------------------------------------------------------------------- DOCX helpers
def _shade(cell, hex_color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def _cell_text(cell, text, bold=False, color=None, size=9.5, font="Inter"):
    cell.text = ""
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)
    run = p.add_run(text)
    run.bold = bold
    run.font.size = Pt(size)
    run.font.name = font
    run._element.rPr.rFonts.set(qn("w:eastAsia"), font)
    if color:
        run.font.color.rgb = RGBColor.from_string(color)


def _para(doc, text, size=10.5, bold=False, color="1A1A1A", space_after=6, space_before=0,
          italic=False, font="Inter", align=None, line=1.35):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.line_spacing = line
    if align:
        p.alignment = align
    run = p.add_run(text)
    run.bold = bold
    run.italic = italic
    run.font.size = Pt(size)
    run.font.name = font
    run._element.rPr.rFonts.set(qn("w:eastAsia"), font)
    run.font.color.rgb = RGBColor.from_string(color)
    return p


def _heading(doc, text, size=17, color="061A23", space_before=16, space_after=6):
    return _para(doc, text, size=size, bold=True, color=color, space_before=space_before,
                 space_after=space_after, line=1.15)


def _rule(doc):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(8)
    pPr = p._p.get_or_add_pPr()
    borders = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "6")
    bottom.set(qn("w:color"), "CBDCDD")
    borders.append(bottom)
    pPr.append(borders)


# --------------------------------------------------------------------------- speaker script
def build_script_docx(path: str):
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
    sec.left_margin = sec.right_margin = Cm(2.2)
    sec.top_margin = sec.bottom_margin = Cm(2.0)

    style = doc.styles["Normal"]
    style.font.name = "Inter"
    style.font.size = Pt(10.5)
    style.element.rPr.rFonts.set(qn("w:eastAsia"), "Inter")

    total, per = script.spoken_words()
    mm, ss = divmod(round(total / 160 * 60), 60)

    # ---- cover ----
    _para(doc, "PRANAGUARD", size=9, bold=True, color="177F79", space_after=2)
    _para(doc, "International Jury Presentation", size=24, bold=True, color="061A23", space_after=2,
          line=1.1)
    _para(doc, "Speaker Script  \u00b7  Two Presenters  \u00b7  Five to Seven Minutes", size=13,
          color="415A64", space_after=10)
    _rule(doc)

    meta = doc.add_table(rows=4, cols=2)
    meta.alignment = WD_TABLE_ALIGNMENT.LEFT
    for row_i, (k, v) in enumerate([
        ("Event", "Happiest Health Digital Twin Challenge 2026 \u2014 international jury round"),
        ("Institution", "Pune Institute of Computer Technology (PICT), Pune"),
        ("Duration", f"{total} spoken words \u2248 {mm}:{ss:02d} at a conversational pace, "
                     "with room inside the seven-minute limit for pauses and one handover"),
        ("Running order", "Presenter 1: slides 1\u20132 (1:40)   \u00b7   Presenter 2: slides 3\u20135 (3:20)"),
    ]):
        _cell_text(meta.cell(row_i, 0), k.upper(), bold=True, color="177F79", size=8)
        _cell_text(meta.cell(row_i, 1), v, color="1A1A1A", size=9.5)
    doc.add_paragraph()

    _para(doc, "The rule that governs every word of this script", size=10.5, bold=True, color="061A23",
          space_before=6, space_after=3)
    _para(doc, "PranaGuard is a research prototype built entirely on synthetic patient data. It is not a "
               "medical device and it has not been clinically validated. Nothing in this script claims that "
               "patient outcomes, hospitalisations or exacerbation rates have improved, because no such "
               "improvement has been measured. Where the deck describes impact, it says \u201cpotential\u201d and "
               "means it.", size=10, color="415A64", space_after=10)

    _para(doc, "Timing overview", size=10.5, bold=True, color="061A23", space_after=4)
    t = doc.add_table(rows=len(script.SLIDES) + 2, cols=4)
    t.style = "Table Grid"
    for j, h in enumerate(["Slide", "Section", "Presenter", "Time"]):
        _cell_text(t.cell(0, j), h.upper(), bold=True, color="FFFFFF", size=8)
        _shade(t.cell(0, j), "061A23")
    for i, sl in enumerate(script.SLIDES, start=1):
        vals = (str(sl["n"]), sl["title"].title(), sl["presenter"].title(), sl["window"])
        for j, v in enumerate(vals):
            _cell_text(t.cell(i, j), v, size=9)
    last = len(script.SLIDES) + 1
    for j, v in enumerate(("", "Target total (seven-minute hard stop)", "", "5:00")):
        _cell_text(t.cell(last, j), v, bold=True, size=9)
        _shade(t.cell(last, j), "EAF2F2")

    # ---- introduction ----
    doc.add_page_break()
    _para(doc, "PRANAGUARD  \u00b7  SPEAKER SCRIPT", size=8, bold=True, color="177F79", space_after=2)
    _heading(doc, script.INTRO["title"], size=15, space_before=0)
    _rule(doc)
    _para(doc, script.INTRO["main"], size=10, color="177F79", italic=True, space_after=8)
    for kind, text in script.INTRO["blocks"]:
        if kind == "h":
            _para(doc, text, size=10.5, bold=True, color="0B2430", space_before=8, space_after=3)
        else:
            p = doc.add_paragraph(style="List Bullet")
            p.paragraph_format.space_after = Pt(3)
            p.paragraph_format.line_spacing = 1.3
            r = p.add_run(text)
            r.font.size = Pt(10)
            r.font.name = "Inter"

    # ---- each slide ----
    for sl in script.SLIDES:
        doc.add_page_break()
        _para(doc, f"{sl['presenter']}  \u00b7  {sl['window']}", size=8, bold=True, color="177F79",
              space_after=2)
        _heading(doc, f"SLIDE {sl['n']} \u2014 {sl['title']}", size=15, space_before=0)
        _rule(doc)
        _para(doc, sl["main"], size=10, color="177F79", italic=True, space_after=8)

        for kind, text in sl["blocks"]:
            if kind == "h":
                _para(doc, text, size=10.2, bold=True, color="0B2430", space_before=8, space_after=4)
            elif kind == "q":
                p = _para(doc, text, size=11, color="0B2430", space_after=7, line=1.45)
                p.paragraph_format.left_indent = Cm(0.55)
                pPr = p._p.get_or_add_pPr()
                borders = OxmlElement("w:pBdr")
                left = OxmlElement("w:left")
                left.set(qn("w:val"), "single")
                left.set(qn("w:sz"), "12")
                left.set(qn("w:space"), "8")
                left.set(qn("w:color"), "3FE0CF")
                borders.append(left)
                pPr.append(borders)
            else:
                _para(doc, text, size=10, color="415A64", space_after=6)

        _para(doc, "SOURCES FOR THIS SLIDE", size=8, bold=True, color="177F79", space_before=10,
              space_after=3)
        for src in sl["sources"]:
            p = doc.add_paragraph(style="List Bullet")
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.line_spacing = 1.3
            r = p.add_run(src)
            r.font.size = Pt(8.8)
            r.font.name = "Inter"
            r.font.color.rgb = RGBColor.from_string("415A64")

    # ---- evidence base ----
    doc.add_page_break()
    _para(doc, "PRANAGUARD  \u00b7  EVIDENCE BASE", size=8, bold=True, color="177F79", space_after=2)
    _heading(doc, "Every factual claim, with its source", size=15, space_before=0)
    _rule(doc)

    t2 = doc.add_table(rows=len(script.QA) + 1, cols=2)
    t2.style = "Table Grid"
    for j, h in enumerate(["Claim as it appears in the deck", "Source"]):
        _cell_text(t2.cell(0, j), h.upper(), bold=True, color="FFFFFF", size=8)
        _shade(t2.cell(0, j), "061A23")
    for i, (q, a, src) in enumerate(script.QA, start=1):
        _cell_text(t2.cell(i, 0), q.rstrip("?").title(), size=8.6)
        _cell_text(t2.cell(i, 1), a, size=8.6, color="415A64")

    _para(doc, "Nothing outside this table is asserted as fact anywhere in the presentation. Three items on "
               "the slides are explicitly labelled as illustrations: the patient photograph (slides 1 and "
               "5), the 90-day interval (slide 2) and the interface screenshots, which come from the running "
               "prototype with a synthetic patient.", size=9.2, color="415A64", space_before=10)

    doc.core_properties.title = "PranaGuard \u2014 Speaker Script (5\u20137 minutes)"
    doc.core_properties.author = "PranaGuard \u00b7 Pune Institute of Computer Technology"
    doc.core_properties.subject = "Two-presenter script with timings, interactions and an evidence base"
    doc.core_properties.comments = ("Research prototype, synthetic data only, not clinically validated.")
    doc.save(path)


# --------------------------------------------------------------------------- Q&A cheat sheet
QA_PAGES = [
    ("01", "COPD, IN ONE BREATH",
     [("What is COPD?",
       "A common, preventable and treatable disease with persistent respiratory symptoms and airflow "
       "limitation. Breathlessness, cough and sputum are typical. It is not curable, but it is "
       "treatable."),
      ("What is an exacerbation?",
       "An acute worsening of respiratory symptoms that leads to additional therapy — from extra "
       "bronchodilators at home up to hospitalisation. Exacerbations drive health status, admissions "
       "and disease progression."),
      ("Say it like this",
       "\u201cCOPD is a disease of trajectory, and we mostly measure it in snapshots.\u201d")],
     ["WHO COPD fact sheet, 10 June 2026.", "GOLD 2026 report."]),
    ("02", "THE GAP IN CARE",
     [("Why is longitudinal monitoring useful?",
       "A single value is a moment. Repeated records against a personal baseline begin to show "
       "direction of change — and the strongest known predictor of future exacerbations is the history "
       "of past ones."),
      ("Is this just poor healthcare?",
       "No. It is the shape of the instrument. A fifteen-minute consultation cannot observe ninety "
       "days. We are not asking clinicians to watch harder; we are making the gap legible."),
      ("How big is the reporting gap?",
       "In one longitudinal cohort, 68% of diary-recorded exacerbations were never reported to a health "
       "professional. Reported and unreported events had similar characteristics.")],
     ["Hurst et al., NEJM 2010;363:1128-38.", "Langsetmo et al., AJRCCM 2008;177:396-401.",
      "Elliott-Button et al., npj Prim Care Respir Med 2024;34:37."]),
    ("03", "THE PRANAQUARD SYSTEM",
     [("What is the digital twin here?",
       "A versioned, replayable state per patient: observations, a personal baseline taken from the "
       "first 72 observed hours, derived features, and the model context attached to each saved state. "
       "Data-driven, not a mechanistic lung model."),
      ("How does the doctor use it?",
       "Signs in, opens an assigned patient, reviews the twin, the trends and the labelled model "
       "context, then records a review. Access is enforced server-side by patient assignment, and every "
       "action is attributed in an audit trail."),
      ("What does the model actually predict?",
       "An experimental estimate of a new synthetic exacerbation onset within 24, 48 or 72 hours on the "
       "research cohort. Research output — not a validated probability, not an alert.")],
     ["PranaGuard docs: METHODOLOGY.md, ARCHITECTURE.md, MODEL_CARD.md.",
      "Screenshots from the running prototype, synthetic patient PG-0071."]),
    ("04", "EVIDENCE AND HONESTY",
     [("Has it been clinically validated?",
       "No. No clinical trial, no real patient data, no regulatory review. It is labelled a research "
       "prototype and not a medical device throughout the product."),
      ("What impact has actually been demonstrated?",
       "Software impact only: a working, audited, reproducible prototype with tested clinician and "
       "patient workflows. No patient, clinical or system-level outcome has been measured."),
      ("How good is the model really?",
       "Weak beyond 48 hours on held-out synthetic data — the 72-hour model had AUROC 0.395, below "
       "chance, with AUPRC below prevalence. We publish that rather than tune it away.")],
     ["docs/LIMITATIONS.md; docs/MODEL_CARD.md; artifacts/evaluation.md.",
      "Synthetic cohort of 120 patients; no external clinical validation."]),
    ("05", "WHAT HAPPENS NEXT",
     [("What data is real and what is synthetic?",
       "Every patient, physiological stream and outcome label is synthetic — 120 generated patients. "
       "The only real inputs are public modelled city air-quality and weather data, used as context, "
       "not personal exposure. No clinical data is involved, so nothing here is clinical validation."),
      ("How would it be evaluated?",
       "Three stages: clinician-supervised usability and workflow studies; prospective observational "
       "research with adjudicated outcomes under ethics approval; then outcome measurement including "
       "calibration, subgroup fairness and net benefit."),
      ("If you don't know the answer",
       "Say: \u201cWe have not evaluated that, and it would be part of the next stage.\u201d That is always "
       "stronger than an invention.")],
     ["docs/DATA_PROVENANCE.md; docs/LIMITATIONS.md (next steps).",
      "Ethics approval and governance are prerequisites, not afterthoughts."]),
]


QA_GROUPS = [
    ("01", "COPD, IN ONE BREATH", (0, 1, 2)),
    ("02", "THE DIGITAL TWIN", (3, 4, 5)),
    ("03", "EVIDENCE AND HONESTY", (6, 7, 8)),
    ("04", "THE CLINICIAN WORKFLOW", (9,)),
    ("05", "IF THE ROOM PUSHES BACK", ()),
]

PUSHBACK = [
    ("Is this just a dashboard?",
     "No. A dashboard shows the latest number. This keeps every hour as a versioned, replayable state, so "
     "the clinician can look at direction of change against that patient's own baseline."),
    ("Why should we trust a model that scores 0.4?",
     "You shouldn't trust it as a clinical tool — and we don't ask you to. The value we demonstrated is "
     "that the workflow is buildable and auditable. The model is a research component with published, "
     "honest limitations."),
    ("So what would you need to make this real?",
     "Ethics approval and prospective data with adjudicated outcomes, then calibration and subgroup "
     "analysis, then outcome measurement. That is a multi-year research programme, not a software release."),
]


def build_qa_pdf(path: str):
    out = PdfOut()
    for num, title, idxs in QA_GROUPS:
        cv = Canvas(LIGHT_BG)
        cv.rect(0, 0, 960, 78, fill=NAVY)
        cv.text(MARGIN, 22, "PRANAGUARD  \u00b7  JURY Q&A CARDS", size=8.4, weight=700, color=CYAN,
                tracking=0.2)
        cv.text(MARGIN, 38, title, size=22, weight=700, color=WHITE, tracking=-0.012)
        cv.text(560, 25, "BACKUP CARD  " + num + " / 05", size=8.0, weight=700, color=MUTED,
                tracking=0.16, width=336, align="right")

        items = [(script.QA[i][0], script.QA[i][1]) for i in idxs] if idxs else PUSHBACK
        srcs = [script.QA[i][2] for i in idxs] if idxs else []

        y = 112 if len(items) > 2 else 132
        for i, (q, a) in enumerate(items):
            cv.text(MARGIN, y, q.upper(), size=9.0, weight=700, color=CYAN_DEEP, tracking=0.1,
                    max_w=676, min_size=7.6)
            y = wrap_multi(cv, MARGIN, y + 18, a, 15.0, 400, "1E3A45", 676,
                           leading=1.54) + (30 if len(items) > 2 else 40)
            if i < len(items) - 1:
                cv.line(MARGIN, y - 15, MARGIN + 676, y - 15, color="D6E3E3", lw=0.8)

        # right rail: delivery reminders
        rx = 780
        cv.rect(rx, 116, 116, 296, fill="EAF2F2", line="C7DADB", lw=0.8, radius=4)
        cv.text(rx + 13, 130, "WHEN YOU ANSWER", size=6.6, weight=700, color=CYAN_DEEP, tracking=0.12,
                max_w=92, min_size=5.8)
        ry = 150
        for line in script.QA_CLOSERS:
            ry = wrap_multi(cv, rx + 13, ry, line, 8.4, 400, "3E5A66", 92, leading=1.4) + 12

        cv.line(MARGIN, 452, 896, 452, color="CBDCDD", lw=0.8)
        cv.text(MARGIN, 464, "SOURCES", size=7.0, weight=700, color=CYAN_DEEP, tracking=0.14)
        yy = 477
        for src_line in (srcs or ["All answers traceable to project documentation and cited publications."]):
            yy = wrap_multi(cv, MARGIN, yy, src_line, 8.0, 400, "5A737D", 560, leading=1.4) + 1
        cv.text(420, 464, "RESEARCH PROTOTYPE \u00b7 SYNTHETIC DATA ONLY\nNOT A MEDICAL DEVICE \u00b7 NOT CLINICALLY VALIDATED",
                size=7.0, weight=700, color="8AA2AC", tracking=0.06, width=476, align="right")
        out.page(cv)
    out.save(path)
