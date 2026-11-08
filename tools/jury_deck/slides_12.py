# -*- coding: utf-8 -*-
"""Slide 1 and Slide 2 — Presenter 1 (human problem, healthcare gap)."""
from __future__ import annotations

import os

from deck_lib import (AMBER, CYAN, CYAN_DEEP, CYAN_MID, LIGHT_BG, LIGHT_PANEL, LIGHT_LINE,
                      LINE, MUTED, MUTED_DIM, NAVY, NAVY_2, PANEL, PANEL_2, WHITE, Canvas,
                      face)
from draw import (MARGIN, RIGHT, arrow, arrow_down, check, kicker, number_badge, rule,
                  soft_panel, wrap_multi, wrap_lines)
from content import S1, S2

HERE = os.path.dirname(os.path.abspath(__file__))
A = lambda n: os.path.join(HERE, "assets", n)


# =====================================================================================
# SLIDE 1 — THE HUMAN PROBLEM
# =====================================================================================
def slide1() -> Canvas:
    cv = Canvas(NAVY)
    # ---- photo panel (right) -------------------------------------------------------
    cv.image(592.4, 0, 380, 540, A("hero_panel.jpg"))
    cv.rect(592.4, 0, 1.1, 540, fill=CYAN, opacity=0.28)

    # ---- header --------------------------------------------------------------------
    kicker(cv, MARGIN, 45, S1["kicker"])
    cv.text(392, 45.6, "PRANAGUARD", size=8.4, weight=700, color=MUTED, tracking=0.24, width=160,
            align="right")

    # ---- headline ------------------------------------------------------------------
    y = 90
    for i, ln in enumerate(S1["headline"]):
        col = WHITE if i < 3 else CYAN
        cv.text(MARGIN, y, ln, size=26.5, weight=700, color=col, tracking=-0.014)
        y += 33.5
    y += 10

    # ---- lead ----------------------------------------------------------------------
    for ln in S1["lead"]:
        cv.text(MARGIN, y, ln, size=13.2, weight=400, color=MUTED)
        y += 20.0

    # ---- the three-step contrast ---------------------------------------------------
    y = 316
    cv.text(MARGIN, y - 25, "THE PATH FROM A BAD DAY TO A HOSPITAL VISIT", size=8.3, weight=700,
            color=MUTED_DIM, tracking=0.19)
    box_w, gap = 146, 25
    for i, (title, detail) in enumerate(S1["steps"]):
        x = MARGIN + i * (box_w + gap)
        cv.rect(x, y, box_w, 98, fill=PANEL, line=LINE, lw=0.7, radius=6)
        number_badge(cv, x + 21, y + 21, 10.2, f"0{i+1}", CYAN, NAVY, size=7.4)
        cv.text(x + 36, y + 15, title.upper(), size=8.1, weight=700, color=WHITE, tracking=0.045,
                max_w=box_w - 44, min_size=6.6)
        wrap_multi(cv, x + 15, y + 40, detail, 9.4, 400, MUTED, box_w - 30, leading=1.45)
        if i < 2:
            arrow(cv, x + box_w + 6, y + 46, x + box_w + gap - 7, color=CYAN_DEEP, lw=1.0, head=4.0)
    cv.rect(MARGIN + 2 * (box_w + gap), y, box_w, 98, fill=None, line=CYAN_DEEP, lw=0.9, radius=6)

    # ---- the one statistic ---------------------------------------------------------
    y = 444
    rule(cv, MARGIN, y - 18, 512, LINE, lw=0.8)
    cv.text(MARGIN, y + 2, S1["fact_num"], size=40, weight=700, color=CYAN, tracking=-0.025)
    tw = face("Inter", 700).width(S1["fact_num"], 40, -0.025)
    cv.text(MARGIN + tw + 15, y - 3, "LEADING CAUSE OF DEATH", size=8.0, weight=700,
            color=MUTED, tracking=0.16)
    cv.text(MARGIN + tw + 15, y + 12, "WORLDWIDE", size=8.0, weight=700, color=MUTED, tracking=0.16)
    wrap_multi(cv, MARGIN + 232, y + 2, S1["fact_detail"], 10.2, 400, MUTED, 272, leading=1.5)

    # ---- citations -----------------------------------------------------------------
    cv.text(MARGIN, 512, S1["cite"], size=7.6, weight=400, color=MUTED_DIM)
    cv.text(392, 512, "ILLUSTRATIVE PHOTOGRAPH  \u00b7  SYNTHETIC PATIENT DATA ONLY", size=7.0,
            weight=700, color=MUTED_DIM, tracking=0.10, width=160, align="right")
    return cv


# =====================================================================================
# SLIDE 2 — THE HEALTHCARE GAP
# =====================================================================================
def slide2() -> Canvas:
    cv = Canvas(LIGHT_BG)
    cv.rect(0, 0, 312, 540, fill=NAVY)

    # ---------------- left column (dark) ------------------------------------------
    L = 44
    kicker(cv, L, 45, S2["kicker"])
    y = 88
    cv.text(L, y, "Care is built from", size=21, weight=700, color=WHITE, tracking=-0.012)
    cv.text(L, y + 28.5, "snapshots.", size=21, weight=700, color=WHITE, tracking=-0.012)
    cv.text(L, y + 57, "COPD is not a", size=21, weight=700, color=CYAN, tracking=-0.012)
    cv.text(L, y + 85.5, "snapshot disease.", size=21, weight=700, color=CYAN, tracking=-0.012)

    # the 68% statistic
    sy = 232
    cv.text(L, sy, S2["gap_num"], size=56, weight=700, color=CYAN, tracking=-0.03)
    nw = face("Inter", 700).width(S2["gap_num"], 56, -0.03)
    cv.text(L + nw + 12, sy + 12, "OF EXACERBATIONS", size=8.0, weight=700, color=WHITE, tracking=0.13,
            max_w=120, min_size=6.6)
    cv.text(L + nw + 12, sy + 24, "GO UNREPORTED", size=8.0, weight=700, color=WHITE, tracking=0.13,
            max_w=120, min_size=6.6)
    ny = wrap_multi(cv, L, sy + 64, S2["gap_text"], 9.7, 400, MUTED, 228, leading=1.5)
    cv.text(L, ny + 1, S2["gap_cite"], size=7.6, weight=700, color=MUTED_DIM, tracking=0.03)

    # the 90-day timeline
    ty = 388
    rule(cv, L, ty - 16, L + 228, LINE, lw=0.9)
    cv.text(L, ty, S2["timeline_title"], size=8.0, weight=700, color=CYAN, tracking=0.14)
    bar = ty + 46
    cv.line(L, bar, L + 228, bar, color=LINE, lw=1.6)
    for frac in (0.25, 0.5, 0.75):
        cv.circle(L + 228 * frac, bar, 1.1, fill=MUTED_DIM)
    for xx in (L, L + 228):
        cv.circle(xx, bar, 4.2, fill=CYAN)
        cv.circle(xx, bar, 8.6, line=CYAN, lw=0.7)
    cv.text(L, bar + 13, S2["timeline_left"], size=8.0, weight=700, color=WHITE, tracking=0.06)
    cv.text(L, bar + 13, S2["timeline_right"], size=8.0, weight=700, color=WHITE, tracking=0.06,
            width=228, align="right")
    wrap_multi(cv, L, bar + 30, S2["timeline_note"], 9.4, 400, MUTED, 228, leading=1.5)
    cv.text(L, bar + 62, S2["timeline_basis"], size=6.8, weight=400, color=MUTED_DIM, max_w=228,
            min_size=5.8)

    # ---------------- right column (light) ------------------------------------------
    X = 352
    W = 528
    cv.text(X, 45, "THREE POINTS ON THE PATH WHERE THE PICTURE BREAKS DOWN", size=8.0, weight=700,
            color=CYAN_DEEP, tracking=0.15, max_w=W, min_size=6.8)

    y = 70
    for n, t, d in S2["breaks"]:
        cv.rect(X, y, W, 66, fill="FFFFFF", line=LIGHT_LINE, lw=0.7, radius=3)
        cv.rect(X, y, 3, 66, fill=CYAN_MID)
        cv.text(X + 18, y + 13, n, size=8.2, weight=700, color=CYAN_DEEP, tracking=0.1)
        cv.text(X + 44, y + 11.5, t, size=10.4, weight=700, color=NAVY, tracking=0.05, max_w=W - 62)
        cv.text(X + 44, y + 29, d, size=9.5, weight=400, color="4A6570", max_w=W - 62, min_size=8.2)
        y += 74

    # ---- single measurement vs longitudinal understanding --------------------------
    cy = 306
    cv.text(X, cy, "A SNAPSHOT IS NOT A TRAJECTORY", size=8.0, weight=700, color=CYAN_DEEP,
            tracking=0.14)
    cv.text(X, cy + 16, S2["compare_body"], size=9.6, weight=400, color="3E5A66", max_w=W,
            min_size=8.4)

    dy = cy + 56
    cw, cgap = 250, 12
    for i, (t, d) in enumerate(S2["defs"]):
        bx = X + i * (cw + cgap) + (W - (2 * cw + cgap)) / 2
        fill = LIGHT_PANEL if i == 0 else NAVY
        fg_t = NAVY if i == 0 else CYAN
        fg_d = "3E5A66" if i == 0 else MUTED
        cv.rect(bx, dy, cw, 66, fill=fill, line=LIGHT_LINE if i == 0 else None, lw=0.7, radius=3)
        cv.text(bx + 13, dy + 10, t, size=7.7, weight=700, color=fg_t, tracking=0.1,
                max_w=cw - 26, min_size=6.2)
        wrap_multi(cv, bx + 13, dy + 27, d, 9.2, 400, fg_d, cw - 26, leading=1.45)

    # ---- bottom callout --------------------------------------------------------------
    by = 442
    cv.rect(X, by, W, 52, fill=None, line=CYAN_MID, lw=1.0, radius=3)
    cv.text(X + 14, by + 9, "THE RISKIEST PATIENTS CAN LOOK ORDINARY", size=8.0, weight=700,
            color=CYAN_DEEP, tracking=0.12)
    cv.text(X + 14, by + 26, S2["worst_src"], size=8.7, weight=400, color="3E5A66", max_w=W - 28,
            min_size=7.5)

    cv.text(X, 508, S2["cite"], size=7.2, weight=400, color=MUTED_DIM, max_w=W, min_size=6.4)
    return cv
