"""
analyzer.py
-----------
Core engine for the AI CV Analyzer prototype.

Pipeline:
  1. extract_text()        -> raw text from PDF / DOCX / TXT
  2. parse_resume()        -> structured fields (contact, sections, skills, experience years)
  3. score_resume()        -> transparent, weighted profile score (0-100) broken down by category
  4. match_against_jd()    -> TF-IDF cosine similarity + explicit skill-gap diff vs a Job Description
  5. recommend()           -> ranked list of skill gaps + learning resources

Design principle: every score is explainable. We never return a single opaque
number — each sub-score has a stated formula and the matched/missing
keywords are surfaced to the user, addressing the "transparent and
industry-aligned" requirement and the "unbiased AI" requirement (no use of
demographic signals — gender, age, name-based ethnicity inference, photos —
anywhere in the scoring path).
"""

import re
import io
from dataclasses import dataclass, field
from typing import Optional

import spacy
from spacy.matcher import PhraseMatcher
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from knowledge_base import ALL_SKILLS, ROLE_SKILLS, LEARNING_RESOURCES, SECTION_KEYWORDS

# ---------------------------------------------------------------------------
# NLP setup
# ---------------------------------------------------------------------------
# NOTE: This prototype uses spaCy's blank English pipeline + a PhraseMatcher
# for skill extraction (sandbox had no network access to fetch the trained
# `en_core_web_sm` weights). In production, swap to `spacy.load("en_core_web_sm")`
# for proper Named Entity Recognition (person names, organisations, dates),
# which is straightforward and documented in Documentation.md, Section 3.
_nlp = spacy.blank("en")
_matcher = PhraseMatcher(_nlp.vocab, attr="LOWER")
_matcher.add("SKILL", [_nlp.make_doc(skill) for skill in ALL_SKILLS])

EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_RE = re.compile(r"(\+?\d{1,3}[\s.-]?)?(\(?\d{3,5}\)?[\s.-]?){2,4}\d{3,4}")
LINKEDIN_RE = re.compile(r"(linkedin\.com/in/[A-Za-z0-9\-_/]+)", re.IGNORECASE)
GITHUB_RE = re.compile(r"(github\.com/[A-Za-z0-9\-_/]+)", re.IGNORECASE)
YEAR_RANGE_RE = re.compile(r"(19|20)\d{2}\s*(-|–|to)\s*((19|20)\d{2}|present|current)", re.IGNORECASE)
BULLET_RE = re.compile(r"^\s*[•\-\*▪◦]\s+", re.MULTILINE)


@dataclass
class ParsedResume:
    raw_text: str
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    sections_found: list = field(default_factory=list)
    skills_found: list = field(default_factory=list)
    bullet_count: int = 0
    estimated_years_experience: float = 0.0
    word_count: int = 0


# ---------------------------------------------------------------------------
# 1. Text extraction
# ---------------------------------------------------------------------------
def extract_text(file_bytes: bytes, filename: str) -> str:
    name = filename.lower()
    if name.endswith(".pdf"):
        import pdfplumber
        text = []
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                text.append(page.extract_text() or "")
        return "\n".join(text)
    elif name.endswith(".docx"):
        import docx
        document = docx.Document(io.BytesIO(file_bytes))
        return "\n".join(p.text for p in document.paragraphs)
    elif name.endswith(".txt"):
        return file_bytes.decode("utf-8", errors="ignore")
    else:
        raise ValueError("Unsupported file type. Please upload PDF, DOCX or TXT.")


# ---------------------------------------------------------------------------
# 2. Parsing
# ---------------------------------------------------------------------------
def _extract_section_segment(text: str, section: str) -> str:
    """Return the text block belonging to a given section (e.g. 'experience'),
    from its heading up to the next recognised section heading. Falls back to
    the full text if no heading is found, so downstream regex still has
    something reasonable to scan."""
    lines = text.split("\n")
    all_headings = [kw for kws in SECTION_KEYWORDS.values() for kw in kws]
    start_idx = None
    for i, line in enumerate(lines):
        l = line.strip().lower()
        if any(l == kw or l.startswith(kw) for kw in SECTION_KEYWORDS.get(section, [])):
            start_idx = i
            break
    if start_idx is None:
        return text
    end_idx = len(lines)
    for j in range(start_idx + 1, len(lines)):
        l = lines[j].strip().lower()
        if l and any(l == kw or l.startswith(kw) for kw in all_headings) and \
           not any(l.startswith(kw) for kw in SECTION_KEYWORDS.get(section, [])):
            end_idx = j
            break
    return "\n".join(lines[start_idx:end_idx])


def parse_resume(text: str) -> ParsedResume:
    parsed = ParsedResume(raw_text=text)
    lower = text.lower()

    email_match = EMAIL_RE.search(text)
    parsed.email = email_match.group(0) if email_match else None

    phone_match = PHONE_RE.search(text)
    parsed.phone = phone_match.group(0).strip() if phone_match else None

    li_match = LINKEDIN_RE.search(text)
    parsed.linkedin = li_match.group(0) if li_match else None

    gh_match = GITHUB_RE.search(text)
    parsed.github = gh_match.group(0) if gh_match else None

    # Section detection
    for section, keywords in SECTION_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            parsed.sections_found.append(section)

    # Skill extraction via PhraseMatcher
    doc = _nlp.make_doc(text)
    matches = _matcher(doc)
    found = set()
    for match_id, start, end in matches:
        found.add(doc[start:end].text.lower())
    parsed.skills_found = sorted(found)

    parsed.bullet_count = len(BULLET_RE.findall(text))
    parsed.word_count = len(text.split())

    # Rough years-of-experience estimate from date ranges (e.g. "2019 - 2023"),
    # restricted to the EXPERIENCE section only so education date ranges
    # (e.g. degree years) aren't double-counted as work experience.
    exp_segment = _extract_section_segment(text, "experience")
    years_spans = []
    for m in YEAR_RANGE_RE.finditer(exp_segment):
        start_year = int(m.group(0)[:4])
        end_token = m.group(3).lower()
        end_year = 2026 if end_token in ("present", "current") else int(end_token[:4])
        if end_year >= start_year:
            years_spans.append(end_year - start_year)
    # Use the max span rather than summing overlapping/multiple roles, which
    # gives a more realistic "years of experience" approximation.
    parsed.estimated_years_experience = float(max(years_spans)) if years_spans else 0.0

    return parsed


# ---------------------------------------------------------------------------
# 3. Scoring logic (transparent, weighted, explainable)
# ---------------------------------------------------------------------------
# Weights are documented and justified in Documentation.md, Section 2.
SCORE_WEIGHTS = {
    "completeness": 0.20,   # Are standard resume sections present?
    "skills_match": 0.35,   # Overlap with target role's skill taxonomy
    "experience": 0.20,     # Estimated years + quantified bullet points
    "formatting": 0.10,     # Bullet usage, length sanity, contact info present
    "keyword_alignment": 0.15,  # TF-IDF similarity vs supplied Job Description (optional)
}


def _completeness_score(parsed: ParsedResume) -> tuple[float, dict]:
    expected = list(SECTION_KEYWORDS.keys())
    present = parsed.sections_found
    score = 100 * len(present) / len(expected)
    detail = {"sections_present": present,
               "sections_missing": [s for s in expected if s not in present]}
    return score, detail


def _skills_score(parsed: ParsedResume, target_role: Optional[str]) -> tuple[float, dict]:
    if not target_role or target_role not in ROLE_SKILLS:
        # No target role chosen: score relative to breadth of overall vocabulary matched
        score = min(100, len(parsed.skills_found) * 8)
        return score, {"matched": parsed.skills_found, "missing": [], "role": None}

    core = set(ROLE_SKILLS[target_role]["core"])
    good = set(ROLE_SKILLS[target_role]["good_to_have"])
    found = set(parsed.skills_found)

    core_hit = found & core
    good_hit = found & good
    # Core skills weighted 70%, good-to-have 30%
    core_pct = len(core_hit) / len(core) if core else 0
    good_pct = len(good_hit) / len(good) if good else 0
    score = 100 * (0.7 * core_pct + 0.3 * good_pct)

    detail = {
        "matched_core": sorted(core_hit), "missing_core": sorted(core - found),
        "matched_good_to_have": sorted(good_hit), "missing_good_to_have": sorted(good - found),
        "role": target_role,
    }
    return score, detail


def _experience_score(parsed: ParsedResume) -> tuple[float, dict]:
    years_component = min(60, parsed.estimated_years_experience * 12)  # caps at 5 yrs = 60 pts
    bullets_component = min(40, parsed.bullet_count * 2)               # caps at 20 bullets = 40 pts
    score = years_component + bullets_component
    detail = {"estimated_years": parsed.estimated_years_experience,
               "bullet_points": parsed.bullet_count}
    return score, detail


def _formatting_score(parsed: ParsedResume) -> tuple[float, dict]:
    score = 0
    notes = []
    if parsed.email:
        score += 25
    else:
        notes.append("No email address detected.")
    if parsed.phone:
        score += 15
    else:
        notes.append("No phone number detected.")
    if parsed.bullet_count >= 3:
        score += 30
    else:
        notes.append("Use bullet points to describe achievements (found too few).")
    if 200 <= parsed.word_count <= 1200:
        score += 30
    elif parsed.word_count < 200:
        notes.append("Resume seems too short — add more detail on projects/experience.")
    else:
        notes.append("Resume is lengthy — consider trimming to 1-2 pages.")
    return float(score), {"notes": notes}


def _keyword_alignment_score(resume_text: str, jd_text: Optional[str]) -> tuple[float, dict]:
    if not jd_text or not jd_text.strip():
        return 0.0, {"note": "No job description supplied — this component excluded from total.", "similarity": None}
    vectorizer = TfidfVectorizer(stop_words="english")
    tfidf = vectorizer.fit_transform([resume_text, jd_text])
    sim = cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0]
    score = round(sim * 100, 1)
    return score, {"similarity": score}


def score_resume(parsed: ParsedResume, target_role: Optional[str] = None,
                  jd_text: Optional[str] = None) -> dict:
    completeness, completeness_detail = _completeness_score(parsed)
    skills, skills_detail = _skills_score(parsed, target_role)
    experience, experience_detail = _experience_score(parsed)
    formatting, formatting_detail = _formatting_score(parsed)
    keyword, keyword_detail = _keyword_alignment_score(parsed.raw_text, jd_text)

    weights = dict(SCORE_WEIGHTS)
    if not jd_text or not jd_text.strip():
        # Redistribute the keyword_alignment weight proportionally if no JD given
        dropped = weights.pop("keyword_alignment")
        total = sum(weights.values())
        weights = {k: v + (v / total) * dropped for k, v in weights.items()}

    components = {
        "completeness": completeness,
        "skills_match": skills,
        "experience": experience,
        "formatting": formatting,
    }
    if jd_text and jd_text.strip():
        components["keyword_alignment"] = keyword

    overall = sum(components[k] * weights[k] for k in components)

    return {
        "overall_score": round(overall, 1),
        "weights_used": {k: round(v, 3) for k, v in weights.items()},
        "components": {
            "completeness": {"score": round(completeness, 1), **completeness_detail},
            "skills_match": {"score": round(skills, 1), **skills_detail},
            "experience": {"score": round(experience, 1), **experience_detail},
            "formatting": {"score": round(formatting, 1), **formatting_detail},
            "keyword_alignment": {"score": round(keyword, 1), **keyword_detail},
        },
    }


# ---------------------------------------------------------------------------
# 4. Recommendation engine (skill-gap based)
# ---------------------------------------------------------------------------
def recommend(score_result: dict, top_n: int = 5) -> list:
    skills_detail = score_result["components"]["skills_match"]
    missing_core = skills_detail.get("missing_core", [])
    missing_good = skills_detail.get("missing_good_to_have", [])

    # Core gaps are prioritised over good-to-have gaps
    ranked = [(s, "High priority — core requirement") for s in missing_core] + \
             [(s, "Medium priority — strengthens profile") for s in missing_good]

    recommendations = []
    for skill, priority in ranked[:top_n]:
        recommendations.append({
            "skill": skill,
            "priority": priority,
            "resource": LEARNING_RESOURCES.get(skill, "Search official documentation / Coursera / Udemy"),
        })
    return recommendations
