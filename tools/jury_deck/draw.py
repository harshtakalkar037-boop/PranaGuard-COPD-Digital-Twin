"""Shared drawing helpers for the PranaGuard jury deck (all vector, no font-glyph gaps)."""
from __future__ import annotations

import math

from deck_lib import CYAN, CYAN_DEEP, MUTED, MUTED_DIM, WHITE, face

MARGIN = 64.0
RIGHT = 896.0


def kicker(cv, x, y, s, color=CYAN, size=9.0, tracking=0.17):
    cv.text(x, y, s.upper(), size=size, weight=700, color=color, tracking=tracking)


def arrow(cv, x1, y, x2, color=MUTED, lw=1.1, head=4.6):
    """Horizontal arrow drawn as vectors (no reliance on font glyph coverage)."""
    cv.line(x1, y, x2 - head * 0.85, y, color=color, lw=lw)
    cv.line(x2 - head, y - head * 0.62, x2, y, color=color, lw=lw)
    cv.line(x2 - head, y + head * 0.62, x2, y, color=color, lw=lw)


def arrow_down(cv, x, y1, y2, color=MUTED, lw=1.1, head=4.2):
    cv.line(x, y1, x, y2 - head * 0.9, color=color, lw=lw)
    cv.line(x - head * 0.6, y2 - head, x, y2, color=color, lw=lw)
    cv.line(x + head * 0.6, y2 - head, x, y2, color=color, lw=lw)


def check(cv, x, y, s, color, lw=1.2):
    cv.line(x, y + s * 0.48, x + s * 0.36, y + s * 0.86, color=color, lw=lw)
    cv.line(x + s * 0.36, y + s * 0.86, x + s, y + s * 0.06, color=color, lw=lw)


def dot(cv, cx, cy, r, color):
    cv.circle(cx, cy, r, fill=color)


def number_badge(cv, cx, cy, r, n, fill, fg, size=None):
    cv.circle(cx, cy, r, fill=fill)
    size = size or r * 1.15
    f = face("Inter", 700)
    w = f.width(str(n), size)
    cv.text(cx - w / 2, cy - f.ascent * size * 0.52, str(n), size=size, weight=700, color=fg)


def rule(cv, x1, y, x2, color, lw=0.8):
    cv.line(x1, y, x2, y, color=color, lw=lw)


def soft_panel(cv, x, y, w, h, fill, line=None, radius=10.0, lw=0.8):
    cv.rect(x, y, w, h, fill=fill, line=line, lw=lw, radius=radius)


def big_number(cv, x, y, s, size, color, weight=700, tracking=-0.02):
    cv.text(x, y, s, size=size, weight=weight, color=color, tracking=tracking)


def stage_row(cv, x, y, n, title, detail, w, 
              num_color=CYAN, title_color=WHITE, detail_color=MUTED,
              title_size=12.5, detail_size=10.5, num_size=8.5):
    """`01  TITLE` over a small detail line. Returns the y of the next row."""
    f = face("Inter", 700)
    cv.text(x, y + 1.2, n, size=num_size, weight=700, color=num_color, tracking=0.1)
    cv.text(x + 24, y, title.upper(), size=title_size, weight=700, color=title_color, tracking=0.055,
            max_w=w - 24)
    cv.text(x + 24, y + 18, detail, size=detail_size, weight=400, color=detail_color, max_w=w - 24)
    return y + 46


def wrap_multi(cv, x, y, s, size, weight, color, max_w, leading=1.42, fam="Inter"):
    """Greedy wrap using real metrics; draws and returns the next y."""
    f = face(fam, weight)
    words = s.split()
    lines, cur = [], ""
    for wd in words:
        t = (cur + " " + wd).strip()
        if f.width(t, size) <= max_w or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    yy = y
    for ln in lines:
        cv.text(x, yy, ln, size=size, weight=weight, color=color, fam=fam)
        yy += size * leading
    return yy


def wrap_lines(s, size, weight, max_w, fam="Inter"):
    f = face(fam, weight)
    words = s.split()
    lines, cur = [], ""
    for wd in words:
        t = (cur + " " + wd).strip()
        if f.width(t, size) <= max_w or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    return lines
