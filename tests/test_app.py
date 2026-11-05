import os
from pathlib import Path

os.environ["EXAMINTEL_DEMO_DELAY"] = "0"
os.environ.pop("API_KEY", None)

from streamlit.testing.v1 import AppTest

MAIN = Path(__file__).resolve().parent.parent / "main.py"
PAGES = ["🚀 Mission Control", "📊 Insights", "🎯 Quiz Arena", "🧭 Coach", "💬 Ask the Agent"]


def open_page(at, name):
    at.sidebar.radio[0].set_value(name).run()
    assert not at.exception, [e.value for e in at.exception]


def launch():
    at = AppTest.from_file(str(MAIN), default_timeout=30).run()
    assert not at.exception
    [b for b in at.button if "Launch" in b.label][0].click().run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def test_demo_mission_then_every_page():
    at = launch()
    assert at.session_state["result"].analysis is not None
    for name in PAGES[1:4]:
        open_page(at, name)


def test_quiz_flow_updates_progress():
    at = launch()
    open_page(at, PAGES[2])
    for radio in at.radio:
        if radio.label == "Answer":
            radio.set_value(1)
    [b for b in at.button if "Submit" in b.label][0].click().run()
    assert not at.exception, [e.value for e in at.exception]
    assert at.session_state["quiz_submitted"] is not None


def test_chat_uses_tools():
    at = launch()
    open_page(at, PAGES[4])
    at.chat_input[0].set_value("How many days do I have?").run()
    assert not at.exception, [e.value for e in at.exception]
    last = at.session_state["chat"][-1]
    assert last["trace"] and last["trace"][0]["tool"] == "days_until_exam"
