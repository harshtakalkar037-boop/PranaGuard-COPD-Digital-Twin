# -*- coding: utf-8 -*-
"""Backup / appendix slides (separate from the five-slide main narrative)."""
from __future__ import annotations

import os

from deck_lib import (CYAN, CYAN_DEEP, CYAN_MID, LIGHT_BG, LIGHT_LINE, LINE, MUTED, MUTED_DIM,
                      NAVY, PANEL, WHITE, Canvas, face)
from draw import MARGIN, wrap_multi
from content import A1

HERE = os.path.dirname(os.path.abspath(__file__))


def appendix_qa() -> Canvas:
    cv = Canvas(NAVY)
    cv.text(MARGIN, 40, A1["kicker"], size=8.6, weight=700, color=CYAN, tracking=0.2)
    cv.text(MARGIN, 60, "Ten answers, ready to deliver", size=24, weight=700, color=WHITE, tracking=-0.015)
    cv.text(460, 69, "BACKUP \u00b7 NOT PART OF THE FIVE-MINUTE FLOW", size=7.2, weight=700,
            color=MUTED_DIM, tracking=0.13, width=436, align="right")

    # two columns of five Q&A pairs
    colw = 404
    pitch = 82
    for i, (q, a) in enumerate(A1["items"]):
        col = i // 5
        row = i % 5
        x = MARGIN + col * (colw + 28)
        y = 106 + row * pitch
        cv.text(x, y, q, size=8.4, weight=700, color=CYAN, tracking=0.09, max_w=colw, min_size=7.2)
        wrap_multi(cv, x, y + 14, a, 9.2, 400, "C3D6DC", colw, leading=1.42)
        if row < 4:
            cv.line(x, y + pitch - 16, x + colw, y + pitch - 16, color="123C4B", lw=0.7)

    cv.text(MARGIN, 508, "Full source list on the next page. Every answer above is defensible "
                         "from the project\u2019s own documentation or a cited publication.",
            size=7.8, weight=400, color=MUTED_DIM, max_w=832, min_size=6.8)
    return cv


def appendix_refs() -> Canvas:
    cv = Canvas(LIGHT_BG)
    cv.text(MARGIN, 40, "APPENDIX  \u00b7  REFERENCES", size=8.6, weight=700, color=CYAN_DEEP, tracking=0.2)
    cv.text(MARGIN, 60, "Sources and further reading", size=24, weight=700, color=NAVY, tracking=-0.015)

    end = wrap_multi(cv, MARGIN, 102, A1["facts"], 10.6, 400, "2E4A55", 520, leading=1.62)

    y = end + 26
    cv.text(MARGIN, y, "REFERENCES", size=8.0, weight=700, color=CYAN_DEEP, tracking=0.15)
    y += 15
    for r in A1["refs"]:
        lines = wrap_multi(cv, MARGIN, y, r, 9.0, 400, "3E5A66", 540, leading=1.45)
        y = lines + 7.0

    # right rail: state of the evidence
    rx = 656
    cv.rect(rx, 102, 240, 232, fill=NAVY, radius=4)
    cv.text(rx + 20, 120, "STATE OF THE EVIDENCE", size=7.8, weight=700, color=CYAN, tracking=0.14,
            max_w=200, min_size=6.8)
    yy = 146
    rows = [("IMPLEMENTED", "Working prototype, audited and reproducible"),
            ("EXPERIMENTAL", "Synthetic-cohort model studies; weak 72-hour performance reported openly"),
            ("INTENDED", "Longitudinal visibility and structured record-keeping"),
            ("NOT CLAIMED", "Any clinical outcome, validated prediction or regulatory status")]
    for lab, txt in rows:
        cv.text(rx + 20, yy, lab, size=7.0, weight=700, color=MUTED_DIM, tracking=0.12)
        yy = wrap_multi(cv, rx + 20, yy + 11, txt, 8.5, 400, "C3D6DC", 200, leading=1.38) + 11

    # citation discipline note, in the space beneath the rail
    cv.text(rx, 356, "CITATION DISCIPLINE", size=7.2, weight=700, color=CYAN_DEEP, tracking=0.13)
    wrap_multi(cv, rx, 372,
               "Only the seven sources listed are used anywhere in this deck. If a jury member asks for a "
               "source that is not among them, say so plainly rather than reaching for a number you cannot "
               "defend.", 8.8, 400, "415A64", 236, leading=1.5)
    return cv
