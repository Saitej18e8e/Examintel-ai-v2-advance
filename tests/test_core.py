from datetime import date, timedelta

import pytest

from core import exporters
from core.agents import run_mission, verify_and_repair, verifier_agent
from core.demo import FakeLLM, sample_papers
from core.documents import Paper, budget_texts, search_pages
from core.memory import Memory
from core.schemas import Exam, MCQ
from core.tools import build_tools


def mission(**over):
    args = dict(llm=FakeLLM(), papers=sample_papers(), exam_date=date.today() + timedelta(days=10),
                hours_per_day=3, goal="pass", n_questions=8, difficulty="Medium", weak_topics=[])
    args.update(over)
    return run_mission(**args)


def test_pipeline_runs_all_agents_in_order():
    events = []
    result = mission(on_event=lambda a, s, m: events.append((a, s)))
    done = [a for a, s in events if s == "done"]
    assert done == ["Reader", "Analyst", "Examiner", "Verifier", "Coach"]
    assert result.analysis and result.exam and result.plan


def test_verifier_catches_and_fixes_a_wrong_answer_key():
    result = mission()
    assert result.verification["disputed"] == 1
    assert result.verification["rewritten"] == 1
    assert result.verification["dropped"] == 0
    assert result.exam.questions[2].correct_index == 1  # fixed key


def test_verifier_drops_questions_that_stay_disputed():
    class Stubborn(FakeLLM):
        def structured(self, prompt, schema, system=None, temperature=0.4):
            if schema is Exam and "disputed" in prompt:
                bad = super().structured(prompt, schema)
                bad.questions[0].correct_index = 0  # still wrong
                return bad
            return super().structured(prompt, schema, system, temperature)

    result = mission(llm=Stubborn())
    assert result.verification["dropped"] == 1
    assert len(result.exam.questions) == 7


def test_no_text_stops_cleanly():
    result = mission(papers=[Paper(name="scan.pdf", pages=["", ""])])
    assert result.analysis is None
    assert any(e["status"] == "failed" for e in result.log)


def test_budget_gives_each_paper_an_equal_share():
    papers = [Paper("a", ["x" * 1000]), Paper("b", ["y" * 10])]
    texts, truncated = budget_texts(papers, max_chars=200)
    assert truncated and len(texts["a"]) == 100 and len(texts["b"]) == 10


def test_search_finds_the_right_page():
    hits = search_pages(sample_papers(), "dijkstra shortest path")
    assert hits and hits[0]["paper"] == "DS_2023_Sem1.pdf"


def test_memory_tracks_weak_topics_and_progress():
    mem = Memory(":memory:")
    mem.record_answers("ana", [("Graphs", False), ("Graphs", False), ("Trees", True)])
    weak = mem.weak_topics("ana", 1)
    assert weak[0]["topic"] == "Graphs"
    assert mem.mastery("ana")["Trees"] > mem.mastery("ana")["Graphs"]
    assert mem.mastery("bob") == {}  # users are isolated
    mem.set_day_done("ana", 2, True)
    assert mem.done_days("ana") == {2}
    mem.reset("ana")
    assert mem.mastery("ana") == {}


def test_tools_return_data_and_log_calls():
    result = mission()
    trace = []
    tools = build_tools(result.analysis, result.papers, Memory(":memory:"), "u", date.today() + timedelta(days=5), trace)
    by = {t.__name__: t for t in tools}
    assert by["days_until_exam"]()["days_left"] == 5
    assert by["get_topic_stats"](2)[0]["topic"] == "Binary Search Trees"
    assert [c["tool"] for c in trace] == ["days_until_exam", "get_topic_stats"]


def test_exports_build_real_files_with_bold_text():
    result = mission()
    md = exporters.exam_to_markdown(result.exam)
    assert exporters.markdown_to_docx(md).read()[:2] == b"PK"      # docx is a zip
    assert exporters.markdown_to_pdf(md).read()[:4] == b"%PDF"
    assert exporters.plan_to_markdown(result.plan).startswith("# Study Plan")
    assert exporters.markdown_to_pdf("# T\n**bold** & <tag> text").read()[:4] == b"%PDF"
