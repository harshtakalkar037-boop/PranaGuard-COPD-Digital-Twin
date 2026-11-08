# -*- coding: utf-8 -*-
"""Complete speaker notes for the five main slides + the two appendix slides."""

S1_NOTES = """SLIDE 1 — THE HUMAN PROBLEM
PRESENTER 1  ·  0:00 – 0:40

MAIN MESSAGE
COPD deterioration usually happens between appointments, not inside them. That gap is the reason
PranaGuard exists.

--- BEFORE YOU CLICK (0:00 – 0:10) -------------------------------------------------
Stand centre-stage, not behind the laptop. Do not read the slide. Let it land first.

SCRIPT (about 40 seconds at a natural pace)

"Before we show you anything we built, we want you to picture one person.

This is someone's father. Someone's neighbour. He has COPD — chronic obstructive pulmonary
disease. On a good day, he can breathe. On a bad day, he cannot walk to the window.

And here is the question we would like you to hold for the next five minutes:

[SLIDE 1 IS ON SCREEN] What happens when a patient's breathing begins to deteriorate — but the
change is not recognised early enough?

In COPD, the weeks between two consultations are usually the least visible part of the disease.

[GESTURE TO THE THREE BOXES] The path is almost always the same. Everyday breathing, managed at
home. Worsening symptoms the patient feels but rarely writes down. And then, eventually, a
healthcare intervention.

COPD is the third leading cause of death worldwide — 3.4 million deaths in 2023. It is not rare,
and it is not curable.

But rarity isn't our point. Visibility is."

INTERACTION 1 — OPENING QUESTION (optional, 15 seconds, do this only if the room is warm)
Ask: "Quick show of hands — who here has a relative who has been told 'your lungs are fine' when
they didn't feel fine?"
Accept two seconds of hands, then: "That gap between what a person feels and what a system
records is the space we work in."
Do NOT wait for stories. Keep it to ten seconds.

TRANSITION TO SLIDE 2
"To understand why that gap exists, it helps to look at how COPD care is actually assembled —
visit by visit, record by record."

SOURCES FOR FACTUAL CLAIMS
• Third leading cause of death; 3.4 million deaths in 2023; ~6% of global deaths —
  WHO COPD fact sheet (10 June 2026).
• COPD is not curable — WHO COPD fact sheet.
• Do not add any prevalence or survival statistic that is not on this slide.

PRODUCTION NOTES
• The photograph is an illustrative image, labelled as such on the slide. Say the word
  "illustrative" if anyone asks about the person. Never imply he is a real PranaGuard patient.
"""

S2_NOTES = """SLIDE 2 — THE HEALTHCARE GAP
PRESENTER 1  ·  0:40 – 1:40

MAIN MESSAGE
COPD care is built from snapshots. COPD is a disease of trajectory. The two do not match.

--- SCRIPT (about 60 seconds)

"Think about how COPD care is actually recorded.

[A] A consultation. A spirometry value. A prescription. Notes in one system, a letter in another,
and a patient's own memory holding everything else.

Three things tend to break.

One — information is fragmented. Results, letters, prescriptions and what the patient reports
live in different places and rarely join up.

Two — daily experience is rarely captured. The GOLD report tells us these symptoms are
under-reported by patients. And a qualitative study in primary care found the opposite half of
the same problem: clinicians do not routinely ask about breathlessness. Everyone is waiting for
the other person to start the conversation.

Three — change is difficult to see. If every contact is a snapshot, then an individual's own
baseline — what is normal for *this* person — is hard to establish, and drift from it is even
harder to judge.

[GESTURE TO 68%] Here is the number that should worry us. In a longitudinal Canadian cohort,
68% of the exacerbations that patients recorded in their own daily diaries were never reported
to a health professional. Two out of three events. Not because they were mild — the study found
reported and unreported events had similar characteristics. They simply never reached the record.

[GESTURE TO THE 90-DAY LINE] So look at the shape of the information we actually have. Two
observations, ninety days apart. Ninety days of lived experience, and two recorded points.

And this matters clinically for a specific reason. [GESTURE TO THE CALLOUT] The single best
predictor of future exacerbations is a history of exacerbations — across all GOLD stages. Risk
lives in the history. A snapshot doesn't carry a history.

One clarification, because it matters: a single measurement is not useless. It is simply a
measurement of a moment. A longitudinal understanding — repeated records against a personal
baseline — is what begins to describe direction of change. Those are different instruments, and
we need both."

INTERACTION 2 — THE JURY QUESTION (20 seconds)
Ask the room: "If a COPD patient feels worse between two hospital visits, how much of that change
is visible to the clinician?"
Pause. Let three seconds pass. If nobody answers, say: "Honestly? Usually very little. And that
is not a criticism of any clinician — it is a property of the record we give them."
Do not reveal slide 3 content early.

TRANSITION TO SLIDE 3 — THE HANDOVER
(Step slightly back, turn to Presenter 2.)
"My colleague will now show you what we built to change that."

→ PRESENTER 2 takes over here. Hand over the clicker at this sentence.

SOURCES FOR FACTUAL CLAIMS
• Symptoms under-reported by patients — GOLD 2026 report, COPD definition and key points.
• Clinicians do not routinely ask about breathlessness; breathlessness normalised and
  under-reported — Elliott-Button et al., npj Primary Care Respiratory Medicine 2024;34:37.
• 68% unreported (327 of 486 diary exacerbations) — Langsetmo L, Platt RW, Ernst P, Bourbeau J.
  Underreporting exacerbation of COPD in a longitudinal cohort. Am J Respir Crit Care Med
  2008;177:396-401.
• Prior exacerbations are the best single predictor of future exacerbations across GOLD stages —
  Hurst JR et al., N Engl J Med 2010;363:1128-38; also stated in GOLD 2026.
• The 90-day interval is illustrative and labelled "schematic, not to scale". Never present it
  as a measured statistic.

IF ASKED WHY THIS ISN'T JUST "POOR HEALTHCARE"
Say: "It isn't. It's the shape of the instrument. A fifteen-minute consultation cannot observe
ninety days. We are not trying to make clinicians watch harder — we are trying to make the gap
between visits legible."
"""

S3_NOTES = """SLIDE 3 — THE PRANAQUARD APPROACH
PRESENTER 2  ·  1:40 – 2:50

MAIN MESSAGE
PranaGuard turns isolated observations into one longitudinal, replayable record of a patient's
COPD — and keeps every model output clearly labelled as research.

--- SCRIPT (about 70 seconds)

[CLICK 1 — reveals stages 01 and 02]
"The first thing we built is a record that behaves like a story, not a filing cabinet.

A patient's observations — daily wellbeing, breathlessness, sputum, adherence, physiology — go in.

They become a longitudinal health record, and in our prototype that means every hour of the
record is a versioned, replayable state. Not one overwritten row — a history you can walk back
through.

[CLICK 2 — reveals stages 03 and 04]
Third, and this is the part that matters clinically: we establish a personal baseline. The first
72 observed hours become that patient's own reference point. Not a population average. *This*
person's normal.

Fourth, research-model insights. We compute experimental 24, 48 and 72-hour estimates, and every
one of them carries its model version, its input completeness, its freshness and its limitations
with it. Nothing is presented as a bare number.

[CLICK 3 — reveals stage 05]
And fifth — the most important design decision in the whole system — a human being reviews. The
model never signs anything. A clinician reviews, documents and decides.

[GESTURE TO THE SCREENSHOT] This is the actual interface, not a mock-up. This is a synthetic
patient — PG-0071 — at replay state 25. On the left is a personal baseline against current
values. In the middle, the body-signal trend across the replay window. And here, the three
research cards — 1.5%, 2.2%, 29.7% — each one labelled with its model version and, crucially,
labelled as an experimental estimate on synthetic data. Not a diagnosis. Not an emergency alert.

That labelling is not decoration. In our own evaluation the 72-hour model performed poorly — an
AUROC of 0.395, below chance. We published that, and the interface repeats the warning, because
a system that hides its weak parts cannot be trusted with its strong ones."

INTERACTION 3 — PROGRESSIVE REVEAL (built into the slide)
Three clicks. Say the stage name, then click. If the projector or the clicker fails, the PDF
version shows the complete flow — carry on with that and keep talking; nothing is lost.
Keep this to roughly 8 seconds per stage.

TRANSITION TO SLIDE 4
"So that is the mechanism. The question that actually matters is: what could this change?"

SOURCES FOR FACTUAL CLAIMS
• Every hour is a versioned, replayable state; personal baseline = median of the first 72
  observed hours — PranaGuard docs/METHODOLOGY.md and docs/ARCHITECTURE.md.
• "Experimental estimate on synthetic data" labels appear in the product screenshots
  (docs/model-v3/verification/screenshots/desktop-patient.png).
• 72-hour AUROC 0.3951, below chance, and AUPRC 0.0593 below prevalence 0.0773 —
  artifacts/evaluation.md and docs/MODEL_CARD.md.
• Screenshot is the actual application, synthetic patient PG-0071, state v25 — captioned on
  the slide. Never describe it as a real patient.

IF ASKED "IS THIS A DIGITAL TWIN OR JUST A DATABASE?"
Say: "It is a stateful, replayable representation of one patient over time. It is a
data-driven twin, not a mechanistic model of the lung — we are careful about that distinction,
and it is written in our architecture document."
"""

S4_NOTES = """SLIDE 4 — HEALTHCARE IMPACT
PRESENTER 2  ·  2:50 – 4:20

MAIN MESSAGE
The potential value is better visibility across three levels — but it is potential. We have not
measured patient benefit, and we will not pretend we have.

--- SCRIPT (about 90 seconds)

"This is the slide we would ask you to judge us on.

[PATIENT COLUMN] For the patient: better visibility of changing breathing patterns. A structured
way to record daily experience — which we know is where 68% of events disappear. One continuous
record instead of disconnected episodes. And, practically, better-informed conversations with
the care team.

[CLINICIAN COLUMN] For the clinician: consolidated longitudinal information in one view. Change
measured against the patient's own baseline, not just today's reading. Patient-reported
information that has actually been gathered and reviewed. And research insight offered as
context — never as a verdict.

[SYSTEM COLUMN] For the health system: a more structured model for longitudinal monitoring. A
research platform for studying exacerbation-associated patterns. And a foundation for future,
evidence-based COPD workflows.

[IMPACT PATHWAY] The pathway we are proposing is deliberately modest. Observations become
structured longitudinal information. That becomes clinician visibility. That supports informed
assessment. And the thing we are actually aiming at is continuity of care.

Now — the honest part, and we would rather say it than be asked.

[EVIDENCE PANEL] What exists today: a working end-to-end software prototype that is audited and
reproducible; model experiments on a synthetic cohort of 120 patients; and public modelled
environmental context, city-level only. What does not exist: any measured reduction in
hospitalisations, exacerbations or mortality. Our own model performance on synthetic data has
been weak at the 72-hour horizon, and we report it as weak.

What must happen next: clinician-supervised evaluation, prospective research, usability and
workflow assessment, and measurement of real patient and healthcare outcomes.

We would rather present a small, honest result than a large, unreliable one."

INTERACTION 4 — THE JURY QUESTION (15 seconds, only if time allows)
Ask: "If you were the clinician receiving this in clinic tomorrow, what would you need to see
before you trusted it?"
Take one answer if offered. Answer it directly and briefly. Then: "That is exactly the
evaluation we are proposing."

TRANSITION TO SLIDE 5
"Which brings us to why we think this is worth the next few years of work."

SOURCES FOR FACTUAL CLAIMS
• Prototype status: implemented, tested, audited, reproducible — README §5, DELIVERY_REPORT.md.
• 120-patient synthetic cohort — docs/DATA_PROVENANCE.md.
• Weak 72-hour performance reported openly — docs/MODEL_CARD.md, artifacts/evaluation.md.
• "No reduction in hospitalisations, exacerbations or mortality demonstrated" — docs/LIMITATIONS.md.
• The word "potential" must be spoken at least twice on this slide. Do not drop it.

IF A JURY MEMBER PUSHES: "SO WHAT IS THE ACTUAL IMPACT?"
Answer: "Today the demonstrated impact is engineering: a working, audited, reproducible system
that shows the workflow is buildable. The clinical impact is a hypothesis with a defined
evaluation path. We are not claiming more than that."
"""

S5_NOTES = """SLIDE 5 — THE VISION AND CLOSING
PRESENTER 2  ·  4:20 – 5:00

MAIN MESSAGE
Understanding change between consultations is the point. That is the whole thesis.

--- SCRIPT (about 40 seconds)

"Let me leave you with the sentence we started from.

[READ IT SLOWLY] Better COPD care begins with understanding the changes happening between
consultations.

Four things have to exist for that to be possible. A patient whose daily experience is captured.
Longitudinal data that keeps the history instead of overwriting it. A clinician who can review
that history and exercise judgement. And research insights that are honest about what they are.

[CLICK — reveals the four nodes]
PranaGuard is one attempt to put those four in the same room.

Today it is a working research prototype on synthetic data. The clinical value is a hypothesis
we have not yet tested in patients — and we think saying so is part of doing this properly.

[PAUSE. THEN THE CLOSING QUESTION, SLOWLY]
What if the changes between consultations were easier to understand?

Thank you — we welcome your questions."

INTERACTION 5 — CLOSING QUESTION (built into the slide, revealed on click)
Ask the question and stop talking. Do not fill the silence. Let the jury sit with it for two
seconds before you say "thank you".

HANDOVER BACK
If the Q&A is handled jointly: Presenter 1 takes clinical and COPD-context questions,
Presenter 2 takes product, model and evaluation questions. Agree this before you walk on stage.

SOURCES FOR FACTUAL CLAIMS
• No claim on this slide requires new evidence. "Working research prototype on synthetic data"
  is the project's own disclosed status — README caution block, docs/LIMITATIONS.md.
• This slide must not be amended to imply the vision has been clinically achieved.

TIMING NOTE
If you are running long, cut the second half of slide 4's evidence panel — but never cut the
"not yet demonstrated" sentence. It is the most credible thing in the deck.
"""

APPENDIX_QA_NOTES = """APPENDIX A — JURY Q&A PREPARATION (backup, not presented)
Use only if asked. Keep answers under 25 seconds each.

1. WHAT IS COPD?
A common, preventable and treatable disease with persistent respiratory symptoms and airflow
limitation. Breathlessness, cough and sputum are typical. It is not curable, but it is
treatable. (WHO; GOLD 2026)

2. WHAT IS AN EXACERBATION?
An acute worsening of respiratory symptoms that leads to additional therapy — from extra
bronchodilators up to hospitalisation. (GOLD 2026)

3. WHY IS LONGITUDINAL MONITORING USEFUL?
Because a single value is a moment, and COPD is a trajectory. Repeated records against a personal
baseline begin to show direction of change — and the strongest known predictor of future events
is the history of past events. (Hurst et al., NEJM 2010)

4. WHAT IS THE DIGITAL TWIN IN PRANAQUARD?
A versioned, replayable state per patient: observations, a personal baseline from the first 72
hours, derived features, and the model context attached to each saved state. It is data-driven,
not a mechanistic lung model.

5. WHAT DOES THE CURRENT MODEL ACTUALLY PREDICT?
An experimental estimate of a new synthetic exacerbation onset within 24, 48 or 72 hours, on the
research cohort. On held-out synthetic data, the 72-hour model had AUROC 0.395 and AUPRC 0.059 —
below chance and below prevalence. We report it as weak and non-clinical.

6. WHAT DATA IS REAL AND WHAT IS SYNTHETIC?
Every patient, physiological stream and outcome label is synthetic — 120 generated patients. The
only real inputs are public modelled city air-quality and weather data, used as context, not as
personal exposure. No clinical data is involved anywhere, so nothing here is clinical validation.

7. HAS THE SYSTEM BEEN CLINICALLY VALIDATED?
No. No trial, no real patient data, no regulatory review, no clinical endorsement. It is
labelled a research prototype and not a medical device throughout.

8. WHAT HEALTHCARE IMPACT HAS ACTUALLY BEEN DEMONSTRATED?
Software impact only: a working, audited, reproducible prototype with tested clinical workflows.
No patient, clinical or system-level outcome has been measured.

9. HOW WOULD THE PLATFORM BE CLINICALLY EVALUATED?
Three stages: clinician-supervised usability and workflow studies; prospective observational
research with adjudicated outcomes under ethics approval; then outcome measurement — including
calibration, subgroup fairness and net benefit.

10. HOW DOES THE DOCTOR INTERACT WITH THE PLATFORM?
Signs in, opens an assigned patient, reviews the twin, the trends and the labelled model context,
then records a review with an audit trail. Access is enforced server-side per patient assignment;
a patient account is blocked from clinician prediction endpoints.

TONE FOR Q&A
Answer the question asked, in one breath, then stop. If you do not know, say "we have not
evaluated that, and it would be part of the next stage." That answer is always stronger than an
invention.
"""

APPENDIX_REF_NOTES = """APPENDIX B — REFERENCES (backup)

1. World Health Organization. Chronic obstructive pulmonary disease (COPD). Fact sheet,
   10 June 2026. who.int
2. Global Initiative for Chronic Obstructive Lung Disease. Global Strategy for the Diagnosis,
   Management and Prevention of COPD: 2026 Report. goldcopd.org
3. Langsetmo L, Platt RW, Ernst P, Bourbeau J. Underreporting exacerbation of chronic obstructive
   pulmonary disease in a longitudinal cohort. Am J Respir Crit Care Med. 2008;177(4):396-401.
4. Hurst JR, Vestbo J, Anzueto A, et al. Susceptibility to exacerbation in chronic obstructive
   pulmonary disease. N Engl J Med. 2010;363(12):1128-1138.
5. Elliott-Button HL, Johnson MJ, Hutchinson A, et al. "I'm living in a 'no' world now…"
   npj Primary Care Respiratory Medicine. 2024;34:37.
6. How People with COPD Perceive and Communicate Exacerbations: A Multicountry Survey Study.
   Int J Chron Obstruct Pulmon Dis. 2025.
7. PranaGuard project documentation: docs/METHODOLOGY.md, docs/MODEL_CARD.md,
   docs/model-v3/RESULTS.md, docs/LIMITATIONS.md, docs/DATA_PROVENANCE.md.

NOTE ON CITATION DISCIPLINE
Only these seven sources are used anywhere in the deck. If a jury member asks for a source that
is not on this list, say so plainly rather than reaching for a number you cannot defend.
"""
