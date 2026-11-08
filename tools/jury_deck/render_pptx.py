# -*- coding: utf-8 -*-
"""Rasterise the PPTX from its own stored geometry, using Arial metrics.

This is an independent check: it reads only what PowerPoint would read (shape positions,
point sizes, runs, picture parts) and re-draws it. If this render looks right and matches the
PDF, the PPTX will look right in PowerPoint.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pymupdf as fitz
from pptx import Presentation
from pptx.util import Emu
from deck_lib import face, load_fonts, hx

EMU = 12700.0

def color_of(run, shape):
    try:
        if run.font.color and run.font.color.rgb is not None:
            return hx(str(run.font.color.rgb))
    except Exception:
        pass
    return (0, 0, 0)

def main(path, out_prefix, dpi=120):
    load_fonts()
    prs = Presentation(path)
    W = prs.slide_width / EMU
    H = prs.slide_height / EMU
    doc = fitz.open()
    for n, slide in enumerate(prs.slides, 1):
        page = doc.new_page(width=W, height=H)
        try:
            bg = slide.background.fill
            page.draw_rect(fitz.Rect(0, 0, W, H), color=None, fill=hx(str(bg.fore_color.rgb)), width=0)
        except Exception:
            page.draw_rect(fitz.Rect(0, 0, W, H), color=None, fill=(1,1,1), width=0)
        for sh in slide.shapes:
            if sh.shape_type == 13 or sh.__class__.__name__ == "Picture":
                try:
                    page.insert_image(fitz.Rect(sh.left/EMU, sh.top/EMU,
                                                (sh.left+sh.width)/EMU, (sh.top+sh.height)/EMU),
                                      stream=sh.image.blob)
                except Exception as e:
                    print("img fail", e)
                continue
            if sh.shape_type == 6:  # group
                continue
            # fills / strokes for autoshapes
            is_textbox = sh.shape_type == 17
            if (not is_textbox) and (sh.shape_type in (1, 9, 3, 5) or
                                     sh.__class__.__name__ in ("Shape", "Connector")):
                try:
                    r = fitz.Rect(sh.left/EMU, sh.top/EMU, (sh.left+sh.width)/EMU, (sh.top+sh.height)/EMU)
                    fill = None
                    try:
                        if sh.fill.type is not None and str(sh.fill.type) != "MSO_FILL_TYPE.BACKGROUND (5)":
                            fill = hx(str(sh.fill.fore_color.rgb))
                    except Exception:
                        fill = None
                    col = None
                    lw = 0
                    try:
                        if sh.line.color and sh.line.color.rgb is not None and sh.line.width:
                            col = hx(str(sh.line.color.rgb)); lw = sh.line.width.pt
                    except Exception:
                        pass
                    if sh.__class__.__name__ == "Connector":
                        page.draw_line((r.x0, r.y0), (r.x1, r.y1), color=col or (0,0,0), width=lw or 1)
                    elif sh.shape_type == 9:
                        page.draw_rect(r, color=col, fill=fill, width=lw,
                                       radius=min(0.5, (sh.adjustments[0] if len(sh.adjustments) else 0.0)))
                    elif sh.shape_type == 5:  # OVAL
                        page.draw_oval(r, color=col, fill=fill, width=lw)
                    elif False:
                        page.draw_rect(r, color=col, fill=fill, width=lw,
                                       radius=min(0.5, (sh.adjustments[0] if len(sh.adjustments) else 0.0)))
                    else:
                        page.draw_rect(r, color=col, fill=fill, width=lw)
                except Exception as e:
                    pass
            if not sh.has_text_frame:
                continue
            txt = sh.text_frame.text
            if not txt.strip():
                continue
            run = sh.text_frame.paragraphs[0].runs[0]
            size = run.font.size.pt if run.font.size else 12
            f = face("Arial", 700 if run.font.bold else 400)
            col = color_of(run, sh)
            x = sh.left/EMU
            base = sh.top/EMU + f.ascent * size
            tw = fitz.TextWriter(page.rect)
            tw.append((x, base), txt, font=fitz.Font(fontfile=f.path), fontsize=size)
            tw.write_text(page, color=col)
        pix = page.get_pixmap(dpi=dpi)
        pix.save(f"{out_prefix}_{n}.png")
    print("rendered", len(prs.slides), "slides")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
