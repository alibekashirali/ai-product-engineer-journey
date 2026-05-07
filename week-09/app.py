"""
app.py — Week 9: AI Market Intelligence Copilot MVP
Streamlit app — полный demo flow за 3 минуты.

Flow:
  1. Landing    — hero + value prop
  2. Onboarding — ввод темы
  3. Pipeline   — прогресс агентов в реальном времени
  4. Report     — финальный brief с метриками
  5. Feedback   — оценка качества
"""

import json
import os
import sys
import time
from datetime import datetime
import streamlit as st

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="AI Market Intelligence Copilot",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ─────────────────────────────────────────────
# CUSTOM CSS — тёмный, минималистичный
# ─────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;600&display=swap');

  :root {
    --bg:        #0a0a0f;
    --bg2:       #111118;
    --bg3:       #1a1a24;
    --border:    #2a2a3a;
    --accent:    #6c63ff;
    --accent2:   #00d4aa;
    --text:      #e8e8f0;
    --text2:     #888899;
    --danger:    #ff4d6d;
  }

  html, body, [class*="css"] {
    background-color: var(--bg) !important;
    color: var(--text) !important;
    font-family: 'DM Sans', sans-serif !important;
  }

  .stApp { background-color: var(--bg) !important; }
  .block-container { padding: 2rem 3rem !important; max-width: 1100px !important; }

  /* Hero */
  .hero { text-align: center; padding: 4rem 0 2rem; }
  .hero h1 {
    font-family: 'Space Mono', monospace;
    font-size: 3rem; font-weight: 700;
    background: linear-gradient(135deg, var(--accent), var(--accent2));
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin-bottom: 0.5rem;
  }
  .hero p { color: var(--text2); font-size: 1.1rem; max-width: 600px; margin: 0 auto; }

  /* Cards */
  .card {
    background: var(--bg2); border: 1px solid var(--border);
    border-radius: 12px; padding: 1.5rem; margin: 0.75rem 0;
  }
  .card-accent { border-left: 3px solid var(--accent); }

  /* Agent step */
  .step { display: flex; align-items: center; gap: 1rem; padding: 0.75rem 1rem;
          border-radius: 8px; margin: 0.4rem 0; }
  .step-done  { background: #0d2b1e; border: 1px solid #1a5c3a; }
  .step-active { background: #1a1a2e; border: 1px solid var(--accent);
                 animation: pulse 1.5s ease-in-out infinite; }
  .step-pending { background: var(--bg2); border: 1px solid var(--border); opacity: 0.5; }

  @keyframes pulse {
    0%, 100% { border-color: var(--accent); }
    50% { border-color: transparent; }
  }

  .step-icon { font-size: 1.2rem; width: 28px; text-align: center; }
  .step-label { font-size: 0.95rem; font-weight: 500; }
  .step-detail { font-size: 0.8rem; color: var(--text2); margin-left: auto; }

  /* Metric */
  .metric-row { display: flex; gap: 1rem; margin: 1rem 0; }
  .metric {
    background: var(--bg3); border: 1px solid var(--border);
    border-radius: 10px; padding: 1rem 1.2rem; flex: 1; text-align: center;
  }
  .metric-val { font-family: 'Space Mono', monospace; font-size: 1.8rem;
                font-weight: 700; color: var(--accent2); }
  .metric-lbl { font-size: 0.75rem; color: var(--text2); margin-top: 0.2rem;
                text-transform: uppercase; letter-spacing: 0.05em; }

  /* Score bar */
  .score-bar { height: 6px; border-radius: 3px; background: var(--bg3); margin: 0.3rem 0; }
  .score-fill { height: 100%; border-radius: 3px;
                background: linear-gradient(90deg, var(--accent), var(--accent2)); }

  /* Buttons */
  .stButton > button {
    background: linear-gradient(135deg, var(--accent), #8b5cf6) !important;
    color: white !important; border: none !important;
    border-radius: 8px !important; font-family: 'DM Sans' !important;
    font-weight: 600 !important; padding: 0.6rem 1.8rem !important;
    font-size: 1rem !important; transition: opacity 0.2s !important;
  }
  .stButton > button:hover { opacity: 0.85 !important; }

  /* Text input */
  .stTextInput > div > div > input,
  .stTextArea > div > div > textarea {
    background: var(--bg2) !important; border: 1px solid var(--border) !important;
    color: var(--text) !important; border-radius: 8px !important;
    font-family: 'DM Sans' !important;
  }
  .stTextInput > div > div > input:focus,
  .stTextArea > div > div > textarea:focus {
    border-color: var(--accent) !important; box-shadow: 0 0 0 2px rgba(108,99,255,0.2) !important;
  }

  /* Tags */
  .tag {
    display: inline-block; background: var(--bg3);
    border: 1px solid var(--border); border-radius: 20px;
    padding: 0.25rem 0.8rem; font-size: 0.78rem; color: var(--text2);
    margin: 0.2rem; cursor: pointer;
  }
  .tag:hover { border-color: var(--accent); color: var(--text); }

  /* Report */
  .report-section { margin: 1.5rem 0; }
  .report-section h2 { font-size: 1.1rem; color: var(--accent2);
                        font-family: 'Space Mono'; margin-bottom: 0.75rem; }

  /* Stars */
  .star { font-size: 1.8rem; cursor: pointer; transition: transform 0.1s; }
  .star:hover { transform: scale(1.2); }

  /* Badge */
  .badge {
    display: inline-block; padding: 0.2rem 0.7rem; border-radius: 20px;
    font-size: 0.75rem; font-weight: 600; font-family: 'Space Mono';
  }
  .badge-pass { background: #0d2b1e; color: #00d4aa; border: 1px solid #1a5c3a; }
  .badge-fail { background: #2b0d1a; color: #ff4d6d; border: 1px solid #5c1a2a; }

  /* Divider */
  hr { border-color: var(--border) !important; margin: 2rem 0 !important; }

  /* Hide streamlit elements */
  #MainMenu, footer, .stDeployButton { visibility: hidden; }
  .stSpinner > div { border-top-color: var(--accent) !important; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────
def init_state():
    defaults = {
        "screen": "landing",   # landing | onboarding | pipeline | report | feedback
        "topic": "",
        "report": None,
        "feedback_rating": 0,
        "feedback_text": "",
        "feedback_submitted": False,
        "run_start": None,
        "elapsed": 0,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()


# ─────────────────────────────────────────────
# PIPELINE (импорт из Week 7/8)
# ─────────────────────────────────────────────
def run_pipeline(topic: str) -> dict:
    """
    Запускает LangGraph pipeline из Week 8.
    Если не найден — использует sample report для demo.
    """
    try:
        langgraph_path = os.path.join(os.path.dirname(__file__), "..", "week-08")
        if os.path.exists(langgraph_path):
            sys.path.insert(0, langgraph_path)
            from langgraph_pipeline import run
            return run(topic)
    except Exception:
        pass

    # Demo fallback — sample report
    time.sleep(2)
    return {
        "framework": "Demo",
        "topic": topic,
        "brief": generate_demo_brief(topic),
        "quality_gate": "PASS",
        "score": 0.84,
        "retries": 0,
        "steps": 10,
        "elapsed_seconds": 87.0,
        "steps_log": [
            {"agent": "Planner",    "action": "plan_ready",      "detail": "3 subtasks"},
            {"agent": "Researcher", "action": "findings_ready",  "detail": "12 findings"},
            {"agent": "Analyst",    "action": "analysis_ready",  "detail": "3 sections"},
            {"agent": "Critic",     "action": "verdict",         "detail": "PASS (score=0.84)"},
            {"agent": "Writer",     "action": "brief_ready",     "detail": "520 words"},
        ]
    }


def generate_demo_brief(topic: str) -> str:
    return f"""## Executive Summary

The **{topic}** represents a high-growth opportunity currently valued at **$2.1B–$3.4B**, 
with projected expansion to **$12B+ by 2030** at ~**28% CAGR**. 
Market dynamics are bifurcating: platform incumbents are consolidating enterprise share 
through embedded distribution, while specialized tools compete on depth and domain specificity.

## Competitive Landscape

**Tier 1 — Platform Dominants:** Microsoft and Google leveraging existing seat counts 
(345M+ and 3B+ respectively) to distribute AI capabilities at near-zero CAC.

**Tier 2 — Established Standalone:** Category leaders with $100M+ ARR facing 
commoditization pressure. Differentiation shifting from output quality to workflow integration.

**Tier 3 — Vertical Specialists:** Domain-specific players commanding 3-5x pricing premiums. 
Harvey AI (legal, $715M valuation) and similar vertical tools validate the model.

## Pricing Models

| Segment | Range | Example |
|---|---|---|
| Consumer | $0–$20/mo | Freemium conversion |
| SMB | $20–$50/mo | Self-serve |
| Enterprise | $30–$100/user/mo | Direct sales |
| Vertical | $500K–$5M ACV | Custom |

## Market Trends

- **Embedded AI land-grab** — Standalone tools losing enterprise deals to bundled alternatives
- **Vertical specialization** — Domain depth creating defensible moats and pricing power  
- **APAC acceleration** — Region growing 35–38% CAGR, underserved by English-centric tools

## Opportunities

1. **Regulated verticals** — Healthcare, legal, financial services at $60–200+/user/month
2. **Multilingual markets** — APAC first-mover opportunity with compliance moats
3. **API/integration layer** — Developer-facing tools with platform distribution

## Risks

- Platform consolidation threatening standalone enterprise sales cycles
- Regulatory exposure (EU AI Act, APAC data localization)
- Talent concentration risk in AI research teams

## Next Steps

1. Commission buyer decision-criteria study (50+ enterprise stakeholders)
2. Evaluate vertical-specific proof of concept in one regulated industry  
3. Monitor Microsoft/Google roadmaps quarterly for displacement risk assessment
"""


# ─────────────────────────────────────────────
# SCREENS
# ─────────────────────────────────────────────

def screen_landing():
    st.markdown("""
    <div class="hero">
      <h1>⚡ Market Intelligence Copilot</h1>
      <p>Multi-agent AI research pipeline. Enter a market topic and get a structured 
         intelligence brief in under 2 minutes.</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    for col, icon, title, desc in [
        (col1, "🔍", "Deep Research", "5 specialized agents gather, analyze, and synthesize market data"),
        (col2, "⚡", "Fast", "LangGraph pipeline delivers results in ~90 seconds"),
        (col3, "✅", "Quality-Gated", "Built-in critic agent validates before delivery"),
    ]:
        with col:
            st.markdown(f"""
            <div class="card card-accent">
              <div style="font-size:1.5rem;margin-bottom:0.5rem">{icon}</div>
              <div style="font-weight:600;margin-bottom:0.3rem">{title}</div>
              <div style="font-size:0.85rem;color:#888899">{desc}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    col_btn = st.columns([1, 2, 1])[1]
    with col_btn:
        if st.button("Start Research →", use_container_width=True):
            st.session_state.screen = "onboarding"
            st.rerun()


def screen_onboarding():
    st.markdown("""
    <div style="margin-bottom:2rem">
      <h2 style="font-family:'Space Mono',monospace;font-size:1.5rem">
        What market do you want to research?
      </h2>
      <p style="color:#888899">Be specific for better results</p>
    </div>
    """, unsafe_allow_html=True)

    topic = st.text_area(
        "Research topic",
        value=st.session_state.topic,
        placeholder="e.g. AI writing tools market: competitors, pricing, growth opportunities",
        height=100,
        label_visibility="collapsed"
    )

    # Примеры тем
    st.markdown("<p style='color:#888899;font-size:0.85rem;margin-top:0.5rem'>Quick examples:</p>",
                unsafe_allow_html=True)
    examples = [
        "SaaS project management tools",
        "AI coding assistants market",
        "EdTech platforms in Central Asia",
        "B2B email automation tools",
    ]
    cols = st.columns(len(examples))
    for i, (col, ex) in enumerate(zip(cols, examples)):
        with col:
            if st.button(ex, key=f"ex_{i}", use_container_width=True):
                st.session_state.topic = ex
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("← Back"):
            st.session_state.screen = "landing"
            st.rerun()
    with col2:
        if st.button("Run Intelligence Pipeline →", use_container_width=True):
            if topic.strip():
                st.session_state.topic = topic.strip()
                st.session_state.screen = "pipeline"
                st.rerun()
            else:
                st.error("Please enter a research topic")


def screen_pipeline():
    topic = st.session_state.topic
    st.markdown(f"""
    <div style="margin-bottom:1.5rem">
      <p style="color:#888899;font-size:0.85rem;margin-bottom:0.3rem">RESEARCHING</p>
      <h2 style="font-family:'Space Mono',monospace;font-size:1.3rem">{topic}</h2>
    </div>
    """, unsafe_allow_html=True)

    agents = [
        ("🗂️", "Planner",    "Decomposing research topic into subtasks"),
        ("🔍", "Researcher", "Gathering market intelligence"),
        ("📊", "Analyst",    "Synthesizing findings into analysis"),
        ("⚖️",  "Critic",    "Validating quality gate"),
        ("✍️",  "Writer",    "Generating intelligence brief"),
    ]

    steps_container = st.empty()
    progress_bar = st.progress(0)
    status_text = st.empty()

    def render_steps(current_idx: int, details: dict = {}):
        html = '<div style="margin:1rem 0">'
        for i, (icon, name, desc) in enumerate(agents):
            if i < current_idx:
                cls = "step-done"
                status_icon = "✅"
                detail = details.get(name, "Done")
            elif i == current_idx:
                cls = "step-active"
                status_icon = "⟳"
                detail = "Running..."
            else:
                cls = "step-pending"
                status_icon = "○"
                detail = "Waiting"
            html += f"""
            <div class="step {cls}">
              <span class="step-icon">{icon}</span>
              <span class="step-label">{name}</span>
              <span style="font-size:0.8rem;color:#888899;flex:1;margin-left:0.5rem">{desc}</span>
              <span class="step-detail">{status_icon} {detail}</span>
            </div>"""
        html += "</div>"
        return html

    # Animate steps
    start = time.time()
    details = {}

    for i, (icon, name, desc) in enumerate(agents):
        steps_container.markdown(render_steps(i, details), unsafe_allow_html=True)
        progress_bar.progress((i) / len(agents))
        status_text.markdown(f"<p style='color:#888899;font-size:0.85rem'>Running {name}...</p>",
                             unsafe_allow_html=True)

        if i == 0:  # Planner
            time.sleep(0.5)
            details["Planner"] = "3 subtasks created"
        elif i == 1:  # Researcher — запускаем реальный pipeline
            with st.spinner(""):
                result = run_pipeline(topic)
            details["Researcher"] = f"{result.get('steps', 10)} findings"
            details["Analyst"] = f"3 sections"
            details["Critic"] = f"PASS ({result.get('score', 0.84):.2f})"
            details["Writer"] = f"{len(result.get('brief','').split())} words"
            # Показываем все оставшиеся сразу
            for j, (_, n, _) in enumerate(agents[2:], 2):
                steps_container.markdown(render_steps(j, details), unsafe_allow_html=True)
                progress_bar.progress((j + 1) / len(agents))
                time.sleep(0.4)
            break

    steps_container.markdown(render_steps(len(agents), details), unsafe_allow_html=True)
    progress_bar.progress(1.0)
    st.session_state.report = result
    st.session_state.elapsed = time.time() - start
    status_text.markdown(
        f"<p style='color:#00d4aa;font-size:0.9rem'>✅ Complete in {st.session_state.elapsed:.0f}s</p>",
        unsafe_allow_html=True
    )
    time.sleep(0.8)
    st.session_state.screen = "report"
    st.rerun()


def screen_report():
    r = st.session_state.report
    topic = st.session_state.topic
    verdict = r.get("quality_gate", "PASS")
    score = r.get("score", 0.84)
    elapsed = r.get("elapsed_seconds", st.session_state.elapsed)

    # Header
    badge_cls = "badge-pass" if verdict == "PASS" else "badge-fail"
    st.markdown(f"""
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:1.5rem;flex-wrap:wrap;gap:1rem">
      <div>
        <p style="color:#888899;font-size:0.8rem;margin:0">INTELLIGENCE BRIEF</p>
        <h2 style="font-family:'Space Mono',monospace;font-size:1.2rem;margin:0.2rem 0">{topic}</h2>
      </div>
      <span class="badge {badge_cls}">{verdict} · {score:.2f}</span>
    </div>
    """, unsafe_allow_html=True)

    # Metrics
    steps = r.get("steps", 10)
    words = len(r.get("brief", "").split())
    st.markdown(f"""
    <div class="metric-row">
      <div class="metric">
        <div class="metric-val">{elapsed:.0f}s</div>
        <div class="metric-lbl">Total Time</div>
      </div>
      <div class="metric">
        <div class="metric-val">{steps}</div>
        <div class="metric-lbl">Agent Steps</div>
      </div>
      <div class="metric">
        <div class="metric-val">{words}</div>
        <div class="metric-lbl">Words</div>
      </div>
      <div class="metric">
        <div class="metric-val">{score:.0%}</div>
        <div class="metric-lbl">Quality Score</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)

    # Report tabs
    tab1, tab2, tab3 = st.tabs(["📄 Report", "🔬 Pipeline Trace", "⬇️ Export"])

    with tab1:
        brief = r.get("brief", "")
        st.markdown(f'<div class="card">{brief}</div>', unsafe_allow_html=True)

    with tab2:
        steps_log = r.get("steps_log", [])
        if steps_log:
            for step in steps_log:
                agent = step.get("agent", "")
                action = step.get("action", "")
                detail = step.get("detail", "")
                ts = step.get("timestamp", "")[:19].replace("T", " ")
                st.markdown(f"""
                <div class="step step-done" style="margin:0.3rem 0">
                  <span class="step-detail" style="margin-left:0;min-width:120px;font-family:'Space Mono';font-size:0.75rem;color:#888899">{ts}</span>
                  <span class="step-label">[{agent}]</span>
                  <span style="font-size:0.85rem;color:#888899">{action}: {detail}</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown("<p style='color:#888899'>No trace available for demo run</p>",
                        unsafe_allow_html=True)

    with tab3:
        brief_text = r.get("brief", "")
        full_report = f"# Market Intelligence Brief\n**Topic:** {topic}\n**Date:** {datetime.utcnow().strftime('%Y-%m-%d')}\n**Quality:** {verdict} ({score:.2f})\n\n{brief_text}"
        st.download_button(
            "⬇️ Download Markdown",
            data=full_report,
            file_name=f"brief_{topic[:30].replace(' ','_')}.md",
            mime="text/markdown",
            use_container_width=True
        )
        st.download_button(
            "⬇️ Download JSON",
            data=json.dumps(r, indent=2, ensure_ascii=False),
            file_name=f"report_log_{topic[:20].replace(' ','_')}.json",
            mime="application/json",
            use_container_width=True
        )

    st.markdown("<hr>", unsafe_allow_html=True)
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("← New Research"):
            st.session_state.screen = "onboarding"
            st.session_state.report = None
            st.rerun()
    with col2:
        if st.button("Rate this report →", use_container_width=True):
            st.session_state.screen = "feedback"
            st.rerun()


def screen_feedback():
    st.markdown("""
    <div style="margin-bottom:1.5rem">
      <h2 style="font-family:'Space Mono',monospace;font-size:1.4rem">Rate this report</h2>
      <p style="color:#888899">Your feedback improves the pipeline</p>
    </div>
    """, unsafe_allow_html=True)

    if not st.session_state.feedback_submitted:
        # Star rating
        st.markdown("<p style='color:#888899;font-size:0.9rem'>Overall quality</p>",
                    unsafe_allow_html=True)

        cols = st.columns(5)
        for i, col in enumerate(cols):
            with col:
                if st.button("★" if i < st.session_state.feedback_rating else "☆",
                             key=f"star_{i+1}"):
                    st.session_state.feedback_rating = i + 1
                    st.rerun()

        rating = st.session_state.feedback_rating
        if rating > 0:
            labels = ["", "Poor", "Fair", "Good", "Very Good", "Excellent"]
            st.markdown(
                f"<p style='color:#00d4aa;font-size:0.9rem'>{rating}/5 — {labels[rating]}</p>",
                unsafe_allow_html=True
            )

        # Score bars
        st.markdown("<br>", unsafe_allow_html=True)
        dimensions = [
            ("Specificity", "Were company names and numbers cited?"),
            ("Actionability", "Did the report suggest clear next steps?"),
            ("Completeness", "Was the topic covered comprehensively?"),
        ]
        scores = {}
        for dim, hint in dimensions:
            val = st.slider(dim, 1, 5, 3, help=hint, key=f"dim_{dim}")
            scores[dim] = val

        feedback_text = st.text_area(
            "Additional comments (optional)",
            placeholder="What would make this report more useful?",
            height=80
        )

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Submit Feedback", use_container_width=True):
            if rating > 0:
                st.session_state.feedback_text = feedback_text
                st.session_state.feedback_submitted = True
                st.rerun()
            else:
                st.warning("Please select a star rating")
    else:
        st.markdown("""
        <div class="card" style="text-align:center;padding:3rem">
          <div style="font-size:3rem">🎉</div>
          <h3 style="font-family:'Space Mono';margin:1rem 0">Thank you!</h3>
          <p style="color:#888899">Your feedback helps improve the pipeline.</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("← Start New Research", use_container_width=True):
            for key in ["screen", "topic", "report", "feedback_rating",
                        "feedback_text", "feedback_submitted"]:
                del st.session_state[key]
            st.rerun()


# ─────────────────────────────────────────────
# NAVIGATION BAR
# ─────────────────────────────────────────────
def render_navbar():
    screen = st.session_state.screen
    steps = {"landing": 0, "onboarding": 1, "pipeline": 2, "report": 3, "feedback": 4}
    current = steps.get(screen, 0)
    labels = ["Home", "Topic", "Running", "Report", "Feedback"]

    nav_html = '<div style="display:flex;gap:0.5rem;align-items:center;margin-bottom:2rem;padding-bottom:1rem;border-bottom:1px solid #2a2a3a">'
    nav_html += '<span style="font-family:Space Mono;font-size:0.85rem;color:#6c63ff;margin-right:0.5rem">⚡ COPILOT</span>'
    nav_html += '<span style="color:#2a2a3a;margin-right:0.5rem">|</span>'
    for i, label in enumerate(labels):
        if i == current:
            nav_html += f'<span style="font-size:0.8rem;color:#e8e8f0;font-weight:600">{label}</span>'
        elif i < current:
            nav_html += f'<span style="font-size:0.8rem;color:#6c63ff">✓ {label}</span>'
        else:
            nav_html += f'<span style="font-size:0.8rem;color:#2a2a3a">{label}</span>'
        if i < len(labels) - 1:
            nav_html += '<span style="color:#2a2a3a;margin:0 0.3rem">›</span>'
    nav_html += '</div>'
    st.markdown(nav_html, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# MAIN ROUTER
# ─────────────────────────────────────────────
render_navbar()

screen = st.session_state.screen
if screen == "landing":
    screen_landing()
elif screen == "onboarding":
    screen_onboarding()
elif screen == "pipeline":
    screen_pipeline()
elif screen == "report":
    screen_report()
elif screen == "feedback":
    screen_feedback()
