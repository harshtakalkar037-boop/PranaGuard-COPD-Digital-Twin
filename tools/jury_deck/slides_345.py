# -*- coding: utf-8 -*-
"""Slide 3, Slide 4, Slide 5 — Presenter 2 (approach, impact, vision)."""
from __future__ import annotations

import os

from deck_lib import (AMBER, CYAN, CYAN_DEEP, CYAN_MID, LIGHT_BG, LIGHT_PANEL, LIGHT_LINE,
                      LINE, MUTED, MUTED_DIM, NAVY, NAVY_2, PANEL, PANEL_2, WHITE, Canvas,
                      face)
from draw import (MARGIN, RIGHT, arrow, arrow_down, check, kicker, number_badge, rule,
                  soft_panel, wrap_multi, wrap_lines)
from content import S3, S4, S5

HERE = os.path.dirname(os.path.abspath(__file__))
A = lambda n: os.path.join(HERE, "assets", n)


# =====================================================================================
# SLIDE 3 — THE PRANAQUARD APPROACH
# =====================================================================================
def slide3() -> Canvas:
    cv = Canvas(NAVY)
    kicker(cv, MARGIN, 45, S3["kicker"])
    cv.text(600, 45.6, "PRANAGUARD", size=8.4, weight=700, color=MUTED, tracking=0.24, width=176,
            align="right")

    cv.text(MARGIN, 74, "From isolated observations", size=29, weight=700, color=WHITE, tracking=-0.016)
    cv.text(MARGIN, 74 + 36, "to a longitudinal COPD", size=29, weight=700, color=CYAN, tracking=-0.016)
    cv.text(MARGIN, 74 + 72, "digital twin", size=29, weight=700, color=CYAN, tracking=-0.016)
    wrap_multi(cv, MARGIN, 190, S3["sub"], 10.8, 400, MUTED, 366, leading=1.5)

    # ---- right: the actual interface -------------------------------------------------
    px, py, pw, ph = 476, 116, 420, 349
    cv.rect(px - 8, py - 8, pw + 16, ph + 16, fill=PANEL, line=LINE, lw=0.8, radius=8)
    cv.image(px, py, pw, ph, A("ui_twin_crop.png"))
    cv.rect(px, py, pw, ph, fill=None, line="2B6577", lw=0.7, radius=3)
    cv.text(px, py + ph + 17, S3["shot_caption"], size=8.2, weight=700, color=CYAN, tracking=0.04,
            max_w=pw, min_size=7.0)
    wrap_multi(cv, px, py + ph + 31, S3["shot_note"], 8.2, 400, MUTED, pw, leading=1.4)

    # ---- left: the flow, revealed progressively (click 1-2-3) -------------------------
    fy = 268
    step_w = 372
    step_h = 39
    cv.text(MARGIN, fy - 19, "THE INFORMATION FLOW  \u00b7  CLICK TO REVEAL", size=7.8,
            weight=700, color=MUTED_DIM, tracking=0.14, max_w=step_w - 10, min_size=6.4)

    for i, (n, t, d) in enumerate(S3["flow"]):
        grp = 1 if i < 2 else (2 if i < 4 else 3)
        cv.click_group(grp)
        y = fy + i * (step_h + 6)
        last = i == len(S3["flow"]) - 1
        cv.rect(MARGIN, y, step_w, step_h, fill=PANEL_2 if last else PANEL,
                line=CYAN_DEEP if last else LINE, lw=0.9 if last else 0.7, radius=4)
        cv.text(MARGIN + 15, y + 6.5, n, size=7.6, weight=700, color=CYAN, tracking=0.1)
        cv.text(MARGIN + 38, y + 5, t, size=9.4, weight=700, color=WHITE, tracking=0.05, max_w=step_w - 48)
        cv.text(MARGIN + 38, y + 19, d, size=8.3, weight=400, color=MUTED, max_w=step_w - 48,
                min_size=7.1)
        if not last:
            arrow_down(cv, MARGIN + 25, y + step_h + 1.0, y + step_h + 5.4, color="2C6C77", lw=1.0, head=2.4)
    cv.click_group(0)

    cv.text(MARGIN, 508, S3["note_line"], size=7.6, weight=400, color=MUTED_DIM, max_w=832,
            min_size=6.6)
    return cv


# =====================================================================================
# SLIDE 4 — HEALTHCARE IMPACT
# =====================================================================================
def slide4() -> Canvas:
    cv = Canvas(LIGHT_BG)
    kicker(cv, MARGIN, 45, S4["kicker"], color=CYAN_DEEP)
    cv.text(600, 45.6, "PRANAGUARD", size=8.4, weight=700, color=MUTED_DIM, tracking=0.24, width=296,
            align="right")

    cv.text(MARGIN, 70, "What could change \u2014", size=28, weight=700, color=NAVY, tracking=-0.018)
    tw = face("Inter", 700).width("What could change \u2014", 28, -0.018)
    cv.text(MARGIN + tw + 20, 70, "if the approach is validated", size=28, weight=700, color=CYAN_DEEP,
            tracking=-0.018)
    cv.text(MARGIN, 106, S4["sub"], size=10.2, weight=400, color="3E5A66", max_w=760, min_size=9.0)

    # ---- three lanes -------------------------------------------------------------------
    ly, lh, colw, gap = 130, 136, 266, 15
    heads = ["PATIENT IMPACT", "CLINICIAN IMPACT", "HEALTHCARE SYSTEM IMPACT"]
    for i, (role, bullets) in enumerate(S4["lanes"]):
        x = MARGIN + i * (colw + gap)
        cv.rect(x, ly, colw, lh, fill="FFFFFF", line=LIGHT_LINE, lw=0.7, radius=3)
        cv.rect(x, ly, colw, 3, fill=CYAN if i < 2 else CYAN_DEEP)
        cv.text(x + 15, ly + 14, heads[i], size=8.1, weight=700, color=CYAN_DEEP, tracking=0.11,
                max_w=colw - 30, min_size=7.0)
        yy = ly + 33
        for b in bullets:
            cv.circle(x + 19, yy + 4.1, 1.45, fill=CYAN_MID)
            yy = wrap_multi(cv, x + 27, yy, b, 9.3, 400, "2E4A55", colw - 42, leading=1.4) + 5.2

    # ---- impact pathway -----------------------------------------------------------------
    py = 290
    cv.text(MARGIN, py, "THE IMPACT PATHWAY  \u00b7  POTENTIAL, NOT MEASURED", size=7.8, weight=700,
            color=CYAN_DEEP, tracking=0.13)
    by, bh = py + 15, 52
    cv.rect(MARGIN, by, 832, bh, fill=NAVY, radius=3)
    n = len(S4["pathway"])
    seg_w = (832 - 2 * 12) / n
    for i, label in enumerate(S4["pathway"]):
        x = MARGIN + 12 + i * seg_w
        cv.text(x, by + 7, f"0{i+1}", size=6.8, weight=700, color=CYAN, tracking=0.1)
        lines = wrap_lines(label, 8.6, 700, seg_w - 26)
        for j, ln in enumerate(lines[:2]):
            cv.text(x, by + 17 + j * 10.4, ln, size=8.6, weight=700, color=WHITE, tracking=0.02)
        if i < n - 1:
            arrow(cv, x + seg_w - 15, by + bh / 2, x + seg_w - 5, color=CYAN_DEEP, lw=1.0, head=3.4)

    # ---- current evidence vs future validation -------------------------------------------
    ey = 386
    cv.text(MARGIN, ey, S4["ev_title"], size=7.8, weight=700, color=CYAN_DEEP, tracking=0.13)
    iy, half = ey + 13, 408
    cv.rect(MARGIN, iy, half, 80, fill=LIGHT_PANEL, line=LIGHT_LINE, lw=0.7, radius=3)
    cv.text(MARGIN + 14, iy + 11, S4["current_title"], size=7.8, weight=700, color=NAVY, tracking=0.11)
    for k, item in enumerate(S4["current"]):
        cv.circle(MARGIN + 16, iy + 31.4 + k * 15.6, 1.4, fill=CYAN_DEEP)
        cv.text(MARGIN + 24, iy + 26.5 + k * 15.6, item, size=8.8, weight=400, color="2E4A55",
                max_w=half - 34, min_size=7.4)
    fx = MARGIN + half + 16
    cv.rect(fx, iy, half, 80, fill=NAVY, radius=3)
    cv.text(fx + 14, iy + 11, S4["future_title"], size=7.8, weight=700, color=CYAN, tracking=0.11)
    for k, item in enumerate(S4["future"]):
        cv.circle(fx + 16, iy + 31.4 + k * 15.6, 1.4, fill=CYAN)
        cv.text(fx + 24, iy + 26.5 + k * 15.6, item, size=8.8, weight=400, color="C6DCE2",
                max_w=half - 28, min_size=7.4)

    # ---- honest disclaimer ---------------------------------------------------------------
    cv.text(MARGIN, 496, "NOT YET DEMONSTRATED", size=7.2, weight=700, color="9A6414", tracking=0.12)
    cv.text(MARGIN, 508, S4["disclaimer"], size=8.4, weight=400, color="6B4A16", max_w=832, min_size=7.2)
    return cv


# =====================================================================================
# SLIDE 5 — THE VISION
# =====================================================================================
def slide5() -> Canvas:
    cv = Canvas(NAVY)
    cv.image(592.4, 0, 380, 540, A("hero_panel.jpg"))
    cv.rect(592.4, 0, 1.1, 540, fill=CYAN, opacity=0.20)

    kicker(cv, MARGIN, 45, S5["kicker"])
    cv.text(392, 45.6, "PRANAGUARD", size=8.4, weight=700, color=MUTED, tracking=0.24, width=160,
            align="right")

    # the closing statement
    cv.text(MARGIN, 96, "Better COPD care begins", size=27, weight=700, color=WHITE, tracking=-0.018)
    cv.text(MARGIN, 96 + 36, "with understanding the changes", size=27, weight=700, color=WHITE,
            tracking=-0.018)
    cv.text(MARGIN, 96 + 72, "happening between consultations.", size=27, weight=700, color=CYAN,
            tracking=-0.018)

    # four-node system diagram (revealed on one click)
    cv.click_group(1)
    ny = 232
    cw, ch, cgap = 132, 66, 19
    x0 = 64.0
    for i, (t, d) in enumerate(S5["nodes"]):
        x = x0 + i * (cw + cgap)
        cv.rect(x, ny, cw, ch, fill=PANEL, line=LINE, lw=0.7, radius=4)
        cv.rect(x, ny, cw, 2.0, fill=CYAN if i in (0, 2) else CYAN_DEEP)
        cv.text(x + 12, ny + 13, f"0{i+1}", size=6.8, weight=700, color=CYAN, tracking=0.1)
        cv.text(x + 12, ny + 25, t, size=8.0, weight=700, color=WHITE, tracking=0.05, max_w=cw - 24,
                min_size=6.6)
        cv.text(x + 12, ny + 38, d, size=7.6, weight=400, color=MUTED, max_w=cw - 24, min_size=6.4)
        if i < 3:
            arrow(cv, x + cw + 4, ny + ch / 2, x + cw + cgap - 4, color="2C6C77", lw=1.0, head=4.0)
    cv.click_group(0)

    # the closing line
    cv.rect(MARGIN, 330, 2.4, 52, fill=CYAN)
    lines = wrap_lines(S5["close"], 13.4, 700, 508)
    yy = 328
    for ln in lines:
        cv.text(MARGIN + 15, yy, ln, size=13.4, weight=700, color=WHITE)
        yy += 18.6
    cv.text(MARGIN + 15, yy + 4, S5["status"], size=8.2, weight=400, color=MUTED, max_w=496,
            min_size=7.0)

    # the closing interaction
    cv.rect(MARGIN, 412, 508, 40, fill=None, line=CYAN_DEEP, lw=0.9, radius=3)
    cv.text(MARGIN + 14, 420, "ASK THE ROOM", size=6.9, weight=700, color=MUTED_DIM, tracking=0.16)
    cv.text(MARGIN + 14, 431, S5["ask"], size=9.6, weight=700, color=CYAN, max_w=480, min_size=8.0)

    # the invitation
    cv.text(MARGIN, 470, S5["invite"], size=15.0, weight=700, color=WHITE, max_w=508, min_size=12.0)
    cv.text(MARGIN, 496, "PranaGuard  \u00b7  Happiest Health Digital Twin Challenge 2026", size=8.4,
            weight=400, color=MUTED_DIM, max_w=508, min_size=7.2)
    return cv
