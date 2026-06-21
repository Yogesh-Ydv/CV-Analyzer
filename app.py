"""
app.py
------
Streamlit front-end for the AI CV Analyzer prototype.
Run with:  streamlit run app.py
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from analyzer import extract_text, parse_resume, score_resume, recommend
from knowledge_base import ROLE_SKILLS

st.set_page_config(page_title="AI CV Analyzer", page_icon="📄", layout="wide")

st.title("📄 AI CV Analyzer")
st.caption("Upload a resume to get a transparent, explainable profile score, skill-gap "
           "analysis, and personalised recommendations.")

# --- Sidebar inputs -------------------------------------------------------
with st.sidebar:
    st.header("1. Upload Resume")
    uploaded = st.file_uploader("PDF, DOCX or TXT", type=["pdf", "docx", "txt"])

    st.header("2. Target Role (optional)")
    role = st.selectbox("Compare against role skill taxonomy",
                         ["(none)"] + list(ROLE_SKILLS.keys()))
    role = None if role == "(none)" else role

    st.header("3. Job Description (optional)")
    jd_text = st.text_area("Paste a job description to compute keyword-match similarity",
                            height=180)

    analyze_btn = st.button("Analyze Resume", type="primary", use_container_width=True)

# --- Main panel -------------------------------------------------------
if analyze_btn:
    if not uploaded:
        st.warning("Please upload a resume file first.")
        st.stop()

    with st.spinner("Extracting and analyzing..."):
        text = extract_text(uploaded.read(), uploaded.name)
        if not text.strip():
            st.error("Could not extract any text from this file. Try a different file.")
            st.stop()
        parsed = parse_resume(text)
        result = score_resume(parsed, target_role=role, jd_text=jd_text)
        recs = recommend(result)

    # --- Overall score -----------------------------------------------
    col1, col2 = st.columns([1, 2])
    with col1:
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=result["overall_score"],
            title={"text": "Overall Profile Score"},
            gauge={"axis": {"range": [0, 100]},
                   "bar": {"color": "#2563eb"},
                   "steps": [
                       {"range": [0, 40], "color": "#fee2e2"},
                       {"range": [40, 70], "color": "#fef9c3"},
                       {"range": [70, 100], "color": "#dcfce7"},
                   ]}))
        fig.update_layout(height=300, margin=dict(t=40, b=10))
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        comp = result["components"]
        labels = list(comp.keys())
        values = [comp[k]["score"] for k in labels]
        radar = go.Figure()
        radar.add_trace(go.Scatterpolar(r=values, theta=labels, fill='toself', name='Score'))
        radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                             showlegend=False, height=300, margin=dict(t=20, b=20))
        st.plotly_chart(radar, use_container_width=True)

    st.caption(
        f"Weights applied: " +
        ", ".join(f"{k} {v*100:.0f}%" for k, v in result["weights_used"].items())
    )

    # --- Score breakdown -----------------------------------------------
    st.subheader("Score Breakdown (transparent & explainable)")
    tabs = st.tabs(["Completeness", "Skills Match", "Experience", "Formatting", "Keyword Alignment"])

    with tabs[0]:
        d = comp["completeness"]
        st.metric("Score", f"{d['score']}/100")
        st.write("**Sections found:**", ", ".join(d["sections_present"]) or "None")
        st.write("**Sections missing:**", ", ".join(d["sections_missing"]) or "None")

    with tabs[1]:
        d = comp["skills_match"]
        st.metric("Score", f"{d['score']}/100")
        if d.get("role"):
            st.write(f"Compared against **{d['role']}** skill taxonomy")
            c1, c2 = st.columns(2)
            with c1:
                st.write("✅ **Matched core skills:**", ", ".join(d["matched_core"]) or "None")
                st.write("✅ **Matched good-to-have:**", ", ".join(d["matched_good_to_have"]) or "None")
            with c2:
                st.write("❌ **Missing core skills:**", ", ".join(d["missing_core"]) or "None")
                st.write("❌ **Missing good-to-have:**", ", ".join(d["missing_good_to_have"]) or "None")
        else:
            st.write("**Skills detected:**", ", ".join(d["matched"]) or "None")
            st.info("Select a target role in the sidebar for a skill-gap comparison.")

    with tabs[2]:
        d = comp["experience"]
        st.metric("Score", f"{d['score']}/100")
        st.write(f"Estimated years of experience (from date ranges): **{d['estimated_years']}**")
        st.write(f"Quantified bullet points found: **{d['bullet_points']}**")

    with tabs[3]:
        d = comp["formatting"]
        st.metric("Score", f"{d['score']}/100")
        for note in d["notes"]:
            st.write("⚠️", note)
        if not d["notes"]:
            st.write("✅ No formatting issues detected.")

    with tabs[4]:
        d = comp["keyword_alignment"]
        st.metric("Score", f"{d['score']}/100" if d.get("similarity") is not None else "N/A")
        if d.get("similarity") is None:
            st.info(d.get("note"))
        else:
            st.write("TF-IDF cosine similarity between resume and job description.")

    # --- Recommendations -----------------------------------------------
    st.subheader("🎯 Recommendations (skill-gap based)")
    if recs:
        st.dataframe(pd.DataFrame(recs), use_container_width=True, hide_index=True)
    else:
        st.success("No major skill gaps detected for the selected role — strong profile match!")

    # --- Extracted contact info -----------------------------------------------
    with st.expander("Extracted contact details"):
        st.write("**Email:**", parsed.email or "Not found")
        st.write("**Phone:**", parsed.phone or "Not found")
        st.write("**LinkedIn:**", parsed.linkedin or "Not found")
        st.write("**GitHub:**", parsed.github or "Not found")

    st.caption(
        "Note: This score is based only on resume content (skills, structure, experience "
        "signals) and does not use name, gender, age, photo, or any demographic signal — "
        "see Documentation.md, Section 8 (Ethical & Unbiased AI Practices)."
    )

else:
    st.info("👈 Upload a resume and click **Analyze Resume** to get started.")
    st.markdown("""
    **What this tool does:**
    - Parses PDF/DOCX/TXT resumes
    - Extracts skills using NLP phrase matching against an industry skill taxonomy
    - Computes a transparent, weighted profile score (completeness, skills match,
      experience signals, formatting, and optional JD keyword alignment)
    - Flags missing skills relative to a target role and recommends learning resources
    """)
