# -*- coding: utf-8 -*-
"""
Build every PranaGuard jury deliverable from one source of truth.

Outputs (repository root):
  PranaGuard_International_Jury_Presentation.pptx   five slides + 2 appendix, editable, notes
  PranaGuard_International_Jury_Presentation.pdf    same 7 pages, print quality
  PranaGuard_5_Minute_Speaker_Script.docx           full two-presenter script + timings
  PranaGuard_Jury_QA_CheatSheet.pdf                 one-page-per-answer Q&A card
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)

from deck_lib import PdfOut, PptxOut, load_fonts          # noqa: E402
import slides_12, slides_345, appendix_slides             # noqa: E402
import notes, script                                      # noqa: E402
import docs                                               # noqa: E402

PPTX = os.path.join(ROOT, "PranaGuard_International_Jury_Presentation.pptx")
PDF = os.path.join(ROOT, "PranaGuard_International_Jury_Presentation.pdf")
DOCX = os.path.join(ROOT, "PranaGuard_5_Minute_Speaker_Script.docx")
QA = os.path.join(ROOT, "PranaGuard_Jury_QA_CheatSheet.pdf")


def main():
    load_fonts()
    pages = [
        ("slide1", slides_12.slide1, script.notes_text(script.SLIDES[0])),
        ("slide2", slides_12.slide2, script.notes_text(script.SLIDES[1])),
        ("slide3", slides_345.slide3, script.notes_text(script.SLIDES[2])),
        ("slide4", slides_345.slide4, script.notes_text(script.SLIDES[3])),
        ("slide5", slides_345.slide5, script.notes_text(script.SLIDES[4])),
        ("appendix_qa", appendix_slides.appendix_qa, notes.APPENDIX_QA_NOTES),
        ("appendix_refs", appendix_slides.appendix_refs, notes.APPENDIX_REF_NOTES),
    ]

    pdf = PdfOut()
    pptx = PptxOut()
    for name, fn, note in pages:
        cv = fn()
        pdf.page(cv)
        pptx.page(cv, notes=note, title_for_a11y=name)
    pdf.save(PDF)
    pptx.save(PPTX)
    print("wrote", os.path.basename(PDF), os.path.getsize(PDF) // 1024, "KB")
    print("wrote", os.path.basename(PPTX), os.path.getsize(PPTX) // 1024, "KB")

    docs.build_script_docx(DOCX)
    print("wrote", os.path.basename(DOCX), os.path.getsize(DOCX) // 1024, "KB")
    docs.build_qa_pdf(QA)
    print("wrote", os.path.basename(QA), os.path.getsize(QA) // 1024, "KB")


if __name__ == "__main__":
    main()
