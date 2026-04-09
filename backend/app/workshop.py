"""In-memory workshop session store: votes + qualitative comments.

Deliberately simple — no auth, no DB. A workshop is identified by a
short code (e.g. "PT24"). Restart wipes state. For persistent runs
swap the dict for SQLite via sqlite3 stdlib (no extra deps).
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from time import time
from typing import Literal

Choice = Literal["ccs", "electrification", "neither", "both"]
Role = Literal["student", "resident", "worker", "industry", "policy", "other"]


@dataclass
class Session:
    code: str
    site_id: str
    created_at: float = field(default_factory=time)
    votes: list[dict] = field(default_factory=list)
    comments: list[dict] = field(default_factory=list)

    def tally(self) -> dict:
        by_choice: dict[str, int] = defaultdict(int)
        by_role: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for v in self.votes:
            by_choice[v["choice"]] += 1
            by_role[v["role"]][v["choice"]] += 1
        return {
            "total": len(self.votes),
            "by_choice": dict(by_choice),
            "by_role": {k: dict(v) for k, v in by_role.items()},
        }


_SESSIONS: dict[str, Session] = {}


def get_or_create(code: str, site_id: str) -> Session:
    s = _SESSIONS.get(code)
    if s is None:
        s = Session(code=code, site_id=site_id)
        _SESSIONS[code] = s
    return s


def get(code: str) -> Session | None:
    return _SESSIONS.get(code)


def cast_vote(code: str, role: Role, choice: Choice) -> Session:
    s = _SESSIONS.get(code)
    if s is None:
        raise KeyError(code)
    s.votes.append({"role": role, "choice": choice, "at": time()})
    return s


def add_comment(code: str, role: Role, text: str) -> Session:
    s = _SESSIONS.get(code)
    if s is None:
        raise KeyError(code)
    s.comments.append({"role": role, "text": text, "at": time()})
    return s
