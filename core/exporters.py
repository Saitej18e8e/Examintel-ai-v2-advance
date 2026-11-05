"""Turn structured results into Markdown, then into DOCX / PDF downloads."""
from __future__ import annotations

import io
import re
from typing import List

from docx import Document
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from .schemas import Analysis, Exam, StudyPlan

_BOLD = re.compile(r"\*\*(.+?)\*\*")
LETTERS = "ABCD"


# ---------- Markdown renderers ----------
def analysis_to_markdown(a: Analysis) -> str:
    lines: List[str] = [f"# Exam Analysis: {a.subject}", "", "## Summary", a.summary, "", "## Topics"]
    for t in sorted(a.topics, key=lambda t: (t.importance, t.frequency), reverse=True):
        lines.append(f"- **{t.topic}**: importance {t.importance}/10, in {t.frequency} paper(s)")
    lines += ["", "## Repeated Questions"]
    lines += [f"- {q.question} ({len(q.appeared_in)} papers)" for q in a.repeated_questions] or ["- None found"]
    lines += ["", "## Difficulty Trend", a.difficulty_trend, "", "## Study Tips"]
    lines += [f"- {tip}" for tip in a.study_tips]
    return "\n".join(lines)


def exam_to_markdown(exam: Exam, include_answers: bool = True) -> str:
    lines = [f"# {exam.title}", ""]
    for i, q in enumerate(exam.questions, start=1):
        lines.append(f"## Question {i} ({q.topic})")
        lines.append(q.question)
        lines += [f"- {LETTERS[j]}. {opt}" for j, opt in enumerate(q.options)]
        lines.append("")
    if include_answers:
        lines.append("# Answer Key")
        for i, q in enumerate(exam.questions, start=1):
            lines.append(f"- **{i}. {LETTERS[q.correct_index]}**: {q.explanation}")
    return "\n".join(lines)


def plan_to_markdown(p: StudyPlan) -> str:
    lines = ["# Study Plan", "", p.summary, ""]
    for d in p.days:
        lines.append(f"## Day {d.day} ({d.label}), {d.hours:g} h")
        lines.append("Focus: " + ", ".join(d.focus_topics))
        lines += [f"- {task}" for task in d.tasks]
        lines.append("")
    lines += ["# Revision Strategy"] + [f"- {s}" for s in p.revision_strategy]
    lines += ["", "# Tips"] + [f"- {s}" for s in p.tips]
    return "\n".join(lines)


# ---------- File builders ----------
def _add_runs(paragraph, text: str) -> None:
    """Add text to a DOCX paragraph, turning **bold** markers into real bold."""
    position = 0
    for match in _BOLD.finditer(text):
        if match.start() > position:
            paragraph.add_run(text[position : match.start()])
        paragraph.add_run(match.group(1)).bold = True
        position = match.end()
    if position < len(text):
        paragraph.add_run(text[position:])


def markdown_to_docx(markdown: str, title: str = "ExamIntel AI Report") -> io.BytesIO:
    doc = Document()
    doc.add_heading(title, level=0)
    for raw in markdown.split("\n"):
        line = raw.strip()
        if not line:
            continue
        if line.startswith("### "):
            doc.add_heading(line[4:], level=3)
        elif line.startswith("## "):
            doc.add_heading(line[3:], level=2)
        elif line.startswith("# "):
            doc.add_heading(line[2:], level=1)
        elif line.startswith(("- ", "* ")):
            _add_runs(doc.add_paragraph(style="List Bullet"), line[2:])
        else:
            _add_runs(doc.add_paragraph(), line)
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer


def _escape(text: str) -> str:
    safe = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return _BOLD.sub(r"<b>\1</b>", safe)


def markdown_to_pdf(markdown: str, title: str = "ExamIntel AI Report") -> io.BytesIO:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    for name in ("Normal", "Heading1", "Heading2", "Heading3", "Title"):
        styles[name].wordWrap = "CJK"  # lets long unbroken words wrap

    story = [Paragraph(_escape(title), styles["Title"]), Spacer(1, 12)]
    for raw in markdown.split("\n"):
        line = raw.strip()
        if not line:
            story.append(Spacer(1, 6))
            continue
        try:
            if line.startswith("### "):
                story.append(Paragraph(_escape(line[4:]), styles["Heading3"]))
            elif line.startswith("## "):
                story.append(Paragraph(_escape(line[3:]), styles["Heading2"]))
            elif line.startswith("# "):
                story.append(Paragraph(_escape(line[2:]), styles["Heading1"]))
            elif line.startswith(("- ", "* ")):
                story.append(Paragraph("• " + _escape(line[2:]), styles["Normal"]))
            else:
                story.append(Paragraph(_escape(line), styles["Normal"]))
        except Exception:  # skip one bad line instead of losing the whole file
            continue
    doc.build(story)
    buffer.seek(0)
    return buffer
