# -*- coding: utf-8 -*-
"""
PranaGuard — content for the five jury slides.
Every factual statement here is either (a) traced to the project's own verified
documentation, or (b) an external COPD fact with a citation key in REFS.
Nothing claims clinical validation or measured patient benefit.
"""

# --------------------------------------------------------------------------- sources
REFS = {
    "who": "WHO. Chronic obstructive pulmonary disease (COPD) — fact sheet, 10 June 2026.",
    "gold": "GOLD. Global Strategy for the Diagnosis, Management and Prevention of COPD, 2026 report.",
    "langsetmo": ("Langsetmo L, Platt RW, Ernst P, Bourbeau J. Underreporting exacerbation of COPD in a "
                  "longitudinal cohort. Am J Respir Crit Care Med 2008;177:396-401."),
    "hurst": ("Hurst JR, Vestbo J, Anzueto A, et al. Susceptibility to exacerbation in COPD. "
              "N Engl J Med 2010;363:1128-38."),
    "elliott": ("Elliott-Button HL, Johnson MJ, Hutchinson A, et al. \u201cI\u2019m living in a \u2018no\u2019 world now\u2026\u201d "
                "npj Prim Care Respir Med 2024;34:37."),
    "multicountry": ("How people with COPD perceive and communicate exacerbations: a multicountry survey. "
                     "Int J Chron Obstruct Pulmon Dis 2025."),
}
REPO = "PranaGuard repository: docs/METHODOLOGY.md, docs/LIMITATIONS.md, docs/model-v3/RESULTS.md"

CITATION_STRIP = "Sources: WHO COPD fact sheet 2026  \u00b7  GOLD 2026 report  \u00b7  Langsetmo et al., AJRCCM 2008"

# --------------------------------------------------------------------------- slide 1
S1 = dict(
    kicker="01  \u00b7  THE HUMAN PROBLEM",
    headline=["What happens when a", "patient\u2019s breathing begins to", "deteriorate \u2014 but the change is",
              "not recognised early enough?"],
    lead=["In COPD, the weeks between two consultations", "are usually the least visible part of the disease."],
    steps=[("Everyday breathing", "Good days and bad days, managed at home"),
           ("Worsening symptoms", "A change the patient feels \u2014 rarely written down"),
           ("Healthcare intervention", "A consultation, a prescription, a hospital visit")],
    fact_num="3rd",
    fact_label="leading cause of death worldwide",
    fact_detail=("3.4 million deaths in 2023 \u2014 about 6% of all deaths globally. COPD is not rare, "
                 "and it is not curable."),
    cite="Source: WHO COPD fact sheet, 10 June 2026.",
    photo_caption="Illustrative photograph. PranaGuard uses synthetic patient records only.",
)

# --------------------------------------------------------------------------- slide 2
S2 = dict(
    kicker="02  \u00b7  THE HEALTHCARE GAP",
    headline=["Care is built from snapshots.", "COPD is not a snapshot disease."],
    cite="Sources: Langsetmo et al. 2008; GOLD 2026; Elliott-Button et al. 2024.",
    panel_title="Three points on the path where the picture breaks down",
    breaks=[
        ("01", "INFORMATION IS FRAGMENTED",
         "Results, letters, prescriptions and self-reported symptoms sit in different places and rarely join up."),
        ("02", "DAILY EXPERIENCE IS RARELY CAPTURED",
         "Symptoms are under-reported by patients \u2014 and clinicians do not systematically ask about them."),
        ("03", "CHANGE IS DIFFICULT TO SEE",
         "With a snapshot at each visit, an individual\u2019s baseline and drift between visits are hard to judge."),
    ],
    timeline_title="BETWEEN TWO ROUTINE VISITS",
    timeline_left="Visit",
    timeline_right="Next visit",
    timeline_days="day 1  \u00b7  \u00b7  \u00b7  day 90",
    timeline_note="Ninety days of lived experience. Two recorded observations.",
    timeline_basis="Schematic, not to scale. Illustrative interval \u2014 not a measured statistic.",
    compare_title="VENTILATION IS NOT EXACERBATION",
    compare_body=("A single spirometry value or one saturation reading describes a moment. It does not "
                  "describe how a person has been breathing since the last visit."),
    defs=[
        ("A SINGLE MEASUREMENT", "Valid for that moment. Weak at describing direction."),
        ("A LONGITUDINAL UNDERSTANDING", "Repeated records against a personal baseline."),
    ],
    gap_num="68%",
    gap_text=("In a longitudinal cohort, 68% of exacerbations recorded by patients in daily diaries were never "
              "reported to a health professional (327 of 486)."),
    gap_cite="Langsetmo et al., AJRCCM 2008",
    worst="RISK LIVES IN THE HISTORY, NOT THE SNAPSHOT",
    worst_src=("Hurst et al., NEJM 2010: a history of exacerbations was the single best predictor of future "
               "exacerbations across all GOLD stages."),
)

# --------------------------------------------------------------------------- slide 3
S3 = dict(
    kicker="03  \u00b7  THE PRANAQUARD APPROACH",
    headline=["From isolated observations to a longitudinal COPD digital twin"],
    sub=("A research prototype that keeps each patient\u2019s COPD story in one place \u2014 and labels "
         "every model output for what it is."),
    flow=[
        ("01", "PATIENT OBSERVATIONS", "Daily wellbeing, breathlessness, sputum, adherence, physiology"),
        ("02", "LONGITUDINAL HEALTH RECORD", "A versioned twin state for every hour of the record"),
        ("03", "PERSONAL BASELINE", "First 72 observed hours become that patient\u2019s own reference"),
        ("04", "RESEARCH-MODEL INSIGHTS", "Experimental 24 / 48 / 72-hour estimates, model version attached"),
        ("05", "CLINICIAN REVIEW", "A person reviews, documents and decides \u2014 the model never does"),
    ],
    shot_caption="Actual PranaGuard interface: synthetic patient PG-0071, replay state v25.",
    shot_note=("Outputs shown are experimental research estimates on synthetic data \u2014 not confirmed clinical events."),
    labels=[
        ("PATIENT HEALTH", "daily records, diary, adherence"),
        ("DIGITAL TWIN", "baseline vs current, versioned states"),
        ("LONGITUDINAL TRENDS", "body signals, risk history"),
        ("MODEL EVIDENCE", "version, completeness, limitations"),
        ("DOCTOR \u2192 PATIENT", "review, documents, follow-up"),
    ],
    note_line=("Status: working software prototype \u00b7 synthetic cohort of 120 patients \u00b7 "
               "not a medical device \u00b7 not clinically validated"),
)

# --------------------------------------------------------------------------- slide 4
S4 = dict(
    kicker="04  \u00b7  HEALTHCARE IMPACT",
    headline=["What could change \u2014 if the approach is validated"],
    sub=("Potential impact is described here as potential. The prototype has not demonstrated any of it in patients."),
    lanes=[
        ("PATIENT", [
            "Better visibility of changing breathing patterns",
            "A structured way to record daily experience",
            "One continuous record instead of disconnected episodes",
            "Better-informed conversations with the care team",
        ]),
        ("CLINICIAN", [
            "Consolidated longitudinal information in one view",
            "Change since the personal baseline, not just today",
            "Patient-reported information gathered and reviewed",
            "Research insight offered as context, never as a verdict",
        ]),
        ("HEALTHCARE SYSTEM", [
            "A more structured model for longitudinal monitoring",
            "A research platform for exacerbation-associated patterns",
            "A foundation for future, evidence-based COPD workflows",
        ]),
    ],
    pathway=["Patient observations", "Structured longitudinal information", "Clinician visibility",
             "Informed assessment", "Continuity of care"],
    ev_title="CURRENT EVIDENCE  vs.  FUTURE VALIDATION",
    current_title="WHAT EXISTS TODAY",
    current=[
        "Working end-to-end software prototype, audited and reproducible",
        "Model experiments on a synthetic cohort of 120 patients",
        "Public modelled environmental context (Open-Meteo / CAMS), city-level only",
    ],
    future_title="WHAT MUST HAPPEN NEXT",
    future=[
        "Clinician-supervised evaluation and prospective research",
        "Clinical usability and workflow assessment",
        "Measurement of real patient and healthcare outcomes",
    ],
    disclaimer=("No reduction in hospitalisations, exacerbations or mortality has been demonstrated. "
                "Model performance on synthetic data has been weak and is reported as such."),
)

# --------------------------------------------------------------------------- slide 5
S5 = dict(
    kicker="05  \u00b7  THE VISION",
    headline=["Better COPD care begins with understanding the", "changes happening between consultations."],
    close=("PranaGuard \u2014 turning fragmented COPD observations into a more connected picture of patient health."),
    nodes=[("PATIENT", "daily experience"), ("LONGITUDINAL DATA", "the record over time"),
           ("CLINICIAN", "review and judgement"), ("RESEARCH INSIGHTS", "evidence, explicitly labelled")],
    ask="What if the changes between consultations were easier to understand?",
    status=("Status today: a working research prototype on synthetic data. Clinical value is a hypothesis to be tested, "
            "not a result we are claiming."),
    invite="Thank you \u2014 we welcome your questions.",
)

# --------------------------------------------------------------------------- appendix
A1 = dict(
    kicker="APPENDIX  \u00b7  FURTHER READING",
    headline=["Questions the jury may ask"],
    facts=("Global burden: COPD is the third leading cause of death worldwide, with 3.4 million deaths in 2023 "
           "(about 6% of global deaths). Nearly 90% of COPD deaths under age 70 occur in low- and middle-income "
           "countries (WHO, 2026).\n\n"
           "What PranaGuard does not claim: no clinical validation, no measured outcome improvement, no "
           "regulatory status, no real patient data. All patient records in the prototype are synthetic."),
    items=[
        ("WHAT IS COPD?",
         "A common, preventable and treatable disease with persistent respiratory symptoms and airflow limitation. "
         "Symptoms include breathlessness, cough and sputum. It is not curable. (WHO; GOLD)"),
        ("WHAT IS AN EXACERBATION?",
         "An acute worsening of respiratory symptoms that leads to additional therapy. Severity ranges from extra "
         "bronchodilator use to hospitalisation. (GOLD)"),
        ("WHY LONGITUDINAL MONITORING?",
         "A single reading describes a moment. Repeated records against a personal baseline begin to describe "
         "direction of change between visits."),
        ("WHAT IS THE DIGITAL TWIN HERE?",
         "A versioned, replayable state for each synthetic patient: observations, personal baseline, derived "
         "features and model context kept in one continuous record."),
        ("WHAT DOES THE MODEL PREDICT?",
         "Experimental 24/48/72-hour estimates of a new synthetic exacerbation onset in the research cohort. "
         "These are research outputs, not validated probabilities or alerts."),
        ("WHAT DATA IS, AND IS NOT, REAL",
         "Patients, physiology and outcomes are all synthetic. The only real inputs are public modelled "
         "city air-quality and weather data \u2014 context, not personal exposure. No clinical data at all."),
        ("HAS IT BEEN CLINICALLY VALIDATED?",
         "No. There has been no clinical trial, no real patient data and no regulatory review. It is explicitly "
         "labelled a research prototype and not a medical device."),
        ("WHAT IMPACT IS DEMONSTRATED?",
         "Software functionality only: a working prototype whose behaviour is tested and reproducible. No patient, "
         "clinical or system-level outcome has been measured."),
        ("HOW WOULD IT BE EVALUATED?",
         "Clinician-supervised usability studies, then prospective observational research with adjudicated "
         "outcomes, then outcome measurement \u2014 under ethics approval and governance."),
        ("HOW DOES A DOCTOR USE IT?",
         "Sign in, open an assigned patient, review the twin, trends and labelled model context, then record a "
         "review. Every action is attributed and audited."),
    ],
    refs=[
        "1. World Health Organization. Chronic obstructive pulmonary disease (COPD). Fact sheet, 10 June 2026.",
        "2. Global Initiative for Chronic Obstructive Lung Disease. Global Strategy for the Diagnosis, Management "
        "and Prevention of COPD: 2026 Report. goldcopd.org",
        "3. Langsetmo L, Platt RW, Ernst P, Bourbeau J. Underreporting exacerbation of chronic obstructive "
        "pulmonary disease in a longitudinal cohort. Am J Respir Crit Care Med. 2008;177(4):396-401.",
        "4. Hurst JR, Vestbo J, Anzueto A, et al. Susceptibility to exacerbation in chronic obstructive pulmonary "
        "disease. N Engl J Med. 2010;363(12):1128-1138.",
        "5. Elliott-Button HL, Johnson MJ, Hutchinson A, et al. \u201cI\u2019m living in a \u2018no\u2019 world now\u2026\u201d "
        "npj Primary Care Respiratory Medicine. 2024;34:37.",
        "6. How People with COPD Perceive and Communicate Exacerbations: A Multicountry Survey Study. "
        "Int J Chron Obstruct Pulmon Dis. 2025.",
        "7. PranaGuard project documentation: docs/METHODOLOGY.md, docs/MODEL_CARD.md, "
        "docs/model-v3/RESULTS.md, docs/LIMITATIONS.md, docs/DATA_PROVENANCE.md.",
    ],
)
