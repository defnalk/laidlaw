"""End-to-end tests for the FastAPI surface (compare, workshop, cards, tornado)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _isolated_workshop_db(tmp_path, monkeypatch):
    """Each test gets a clean SQLite DB so workshop state doesn't leak."""
    from app import workshop as w

    monkeypatch.setattr(w, "DB_PATH", tmp_path / "ws.db")
    w._init()
    yield


def test_list_sites():
    r = client.get("/sites")
    assert r.status_code == 200
    sites = r.json()
    assert len(sites) == 3
    assert {s["sector"] for s in sites} == {"steel", "cement", "chemicals"}


def test_compare_returns_recommendation():
    body = {
        "ccs": {"capture_rate": 0.9, "capture_tech": "amine", "transport": "pipeline", "storage": "saline_aquifer"},
        "electrification": {"technology": "electric_arc_furnace", "hydrogen_tonnes_yr": 0, "hydrogen_source": "dedicated_renewable"},
    }
    r = client.post("/compare/uk_steel_pt", json=body)
    assert r.status_code == 200
    d = r.json()
    assert d["recommended"] in ("ccs", "electrification", "tie")
    assert "narrative" in d and len(d["caveats"]) >= 4
    assert d["ccs"]["abatement_percentage"] == pytest.approx(90)


def test_explain_returns_latex_steps():
    body = {
        "ccs": {"capture_rate": 0.9, "capture_tech": "amine", "transport": "pipeline", "storage": "saline_aquifer"},
        "electrification": {"technology": "electric_kiln", "hydrogen_tonnes_yr": 0, "hydrogen_source": "dedicated_renewable"},
    }
    r = client.post("/explain/uk_cement_north", json=body)
    assert r.status_code == 200
    d = r.json()
    assert all("latex" in s and "source" in s for s in d["ccs"])
    assert all("latex" in s and "source" in s for s in d["electrification"])


def test_cards_html_has_all_applicable_techs():
    r = client.get("/cards/uk_steel_pt")
    assert r.status_code == 200
    html = r.text
    # 3 CCS techs + 1 sector-applicable electrification tech
    assert "Amine" in html and "Oxy-fuel" in html and "Calcium" in html
    assert "Electric Arc Furnace" in html
    # Cement-only tech should NOT appear in steel cards
    assert "Electric Kiln" not in html


def test_tornado_orders_by_swing():
    r = client.get("/tornado/uk_steel_pt")
    assert r.status_code == 200
    rows = r.json()["rows"]
    assert len(rows) == 3
    swings = [max(r["ccs_swing"], r["elec_swing"]) for r in rows]
    assert swings == sorted(swings, reverse=True)


def test_workshop_full_cycle():
    client.post("/workshop/PT24/start", params={"site_id": "uk_steel_pt"})
    client.post("/workshop/PT24/vote", json={"role": "worker", "choice": "ccs"})
    client.post("/workshop/PT24/vote", json={"role": "resident", "choice": "electrification"})
    client.post("/workshop/PT24/vote", json={"role": "resident", "choice": "electrification"})
    client.post("/workshop/PT24/comment", json={"role": "resident", "text": "What about my kids' asthma?"})

    r = client.get("/workshop/PT24")
    assert r.status_code == 200
    s = r.json()
    assert s["tally"]["total"] == 3
    assert s["tally"]["by_choice"]["electrification"] == 2
    assert s["tally"]["by_role"]["resident"]["electrification"] == 2
    assert len(s["comments"]) == 1
    assert "asthma" in s["comments"][0]["text"]


def test_workshop_vote_without_start_404s():
    r = client.post("/workshop/NOPE/vote", json={"role": "worker", "choice": "ccs"})
    assert r.status_code == 404


def test_reload_assumptions():
    r = client.post("/reload")
    assert r.status_code == 200
