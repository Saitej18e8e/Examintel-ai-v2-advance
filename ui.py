"""Look and feel: CSS animations, HTML components and Plotly charts.

Everything that came from an AI or a PDF is passed through html.escape before it
is placed in HTML, so a malicious paper cannot inject markup into the page.
"""
from __future__ import annotations

from html import escape
from typing import Dict, List, Optional

import plotly.graph_objects as go
import streamlit as st

from core.agents import AGENTS
from core.schemas import Analysis, Exam

CYAN, VIOLET, GREEN, AMBER, RED = "#38e8ff", "#8b5cf6", "#34d399", "#fbbf24", "#f87171"

AGENT_META = {
    "Reader": ("📄", "Reads your PDFs"),
    "Analyst": ("🔬", "Finds patterns"),
    "Examiner": ("✍️", "Writes questions"),
    "Verifier": ("🛡️", "Checks the answers"),
    "Coach": ("🧭", "Plans your days"),
}

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@500;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

@property --num { syntax: '<integer>'; initial-value: 0; inherits: false; }
@property --pct { syntax: '<number>'; initial-value: 0; inherits: false; }

:root { --cyan:#38e8ff; --violet:#8b5cf6; --green:#34d399; --amber:#fbbf24; --red:#f87171;
        --card:rgba(255,255,255,.045); --line:rgba(255,255,255,.10); }

.stApp { background: radial-gradient(1200px 600px at 10% -10%, rgba(139,92,246,.18), transparent 60%),
                     radial-gradient(900px 500px at 100% 0%, rgba(56,232,255,.12), transparent 55%), #0a0f1e; }
h1, h2, h3 { font-family: 'Sora', sans-serif !important; letter-spacing: -.01em; }

/* ---------- hero ---------- */
.hero { padding: 6px 0 18px; }
.hero h1 { font-size: clamp(2rem, 5vw, 3.1rem); font-weight: 800; margin: 0;
  background: linear-gradient(90deg, var(--cyan), var(--violet), var(--cyan));
  background-size: 200% auto; -webkit-background-clip: text; background-clip: text;
  color: transparent; animation: shine 6s linear infinite; }
.hero p { color: #9fb0d0; margin: 6px 0 0; font-size: 1.02rem; }
@keyframes shine { to { background-position: 200% center; } }

/* ---------- agent pipeline ---------- */
.pipe { display: flex; align-items: flex-start; gap: 0; flex-wrap: wrap; margin: 10px 0 4px; }
.node { flex: 1 1 130px; min-width: 120px; text-align: center; padding: 10px 6px; opacity: .45;
        transition: opacity .4s; animation: rise .5s ease both; }
.node.running, .node.done, .node.failed { opacity: 1; }
.orb { width: 56px; height: 56px; margin: 0 auto 8px; border-radius: 50%; display: grid; place-items: center;
       font-size: 1.5rem; background: var(--card); border: 1.5px solid var(--line); position: relative; }
.node.running .orb { border-color: var(--cyan); box-shadow: 0 0 0 0 rgba(56,232,255,.6);
       animation: pulse 1.4s ease-out infinite; }
.node.running .orb::after { content:''; position:absolute; inset:-6px; border-radius:50%;
       border: 2px solid transparent; border-top-color: var(--violet); animation: spin 1s linear infinite; }
.node.done .orb { border-color: var(--green); background: rgba(52,211,153,.12); animation: pop .45s ease; }
.node.failed .orb { border-color: var(--red); background: rgba(248,113,113,.12); }
.node .nm { font-family: 'Sora', sans-serif; font-weight: 700; font-size: .95rem; }
.node .role { color: #7f90b2; font-size: .78rem; }
.node .msg { font-family: 'JetBrains Mono', monospace; font-size: .72rem; color: #9fb0d0; margin-top: 6px;
             min-height: 2.2em; }
.node.running .msg { color: var(--cyan); }
@keyframes pulse { 70% { box-shadow: 0 0 0 16px rgba(56,232,255,0); } 100% { box-shadow: 0 0 0 0 rgba(56,232,255,0); } }
@keyframes spin { to { transform: rotate(360deg); } }
@keyframes pop { 0% { transform: scale(.8); } 60% { transform: scale(1.12); } 100% { transform: scale(1); } }
@keyframes rise { from { opacity: 0; transform: translateY(10px); } }

/* ---------- stat tiles with count-up ---------- */
.tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin: 12px 0; }
.tile { background: var(--card); border: 1px solid var(--line); border-radius: 14px; padding: 14px 16px;
        animation: rise .6s ease both; }
.tile:nth-child(2) { animation-delay: .08s; } .tile:nth-child(3) { animation-delay: .16s; }
.tile:nth-child(4) { animation-delay: .24s; }
.tile .big { font-family: 'Sora', sans-serif; font-size: 2.1rem; font-weight: 800;
             counter-reset: num var(--num); animation: count 1.1s ease-out forwards; }
.tile .big::after { content: counter(num); }
.tile .lbl { color: #8fa1c4; font-size: .82rem; text-transform: uppercase; letter-spacing: .06em; }
@keyframes count { from { --num: 0; } to { --num: var(--to); } }

/* ---------- verifier badge ---------- */
.badge { display: inline-flex; align-items: center; gap: 8px; padding: 8px 14px; border-radius: 999px;
         background: rgba(52,211,153,.12); border: 1px solid rgba(52,211,153,.4); color: #b7f5dc;
         font-size: .9rem; animation: rise .6s ease both; }

/* ---------- quiz review cards ---------- */
.qcard { background: var(--card); border: 1px solid var(--line); border-radius: 14px; padding: 14px 16px;
         margin: 12px 0; animation: rise .5s ease both; }
.qcard .topic { display: inline-block; font-size: .72rem; color: var(--cyan); border: 1px solid rgba(56,232,255,.35);
                border-radius: 999px; padding: 2px 10px; margin-bottom: 8px; }
.qcard .q { font-weight: 600; margin-bottom: 10px; }
.opt { padding: 8px 12px; border-radius: 10px; margin: 6px 0; border: 1px solid var(--line); }
.opt.right { border-color: var(--green); background: rgba(52,211,153,.14); animation: glow 1s ease; }
.opt.wrong { border-color: var(--red); background: rgba(248,113,113,.14); animation: shake .45s ease; }
.why { color: #9fb0d0; font-size: .88rem; margin-top: 8px; }
@keyframes glow { 0% { box-shadow: 0 0 0 0 rgba(52,211,153,.7); } 100% { box-shadow: 0 0 0 14px rgba(52,211,153,0); } }
@keyframes shake { 20%,60% { transform: translateX(-6px); } 40%,80% { transform: translateX(6px); } }

/* ---------- score ring ---------- */
.ring { --pct: 0; width: 120px; height: 120px; border-radius: 50%; display: grid; place-items: center;
        background: conic-gradient(var(--ringc, var(--green)) calc(var(--pct) * 1%), rgba(255,255,255,.08) 0);
        animation: fill 1.4s ease-out forwards; position: relative; }
.ring::before { content:''; position:absolute; inset: 10px; background: #0a0f1e; border-radius: 50%; }
.ring span { position: relative; font-family: 'Sora', sans-serif; font-weight: 800; font-size: 1.5rem; }
@keyframes fill { from { --pct: 0; } to { --pct: var(--to); } }

/* ---------- agent tool chips (chat) ---------- */
.chip { display: inline-block; font-family: 'JetBrains Mono', monospace; font-size: .74rem; padding: 4px 10px;
        margin: 2px 6px 2px 0; border-radius: 8px; background: rgba(139,92,246,.16);
        border: 1px solid rgba(139,92,246,.45); color: #d8c8ff; animation: rise .4s ease both; }

</style>
"""


REDUCED_CSS = """
<style>
*, *::before, *::after { animation: none !important; transition: none !important; }
.tile .big::after { content: var(--to); }
.ring { --pct: var(--to); }
</style>
"""


def inject_css(reduce_motion: bool = False) -> None:
    """Animations are on by default. They are switched off only when the user
    ticks 'Reduce motion' in the sidebar, not by the operating system setting."""
    st.markdown(CSS, unsafe_allow_html=True)
    if reduce_motion:
        st.markdown(REDUCED_CSS, unsafe_allow_html=True)


def hero(title: str, subtitle: str) -> None:
    st.markdown(f'<div class="hero"><h1>{escape(title)}</h1><p>{escape(subtitle)}</p></div>', unsafe_allow_html=True)


def plot(fig: go.Figure, key: Optional[str] = None) -> None:
    """Show a Plotly chart full width on any Streamlit version."""
    try:
        st.plotly_chart(fig, width="stretch", key=key)
    except TypeError:
        st.plotly_chart(fig, use_container_width=True, key=key)


# ---------- pipeline ----------
def pipeline_html(states: Dict[str, tuple]) -> str:
    """states maps agent name -> (status, message); missing agents are pending."""
    nodes = []
    for name in AGENTS:
        status, message = states.get(name, ("pending", ""))
        icon, role = AGENT_META[name]
        shown = {"done": "✓", "failed": "✕"}.get(status, icon)
        nodes.append(
            f'<div class="node {escape(status)}"><div class="orb">{shown}</div>'
            f'<div class="nm">{escape(name)}</div><div class="role">{escape(role)}</div>'
            f'<div class="msg">{escape(message)}</div></div>'
        )
    return f'<div class="pipe">{"".join(nodes)}</div>'


def tiles_html(items: List[tuple]) -> str:
    cells = "".join(
        f'<div class="tile"><div class="big" style="--to:{int(value)}"></div><div class="lbl">{escape(label)}</div></div>'
        for label, value in items
    )
    return f'<div class="tiles">{cells}</div>'


def ring_html(score: int, total: int) -> str:
    pct = round(100 * score / total) if total else 0
    color = GREEN if pct >= 70 else AMBER if pct >= 40 else RED
    return (f'<div class="ring" style="--to:{pct};--ringc:{color}"><span>{score}/{total}</span></div>')


def review_html(exam: Exam, chosen: List[Optional[int]]) -> str:
    letters = "ABCD"
    cards = []
    for i, q in enumerate(exam.questions):
        picked = chosen[i] if i < len(chosen) else None
        rows = []
        for j, option in enumerate(q.options):
            css = "opt"
            mark = ""
            if j == q.correct_index:
                css, mark = "opt right", " ✓"
            elif j == picked:
                css, mark = "opt wrong", " ✕ your answer"
            rows.append(f'<div class="{css}">{letters[j]}. {escape(option)}{mark}</div>')
        cards.append(
            f'<div class="qcard" style="animation-delay:{min(i, 10) * 0.06:.2f}s">'
            f'<span class="topic">{escape(q.topic)}</span><div class="q">{i + 1}. {escape(q.question)}</div>'
            f'{"".join(rows)}<div class="why">{escape(q.explanation)}</div></div>'
        )
    return "".join(cards)


def chips_html(trace: List[dict]) -> str:
    chips = []
    for call in trace:
        args = call.get("args")
        shown = ", ".join(f"{k}={v}" for k, v in args.items()) if isinstance(args, dict) else ""
        chips.append(f'<span class="chip">🔧 {escape(call["tool"])}({escape(shown)})</span>')
    return "".join(chips)


# ---------- charts ----------
def _dark(fig: go.Figure, height: int = 380) -> go.Figure:
    fig.update_layout(
        template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        height=height, margin=dict(l=10, r=20, t=40, b=10), font=dict(family="Inter, sans-serif"),
    )
    return fig


def topic_chart(analysis: Analysis) -> go.Figure:
    """Horizontal bars that grow from zero when you press Play."""
    topics = sorted(analysis.topics, key=lambda t: (t.importance, t.frequency))[-10:]
    names = [t.topic for t in topics]
    values = [t.importance for t in topics]
    freqs = [t.frequency for t in topics]
    steps = 12

    def bars(scale: float) -> go.Bar:
        return go.Bar(
            x=[v * scale for v in values], y=names, orientation="h",
            marker=dict(color=values, colorscale=[[0, VIOLET], [1, CYAN]], cmin=0, cmax=10),
            customdata=freqs, hovertemplate="%{y}<br>importance %{x:.0f}/10<br>in %{customdata} paper(s)<extra></extra>",
        )

    fig = go.Figure(
        data=[bars(1.0)],
        frames=[go.Frame(data=[bars(k / steps)], name=str(k)) for k in range(1, steps + 1)],
    )
    fig.update_layout(
        title="Topic importance across your papers",
        xaxis=dict(range=[0, 10.5], title="Importance (1-10)"),
        updatemenus=[dict(
            type="buttons", direction="left", x=1.0, xanchor="right", y=1.12, showactive=False,
            buttons=[dict(label="▶ Replay", method="animate",
                          args=[None, dict(frame=dict(duration=60, redraw=True), fromcurrent=False,
                                           transition=dict(duration=40))])],
        )],
    )
    return _dark(fig, 420)


def difficulty_chart(analysis: Analysis) -> go.Figure:
    papers = analysis.papers
    labels = [p.year or p.paper for p in papers]
    fig = go.Figure(go.Scatter(
        x=labels, y=[p.difficulty for p in papers], mode="lines+markers",
        line=dict(color=CYAN, width=3, shape="spline"), marker=dict(size=11, color=VIOLET),
        fill="tozeroy", fillcolor="rgba(56,232,255,.10)",
        hovertemplate="%{x}<br>difficulty %{y}/10<extra></extra>",
    ))
    fig.update_layout(title="Difficulty by paper", yaxis=dict(range=[0, 10], title="Difficulty (1-10)"))
    return _dark(fig, 320)


def mastery_chart(mastery: Dict[str, float]) -> go.Figure:
    topics = list(mastery)[:10]
    values = [round(mastery[t] * 100) for t in topics]
    fig = go.Figure(go.Scatterpolar(
        r=values + values[:1], theta=topics + topics[:1], fill="toself",
        line=dict(color=CYAN, width=2), fillcolor="rgba(56,232,255,.18)",
        hovertemplate="%{theta}: %{r}%<extra></extra>",
    ))
    fig.update_layout(title="Topic mastery", polar=dict(radialaxis=dict(range=[0, 100], ticksuffix="%")))
    return _dark(fig, 420)


def history_chart(history: List[dict]) -> go.Figure:
    pct = [round(100 * h["score"] / h["total"]) if h["total"] else 0 for h in history]
    fig = go.Figure(go.Scatter(
        x=list(range(1, len(pct) + 1)), y=pct, mode="lines+markers",
        line=dict(color=GREEN, width=3), marker=dict(size=10),
    ))
    fig.update_layout(title="Quiz scores over time", xaxis=dict(title="Attempt", dtick=1),
                      yaxis=dict(range=[0, 100], ticksuffix="%"))
    return _dark(fig, 300)
