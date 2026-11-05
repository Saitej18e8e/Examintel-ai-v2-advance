"""Typed data models shared by every agent.

Gemini is asked to return JSON that matches these models, so the app can draw
charts, score quizzes and track progress instead of just showing text.
"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


# ---------- Analyst agent ----------
class TopicStat(BaseModel):
    topic: str
    frequency: int = Field(description="Number of papers in which the topic appears")
    importance: int = Field(description="1 (minor) to 10 (essential)")
    avg_marks: Optional[float] = Field(default=None, description="Average marks if visible")
    papers: List[str] = Field(default_factory=list, description="File names where it appears")


class PaperProfile(BaseModel):
    paper: str
    year: Optional[str] = None
    difficulty: int = Field(description="1 (easy) to 10 (very hard)")
    question_count: Optional[int] = None


class RepeatedQuestion(BaseModel):
    question: str
    appeared_in: List[str]


class Analysis(BaseModel):
    subject: str
    topics: List[TopicStat]
    papers: List[PaperProfile]
    repeated_questions: List[RepeatedQuestion]
    difficulty_trend: str
    summary: str
    study_tips: List[str]


# ---------- Examiner + Verifier agents ----------
class MCQ(BaseModel):
    topic: str
    question: str
    options: List[str] = Field(description="Exactly four answer options, without A/B/C/D prefixes")
    correct_index: int = Field(description="Index 0-3 of the correct option")
    explanation: str
    difficulty: int = Field(description="1 (easy) to 10 (very hard)")


class Exam(BaseModel):
    title: str
    questions: List[MCQ]


class BlindAnswer(BaseModel):
    question_index: int
    chosen_index: int
    confidence: int = Field(description="0-100")


class BlindAnswers(BaseModel):
    answers: List[BlindAnswer]


# ---------- Coach agent ----------
class StudyDay(BaseModel):
    day: int
    label: str = Field(description="Date or weekday label")
    focus_topics: List[str]
    tasks: List[str]
    hours: float


class StudyPlan(BaseModel):
    summary: str
    days: List[StudyDay]
    revision_strategy: List[str]
    tips: List[str]


# ---------- Run bookkeeping ----------
class AgentEvent(BaseModel):
    agent: str
    status: str  # running | done | failed | skipped
    message: str = ""
    seconds: float = 0.0
