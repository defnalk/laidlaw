"""Workshop session store — SQLite-backed (stdlib only).

A workshop is identified by a short code (e.g. "PT24"). Votes and
qualitative comments survive server restarts. The DB lives at
data/workshops.db so it sits next to the rest of the knowledge layer.
"""
from __future__ import annotations

import sqlite3
from collections import defaultdict
from pathlib import Path
from time import time
from typing import Literal

Choice = Literal["ccs", "electrification", "neither", "both"]
Role = Literal["student", "resident", "worker", "industry", "policy", "other"]

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "workshops.db"


def _conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def _init() -> None:
    with _conn() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                code TEXT PRIMARY KEY,
                site_id TEXT NOT NULL,
                created_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS votes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL,
                role TEXT NOT NULL,
                choice TEXT NOT NULL,
                at REAL NOT NULL,
                FOREIGN KEY(code) REFERENCES sessions(code)
            );
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL,
                role TEXT NOT NULL,
                text TEXT NOT NULL,
                at REAL NOT NULL,
                FOREIGN KEY(code) REFERENCES sessions(code)
            );
            CREATE INDEX IF NOT EXISTS idx_votes_code ON votes(code);
            CREATE INDEX IF NOT EXISTS idx_comments_code ON comments(code);
            """
        )


_init()


def get_or_create(code: str, site_id: str) -> dict:
    with _conn() as c:
        row = c.execute("SELECT * FROM sessions WHERE code = ?", (code,)).fetchone()
        if row is None:
            c.execute(
                "INSERT INTO sessions(code, site_id, created_at) VALUES (?, ?, ?)",
                (code, site_id, time()),
            )
            return {"code": code, "site_id": site_id, "created_at": time()}
        return dict(row)


def get(code: str) -> dict | None:
    with _conn() as c:
        row = c.execute("SELECT * FROM sessions WHERE code = ?", (code,)).fetchone()
        return dict(row) if row else None


def cast_vote(code: str, role: Role, choice: Choice) -> dict:
    if get(code) is None:
        raise KeyError(code)
    with _conn() as c:
        c.execute(
            "INSERT INTO votes(code, role, choice, at) VALUES (?, ?, ?, ?)",
            (code, role, choice, time()),
        )
    return tally(code)


def add_comment(code: str, role: Role, text: str) -> dict:
    if get(code) is None:
        raise KeyError(code)
    with _conn() as c:
        c.execute(
            "INSERT INTO comments(code, role, text, at) VALUES (?, ?, ?, ?)",
            (code, role, text, time()),
        )
    return {"comments": _comment_count(code)}


def _comment_count(code: str) -> int:
    with _conn() as c:
        return c.execute("SELECT COUNT(*) FROM comments WHERE code = ?", (code,)).fetchone()[0]


def tally(code: str) -> dict:
    with _conn() as c:
        rows = c.execute("SELECT role, choice FROM votes WHERE code = ?", (code,)).fetchall()
    by_choice: dict[str, int] = defaultdict(int)
    by_role: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for r in rows:
        by_choice[r["choice"]] += 1
        by_role[r["role"]][r["choice"]] += 1
    return {
        "total": len(rows),
        "by_choice": dict(by_choice),
        "by_role": {k: dict(v) for k, v in by_role.items()},
    }


def comments(code: str, limit: int = 100) -> list[dict]:
    with _conn() as c:
        rows = c.execute(
            "SELECT role, text, at FROM comments WHERE code = ? ORDER BY at DESC LIMIT ?",
            (code, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def state(code: str) -> dict | None:
    s = get(code)
    if s is None:
        return None
    return {**s, "tally": tally(code), "comments": comments(code)}
