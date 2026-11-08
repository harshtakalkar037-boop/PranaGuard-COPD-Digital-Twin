# -*- coding: utf-8 -*-
"""
THE canonical speaking script. Single source of truth for
  * the PPTX speaker notes
  * PranaGuard_5_Minute_Speaker_Script.docx

Word budget is deliberate: ~760 spoken words. At a conversational 150-160 words per minute
that is 4:45-5:05 of speech, leaving the rest of the five-to-seven minute window for pauses,
two clicks and one handover.
"""

INTRO = {
    "title": "INTRODUCTION  \u00b7  BEFORE YOU WALK ON",
    "window": "0:00",
    "main": "Two presenters, five slides, five minutes. Presenter 1 owns slides 1\u20132 (1:40). "
            "Presenter 2 owns slides 3\u20135 (3:20).",
    "blocks": [
        ("h", "Before you begin"),
        ("b", "Say the handover sentence out loud together, twice."),
        ("b", "Agree who answers what: Presenter 1 takes COPD and clinical context; Presenter 2 takes "
              "product, model and evaluation."),
        ("b", "Open the PPTX, not the PDF, so the three click-reveals work. Keep the PDF open in a second "
              "window as a fallback."),
        ("b", "Test the clicker once. Nothing in this deck needs an internet connection."),
        ("b", "The one thing that must land in the first two minutes: the problem, and the intervention "
              "proposed to address it."),
    ],
}

SLIDES = [
    {
        "n": 1,
        "title": "THE HUMAN PROBLEM",
        "presenter": "PRESENTER 1",
        "window": "0:00 \u2013 0:35",
        "main": "COPD deterioration happens between appointments, not inside them.",
        "blocks": [
            ("h", "Script  \u00b7  35 seconds  \u00b7  stand centre stage, not behind the laptop"),
            ("q", "Before we show you anything we built, picture one person."),
            ("q", "This is someone's father. He has COPD. On a good day he can breathe. On a bad day he "
                  "cannot walk to the window."),
            ("q", "What happens when a patient's breathing begins to deteriorate \u2014 but the change is not "
                  "recognised early enough?"),
            ("q", "The pattern is almost always the same. Everyday breathing at home. Symptoms the patient "
                  "feels but rarely writes down. Then a healthcare intervention."),
            ("q", "COPD is the third leading cause of death worldwide \u2014 3.4 million deaths in 2023. But "
                  "rarity isn't our point. Visibility is."),
            ("h", "Interaction  \u00b7  optional, 10 seconds"),
            ("p", "\u201cQuick show of hands \u2014 who here has a relative who was told their lungs were fine "
                  "when they didn't feel fine?\u201d Accept two seconds of hands. \u201cThat gap between what a "
                  "person feels and what a system records is the space we work in.\u201d Do not wait for stories."),
            ("h", "Transition"),
            ("q", "To understand why that gap exists, look at how COPD care is actually assembled."),
        ],
        "sources": [
            "Third leading cause of death worldwide; 3.4 million deaths in 2023 (\u22486% of global deaths); "
            "COPD is not curable \u2014 WHO COPD fact sheet, 10 June 2026.",
            "The photograph is an illustrative image, labelled as such on the slide. Never imply he is a "
            "real PranaGuard patient.",
        ],
    },
    {
        "n": 2,
        "title": "THE HEALTHCARE GAP",
        "presenter": "PRESENTER 1",
        "window": "0:35 \u2013 1:40",
        "main": "COPD care is built from snapshots. COPD is a disease of trajectory.",
        "blocks": [
            ("h", "Script  \u00b7  65 seconds"),
            ("q", "Think about how COPD care is recorded. A consultation, a spirometry value, a prescription "
                  "\u2014 notes in one system, a letter in another, the patient's memory holding the rest."),
            ("q", "Three things break. Information is fragmented. Daily experience is rarely captured \u2014 "
                  "GOLD tells us these symptoms are under-reported, and a primary-care study found "
                  "clinicians do not routinely ask about breathlessness. And change is hard to see when "
                  "every contact is a snapshot."),
            ("q", "Here is the number that should worry us. In one longitudinal cohort, 68 percent of the "
                  "exacerbations patients recorded in their own diaries were never reported to a clinician. "
                  "Two out of three. Not because they were mild \u2014 they looked like the reported ones. They "
                  "simply never reached the record."),
            ("q", "And this matters clinically: the best single predictor of future exacerbations is the "
                  "history of past ones. Risk lives in history — a snapshot carries none."),
            ("q", "A single measurement isn't useless. It is a measurement of a moment. Longitudinal "
                  "understanding is what shows direction."),
            ("h", "Interaction  \u00b7  15 seconds"),
            ("p", "\u201cIf a COPD patient feels worse between two hospital visits, how much of that change is "
                  "visible to the clinician?\u201d Pause three seconds. If nobody answers: \u201cUsually very "
                  "little \u2014 and that is not a criticism of any clinician. It is a property of the record we "
                  "give them.\u201d"),
            ("h", "Handover  \u00b7  1:40  \u00b7  hand over the clicker on this sentence"),
            ("q", "My colleague will now show you what we built for that."),
        ],
        "sources": [
            "Symptoms may be under-reported by patients \u2014 GOLD 2026 report.",
            "Breathlessness normalised and under-reported; clinicians do not routinely ask about it \u2014 "
            "Elliott-Button et al., npj Primary Care Respiratory Medicine 2024;34:37.",
            "68% unreported (327 of 486 diary-recorded exacerbations) \u2014 Langsetmo L, Platt RW, Ernst P, "
            "Bourbeau J. Am J Respir Crit Care Med 2008;177:396-401.",
            "History of exacerbations is the best single predictor of future events across GOLD stages \u2014 "
            "Hurst JR et al., N Engl J Med 2010;363:1128-38; restated in GOLD 2026.",
            "The 90-day timeline on the slide is a labelled schematic, not a measured statistic.",
        ],
    },
    {
        "n": 3,
        "title": "THE PRANAQUARD APPROACH",
        "presenter": "PRESENTER 2",
        "window": "1:40 \u2013 2:50",
        "main": "One longitudinal, replayable record \u2014 with every model output labelled as research.",
        "blocks": [
            ("h", "Script  \u00b7  70 seconds  \u00b7  three clicks, one per stage group"),
            ("p", "Click 1 \u2014 stages 01 and 02 appear:"),
            ("q", "The first thing we built is a record that behaves like a story, not a filing cabinet. "
                  "Observations go in: daily wellbeing, breathlessness, sputum, adherence, physiology. They "
                  "become a longitudinal record where every hour is a versioned, replayable state."),
            ("p", "Click 2 \u2014 stages 03 and 04:"),
            ("q", "We establish a personal baseline: the first 72 observed hours become this person's own "
                  "reference, not a population average. Then research-model insights \u2014 experimental 24, 48 "
                  "and 72-hour estimates, each carrying its model version, completeness and limitations."),
            ("p", "Click 3 \u2014 stage 05:"),
            ("q", "And the most important decision in the system: a clinician reviews. The model never signs "
                  "anything."),
            ("q", "This is the actual interface \u2014 synthetic patient PG-0071. Baseline against current values. "
                  "Body-signal trend. Three research cards, each labelled an experimental estimate on "
                  "synthetic data."),
            ("q", "That labelling isn't decoration. Our 72-hour model had an AUROC of 0.395 \u2014 below chance. "
                  "We published that, and the interface repeats it, because a system that hides its weak "
                  "parts cannot be trusted with its strong ones."),
            ("h", "Transition"),
            ("q", "So that is the mechanism. The question that matters is: what could this change?"),
        ],
        "sources": [
            "Every hour persisted as a versioned, replayable state; personal baseline = median of the first "
            "72 observed hours \u2014 docs/METHODOLOGY.md, docs/ARCHITECTURE.md.",
            "\u201cExperimental estimate on synthetic data\u201d labels are visible in the product screenshot \u2014 "
            "docs/model-v3/verification/screenshots/desktop-patient.png.",
            "72-hour AUROC 0.3951 (below chance), AUPRC 0.0593 (below prevalence 0.0773) \u2014 "
            "artifacts/evaluation.md, docs/MODEL_CARD.md.",
            "If the clicker fails, use the PDF: it shows the complete flow. Keep talking.",
        ],
    },
    {
        "n": 4,
        "title": "HEALTHCARE IMPACT",
        "presenter": "PRESENTER 2",
        "window": "2:50 \u2013 4:20",
        "main": "Potential value at three levels \u2014 with a hard line between what is claimed and what has been measured.",
        "blocks": [
            ("h", "Script  \u00b7  90 seconds"),
            ("q", "This is the slide we ask you to judge us on."),
            ("q", "For the patient: visibility of changing patterns, a structured way to record daily "
                  "experience, one continuous record, better-informed conversations with the care team."),
            ("q", "For the clinician: consolidated longitudinal information, change measured against the "
                  "patient's own baseline, patient-reported information actually gathered and reviewed, and "
                  "research insight offered as context \u2014 never as a verdict."),
            ("q", "For the health system: a more structured model for monitoring, a research platform for "
                  "exacerbation patterns, a foundation for evidence-based workflows."),
            ("q", "The pathway is deliberately modest. Observations become structured information, which "
                  "becomes clinician visibility, which supports informed assessment. What we aim at is "
                  "continuity of care."),
            ("q", "Now the honest part. What exists today: a working end-to-end prototype, audited and "
                  "reproducible; model experiments on 120 synthetic patients; public modelled environmental "
                  "context. What does not exist: any measured reduction in hospitalisations, exacerbations "
                  "or mortality. Our 72-hour model performed poorly, and we report it as poor."),
            ("q", "Next: clinician-supervised evaluation, prospective research, and measurement of real "
                  "outcomes."),
            ("q", "We would rather present a small, honest result than a large, unreliable one."),
            ("h", "Transition"),
            ("q", "Which brings us to why we think this is worth the next few years of work."),
        ],
        "sources": [
            "Prototype status: implemented, tested, audited, reproducible \u2014 README \u00a75, DELIVERY_REPORT.md.",
            "120-patient synthetic cohort \u2014 docs/DATA_PROVENANCE.md.",
            "Weak 72-hour performance reported openly \u2014 docs/MODEL_CARD.md, artifacts/evaluation.md.",
            "No demonstrated reduction in hospitalisations, exacerbations or mortality \u2014 docs/LIMITATIONS.md.",
            "Say the word \u201cpotential\u201d at least twice on this slide. If time is short, compress the three "
            "impact columns to one sentence each \u2014 never cut the \u201cnot yet demonstrated\u201d sentence.",
        ],
    },
    {
        "n": 5,
        "title": "THE VISION AND CLOSING",
        "presenter": "PRESENTER 2",
        "window": "4:20 \u2013 5:00",
        "main": "Understanding change between consultations is the entire thesis.",
        "blocks": [
            ("h", "Script  \u00b7  40 seconds"),
            ("q", "Let me leave you with the sentence we started from. Better COPD care begins with "
                  "understanding the changes happening between consultations."),
            ("q", "Four things have to exist: a patient whose daily experience is captured; longitudinal data "
                  "that keeps history instead of overwriting it; a clinician who can review and judge; and "
                  "research insights that are honest about what they are."),
            ("p", "Click \u2014 the four nodes appear."),
            ("q", "PranaGuard is one attempt to put those four in the same room. Today it is a working "
                  "research prototype on synthetic data. The clinical value is a hypothesis we have not yet "
                  "tested in patients."),
            ("p", "Pause. Then the closing question, slowly."),
            ("q", "What if the changes between consultations were easier to understand?"),
            ("q", "Thank you \u2014 we welcome your questions."),
            ("p", "Stop talking. Let two seconds of silence pass before anyone moves."),
        ],
        "sources": [
            "\u201cWorking research prototype on synthetic data\u201d is the project's own disclosed status \u2014 "
            "README caution block, docs/LIMITATIONS.md.",
            "This slide must never be amended to imply the vision has been clinically achieved.",
        ],
    },
]

QA = [
    ("WHAT IS COPD?",
     "A common, preventable and treatable disease with persistent respiratory symptoms and airflow "
     "limitation. Breathlessness, cough and sputum are typical. It is not curable, but it is treatable.",
     "WHO COPD fact sheet, 10 June 2026; GOLD 2026 report."),
    ("WHAT IS AN EXACERBATION?",
     "An acute worsening of respiratory symptoms that leads to additional therapy \u2014 from extra "
     "bronchodilators at home up to hospitalisation. Exacerbations drive health status, admissions and "
     "disease progression.",
     "GOLD 2026 report."),
    ("WHY IS LONGITUDINAL MONITORING USEFUL?",
     "A single value is a moment. Repeated records against a personal baseline begin to show direction of "
     "change \u2014 and the strongest known predictor of future exacerbations is the history of past ones.",
     "Hurst JR et al., N Engl J Med 2010;363:1128-38."),
    ("WHAT IS THE DIGITAL TWIN IN PRANAQUARD?",
     "A versioned, replayable state per patient: observations, a personal baseline from the first 72 "
     "observed hours, derived features, and the model context attached to each saved state. It is "
     "data-driven, not a mechanistic lung model.",
     "PranaGuard docs/METHODOLOGY.md, docs/ARCHITECTURE.md."),
    ("WHAT DOES THE MODEL ACTUALLY PREDICT?",
     "An experimental estimate of a new synthetic exacerbation onset within 24, 48 or 72 hours on the "
     "research cohort. On held-out synthetic data the 72-hour model reached AUROC 0.395 and AUPRC 0.059 "
     "\u2014 below chance and below prevalence. Reported as weak and non-clinical.",
     "artifacts/evaluation.md; docs/MODEL_CARD.md."),
    ("WHAT DATA IS REAL AND WHAT IS SYNTHETIC?",
     "Every patient, physiological stream and outcome label is synthetic \u2014 120 generated patients. The "
     "only real inputs are public modelled city air-quality and weather data, used as context, not "
     "personal exposure. No clinical data is involved, so nothing here is clinical validation.",
     "docs/DATA_PROVENANCE.md; docs/LIMITATIONS.md."),
    ("HAS THE SYSTEM BEEN CLINICALLY VALIDATED?",
     "No. No clinical trial, no real patient data, no regulatory review. It is labelled a research "
     "prototype and not a medical device throughout the product.",
     "docs/LIMITATIONS.md; README caution block."),
    ("WHAT HEALTHCARE IMPACT HAS ACTUALLY BEEN DEMONSTRATED?",
     "Software impact only: a working, audited, reproducible prototype with tested clinician and patient "
     "workflows. No patient, clinical or system-level outcome has been measured.",
     "DELIVERY_REPORT.md; docs/LIMITATIONS.md."),
    ("HOW WOULD THE PLATFORM BE CLINICALLY EVALUATED?",
     "Three stages: clinician-supervised usability and workflow studies; prospective observational "
     "research with adjudicated outcomes under ethics approval; then outcome measurement including "
     "calibration, subgroup fairness and net benefit.",
     "docs/LIMITATIONS.md (next steps)."),
    ("HOW DOES THE DOCTOR INTERACT WITH THE PLATFORM?",
     "Signs in, opens an assigned patient, reviews the twin, the trends and the labelled model context, "
     "then records a review. Access is enforced server-side by patient assignment, and every action is "
     "attributed in an audit trail.",
     "docs/DOCTOR_PATIENT_DELIVERY.md."),
]

QA_CLOSERS = [
    "Answer in one breath.",
    "Then stop talking.",
    "Do not add a number you cannot defend.",
    "If you do not know, say: \u201cWe have not evaluated that \u2014 it would be part of the next stage.\u201d",
]

REFERENCES = [
    "World Health Organization. Chronic obstructive pulmonary disease (COPD). Fact sheet, 10 June 2026.",
    "Global Initiative for Chronic Obstructive Lung Disease. Global Strategy for the Diagnosis, Management "
    "and Prevention of COPD: 2026 Report. goldcopd.org",
    "Langsetmo L, Platt RW, Ernst P, Bourbeau J. Underreporting exacerbation of chronic obstructive "
    "pulmonary disease in a longitudinal cohort. Am J Respir Crit Care Med. 2008;177(4):396-401.",
    "Hurst JR, Vestbo J, Anzueto A, et al. Susceptibility to exacerbation in chronic obstructive pulmonary "
    "disease. N Engl J Med. 2010;363(12):1128-1138.",
    "Elliott-Button HL, Johnson MJ, Hutchinson A, et al. \u201cI\u2019m living in a \u2018no\u2019 world now\u2026\u201d "
    "npj Primary Care Respiratory Medicine. 2024;34:37.",
    "How People with COPD Perceive and Communicate Exacerbations: A Multicountry Survey Study. "
    "Int J Chron Obstruct Pulmon Dis. 2025.",
    "PranaGuard project documentation: docs/METHODOLOGY.md, docs/MODEL_CARD.md, docs/model-v3/RESULTS.md, "
    "docs/LIMITATIONS.md, docs/DATA_PROVENANCE.md.",
]

# --------------------------------------------------------------------------- derived
def spoken_words():
    total = 0
    per = {}
    for s in SLIDES:
        w = sum(len(t.split()) for k, t in s["blocks"] if k == "q")
        per[s["n"]] = w
        total += w
    return total, per


def notes_text(slide) -> str:
    """PowerPoint speaker notes for one of the five main slides."""
    L = [f"SLIDE {slide['n']} \u2014 {slide['title']}",
         f"{slide['presenter']}  \u00b7  {slide['window']}",
         "",
         "MAIN MESSAGE",
         slide["main"],
         ""]
    for kind, text in slide["blocks"]:
        if kind == "h":
            label = text.upper()[:58]
            L.append("")
            L.append(label)
            L.append("-" * min(len(label), 58))
        elif kind == "q":
            L.append(text)
        else:
            L.append(text)
    L.append("")
    L.append("SOURCES FOR FACTUAL CLAIMS")
    L.extend("\u2022 " + s for s in slide["sources"])
    L.append("")
    L.append("Full script, timings and evidence table: PranaGuard_5_Minute_Speaker_Script.docx")
    return "\n".join(L)


SCRIPT_WORD_TOTAL, SCRIPT_WORDS_PER_SLIDE = spoken_words()
