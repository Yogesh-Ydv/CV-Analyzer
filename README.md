# AI CV Analyzer — Prototype

A transparent, explainable resume-scoring tool built with Streamlit, spaCy, and scikit-learn.

## What's in this folder
- `app.py` — Streamlit UI (run this)
- `analyzer.py` — core engine: text extraction, NLP parsing, scoring, recommendations
- `knowledge_base.py` — role/skill taxonomy and learning-resource map (editable, no code changes needed to extend)
- `sample_resume.txt` — a sample resume you can use to demo the tool immediately
- `requirements.txt` — Python dependencies
- `CV_Analyzer_Documentation.docx` — full project documentation (architecture, scoring logic, AI/NLP approach, tech stack, API plan, ethics)

## Setup

```bash
pip install -r requirements.txt
```

(Optional, recommended for production-quality NER): `python -m spacy download en_core_web_sm`
— the prototype works without this since it uses a blank spaCy pipeline + rule-based skill matching.

## Run

```bash
streamlit run app.py
```

Then in the browser:
1. Upload `sample_resume.txt` (or any PDF/DOCX/TXT resume).
2. Optionally select a target role and/or paste a job description.
3. Click **Analyze Resume**.

## How it works (quick version)
1. **Extract** text from the uploaded file (`pdfplumber` / `python-docx`).
2. **Parse** it with spaCy's PhraseMatcher + regex to pull out contact info, detected resume
   sections, matched skills, bullet count, and an estimated years-of-experience.
3. **Score** the resume across 5 transparent, weighted components (see Documentation, Section 4).
4. **Recommend** the highest-priority missing skills (vs. the chosen target role) along with a
   free/low-cost learning resource for each.

See `CV_Analyzer_Documentation.docx` for the full write-up, including the production roadmap,
proposed tech stack, API integration plan (LinkedIn/GitHub/Tableau/Power BI), and ethical
safeguards.
