"""
ExamIntel AI v2: a multi-agent exam preparation assistant.

Run:  streamlit run main.py
"""
from __future__ import annotations

import os
from datetime import date, timedelta

import streamlit as st
from dotenv import load_dotenv

from core import exporters
from core.agents import AGENTS, build_exam_round, run_mission
from core.demo import FakeLLM, sample_papers
from core.documents import load_paper
from core.llm import GeminiLLM, LLMError
from core.memory import Memory
from core.tools import CHAT_SYSTEM, build_tools
import ui

load_dotenv()
st.set_page_config(page_title="ExamIntel AI", page_icon="🧠", layout="wide")

PAGES = ["🚀 Mission Control", "📊 Insights", "🎯 Quiz Arena", "🧭 Coach", "💬 Ask the Agent"]


# ------------------------------------------------------------------
# setup helpers
# ------------------------------------------------------------------
def read_api_key() -> str:
    """Streamlit Secrets first, then the .env / environment variable."""
    try:
        value = st.secrets.get("API_KEY", "")
        if value:
            return str(value)
    except Exception:  # no secrets file is fine locally
        pass
    return os.getenv("API_KEY", "")


@st.cache_resource
def get_memory() -> Memory:
    return Memory()


def get_llm(demo: bool):
    if demo:
        return FakeLLM(delay=float(os.getenv("EXAMINTEL_DEMO_DELAY", "0.7")))  # delay keeps the animation visible
    return GeminiLLM(read_api_key())


def init_state() -> None:
    st.session_state.setdefault("result", None)
    st.session_state.setdefault("quiz_round", 0)
    st.session_state.setdefault("quiz_submitted", None)
    st.session_state.setdefault("chat", [])
    st.session_state.setdefault("exam_date", date.today() + timedelta(days=21))


def need_result() -> bool:
    if st.session_state["result"] is None or st.session_state["result"].analysis is None:
        st.info("Run **Mission Control** first. The agents will analyse your papers and everything else unlocks.")
        return False
    return True


init_state()
memory = get_memory()

# ------------------------------------------------------------------
# sidebar
# ------------------------------------------------------------------
has_key = bool(read_api_key())
with st.sidebar:
    st.markdown("## 🧠 ExamIntel AI")
    st.caption("Multi-agent exam preparation")
    page = st.radio("Navigate", PAGES, label_visibility="collapsed")
    st.markdown("---")
    user = st.text_input("Your name (saves your progress)", value="guest", max_chars=30).strip() or "guest"
    demo = st.toggle(
        "Demo mode (sample papers, no API calls)",
        value=not has_key,
        help="Runs the whole app offline with invented sample papers. Turn it off to use your own PDFs and Gemini.",
    )
    if not demo and not has_key:
        st.error("API_KEY not found. Add it to .env (local) or Secrets (Streamlit Cloud), or use demo mode.")
    reduce_motion = st.toggle("Reduce motion", value=False, help="Turn animations off if they bother you.")
    if st.button("Reset my progress"):
        memory.reset(user)
        st.session_state["quiz_submitted"] = None
        st.toast("Progress cleared")


ui.inject_css(reduce_motion)

# ------------------------------------------------------------------
# PAGE 1: MISSION CONTROL
# ------------------------------------------------------------------
if page == PAGES[0]:
    ui.hero("ExamIntel AI", "Five agents read your past papers, write a verified mock exam and plan your days.")

    left, right = st.columns([3, 2])
    with left:
        if demo:
            st.info("Demo mode is on: the agents will use three invented sample papers.")
            uploads = []
        else:
            uploads = st.file_uploader("Upload past papers (PDF). Select several for cross-paper insights.",
                                       type=["pdf"], accept_multiple_files=True)
        goal = st.text_input("Your goal", placeholder="e.g. score above 75%, I find graphs hard")
    with right:
        exam_date = st.date_input("Exam date", value=st.session_state["exam_date"], min_value=date.today())
        hours = st.slider("Study hours per day", 1.0, 10.0, 3.0, 0.5)
        n_questions = st.slider("Mock exam questions", 5, 20, 10)
        difficulty = st.selectbox("Mock exam difficulty", ["Easy", "Medium", "Hard"], index=1)
    st.session_state["exam_date"] = exam_date

    launch = st.button("🚀 Launch agents", type="primary", disabled=(not demo and not uploads))

    pipeline = st.empty()
    pipeline.markdown(ui.pipeline_html({}), unsafe_allow_html=True)

    if launch:
        states: dict = {}

        def on_event(agent: str, status: str, message: str) -> None:
            states[agent] = (status, message)
            pipeline.markdown(ui.pipeline_html(states), unsafe_allow_html=True)

        try:
            llm = get_llm(demo)
            if demo:
                papers = sample_papers()
            else:
                papers = [load_paper(f.name, f.getvalue(), llm) for f in uploads]
            result = run_mission(
                llm, papers, exam_date, hours, goal, n_questions, difficulty,
                memory.weak_topics(user), on_event,
            )
            st.session_state["result"] = result
            st.session_state["quiz_round"] += 1
            st.session_state["quiz_submitted"] = None
            st.session_state["llm_demo"] = demo
        except LLMError as err:
            st.error(f"⚠️ {err}")
        except Exception as err:  # keep the app alive and show what happened
            st.error(f"Something went wrong while the agents were working: {err}")

    result = st.session_state["result"]
    if result is not None:
        for note in result.notes:
            st.warning(note)
        if result.analysis is not None:
            v = result.verification
            st.markdown(
                ui.tiles_html([
                    ("Papers read", len(result.papers)),
                    ("Topics found", len(result.analysis.topics)),
                    ("Verified questions", len(result.exam.questions)),
                    ("Plan days", len(result.plan.days)),
                ]),
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<div class="badge">🛡️ Verifier solved {v["checked"]} questions blind: '
                f'{v["disputed"]} disputed, {v["rewritten"]} rewritten, {v["dropped"]} dropped</div>',
                unsafe_allow_html=True,
            )
            st.caption("Explore the results in Insights, Quiz Arena and Coach.")
        with st.expander("Agent activity log"):
            for entry in result.log:
                st.code(f'{entry["agent"]:<9} {entry["status"]:<8} {entry["message"]} {entry["seconds"] or ""}')

# ------------------------------------------------------------------
# PAGE 2: INSIGHTS
# ------------------------------------------------------------------
elif page == PAGES[1]:
    ui.hero("Insights", "What your past papers say about the next exam.")
    if need_result():
        a = st.session_state["result"].analysis
        t1, t2, t3, t4 = st.tabs(["Topics", "Difficulty", "Repeated questions", "Summary"])
        with t1:
            ui.plot(ui.topic_chart(a), key="topics")
        with t2:
            if a.papers:
                ui.plot(ui.difficulty_chart(a), key="difficulty")
            st.write(a.difficulty_trend)
        with t3:
            for q in a.repeated_questions or []:
                st.markdown(f"**{q.question}**  \nSeen in: {', '.join(q.appeared_in)}")
            if not a.repeated_questions:
                st.write("No repeated questions found.")
        with t4:
            st.write(a.summary)
            st.markdown("**Study tips**")
            for tip in a.study_tips:
                st.markdown(f"- {tip}")
        md = exporters.analysis_to_markdown(a)
        c1, c2 = st.columns(2)
        c1.download_button("📝 Download DOCX", exporters.markdown_to_docx(md, "Exam Analysis"), "analysis.docx")
        c2.download_button("📄 Download PDF", exporters.markdown_to_pdf(md, "Exam Analysis"), "analysis.pdf")

# ------------------------------------------------------------------
# PAGE 3: QUIZ ARENA
# ------------------------------------------------------------------
elif page == PAGES[2]:
    ui.hero("Quiz Arena", "Answer the verified questions. Your weak topics shape the next round.")
    if need_result():
        result = st.session_state["result"]
        exam = result.exam
        tab_quiz, tab_progress = st.tabs(["Take the quiz", "My progress"])

        with tab_quiz:
            round_id = st.session_state["quiz_round"]
            submitted = st.session_state["quiz_submitted"]
            if not exam.questions:
                st.warning("No verified questions are available. Run Mission Control again.")
            elif submitted is None:
                with st.form(f"quiz_form_{round_id}"):
                    letters = "ABCD"
                    for i, q in enumerate(exam.questions):
                        st.markdown(f"**{i + 1}. {q.question}**  \n`{q.topic}`")
                        st.radio("Answer", list(range(4)), index=None, key=f"q{round_id}_{i}",
                                 format_func=lambda j, q=q: f"{letters[j]}. {q.options[j]}",
                                 label_visibility="collapsed")
                    done = st.form_submit_button("Submit answers", type="primary")
                if done:
                    chosen = [st.session_state.get(f"q{round_id}_{i}") for i in range(len(exam.questions))]
                    outcomes = [(q.topic, chosen[i] == q.correct_index) for i, q in enumerate(exam.questions)]
                    memory.record_answers(user, outcomes)
                    st.session_state["quiz_submitted"] = chosen
                    st.rerun()
            else:
                score = sum(1 for i, q in enumerate(exam.questions) if submitted[i] == q.correct_index)
                col_a, col_b = st.columns([1, 3])
                col_a.markdown(ui.ring_html(score, len(exam.questions)), unsafe_allow_html=True)
                with col_b:
                    st.subheader("Round complete")
                    st.write("Your results were saved. The next round will focus on your weakest topics.")
                    if st.button("🎯 Generate adaptive round", type="primary"):
                        try:
                            with st.spinner("Examiner and Verifier are building a harder round..."):
                                llm = get_llm(st.session_state.get("llm_demo", demo))
                                build_exam_round(llm, result, 10, "Medium", memory.weak_topics(user))
                            st.session_state["quiz_round"] += 1
                            st.session_state["quiz_submitted"] = None
                            st.rerun()
                        except LLMError as err:
                            st.error(f"⚠️ {err}")
                st.markdown(ui.review_html(exam, submitted), unsafe_allow_html=True)
                md = exporters.exam_to_markdown(exam)
                c1, c2 = st.columns(2)
                c1.download_button("📝 Exam + answers (DOCX)", exporters.markdown_to_docx(md, exam.title), "mock_exam.docx")
                c2.download_button("📄 Exam + answers (PDF)", exporters.markdown_to_pdf(md, exam.title), "mock_exam.pdf")

        with tab_progress:
            mastery = memory.mastery(user)
            if len(mastery) >= 3:
                ui.plot(ui.mastery_chart(mastery), key="mastery")
            elif mastery:
                for topic, score_value in mastery.items():
                    st.progress(score_value, text=f"{topic}: {round(score_value * 100)}%")
            else:
                st.write("Finish a quiz to see your mastery by topic.")
            history = memory.history(user)
            if len(history) >= 2:
                ui.plot(ui.history_chart(history), key="history")

# ------------------------------------------------------------------
# PAGE 4: COACH
# ------------------------------------------------------------------
elif page == PAGES[3]:
    ui.hero("Coach", "A day-by-day plan built from your papers and your weak topics.")
    if need_result():
        plan = st.session_state["result"].plan
        done_days = memory.done_days(user)
        st.write(plan.summary)
        completed = len([d for d in plan.days if d.day in done_days])
        st.progress(completed / max(1, len(plan.days)), text=f"{completed} of {len(plan.days)} days complete")
        for d in plan.days:
            with st.expander(f"Day {d.day} · {d.label} · {d.hours:g} h · {', '.join(d.focus_topics)}",
                             expanded=(d.day == 1)):
                for task in d.tasks:
                    st.markdown(f"- {task}")
                checked = st.checkbox("Done", value=d.day in done_days, key=f"day_{d.day}")
                if checked != (d.day in done_days):
                    memory.set_day_done(user, d.day, checked)
                    st.rerun()
        st.markdown("**Revision strategy**")
        for item in plan.revision_strategy:
            st.markdown(f"- {item}")
        md = exporters.plan_to_markdown(plan)
        c1, c2 = st.columns(2)
        c1.download_button("📝 Download DOCX", exporters.markdown_to_docx(md, "Study Plan"), "study_plan.docx")
        c2.download_button("📄 Download PDF", exporters.markdown_to_pdf(md, "Study Plan"), "study_plan.pdf")

# ------------------------------------------------------------------
# PAGE 5: ASK THE AGENT (tool use)
# ------------------------------------------------------------------
else:
    ui.hero("Ask the Agent", "A study coach that looks things up with tools instead of guessing.")
    if need_result():
        result = st.session_state["result"]
        for message in st.session_state["chat"]:
            with st.chat_message(message["role"]):
                if message.get("trace"):
                    st.markdown(ui.chips_html(message["trace"]), unsafe_allow_html=True)
                st.markdown(message["content"])
        if not st.session_state["chat"]:
            st.caption("Try: “What should I study first?”, “Which topics am I weakest in?”, "
                       "“How many days do I have?”, “Search the papers for hashing”.")

        question = st.chat_input("Ask about your papers, weak topics or exam date")
        if question:
            st.session_state["chat"].append({"role": "user", "content": question})
            with st.chat_message("user"):
                st.markdown(question)
            trace: list = []
            tools = build_tools(result.analysis, result.papers, memory, user, st.session_state["exam_date"], trace)
            history = "\n".join(f'{m["role"]}: {m["content"]}' for m in st.session_state["chat"][-7:-1])
            prompt = f"Conversation so far:\n{history}\n\nStudent question: {question}" if history else question
            with st.chat_message("assistant"):
                try:
                    with st.spinner("Thinking and calling tools..."):
                        llm = get_llm(st.session_state.get("llm_demo", demo))
                        answer = llm.run_tools(prompt, tools, system=CHAT_SYSTEM)
                except LLMError as err:
                    answer = f"⚠️ {err}"
                if trace:
                    st.markdown(ui.chips_html(trace), unsafe_allow_html=True)
                st.markdown(answer)
            st.session_state["chat"].append({"role": "assistant", "content": answer, "trace": trace})
