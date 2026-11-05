"""Long-term memory in SQLite: topic mastery, quiz history and plan progress.

Rows are keyed by a user name so several people can share one deployment.
Note: Streamlit Community Cloud storage is not permanent, so progress can reset
when the app restarts. Swap this class for Supabase/Postgres to keep it forever.
"""
from __future__ import annotations

import os
import sqlite3
from contextlib import closing
from typing import Dict, Iterable, List, Tuple

SCHEMA = """
CREATE TABLE IF NOT EXISTS mastery (
    user TEXT NOT NULL, topic TEXT NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0, correct INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user, topic)
);
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT, user TEXT NOT NULL,
    ts TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, score INTEGER NOT NULL, total INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS plan_progress (
    user TEXT NOT NULL, day INTEGER NOT NULL, done INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user, day)
);
"""


class Memory:
    def __init__(self, path: str = "data/examintel.db"):
        self.path = path
        if path != ":memory:":
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        # An in-memory database vanishes when its connection closes, so keep one open.
        self._shared = sqlite3.connect(":memory:", check_same_thread=False) if path == ":memory:" else None
        with self._conn() as conn:
            conn.executescript(SCHEMA)

    def _conn(self):
        return self._shared if self._shared else sqlite3.connect(self.path)

    def _run(self, sql: str, args: Iterable = ()):
        conn = self._conn()
        try:
            cur = conn.execute(sql, tuple(args))
            rows = cur.fetchall()
            conn.commit()
            return rows
        finally:
            if not self._shared:
                conn.close()

    # ---- quiz results -----------------------------------------------
    def record_answers(self, user: str, results: List[Tuple[str, bool]]) -> None:
        for topic, correct in results:
            self._run(
                "INSERT INTO mastery(user, topic, attempts, correct) VALUES(?,?,1,?) "
                "ON CONFLICT(user, topic) DO UPDATE SET attempts=attempts+1, correct=correct+?",
                (user, topic, int(correct), int(correct)),
            )
        score = sum(1 for _, ok in results if ok)
        self._run("INSERT INTO runs(user, score, total) VALUES(?,?,?)", (user, score, len(results)))

    def mastery(self, user: str) -> Dict[str, float]:
        """Smoothed accuracy per topic (0-1); one lucky guess does not mean mastery."""
        rows = self._run("SELECT topic, attempts, correct FROM mastery WHERE user=?", (user,))
        return {topic: (correct + 1) / (attempts + 2) for topic, attempts, correct in rows}

    def weak_topics(self, user: str, limit: int = 5) -> List[dict]:
        scores = self.mastery(user)
        ranked = sorted(scores.items(), key=lambda item: item[1])[:limit]
        return [{"topic": t, "mastery_percent": round(s * 100)} for t, s in ranked]

    def history(self, user: str, limit: int = 20) -> List[dict]:
        rows = self._run(
            "SELECT ts, score, total FROM runs WHERE user=? ORDER BY id DESC LIMIT ?", (user, limit)
        )
        return [{"when": ts, "score": s, "total": t} for ts, s, t in reversed(rows)]

    # ---- study plan progress ----------------------------------------
    def set_day_done(self, user: str, day: int, done: bool) -> None:
        self._run(
            "INSERT INTO plan_progress(user, day, done) VALUES(?,?,?) "
            "ON CONFLICT(user, day) DO UPDATE SET done=?",
            (user, day, int(done), int(done)),
        )

    def done_days(self, user: str) -> set:
        rows = self._run("SELECT day FROM plan_progress WHERE user=? AND done=1", (user,))
        return {day for (day,) in rows}

    def reset(self, user: str) -> None:
        for table in ("mastery", "runs", "plan_progress"):
            self._run(f"DELETE FROM {table} WHERE user=?", (user,))
