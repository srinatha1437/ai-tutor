# socratic_tutor_advanced_v2.py
"""
SocrAI Advanced Tutor — v2
Single-file app: FastAPI backend + Streamlit frontend
Adds: persona styles, fallacy detection, confidence estimation, argument tree extraction,
      collapsible turn details, session replay, export (JSON/text), concept mastery tracking.
Keeps: previous features (chat UI, reasoning map, summary, extract_terms, modes).

Fixes:
- Removed accidental trailing text that caused a runtime/syntax error.
- Moved the inline CSS injection to run after sidebar inputs so theme/font changes are applied on rerun.
"""

import os
import re
import json
import time
import threading
import requests
import streamlit as st
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from typing import Optional
import uvicorn
import openai
import base64
from datetime import datetime

# ------------------------------
# BACKEND (FastAPI)
# ------------------------------
app = FastAPI(title="SocrAI Advanced Tutor (v2)")

# Persistent in-memory storages for demo (replace with DB in prod)
CONVERSATIONS = []      # list of {"role":"student"/"ai","text":..., "ts":...}
REASONING_TRACE = []    # list of {"student_claim", "interpretation", "detected_issue", "detected_fallacies", "confidence", "follow_up"}
SESSION_PROFILES = {}   # per-user profile (demo keyed by token or 'default')

class DialogueRequest(BaseModel):
    mode: str
    persona: str
    topic: str
    student_text: str

def _extract_token(header: Optional[str]) -> str:
    if not header:
        return ""
    return header.split(" ")[1] if " " in header else header

# Persona templates
PERSONA_PROMPTS = {
    "Socrates": "Adopt the classical Socratic style: keep questions short, probing, and relentlessly focused on definitions and contradictions.",
    "Plato": "Adopt a Plato-like analytic tone: explore forms and idealized concepts, encourage abstraction.",
    "Modern Philosopher": "Adopt a contemporary analytic philosopher tone: precise, demand definitions, focus on argument structure.",
    "AI Ethicist": "Adopt a pragmatic ethicalist tone: use ethical frameworks, highlight real-world implications gently."
}

# Socratic modes
STYLE_PROMPTS = {
    "Gentle": "Ask softly reflective clarifying questions and gentle prompts, encouraging the student.",
    "Challenging": "Directly expose contradictions, push for precision, and demand justifications.",
    "Philosophical": "Probe abstract principles, meta-ethical angles, and deeper conceptual distinctions."
}

# Utility: call OpenAI chat
def call_openai_chat(messages, model="gpt-4o-mini", temperature=0.6, max_tokens=400, api_key=None):
    if api_key:
        openai.api_key = api_key
    resp = openai.ChatCompletion.create(model=model, messages=messages, temperature=temperature, max_tokens=max_tokens)
    return resp["choices"][0]["message"]["content"]

@app.post("/api/dialogue")
async def dialogue(req: DialogueRequest, authorization: Optional[str] = Header(None)):
    token = _extract_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing Authorization header with token")
    # minimal user identity for demo
    user_id = token[:8]
    if user_id not in SESSION_PROFILES:
        SESSION_PROFILES[user_id] = {"persona": req.persona, "history_count": 0, "concept_counts": {}}

    # Build system prompt combining persona + style
    persona_prompt = PERSONA_PROMPTS.get(req.persona, "")
    style_prompt = STYLE_PROMPTS.get(req.mode, "")
    system_prompt = (
        "You are SocrAI, an advanced AI Socratic tutor. "
        f"{persona_prompt} {style_prompt} "
        "Your role is to ask open-ended, context-aware questions that help the student refine their thinking. "
        "Never provide direct answers or final judgments. Instead detect potential logical flaws, unstated assumptions, and contradictions. "
        "When you respond, return a JSON object ONLY with keys: "
        "'question' (string), "
        "'detection' (short note or '(none)'), "
        "'fallacies' (list of detected fallacy labels, may be empty), "
        "'confidence' (number 0-100), "
        "'meta' (short interpretation)."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Topic: {req.topic}. Student says: {req.student_text}"}
    ]

    try:
        # ask the model for a structured response
        raw = call_openai_chat(messages, api_key=token)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OpenAI error: {e}")

    # Parse JSON object embedded in output (robustly)
    m = re.search(r"\{.*\}", raw, re.S)
    question = raw.strip()
    detection = "(none)"
    fallacies = []
    confidence = None
    meta = "(auto)"
    if m:
        try:
            data = json.loads(m.group(0))
            question = data.get("question", question)
            detection = data.get("detection", detection)
            fallacies = data.get("fallacies", [])
            confidence = data.get("confidence", None)
            meta = data.get("meta", meta)
        except Exception:
            # fallback: try to extract simple patterns
            pass

    # Fallback: if confidence missing, ask model for quick confidence estimate
    if confidence is None:
        try:
            conf_msg = [
                {"role":"system","content":"You are a short estimator. Given a student claim, output a single integer 0-100 representing confidence that the claim is well-supported."},
                {"role":"user","content":req.student_text}
            ]
            c_raw = call_openai_chat(conf_msg, temperature=0.0, max_tokens=20, api_key=token)
            c_m = re.search(r"(\d{1,3})", c_raw)
            if c_m:
                confidence = min(100, max(0, int(c_m.group(1))))
            else:
                confidence = 50
        except Exception:
            confidence = 50

    # Persist conversation + reasoning trace
    timestamp = time.time()
    CONVERSATIONS.append({"role":"student","text":req.student_text,"ts":timestamp,"user":user_id})
    CONVERSATIONS.append({"role":"ai","text":question,"ts":timestamp+0.001,"user":user_id})
    REASONING_TRACE.append({
        "student_claim": req.student_text,
        "interpretation": meta or "(auto)",
        "detected_issue": detection or "(none)",
        "detected_fallacies": fallacies,
        "confidence": confidence,
        "follow_up": question,
        "ts": timestamp,
        "user": user_id
    })

    # Track concept counts using a light-weight extraction (call simple extraction)
    try:
        term_msg = [
            {"role":"system","content":"Extract 3-6 key terms as JSON: {\"terms\": [...]}."},
            {"role":"user","content":req.student_text}
        ]
        t_raw = call_openai_chat(term_msg, temperature=0.0, max_tokens=120, api_key=token)
        t_m = re.search(r"\{.*\}", t_raw, re.S)
        if t_m:
            t_json = json.loads(t_m.group(0))
            for term in t_json.get("terms", []):
                SESSION_PROFILES[user_id]["concept_counts"][term] = SESSION_PROFILES[user_id]["concept_counts"].get(term, 0) + 1
    except Exception:
        pass

    SESSION_PROFILES[user_id]["history_count"] += 1

    return {"new_turns": [{"role":"ai","text":question}], "status":"ok", "detected_fallacies": fallacies, "confidence": confidence}

@app.get("/api/trace")
async def get_trace(authorization: Optional[str] = Header(None)):
    # Optionally filter by user token
    token = _extract_token(authorization)
    user_id = token[:8] if token else None
    if user_id:
        filtered = [t for t in REASONING_TRACE if t.get("user")==user_id]
    else:
        filtered = REASONING_TRACE
    return {"trace": filtered}

@app.get("/api/summary")
async def get_summary(authorization: Optional[str] = Header(None)):
    token = _extract_token(authorization)
    user_id = token[:8] if token else None
    if user_id:
        trace = [t for t in REASONING_TRACE if t.get("user")==user_id]
    else:
        trace = REASONING_TRACE
    if not trace:
        return {"summary":"No reasoning trace available.", "score":100, "flaws":0, "total":0}
    flaws = sum(1 for t in trace if t.get("detected_issue") and t.get("detected_issue") != "(none)")
    total = len(trace)
    score = max(0, 100 - flaws * 8)
    summary_text = f"During this dialogue, {total} turns were analyzed. {flaws} potential logical issues or assumptions were detected. Reasoning consistency score: {score}/100."
    return {"summary": summary_text, "score": score, "flaws": flaws, "total": total}

@app.post("/api/extract_terms")
async def extract_terms(req: DialogueRequest, authorization: Optional[str] = Header(None)):
    token = _extract_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing Authorization header with token")
    try:
        prompt_system = "Extract 3-6 key abstract/philosophical terms or short phrases and return JSON: {\"terms\": [..]}"
        messages = [{"role":"system","content":prompt_system},{"role":"user","content":req.student_text}]
        content = call_openai_chat(messages, temperature=0.0, max_tokens=200, api_key=token)
        m = re.search(r"\{.*\}", content, re.S)
        if m:
            return json.loads(m.group(0))
    except Exception:
        pass
    # fallback
    words = re.findall(r"\b[A-Z][a-zA-Z]{3,}\b", req.student_text)
    uniq = list(dict.fromkeys(words))[:6]
    return {"terms": uniq}

# ------------------------------
# Backend server thread
# ------------------------------
def run_backend():
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="error")

threading.Thread(target=run_backend, daemon=True).start()

# ------------------------------
# FRONTEND (Streamlit)
# ------------------------------
API_BASE = "http://localhost:8000"

# Theme & session init
if "theme" not in st.session_state:
    st.session_state.theme = {"primary_color":"#4f46e5","background_color":"#0f172a","font_size":16,"card_radius":12}
if "conversation" not in st.session_state:
    st.session_state.conversation = []
if "session_history" not in st.session_state:
    st.session_state.session_history = []  # list of summary scores
if "api_key" not in st.session_state:
    st.session_state.api_key = ""

st.set_page_config(page_title="SocrAI Advanced Tutor v2", layout="wide")
# NOTE: CSS injection moved *after* the sidebar inputs so updates to session_state.theme
# caused by the sidebar take effect when the script reruns.

st.title("🧠 SocrAI — Advanced AI Socratic Tutor (v2)")

# Sidebar controls
with st.sidebar:
    st.header("⚙️ Settings")
    api_key_input = st.text_input("🔑 OpenAI API key", type="password", value=st.session_state.api_key)
    if st.button("Save API Key"):
        st.session_state.api_key = api_key_input.strip()
        st.success("✅ API key saved for this session")
    st.markdown("---")
    st.subheader("Persona & Mode")
    persona = st.selectbox("Persona", ["Socrates","Plato","Modern Philosopher","AI Ethicist"])
    mode = st.selectbox("Socratic Mode", ["Gentle","Challenging","Philosophical"])
    st.markdown("---")
    st.subheader("Theme")
    # These inputs update st.session_state.theme directly; because Streamlit reruns the script after interaction,
    # the CSS injection placed after this block will pick up the new values.
    st.session_state.theme["primary_color"] = st.color_picker("Primary color", st.session_state.theme["primary_color"])
    st.session_state.theme["background_color"] = st.color_picker("Background color", st.session_state.theme["background_color"])
    st.session_state.theme["font_size"] = st.slider("Font Size", 12, 24, st.session_state.theme["font_size"])
    st.markdown("---")
    st.subheader("Session")
    if st.button("📤 Export Full Session JSON"):
        try:
            payload = {"conversations": CONVERSATIONS, "trace": REASONING_TRACE, "profiles": SESSION_PROFILES}
            data_str = json.dumps(payload, indent=2)
            b = data_str.encode("utf-8")
            st.download_button("Download JSON", b, file_name=f"socrai_session_{int(time.time())}.json", mime="application/json")
        except Exception as e:
            st.error(f"Export failed: {e}")
    if st.button("📄 Export Plaintext Report"):
        try:
            lines = []
            lines.append("SocrAI Session Report")
            lines.append(f"Exported: {datetime.utcnow().isoformat()} UTC")
            lines.append("="*40)
            for t in REASONING_TRACE:
                lines.append(f"Claim: {t['student_claim']}")
                lines.append(f"Issue: {t.get('detected_issue','(none)')}")
                lines.append(f"Fallacies: {', '.join(t.get('detected_fallacies',[])) if t.get('detected_fallacies') else '(none)'}")
                lines.append(f"Confidence: {t.get('confidence')}")
                lines.append(f"Follow-up: {t.get('follow_up')}")
                lines.append("-"*30)
            text_blob = "\n".join(lines)
            st.download_button("Download TXT", text_blob, file_name=f"socrai_report_{int(time.time())}.txt", mime="text/plain")
        except Exception as e:
            st.error(f"Export failed: {e}")

# Apply inline CSS after sidebar so the latest session_state.theme values are used
st.markdown(
    f"""
    <style>
    /* Page background & font sizing */
    body, .stApp {{
        background: {st.session_state.theme['background_color']};
        color: #e6eef8;
        font-size: {st.session_state.theme['font_size']}px;
    }}
    /* Primary color variables (used for custom components if you use them) */
    :root {{
        --socrai-primary: {st.session_state.theme['primary_color']};
    }}
    /* Make chat message cards slightly rounded using theme radius */
    .stChatMessage, .stButton > button, .stDownloadButton > button {{
        border-radius: {st.session_state.theme['card_radius']}px !important;
    }}
    </style>
    """,
    unsafe_allow_html=True
)

# Main layout
col1, col2 = st.columns([3,1])

with col1:
    topic = st.text_input("Topic", value="What is justice?")
    user_input = st.text_area("Your argument or question:", height=140)

    if st.button("💬 Start Dialogue"):
        if not st.session_state.api_key:
            st.error("⚠️ Please enter & Save your OpenAI API key in the sidebar first.")
        elif not user_input.strip():
            st.warning("✏️ Write something first.")
        else:
            # show student turn locally
            ts = time.time()
            st.session_state.conversation.append({"role":"student","text":user_input.strip(),"ts":ts})
            payload = {"mode": mode, "persona": persona, "topic": topic, "student_text": user_input.strip()}
            headers = {"Authorization": f"Bearer {st.session_state.api_key}"}
            with st.spinner("🤔 SocrAI is forming a question..."):
                try:
                    resp = requests.post(f"{API_BASE}/api/dialogue", json=payload, headers=headers, timeout=60)
                    if resp.status_code == 200:
                        data = resp.json()
                        for t in data.get("new_turns", []):
                            st.session_state.conversation.append({"role": t["role"], "text": t["text"], "ts": time.time()})
                        # Optionally add mini local note about confidence/fallacies
                        cf = data.get("confidence", None)
                        ff = data.get("detected_fallacies", [])
                        if cf is not None:
                            st.success(f"Confidence estimate: {cf} / 100")
                        if ff:
                            st.warning(f"Detected fallacies: {', '.join(ff)}")
                    else:
                        st.error(f"❌ Backend error: {resp.status_code} — {resp.text}")
                except Exception as e:
                    st.error(f"Request failed: {e}")

    st.markdown("---")
    st.subheader("Conversation")
    if st.session_state.conversation:
        for msg in st.session_state.conversation[-60:]:
            if msg["role"] == "student":
                with st.chat_message("user"):
                    st.markdown(msg["text"])
            else:
                with st.chat_message("assistant"):
                    st.markdown(msg["text"])
    else:
        st.info("Start a dialogue to see SocrAI's questions here.")

    st.markdown("---")
    # Session replay
    if st.button("▶️ Replay Session"):
        if not st.session_state.conversation:
            st.info("No conversation to replay.")
        else:
            replay_placeholder = st.empty()
            for msg in st.session_state.conversation[-60:]:
                if msg["role"] == "student":
                    replay_placeholder.markdown(f"**🧑 You:** {msg['text']}")
                else:
                    replay_placeholder.markdown(f"**🤖 SocrAI:** {msg['text']}")
                time.sleep(0.9)  # small delay to simulate replay
            replay_placeholder.markdown("**Replay finished.**")

with col2:
    st.markdown("### 🧩 Reasoning Trace & Tools")

    if st.button("Show reasoning trace"):
        try:
            resp = requests.get(f"{API_BASE}/api/trace", headers={"Authorization": f"Bearer {st.session_state.get('api_key','')}"} )
            if resp.status_code == 200:
                trace = resp.json().get("trace", [])
                if not trace:
                    st.info("No reasoning trace yet.")
                else:
                    # display each trace item in an expander for details
                    for t in trace[-12:][::-1]:
                        title = (t['student_claim'][:60] + '...') if len(t['student_claim'])>63 else t['student_claim']
                        with st.expander(title):
                            st.write(f"**Full claim:** {t['student_claim']}")
                            st.write(f"**Interpretation:** {t.get('interpretation')}")
                            st.write(f"**Detected issue:** {t.get('detected_issue')}")
                            st.write(f"**Detected fallacies:** {', '.join(t.get('detected_fallacies',[])) if t.get('detected_fallacies') else '(none)'}")
                            st.write(f"**Confidence:** {t.get('confidence')}")
                            st.write(f"**Follow-up question:** {t.get('follow_up')}")
                            st.write(f"**Timestamp:** {datetime.utcfromtimestamp(t.get('ts')).isoformat()} UTC")
            else:
                st.error("Could not fetch reasoning trace.")
        except Exception as e:
            st.error(f"Trace fetch error: {e}")

    st.markdown("---")
    # Reasoning Map (graph) with fallback
    st.markdown("#### Visual Reasoning Map")
    try:
        from streamlit_agraph import agraph, Node, Edge, Config
        has_agraph = True
    except Exception:
        has_agraph = False

    if st.button("🧩 Show Reasoning Map"):
        try:
            resp = requests.get(f"{API_BASE}/api/trace", headers={"Authorization": f"Bearer {st.session_state.get('api_key','')}"} )
            if resp.status_code == 200:
                trace = resp.json().get("trace", [])
                if not trace:
                    st.info("No trace yet.")
                else:
                    if has_agraph:
                        nodes, edges = [], []
                        for i, t in enumerate(trace):
                            color = "#22c55e" if (not t.get("detected_issue") or t.get("detected_issue")=="(none)") else "#ef4444"
                            label = (t["student_claim"][:40] + "...") if len(t["student_claim"])>43 else t["student_claim"]
                            nodes.append(Node(id=str(i), label=label, size=14, color=color))
                            if i>0:
                                edges.append(Edge(source=str(i-1), target=str(i)))
                        config = Config(width=340, height=340, directed=True, physics=True)
                        agraph(nodes=nodes, edges=edges, config=config)
                    else:
                        st.warning("streamlit-agraph not installed — showing textual map")
                        for i, t in enumerate(trace):
                            st.markdown(f"- [{i}] {t['student_claim'][:80]} — Issue: {t['detected_issue']}")
            else:
                st.error("Could not fetch trace for map.")
        except Exception as e:
            st.error(f"Reasoning map error: {e}")

    st.markdown("---")
    st.markdown("#### Key Concepts / Mastery")
    if st.button("Extract Key Terms from Last Student Turn"):
        if not st.session_state.api_key:
            st.error("Save your OpenAI API key first.")
        else:
            last_student = None
            for m in reversed(st.session_state.conversation):
                if m["role"]=="student":
                    last_student = m["text"]; break
            if not last_student:
                st.warning("No student turn yet.")
            else:
                payload = {"mode": mode, "persona": persona, "topic": topic, "student_text": last_student}
                try:
                    resp = requests.post(f"{API_BASE}/api/extract_terms", json=payload, headers={"Authorization": f"Bearer {st.session_state.api_key}"}, timeout=30)
                    if resp.status_code == 200:
                        terms = resp.json().get("terms", [])
                        if not terms:
                            st.info("No key terms found.")
                        else:
                            for t in terms:
                                st.markdown(f"- **{t}**")
                    else:
                        st.error("Failed to extract terms.")
                except Exception as e:
                    st.error(f"Extract error: {e}")

    st.markdown("---")
    st.markdown("#### Progress & Analytics")
    if st.button("📈 Show Progress Chart"):
        if st.session_state.session_history:
            st.line_chart(st.session_state.session_history)
        else:
            st.info("No session summaries saved yet. Generate a summary from the main area to record progress.")

# End-of-dialogue summary action at bottom (global)
st.markdown("---")
if st.button("🧾 End Dialogue & Generate Summary"):
    if not st.session_state.api_key:
        st.error("Save your OpenAI API key first.")
    else:
        try:
            resp = requests.get(f"{API_BASE}/api/summary", headers={"Authorization": f"Bearer {st.session_state.api_key}"} )
            if resp.status_code == 200:
                summary = resp.json()
                st.success(summary["summary"])
                st.metric("Reasoning Consistency Score", f"{summary['score']} / 100")
                st.session_state.session_history.append(summary["score"])
                st.progress(summary["score"]/100 if summary["score"] is not None else 0.0)
            else:
                st.error("Could not fetch summary.")
        except Exception as e:
            st.error(f"Summary error: {e}")

st.markdown('<small>⚠️ Demo mode: keep API keys private. Use server-side key management for production.</small>', unsafe_allow_html=True)
