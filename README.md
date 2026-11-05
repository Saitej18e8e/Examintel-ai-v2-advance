# 🧠 ExamIntel AI v2

**A multi-agent exam preparation assistant built with Python, Streamlit and Google Gemini.**

Upload past exam papers and a team of five agents reads them, finds patterns across years,
writes a mock exam, checks its own answers, and builds a day-by-day study plan. A quiz arena
tracks which topics you are weak at and feeds that back into the next round.

## The agents

| Agent | Job |
|-------|-----|
| 📄 Reader | Extracts text from PDFs (falls back to Gemini vision for scanned papers) and trims input to fit the model |
| 🔬 Analyst | Returns structured JSON: topics, frequency across papers, importance, difficulty per paper, repeated questions |
| ✍️ Examiner | Writes multiple-choice questions weighted towards important topics and your weak topics |
| 🛡️ Verifier | Solves every question blind (without the answer key). Disputed questions are rewritten once, then dropped if they still fail |
| 🧭 Coach | Builds a study plan from days left, hours per day, topic importance and quiz results |

The **Ask the Agent** page uses Gemini function calling: the model chooses between tools
(`get_topic_stats`, `get_weak_topics`, `days_until_exam`, `search_papers`, `get_repeated_questions`)
and the app shows every tool call it made.

## Features

- Animated live agent pipeline, count-up stats, replayable charts, animated quiz review
- Structured outputs validated with Pydantic, so results drive real charts and scoring
- Interactive quiz with scoring, explanations and an adaptive next round
- SQLite memory: topic mastery, quiz history and study-plan progress per user name
- DOCX and PDF export (bold text and special characters handled)
- Demo mode with invented sample papers: works offline, no API key, no quota use
- Rate-limit retries with backoff, clear error messages, prompt-injection guard for PDF text
- 12 automated tests, including headless runs of the whole app

## Run locally

```bash
python -m venv venv
venv\Scripts\activate          # Windows (Mac/Linux: source venv/bin/activate)
pip install -r requirements.txt
```

Create a `.env` file (never commit it):

```
API_KEY=your_gemini_api_key
```

```bash
streamlit run main.py
```

No key yet? Start the app anyway: demo mode is on automatically.

## Deploy on Streamlit Community Cloud

1. Push this folder to GitHub.
2. Create the app with main file `main.py`.
3. In **Advanced settings > Secrets** add `API_KEY = "your_key"`.

Free tier note: a public link lets visitors spend your Gemini quota. Leave demo mode on by
default for public demos, or only share the link with people you trust.

## Project layout

```
main.py            Streamlit pages
ui.py              CSS animations, HTML components, Plotly charts
core/
  schemas.py       Pydantic models for every agent's output
  llm.py           Gemini wrapper: text, structured JSON, tool calling, retries
  agents.py        Reader, Analyst, Examiner, Verifier, Coach + orchestrator
  tools.py         Tools the chat agent can call
  documents.py     PDF reading, size budgeting, keyword search
  memory.py        SQLite long-term memory
  exporters.py     Markdown -> DOCX / PDF
  demo.py          Offline stand-in for Gemini + sample papers
tests/             pytest suite
```

## Tests

```bash
python -m pytest -q
```

## Limits

- Progress is stored in SQLite. Streamlit Community Cloud storage is not permanent, so it can reset.
  Swap `core/memory.py` for Supabase or Postgres to keep it for good.
- Anyone using the same name in the sidebar shares progress. There is no login.
- Gemini output was checked structurally (schemas and tool declarations) but this repo's
  tests use a fake model, so test with your own key and real papers.
