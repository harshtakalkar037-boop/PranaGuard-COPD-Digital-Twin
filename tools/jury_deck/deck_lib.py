"""
deck_lib — one declarative 16:9 layout engine that emits BOTH:
  * a print-quality PDF  (PyMuPDF, Inter embedded)
  * a fully editable PPTX (python-pptx: real text boxes, autoshapes, pictures)

Canvas coordinate system: points, 960 x 540 (== 13.333in x 7.5in == 12192000 x 6858000 EMU).
Everything is drawn from the same element list, so the two outputs are geometrically identical.

Design constraints honoured by construction:
  * every string is an individual, editable text run (no baked-in text in images)
  * text is measured with the real font metrics before it is drawn
  * we only use weights 400 / 700 so PDF and PowerPoint stay visually identical
"""
from __future__ import annotations

import copy
import os
from dataclasses import dataclass, field
from typing import Iterable, Sequence

from fontTools.ttLib import TTFont
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Pt
import pymupdf as fitz

PT_PER_INCH = 72.0
SLIDE_W = 960.0
SLIDE_H = 540.0
EMU_PER_PT = 12700

# ----------------------------------------------------------------------------- palette
NAVY = "061A23"
NAVY_2 = "092330"
PANEL = "0D3140"
PANEL_2 = "113B4B"
LINE = "1D4A5A"
CYAN = "3FE0CF"
CYAN_MID = "2AB9AD"
CYAN_DEEP = "177F79"
WHITE = "F3F8F9"
MUTED = "8FAAB4"
MUTED_DIM = "6C8791"
AMBER = "EFB45F"
INK = "0B2430"
INK_SOFT = "415A64"
LIGHT_BG = "F6F9F9"
LIGHT_PANEL = "EAF2F2"
LIGHT_LINE = "CBDCDD"


def hx(c: str) -> tuple[float, float, float]:
    c = c.lstrip("#")
    return tuple(int(c[i : i + 2], 16) / 255.0 for i in (0, 2, 4))


# ----------------------------------------------------------------------------- fonts
class Face:
    """A single font face with advance widths in em units."""

    def __init__(self, path: str, weight: int):
        self.path = path
        self.weight = weight
        self._tt = TTFont(path)
        self._upem = self._tt["head"].unitsPerEm
        self._hmtx = self._tt["hmtx"]
        self._cmap = self._tt.getBestCmap()
        self._glyph_order = self._tt.getGlyphOrder()
        self.ascent = self._tt["hhea"].ascent / self._upem
        self.descent = abs(self._tt["hhea"].descent) / self._upem
        self.cap_height = 0.727  # measured for Inter; only used for optical tuning

    def advance(self, ch: str) -> float:
        g = self._cmap.get(ord(ch))
        if g is None:
            g = self._cmap.get(ord("?"), ".notdef")
            return 0.6
        try:
            return self._hmtx[g][0] / self._upem
        except KeyError:  # pragma: no cover
            return 0.6

    def width(self, s: str, size: float, tracking_em: float = 0.0) -> float:
        w = sum(self.advance(c) for c in s) * size
        if tracking_em:
            w += tracking_em * size * max(len(s) - 1, 0)
        return w

    def fit_size(self, s: str, max_w: float, size: float, tracking_em: float = 0.0,
                 min_size: float = 6.0) -> float:
        w = self.width(s, size, tracking_em)
        if w <= max_w or w <= 0:
            return size
        return max(min_size, size * max_w / w)


FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
FACES: dict[tuple[str, int], Face] = {}


def load_fonts() -> None:
    global FACES
    for fam, files in {
        "Inter": {400: "Inter-400.ttf", 700: "Inter-700.ttf"},
        "Arial": {400: "Arial-400.ttf", 700: "Arial-700.ttf"},
    }.items():
        for w, fn in files.items():
            p = os.path.join(FONT_DIR, fn)
            if os.path.exists(p):
                FACES[(fam, w)] = Face(p, w)


def face(fam: str, weight: int) -> Face:
    key = (fam, 700 if weight >= 600 else 400)
    if key not in FACES:
        load_fonts()
    return FACES[key]


# ----------------------------------------------------------------------------- elements
@dataclass
class El:
    kind: str
    data: dict = field(default_factory=dict)


class Canvas:
    def __init__(self, bg: str = NAVY):
        self.bg = bg
        self.els: list[El] = []
        self.anim: dict[int, int] = {}   # element index -> click step (1..n)
        self._click = 0

    # -- animation bookkeeping ------------------------------------------------
    def click_group(self, step: int | None = None):
        self._click = step if step is not None else self._click + 1
        return self._click

    def _mark(self, idx: int):
        if self._click:
            self.anim[idx] = self._click

    # -- primitives -----------------------------------------------------------
    def rect(self, x, y, w, h, fill=None, line=None, lw=1.0, radius=0.0, opacity=1.0):
        self.els.append(El("rect", dict(x=x, y=y, w=w, h=h, fill=fill, line=line,
                                        lw=lw, radius=radius, opacity=opacity)))
        self._mark(len(self.els) - 1)
        return self

    def circle(self, cx, cy, r, fill=None, line=None, lw=1.0):
        self.els.append(El("circle", dict(cx=cx, cy=cy, r=r, fill=fill, line=line, lw=lw)))
        self._mark(len(self.els) - 1)
        return self

    def poly(self, pts: Sequence[tuple[float, float]], fill=None, line=None, lw=1.0):
        self.els.append(El("poly", dict(pts=list(pts), fill=fill, line=line, lw=lw)))
        self._mark(len(self.els) - 1)
        return self

    def line(self, x1, y1, x2, y2, color=LINE, lw=1.0, dash=None):
        self.els.append(El("line", dict(x1=x1, y1=y1, x2=x2, y2=y2, color=color, lw=lw, dash=dash)))
        self._mark(len(self.els) - 1)
        return self

    def text(self, x, y, s, size=12, weight=400, color=WHITE, fam="Inter",
             tracking=0.0, align="left", width=None, baseline="top", opacity=1.0,
             max_w=None, min_size=None):
        """y is the top of the em box by default (baseline='top') or the baseline itself."""
        f = face(fam, weight)
        if max_w is not None:
            size = f.fit_size(s, max_w, size, tracking, min_size or size * 0.7)
        w = f.width(s, size, tracking)
        if width is not None and align == "right":
            x = x + width - w
        elif width is not None and align == "center":
            x = x + (width - w) / 2
        top = y if baseline == "top" else y - f.ascent * size
        self.els.append(El("text", dict(x=x, top=top, s=s, size=size, weight=weight, color=color,
                                        fam=fam, tracking=tracking, opacity=opacity, w=w,
                                        ascent=f.ascent, descent=f.descent)))
        self._mark(len(self.els) - 1)
        return self

    def para(self, x, y, lines: Iterable[str], size=12, leading=1.4, weight=400, color=WHITE,
             fam="Inter", tracking=0.0, width=None, opacity=1.0, max_w=None):
        yy = y
        for ln in lines:
            self.text(x, yy, ln, size=size, weight=weight, color=color, fam=fam,
                      tracking=tracking, opacity=opacity, max_w=max_w or width)
            yy += size * leading
        return yy

    def image(self, x, y, w, h, path: str):
        self.els.append(El("image", dict(x=x, y=y, w=w, h=h, path=path)))
        self._mark(len(self.els) - 1)
        return self

    def group(self):
        """Return the index range of elements added since the last call."""
        return len(self.els)


# ----------------------------------------------------------------------------- PDF backend
class PdfOut:
    """PDF renderer. Uses a single fitz.Font per face so the text stream is embedded
    and stays selectable/searchable."""

    def __init__(self):
        self.doc = fitz.open()
        self._fonts: dict[tuple[str, int], fitz.Font] = {}

    def _font(self, fam: str, weight: int) -> fitz.Font:
        key = (fam, 700 if weight >= 600 else 400)
        if key not in self._fonts:
            self._fonts[key] = fitz.Font(fontfile=face(fam, weight).path)
        return self._fonts[key]

    def page(self, cv: Canvas):
        p = self.doc.new_page(width=SLIDE_W, height=SLIDE_H)
        p.draw_rect(fitz.Rect(0, 0, SLIDE_W, SLIDE_H), color=None, fill=hx(cv.bg), width=0)
        for el in cv.els:
            d = el.data
            if el.kind == "rect":
                r = fitz.Rect(d["x"], d["y"], d["x"] + d["w"], d["y"] + d["h"])
                col = hx(d["line"]) if d["line"] else None
                fil = hx(d["fill"]) if d["fill"] else None
                if d["radius"]:
                    p.draw_rect(r, color=col, fill=fil, width=d["lw"] if d["line"] else 0,
                                radius=min(d["radius"] / max(min(d["w"], d["h"]), 1e-6), 0.5),
                                fill_opacity=d["opacity"], stroke_opacity=d["opacity"], lineJoin=1)
                else:
                    p.draw_rect(r, color=col, fill=fil, width=d["lw"] if d["line"] else 0,
                                fill_opacity=d["opacity"], stroke_opacity=d["opacity"])
            elif el.kind == "circle":
                p.draw_circle((d["cx"], d["cy"]), d["r"],
                              color=hx(d["line"]) if d["line"] else None,
                              fill=hx(d["fill"]) if d["fill"] else None,
                              width=d["lw"] if d["line"] else 0)
            elif el.kind == "poly":
                pts = [fitz.Point(*pt) for pt in d["pts"]]
                p.draw_polyline(pts + [pts[0]],
                                color=hx(d["line"]) if d["line"] else None,
                                fill=hx(d["fill"]) if d["fill"] else None,
                                width=d["lw"] if d["line"] else 0, closePath=True)
            elif el.kind == "line":
                pt = fitz.Point
                p.draw_line(pt(d["x1"], d["y1"]), pt(d["x2"], d["y2"]),
                            color=hx(d["color"]), width=d["lw"],
                            dashes=d["dash"] if d["dash"] else None)
            elif el.kind == "text":
                font = self._font(d["fam"], d["weight"])
                base = d["top"] + d["ascent"] * d["size"]
                tw = fitz.TextWriter(p.rect)
                if not d["tracking"]:
                    tw.append((d["x"], base), d["s"], font=font, fontsize=d["size"])
                else:
                    f = face(d["fam"], d["weight"])
                    xx = d["x"]
                    for ch in d["s"]:
                        if ch != " ":
                            tw.append((xx, base), ch, font=font, fontsize=d["size"])
                        xx += f.advance(ch) * d["size"] + d["tracking"] * d["size"]
                tw.write_text(p, color=hx(d["color"]))
            elif el.kind == "image":
                p.insert_image(fitz.Rect(d["x"], d["y"], d["x"] + d["w"], d["y"] + d["h"]),
                               filename=d["path"])
        return p

    def save(self, path: str):
        self.doc.set_metadata({
            "title": "PranaGuard \u2014 International Jury Presentation",
            "author": "PranaGuard \u00b7 Pune Institute of Computer Technology",
            "subject": "COPD digital twin: problem, healthcare gap, approach, impact, vision",
            "keywords": "COPD, digital twin, longitudinal monitoring, PranaGuard, research prototype",
        })
        self.doc.set_toc([[1, "PranaGuard \u2014 Jury Presentation", 1]])
        self.doc.save(path, deflate=True, garbage=4)
        self.doc.close()


# ----------------------------------------------------------------------------- PPTX backend
def _pptx_color(c: str) -> RGBColor:
    return RGBColor.from_string(c.lstrip("#").upper())


class PptxOut:
    def __init__(self):
        self.prs = Presentation()
        self.prs.slide_width = Emu(int(SLIDE_W * EMU_PER_PT))
        self.prs.slide_height = Emu(int(SLIDE_H * EMU_PER_PT))
        self.blank = self.prs.slide_layouts[6]

    def page(self, cv: Canvas, notes: str = "", title_for_a11y: str = ""):
        s = self.prs.slides.add_slide(self.blank)
        # background
        bg = s.background.fill
        bg.solid()
        bg.fore_color.rgb = _pptx_color(cv.bg)
        if title_for_a11y:
            s.shapes.title  # no-op; placeholder absent on blank layout

        shp_ids = []
        # z-order must follow painter order exactly, so the PPTX stacks like the PDF
        for i in range(len(cv.els)):
            el = cv.els[i]
            d = el.data
            shp = self._draw(s, el)
            if shp is not None:
                shp.name = f"{el.kind}_{i}"
                shp_ids.append((i, shp.shape_id))
            else:
                shp_ids.append((i, None))

        self._add_transition(s)
        if cv.anim:
            self._add_timing(s, cv, shp_ids)
        if notes:
            s.notes_slide.notes_text_frame.text = notes
        return s

    def _draw(self, s, el: El):
        d = el.data
        if el.kind == "rect":
            if d["radius"]:
                shp = s.shapes.add_shape(
                    MSO_SHAPE.ROUNDED_RECTANGLE,
                    Emu(int(d["x"] * EMU_PER_PT)), Emu(int(d["y"] * EMU_PER_PT)),
                    Emu(int(d["w"] * EMU_PER_PT)), Emu(int(d["h"] * EMU_PER_PT)))
                try:
                    frac = min(0.5, d["radius"] / max(min(d["w"], d["h"]) / 2, 0.01))
                    shp.adjustments[0] = frac
                except Exception:
                    pass
            else:
                shp = s.shapes.add_shape(
                    MSO_SHAPE.RECTANGLE,
                    Emu(int(d["x"] * EMU_PER_PT)), Emu(int(d["y"] * EMU_PER_PT)),
                    Emu(int(d["w"] * EMU_PER_PT)), Emu(int(d["h"] * EMU_PER_PT)))
            if d["fill"]:
                shp.fill.solid()
                shp.fill.fore_color.rgb = _pptx_color(d["fill"])
            else:
                shp.fill.background()
            if d["line"]:
                shp.line.color.rgb = _pptx_color(d["line"])
                shp.line.width = Pt(d["lw"])
            else:
                shp.line.fill.background()
                shp.line.width = Pt(0)
            shp.shadow.inherit = False
            return shp

        if el.kind == "circle":
            shp = s.shapes.add_shape(
                MSO_SHAPE.OVAL,
                Emu(int((d["cx"] - d["r"]) * EMU_PER_PT)), Emu(int((d["cy"] - d["r"]) * EMU_PER_PT)),
                Emu(int(2 * d["r"] * EMU_PER_PT)), Emu(int(2 * d["r"] * EMU_PER_PT)))
            if d["fill"]:
                shp.fill.solid()
                shp.fill.fore_color.rgb = _pptx_color(d["fill"])
            else:
                shp.fill.background()
            if d["line"]:
                shp.line.color.rgb = _pptx_color(d["line"])
                shp.line.width = Pt(d["lw"])
            else:
                shp.line.fill.background()
            shp.shadow.inherit = False
            return shp

        if el.kind == "poly":
            pts = d["pts"]
            fb = s.shapes.build_freeform(Emu(int(pts[0][0] * EMU_PER_PT)),
                                         Emu(int(pts[0][1] * EMU_PER_PT)), scale=1.0)
            fb.add_line_segments([(Emu(int(x * EMU_PER_PT)), Emu(int(y * EMU_PER_PT)))
                                  for x, y in pts[1:]], close=True)
            shp = fb.convert_to_shape()
            if d["fill"]:
                shp.fill.solid()
                shp.fill.fore_color.rgb = _pptx_color(d["fill"])
            else:
                shp.fill.background()
            if d["line"]:
                shp.line.color.rgb = _pptx_color(d["line"])
                shp.line.width = Pt(d["lw"])
            else:
                shp.line.fill.background()
            shp.shadow.inherit = False
            return shp

        if el.kind == "line":
            from pptx.enum.shapes import MSO_CONNECTOR
            shp = s.shapes.add_connector(
                MSO_CONNECTOR.STRAIGHT,
                Emu(int(d["x1"] * EMU_PER_PT)), Emu(int(d["y1"] * EMU_PER_PT)),
                Emu(int(d["x2"] * EMU_PER_PT)), Emu(int(d["y2"] * EMU_PER_PT)))
            shp.line.color.rgb = _pptx_color(d["color"])
            shp.line.width = Pt(d["lw"])
            if d["dash"]:
                from pptx.enum.dml import MSO_LINE_DASH_STYLE
                shp.line.dash_style = MSO_LINE_DASH_STYLE.DASH
            return shp

        if el.kind == "text":
            f = face(d["fam"], d["weight"])
            # The PDF sets Inter; the PPTX uses Arial so it opens and edits identically on any
            # machine. Arial is ~2-3% narrower, so the point size is compensated by measured
            # advance widths to keep the two renderings visually identical.
            fa = face("Arial", d["weight"])
            scale = (f.width(d["s"], 100.0) / fa.width(d["s"], 100.0)) if d["s"].strip() else 1.0
            psize = d["size"] * max(0.9, min(scale, 1.12))
            # the run box is sized from the authored string so the PPTX/PDR geometry agree
            wpt = max(f.width(d["s"], d["size"]) + 6, 8)
            hpt = (f.ascent + f.descent) * d["size"] * 1.02
            tb = s.shapes.add_textbox(Emu(int(d["x"] * EMU_PER_PT)), Emu(int(d["top"] * EMU_PER_PT)),
                                      Emu(int(wpt * EMU_PER_PT)), Emu(int(hpt * EMU_PER_PT)))
            tf = tb.text_frame
            tf.word_wrap = False
            tf.margin_left = 0
            tf.margin_right = 0
            tf.margin_top = 0
            tf.margin_bottom = 0
            tf.vertical_anchor = MSO_ANCHOR.TOP
            p = tf.paragraphs[0]
            p.alignment = PP_ALIGN.LEFT
            p.line_spacing = 1.0
            r = p.add_run()
            r.text = d["s"]
            r.font.size = Pt(round(psize * 2) / 2)
            r.font.bold = d["weight"] >= 600
            r.font.name = "Arial"
            r.font.color.rgb = _pptx_color(d["color"])
            rPr = r._r.get_or_add_rPr()
            if d["tracking"]:
                rPr.set("spc", str(int(round(d["tracking"] * psize * 100))))
            if d["opacity"] < 1.0:
                from pptx.oxml.ns import qn
                solid = rPr.find(qn("a:solidFill"))
                if solid is not None:
                    clr = solid[0]
                    alpha = clr.makeelement(qn("a:alpha"), {"val": str(int(d["opacity"] * 100000))})
                    clr.append(alpha)
            # keep the box from being auto-resized by PowerPoint on edit
            bodyPr = tf._txBody.find(
                "{http://schemas.openxmlformats.org/drawingml/2006/main}bodyPr")
            for tag in ("a:normAutofit", "a:spAutoFit"):
                e = bodyPr.find("{http://schemas.openxmlformats.org/drawingml/2006/main}" + tag[2:])
                if e is not None:
                    bodyPr.remove(e)
            bodyPr.append(bodyPr.makeelement(
                "{http://schemas.openxmlformats.org/drawingml/2006/main}noAutofit", {}))
            return tb

        if el.kind == "image":
            return s.shapes.add_picture(d["path"], Emu(int(d["x"] * EMU_PER_PT)),
                                        Emu(int(d["y"] * EMU_PER_PT)),
                                        Emu(int(d["w"] * EMU_PER_PT)),
                                        Emu(int(d["h"] * EMU_PER_PT)))
        return None

    # -- animation / transition XML ------------------------------------------
    def _add_timing(self, slide, cv: Canvas, shp_ids):
        """Click-to-reveal fade entrances, in the exact shape PowerPoint writes them."""
        from lxml.builder import ElementMaker

        P = "http://schemas.openxmlformats.org/presentationml/2006/main"
        E = ElementMaker(namespace=P, nsmap={"p": P})

        id_of = {idx: sid for idx, sid in shp_ids if sid}
        steps: dict[int, list[int]] = {}
        for idx, step in cv.anim.items():
            sid = id_of.get(idx)
            if sid:
                steps.setdefault(step, []).append(sid)
        if not steps:
            return

        nid = [2]

        def nxt():
            nid[0] += 1
            return str(nid[0])

        def effect(sid, node_type):
            ctn = E.cTn(id=nxt(), presetID="10", presetClass="entr", presetSubtype="0",
                        fill="hold", grpId="0", nodeType=node_type)
            ctn.append(E.stCondLst(E.cond(delay="0")))
            child = E.childTnLst()

            st = E.set()
            cb = E.cBhvr()
            cb.append(E.cTn(id=nxt(), dur="1", fill="hold"))
            cb.append(E.tgtEl(E.spTgt(spid=str(sid))))
            cb.append(E.attrNameLst(E.attrName("style.visibility")))
            st.append(cb)
            st.append(E.to(E.strVal(val="visible")))
            child.append(st)

            ae = E.animEffect(transition="in", filter="fade")
            ab = E.cBhvr()
            ab.append(E.cTn(id=nxt(), dur="500"))
            ab.append(E.tgtEl(E.spTgt(spid=str(sid))))
            ae.append(ab)
            child.append(ae)

            ctn.append(child)
            return E.par(ctn)

        main = E.cTn(id="2", dur="indefinite", nodeType="mainSeq")
        main_child = E.childTnLst()
        for step in sorted(steps):
            outer = E.cTn(id=nxt(), fill="hold")
            outer.append(E.stCondLst(E.cond(delay="indefinite")))
            mid_child = E.childTnLst()
            mid = E.cTn(id=nxt(), fill="hold")
            mid.append(E.stCondLst(E.cond(delay="0")))
            fx_child = E.childTnLst()
            for j, sid in enumerate(steps[step]):
                fx_child.append(effect(sid, "clickEffect" if j == 0 else "withEffect"))
            mid.append(fx_child)
            mid_child.append(E.par(mid))
            outer.append(mid_child)
            main_child.append(E.par(outer))
        main.append(main_child)

        def click_cond(evt):
            c = E.cond(evt=evt, delay="0")
            c.append(E.tgtEl(E.sldTgt()))
            return c

        seq = E.seq(concurrent="1", nextAc="seek")
        seq.append(main)
        seq.append(E.prevCondLst(click_cond("onPrev")))
        seq.append(E.nextCondLst(click_cond("onNext")))

        root_ctn = E.cTn(id="1", dur="indefinite", restart="never", nodeType="tmRoot")
        root_ctn.append(E.childTnLst(seq))
        slide._element.append(E.timing(E.tnLst(E.par(root_ctn))))

    def _add_transition(self, slide):
        from lxml.builder import ElementMaker
        P = "http://schemas.openxmlformats.org/presentationml/2006/main"
        E = ElementMaker(namespace=P, nsmap={"p": P})
        tr = E.transition(E.fade())
        tr.set("spd", "med")
        slide._element.append(tr)

    def save(self, path: str):
        self.prs.core_properties.title = "PranaGuard — International Jury Presentation"
        self.prs.core_properties.author = "PranaGuard · Pune Institute of Computer Technology"
        self.prs.core_properties.subject = "COPD digital twin: problem, gap, approach, impact, vision"
        self.prs.core_properties.keywords = "COPD; digital twin; longitudinal monitoring; research prototype"
        self.prs.core_properties.comments = (
            "Research prototype. Synthetic data only. Not a medical device and not clinically validated.")
        self.prs.save(path)

