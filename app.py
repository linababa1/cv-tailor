import io
import os
import json
import streamlit as st
from docx import Document
import fitz
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# --- LLM Setup ---
client = OpenAI(
    api_key=os.getenv("LLM_API_KEY"),
    base_url=os.getenv("LLM_BASE_URL") or None
)
MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-120b")

st.set_page_config(page_title="CV Tailor", page_icon="✍️", layout="wide")
st.title("✍️ AI CV Tailor & Cover Letter Generator")

# --- Helper to read PDF/DOCX ---
def extract_text(uploaded) -> str:
    name = uploaded.name.lower()
    data = uploaded.read()
    if name.endswith(".pdf"):
        doc = fitz.open(stream=data, filetype="pdf")
        return "\n".join(p.get_text() for p in doc)
    if name.endswith(".docx"):
        d = Document(io.BytesIO(data))
        return "\n".join(p.text for p in d.paragraphs)
    return data.decode("utf-8", errors="ignore")

# --- The AI Prompt ---
SYSTEM_PROMPT = """You are an expert CV writer and ATS (Applicant Tracking System) optimizer.
Your goal is to tailor a candidate's CV to a specific job description. 
CRITICAL RULE: Do NOT invent experience, degrees, or skills the candidate does not have. You may rephrase their existing experience to highlight relevant keywords and transferable skills.

Return ONLY a valid JSON object with this exact schema:
{
  "match_percentage": <integer 0-100>,
  "top_keywords": ["<5-8 critical keywords/skills from the JD>"],
  "keywords_missing_from_cv": ["<keywords from JD that the CV doesn't have yet>"],
  "ats_tips": ["<2-3 quick tips to beat the ATS for this job>"],
  "cv_rewrites": [
    {
      "original_bullet": "<a bullet point from the candidate's CV>",
      "tailored_bullet": "<the same bullet point rewritten to sound more impressive and match the JD>",
      "reason": "<why this change helps>"
    }
  ],
  "cover_letter": "<A full, 3-paragraph cover letter tailored to this specific job and company. Keep it professional and under 300 words.>"
}"""

# --- Layout ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Your Current CV")
    cv_file = st.file_uploader("Upload CV (PDF / DOCX / TXT)", type=["pdf", "docx", "txt"])
    cv_text = ""
    if cv_file:
        cv_text = extract_text(cv_file)
        st.success("CV loaded!")
        with st.expander("Preview CV Text"):
            st.text(cv_text[:1000] + "...")

with col2:
    st.subheader("2. The Job Description")
    jd_text = st.text_area("Paste the job description here", height=300)

st.divider()

# --- Action Button ---
if st.button("🚀 Tailor My Application", type="primary", use_container_width=True, disabled=not (cv_text and jd_text)):
    with st.spinner("AI is analyzing the job and rewriting your CV..."):
        try:
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"CANDIDATE CV:\n{cv_text}\n\n---\n\nJOB DESCRIPTION:\n{jd_text}"}
            ]
            
            response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.3
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # --- Display Results ---
            st.success(f"Analysis Complete! ATS Match Score: {result.get('match_percentage', 0)}%")
            
            st.subheader("🔑 Top Keywords to Include")
            st.info(", ".join(result.get("top_keywords", [])))
            
            if result.get("keywords_missing_from_cv"):
                st.warning(f"**Missing from your CV (add if you have them!):** {', '.join(result.get('keywords_missing_from_cv', []))}")
            
            st.subheader("📝 CV Bullet Point Upgrades")
            for rewrite in result.get("cv_rewrites", []):
                with st.expander(f"Original: {rewrite.get('original_bullet')}"):
                    st.markdown(f"**Tailored version:**\n> {rewrite.get('tailored_bullet')}")
                    st.caption(f"*Why:* {rewrite.get('reason')}")
            
            st.subheader("✉️ Tailored Cover Letter")
            st.text_area("Copy this letter:", value=result.get("cover_letter", ""), height=250)
            
        except Exception as e:
            st.error(f"An error occurred: {e}")