"""Demo mode: a stand-in for Gemini with canned answers and sample papers.

Used for three things: letting visitors try the app without spending your API
quota, running the tests offline, and showing the verifier catching a bad
question. All sample content is invented for the demo.
"""
from __future__ import annotations

import time
from datetime import date, timedelta
from typing import Callable, List

from .documents import Paper
from .schemas import (
    Analysis, BlindAnswer, BlindAnswers, Exam, MCQ, PaperProfile,
    RepeatedQuestion, StudyDay, StudyPlan, TopicStat,
)

SUBJECT = "Data Structures (sample)"
PAPER_NAMES = ["DS_2022_Sem1.pdf", "DS_2023_Sem1.pdf", "DS_2024_Sem1.pdf"]

_PAGES = {
    "DS_2022_Sem1.pdf": [
        "Q1 (5 marks) Explain a singly linked list and write the algorithm to insert a node at the end.\n"
        "Q2 (10 marks) Describe stack operations and convert an infix expression to postfix.",
        "Q3 (10 marks) Explain binary search tree insertion and deletion with an example.\n"
        "Q4 (5 marks) Compare BFS and DFS graph traversal.",
    ],
    "DS_2023_Sem1.pdf": [
        "Q1 (5 marks) Explain a singly linked list and write the algorithm to delete a node.\n"
        "Q2 (10 marks) Explain queue implementation using arrays and circular queues.",
        "Q3 (10 marks) Explain binary search tree traversals: inorder, preorder and postorder.\n"
        "Q4 (10 marks) Explain Dijkstra's shortest path algorithm with an example.",
    ],
    "DS_2024_Sem1.pdf": [
        "Q1 (5 marks) Convert an infix expression to postfix using a stack.\n"
        "Q2 (10 marks) Explain hashing and collision resolution techniques.",
        "Q3 (10 marks) Explain binary search tree operations and AVL tree rotations.\n"
        "Q4 (10 marks) Compare BFS and DFS and list their applications.",
    ],
}


def sample_papers() -> List[Paper]:
    return [Paper(name=n, pages=list(_PAGES[n])) for n in PAPER_NAMES]


def _analysis() -> Analysis:
    t = lambda topic, freq, imp, marks, papers: TopicStat(
        topic=topic, frequency=freq, importance=imp, avg_marks=marks, papers=papers
    )
    return Analysis(
        subject=SUBJECT,
        topics=[
            t("Binary Search Trees", 3, 10, 10, PAPER_NAMES),
            t("Linked Lists", 2, 8, 5, PAPER_NAMES[:2]),
            t("Stacks and Expression Conversion", 2, 8, 8, [PAPER_NAMES[0], PAPER_NAMES[2]]),
            t("Graph Traversal (BFS/DFS)", 2, 7, 8, [PAPER_NAMES[0], PAPER_NAMES[2]]),
            t("Queues", 1, 5, 10, [PAPER_NAMES[1]]),
            t("Shortest Path Algorithms", 1, 6, 10, [PAPER_NAMES[1]]),
            t("Hashing", 1, 5, 10, [PAPER_NAMES[2]]),
        ],
        papers=[
            PaperProfile(paper=PAPER_NAMES[0], year="2022", difficulty=5, question_count=4),
            PaperProfile(paper=PAPER_NAMES[1], year="2023", difficulty=6, question_count=4),
            PaperProfile(paper=PAPER_NAMES[2], year="2024", difficulty=7, question_count=4),
        ],
        repeated_questions=[
            RepeatedQuestion(question="Explain binary search tree operations", appeared_in=PAPER_NAMES),
            RepeatedQuestion(question="Singly linked list insertion/deletion", appeared_in=PAPER_NAMES[:2]),
            RepeatedQuestion(question="Compare BFS and DFS", appeared_in=[PAPER_NAMES[0], PAPER_NAMES[2]]),
        ],
        difficulty_trend="Difficulty rises each year, with more questions mixing two ideas.",
        summary="Binary search trees appear in every paper. Linked lists, stack expression "
        "conversion and graph traversal each repeat in two of three papers.",
        study_tips=[
            "Practise BST insertion, deletion and traversals by hand until they are automatic.",
            "Write linked list insert/delete code from memory, then trace it on paper.",
            "Learn the infix to postfix steps as a table you can reproduce quickly.",
            "Compare BFS and DFS using one example graph: queue versus stack, order of visits.",
            "Do one timed paper per week and mark it against the marking scheme.",
        ],
    )


def _mcq(topic, q, options, correct, why, diff=5) -> MCQ:
    return MCQ(topic=topic, question=q, options=options, correct_index=correct, explanation=why, difficulty=diff)


def _questions() -> List[MCQ]:
    return [
        _mcq("Binary Search Trees", "Which traversal of a BST visits nodes in ascending order?",
             ["Preorder", "Inorder", "Postorder", "Level order"], 1,
             "Inorder visits left, node, right, which gives sorted order in a BST.", 4),
        _mcq("Linked Lists", "What is the time complexity of inserting at the head of a singly linked list?",
             ["O(1)", "O(log n)", "O(n)", "O(n log n)"], 0,
             "Only the head pointer changes, so the cost does not depend on n.", 3),
        _mcq("Stacks and Expression Conversion", "Which data structure is used to convert infix to postfix?",
             ["Queue", "Stack", "Heap", "Hash table"], 1,
             "Operators wait on a stack until their precedence allows them to be output.", 4),
        _mcq("Graph Traversal (BFS/DFS)", "Which data structure does BFS use to track nodes to visit?",
             ["Stack", "Priority queue", "Queue", "Array of pointers"], 2,
             "BFS visits level by level, which is first-in first-out behaviour.", 4),
        _mcq("Binary Search Trees", "What is the worst-case search time in an unbalanced BST?",
             ["O(1)", "O(log n)", "O(n)", "O(n^2)"], 2,
             "A chain-shaped tree behaves like a linked list.", 5),
        _mcq("Hashing", "Which technique resolves collisions by storing colliding keys in a list per slot?",
             ["Linear probing", "Chaining", "Double hashing", "Rehashing"], 1,
             "Chaining keeps a list at each bucket.", 5),
        _mcq("Queues", "In a circular queue of size n, how is the next rear position computed?",
             ["rear + 1", "(rear + 1) % n", "rear - 1", "n - rear"], 1,
             "The modulo wraps the index back to zero.", 5),
        _mcq("Shortest Path Algorithms", "Dijkstra's algorithm does not work correctly with which kind of edges?",
             ["Zero weight", "Equal weight", "Negative weight", "Directed"], 2,
             "A negative edge can invalidate the assumption that a settled node is final.", 6),
    ]


class FakeLLM:
    """Same interface as GeminiLLM, but offline. Question 3 is deliberately given a
    wrong answer key the first time so the Verifier visibly catches and fixes it."""

    def __init__(self, delay: float = 0.0):
        self.delay = delay
        self.repaired = False

    def _wait(self):
        if self.delay:
            time.sleep(self.delay)

    def structured(self, prompt, schema, system=None, temperature=0.4):
        self._wait()
        if schema is Analysis:
            return _analysis()
        if schema is Exam:
            if "disputed" in prompt:  # the repair request
                self.repaired = True
                return Exam(title="Repairs", questions=[_questions()[2]])
            questions = [q.model_copy(deep=True) for q in _questions()]
            questions[2].correct_index = 0  # wrong key on purpose
            return Exam(title="Sample Mock Exam", questions=questions)
        if schema is BlindAnswers:
            # the independent solver knows the true answers
            truth = _questions()
            n = prompt.count("\n[") + 1
            return BlindAnswers(
                answers=[BlindAnswer(question_index=i, chosen_index=truth[i % len(truth)].correct_index, confidence=90)
                         for i in range(n)]
            )
        if schema is StudyPlan:
            days = []
            focus = ["Binary Search Trees", "Linked Lists", "Stacks and Expression Conversion",
                     "Graph Traversal (BFS/DFS)", "Hashing", "Queues", "Shortest Path Algorithms"]
            for i in range(7):
                days.append(StudyDay(
                    day=i + 1, label=(date.today() + timedelta(days=i)).strftime("%a %d %b"),
                    focus_topics=[focus[i % len(focus)]],
                    tasks=[f"Revise notes on {focus[i % len(focus)]}", "Solve two past-paper questions by hand",
                           "Take a 10-minute self-test"],
                    hours=3.0,
                ))
            return StudyPlan(
                summary="Highest-weight topics come first, then everything is revisited.",
                days=days,
                revision_strategy=["Re-do wrong quiz answers every second day", "Do a full timed paper on the last weekend"],
                tips=["Sleep matters more than a late night of cramming.", "Explain each topic aloud without notes."],
            )
        raise ValueError(f"FakeLLM has no canned answer for {schema.__name__}")

    def text(self, prompt, system=None, temperature=0.6):
        self._wait()
        return "Demo answer."

    def transcribe_pdf(self, data: bytes) -> str:
        return ""

    def run_tools(self, prompt: str, tools: List[Callable], system=None) -> str:
        """Pretend to be a model that picks tools by keyword, so the chat tab works offline."""
        self._wait()
        by_name = {fn.__name__: fn for fn in tools}
        lowered = prompt.lower()
        if "weak" in lowered:
            data = by_name["get_weak_topics"]()
            return ("Your weakest topics so far: " + ", ".join(f"{d['topic']} ({d['mastery_percent']}%)" for d in data)
                    + "." if data else "Take a quiz first and I can tell you where you are weakest.")
        if "day" in lowered or "when" in lowered:
            info = by_name["days_until_exam"]()
            return f"Your exam is on {info['exam_date']}, which is {info['days_left']} days away."
        if "repeat" in lowered:
            data = by_name["get_repeated_questions"]()
            return "Repeated questions: " + "; ".join(d["question"] for d in data)
        if "search" in lowered or "find" in lowered:
            hits = by_name["search_papers"](lowered.split()[-1])
            return "Matches: " + ", ".join(f"{h['paper']} p.{h['page']}" for h in hits) if hits else "No matches."
        data = by_name["get_topic_stats"](3)
        return "Focus first on: " + ", ".join(f"{d['topic']} (importance {d['importance']})" for d in data) + "."
