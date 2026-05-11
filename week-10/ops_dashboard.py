"""
ops_dashboard.py — Streamlit ops dashboard для мониторинга pipeline runs.

Запуск:
  streamlit run ops_dashboard.py

Показывает:
  - KPI карточки: total runs, pass rate, avg score, avg time
  - Таблица истории с фильтрами
  - График score over time
  - Dead letter queue
  - Кнопка "Run Now" для ручного запуска
"""
import os
import sys
import json
import csv
from datetime import datetime, timedelta

import streamlit as st

sys.path.insert(0, os.path.dirname(__file__))
from pipeline_exporters.csv_exporter import CSVExporter, CSV_PATH
from pipeline_exporters.json_exporter import JSONExporter, REPORTS_DIR

DEAD_LETTER_DIR = os.path.join(REPORTS_DIR, "dead_letter")

st.set_page_config(
    page_title="Pipeline Ops Dashboard",
    page_icon="📊",
    layout="wide"
)

st.markdown("""
<style>
  html, body, [class*="css"] { background-color: #f8f9fa !important; color: #1a1a2e !important; }
  .stApp { background-color: #f8f9fa !important; }
  .block-container { padding: 1.5rem 2rem !important; }
  .kpi { background:#ffffff; border:1px solid #dde1ea; border-radius:10px;
         padding:1rem 1.2rem; text-align:center; box-shadow: 0 1px 4px rgba(0,0,0,0.06); }
  .kpi-val { font-size:2rem; font-weight:700; color:#0077cc; font-family:monospace; }
  .kpi-lbl { font-size:0.75rem; color:#777788; text-transform:uppercase; letter-spacing:0.05em; }
  .badge-pass { color:#008855; font-weight:600; }
  .badge-fail { color:#cc2244; font-weight:600; }
  #MainMenu, footer { visibility:hidden; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# LOAD DATA
# ─────────────────────────────────────────────
@st.cache_data(ttl=30)
def load_history() -> list[dict]:
    return CSVExporter().read_history()


def load_dead_letters() -> list[dict]:
    if not os.path.exists(DEAD_LETTER_DIR):
        return []
    results = []
    for fname in sorted(os.listdir(DEAD_LETTER_DIR), reverse=True):
        if fname.endswith(".json"):
            with open(os.path.join(DEAD_LETTER_DIR, fname)) as f:
                results.append(json.load(f))
    return results


def load_brief(run_id: str) -> str:
    path = os.path.join(REPORTS_DIR, f"{run_id}_brief.md")
    if os.path.exists(path):
        with open(path) as f:
            return f.read()
    return "Brief not found"


# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────
col_title, col_refresh = st.columns([4, 1])
with col_title:
    st.markdown("## ⚡ Pipeline Ops Dashboard")
with col_refresh:
    if st.button("🔄 Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

history = load_history()

# ─────────────────────────────────────────────
# KPI CARDS
# ─────────────────────────────────────────────
total   = len(history)
passed  = sum(1 for r in history if r.get("quality") == "PASS")
avg_sc  = (sum(float(r.get("score", 0)) for r in history) / total) if total else 0
avg_t   = (sum(float(r.get("elapsed_s", 0)) for r in history) / total) if total else 0
dead_n  = len(load_dead_letters())

k1, k2, k3, k4, k5 = st.columns(5)
for col, val, lbl in [
    (k1, str(total),               "Total Runs"),
    (k2, f"{passed/total*100:.0f}%" if total else "—", "Pass Rate"),
    (k3, f"{avg_sc:.2f}",          "Avg Score"),
    (k4, f"{avg_t:.0f}s",          "Avg Time"),
    (k5, str(dead_n),              "Dead Letters"),
]:
    with col:
        color = "#cc2244" if (lbl == "Dead Letters" and dead_n > 0) else "#0077cc"
        st.markdown(f"""
        <div class="kpi">
          <div class="kpi-val" style="color:{color}">{val}</div>
          <div class="kpi-lbl">{lbl}</div>
        </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(["📋 Run History", "📈 Trends", "💀 Dead Letters", "▶️ Run Now"])

# ── TAB 1: History ────────────────────────────
with tab1:
    if not history:
        st.info("No runs yet. Run `python3 weekly_pipeline.py` to generate data.")
    else:
        # Фильтры
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            quality_filter = st.selectbox("Quality", ["All", "PASS", "FAIL"])
        with col_f2:
            topic_search = st.text_input("Search topic", placeholder="Filter by keyword...")

        filtered = history
        if quality_filter != "All":
            filtered = [r for r in filtered if r.get("quality") == quality_filter]
        if topic_search:
            filtered = [r for r in filtered if topic_search.lower() in r.get("topic","").lower()]

        st.markdown(f"Showing **{len(filtered)}** of **{len(history)}** runs")
        st.markdown("<br>", unsafe_allow_html=True)

        for run in reversed(filtered[-20:]):
            q = run.get("quality", "—")
            s = float(run.get("score", 0))
            badge = f'<span class="badge-pass">✅ {q}</span>' if q == "PASS" else \
                    f'<span class="badge-fail">❌ {q}</span>'

            with st.expander(f"{run.get('run_id','')} — {run.get('topic','')[:50]}"):
                col_a, col_b, col_c, col_d = st.columns(4)
                col_a.metric("Score",   f"{s:.2f}")
                col_b.metric("Time",    f"{run.get('elapsed_s','—')}s")
                col_c.metric("Words",   run.get("word_count", "—"))
                col_d.metric("Tokens",  run.get("cost_tokens", "—"))

                st.markdown(f"**Quality:** {badge}", unsafe_allow_html=True)
                st.markdown(f"**Date:** {run.get('started_at','')[:19].replace('T',' ')} UTC")

                if run.get("error"):
                    st.error(f"Error: {run['error']}")

                # Показать brief если есть
                brief = load_brief(run.get("run_id", ""))
                if brief and brief != "Brief not found":
                    st.markdown("**📄 Brief:**")
                    st.markdown(brief)

# ── TAB 2: Trends ─────────────────────────────
with tab2:
    if len(history) < 2:
        st.info("Need at least 2 runs for trend charts. Run more topics first.")
    else:
        try:
            import plotly.express as px
            import pandas as pd

            df = pd.DataFrame(history)
            df["score"] = pd.to_numeric(df["score"], errors="coerce")
            df["elapsed_s"] = pd.to_numeric(df["elapsed_s"], errors="coerce")
            df["date"] = df["started_at"].str[:10]

            col_g1, col_g2 = st.columns(2)

            with col_g1:
                st.markdown("**Quality Score Over Time**")
                fig = px.line(df, x="started_at", y="score",
                              color_discrete_sequence=["#6c63ff"],
                              labels={"score": "Score", "started_at": "Run"})
                fig.add_hline(y=0.65, line_dash="dash", line_color="#cc2244",
                              annotation_text="Threshold 0.65")
                fig.update_layout(paper_bgcolor="#f8f9fa", plot_bgcolor="#ffffff",
                                  font_color="#1a1a2e")
                st.plotly_chart(fig, use_container_width=True)

            with col_g2:
                st.markdown("**Latency Distribution**")
                fig2 = px.histogram(df, x="elapsed_s", nbins=10,
                                    color_discrete_sequence=["#00d4aa"],
                                    labels={"elapsed_s": "Elapsed (s)"})
                fig2.update_layout(paper_bgcolor="#f8f9fa", plot_bgcolor="#ffffff",
                                   font_color="#1a1a2e")
                st.plotly_chart(fig2, use_container_width=True)

        except ImportError:
            # Fallback без plotly
            st.markdown("**Score Trend (text)**")
            for r in history[-10:]:
                score = float(r.get("score", 0))
                bar = "█" * int(score * 20) + "░" * (20 - int(score * 20))
                q_color = "🟢" if r.get("quality") == "PASS" else "🔴"
                st.text(f"{q_color} {r.get('run_id','')[:20]} | {bar} {score:.2f}")

# ── TAB 3: Dead Letters ───────────────────────
with tab3:
    dead = load_dead_letters()
    if not dead:
        st.success("✅ Dead letter queue is empty — all runs successful!")
    else:
        st.warning(f"⚠️ {len(dead)} run(s) in dead letter queue")
        for r in dead:
            with st.expander(f"❌ {r.get('run_id','')} — {r.get('topic','')[:40]}"):
                st.json(r)

# ── TAB 4: Run Now ────────────────────────────
with tab4:
    st.markdown("**Запустить pipeline вручную из dashboard**")
    custom_topic = st.text_input(
        "Topic",
        placeholder="e.g. B2B SaaS analytics tools market",
        key="manual_topic"
    )
    if st.button("▶️ Run Pipeline Now", use_container_width=True):
        if custom_topic.strip():
            with st.spinner(f"Running pipeline for: {custom_topic}..."):
                from weekly_pipeline import run_weekly
                result = run_weekly([custom_topic])
            st.success(f"✅ Done! Score: {result['avg_score']:.2f}")
            st.cache_data.clear()
            st.rerun()
        else:
            st.error("Please enter a topic")
