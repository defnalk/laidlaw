"""FastAPI app — endpoints for sites, pathways, comparison, sensitivity."""
from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from . import cards, data_loader, explain, workshop
from .decision import compare
from .engine import compute_ccs, compute_electrification
from .models import (
    CCSPathway,
    ComparisonResult,
    ElectrificationPathway,
    Site,
)

app = FastAPI(
    title="Laidlaw IDPC",
    description="Industrial Decarbonisation Pathway Comparator — CCS vs. Electrification",
    version="0.1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve the minimal static frontend at /ui
_FRONTEND = Path(__file__).resolve().parents[2] / "frontend"
if _FRONTEND.exists():
    app.mount("/ui", StaticFiles(directory=str(_FRONTEND), html=True), name="ui")


def _site(site_id: str) -> Site:
    for s in data_loader.sites():
        if s["id"] == site_id:
            return Site(**s)
    raise HTTPException(404, f"Site {site_id} not found")


@app.get("/sites")
def list_sites() -> list[Site]:
    return [Site(**s) for s in data_loader.sites()]


@app.get("/sites/{site_id}")
def get_site(site_id: str) -> Site:
    return _site(site_id)


@app.get("/assumptions")
def get_assumptions() -> dict:
    return data_loader.assumptions()


@app.get("/sdg-mapping")
def get_sdg_mapping() -> dict:
    return data_loader.sdg_mapping()


@app.post("/reload")
def hot_reload() -> dict:
    """Re-read all JSON in data/. Use during workshops to live-edit assumptions."""
    data_loader.reload_all()
    return {"status": "reloaded"}


@app.post("/compare/{site_id}", response_model=ComparisonResult)
def compare_site(
    site_id: str,
    ccs: CCSPathway,
    electrification: ElectrificationPathway,
    discount_rate: float | None = None,
) -> ComparisonResult:
    site = _site(site_id)
    m_ccs = compute_ccs(site, ccs, discount_rate)
    m_elec = compute_electrification(site, electrification, discount_rate)
    s_ccs, s_elec, verdict = compare(m_ccs, m_elec)
    return ComparisonResult(
        site_id=site_id,
        ccs=m_ccs,
        electrification=m_elec,
        decision_score_ccs=s_ccs,
        decision_score_electrification=s_elec,
        recommended=verdict,
        narrative=explain.narrative(site, m_ccs, m_elec, verdict),
        caveats=explain.CAVEATS,
    )


@app.get("/sensitivity/{site_id}")
def sensitivity(
    site_id: str,
    param: str = "discount_rate",
    lo: float = 0.04,
    hi: float = 0.12,
    step: float = 0.01,
) -> dict:
    """Sweep a parameter and return cost/tCO2 curves for both pathways.

    Currently supports param=discount_rate. Extend by adding branches.
    """
    site = _site(site_id)
    # default pathways for the sweep
    ccs = CCSPathway(capture_rate=0.9, capture_tech="amine", transport="pipeline", storage="saline_aquifer")
    elec = ElectrificationPathway(
        technology={"steel": "electric_arc_furnace", "cement": "electric_kiln", "chemicals": "e_cracker"}[site.sector],
        hydrogen_tonnes_yr=0,
    )

    xs, ccs_y, elec_y = [], [], []
    x = lo
    while x <= hi + 1e-9:
        xs.append(round(x, 4))
        ccs_y.append(compute_ccs(site, ccs, discount_rate=x).cost_per_tco2_avoided)
        elec_y.append(compute_electrification(site, elec, discount_rate=x).cost_per_tco2_avoided)
        x += step
    return {"param": param, "x": xs, "ccs": ccs_y, "electrification": elec_y}


@app.get("/cards/{site_id}", response_class=HTMLResponse)
def pathway_cards(site_id: str) -> str:
    """Print-friendly HTML grid of A5 pathway cards for workshops.
    Open in a browser → File → Print → Save as PDF."""
    return cards.render_cards(_site(site_id))


# ---------- Workshop sessions: votes + comments ----------------------------

class VoteIn(BaseModel):
    role: str
    choice: str  # "ccs" | "electrification" | "neither" | "both"


class CommentIn(BaseModel):
    role: str
    text: str


@app.post("/workshop/{code}/start")
def workshop_start(code: str, site_id: str) -> dict:
    s = workshop.get_or_create(code, site_id)
    return {"code": s.code, "site_id": s.site_id}


@app.post("/workshop/{code}/vote")
def workshop_vote(code: str, vote: VoteIn) -> dict:
    try:
        s = workshop.cast_vote(code, vote.role, vote.choice)  # type: ignore[arg-type]
    except KeyError:
        raise HTTPException(404, "Workshop not started — call /workshop/{code}/start first")
    return s.tally()


@app.post("/workshop/{code}/comment")
def workshop_comment(code: str, comment: CommentIn) -> dict:
    try:
        s = workshop.add_comment(code, comment.role, comment.text)  # type: ignore[arg-type]
    except KeyError:
        raise HTTPException(404, "Workshop not started")
    return {"comments": len(s.comments)}


@app.get("/workshop/{code}")
def workshop_state(code: str) -> dict:
    s = workshop.get(code)
    if s is None:
        raise HTTPException(404, "No such workshop")
    return {
        "code": s.code,
        "site_id": s.site_id,
        "tally": s.tally(),
        "comments": s.comments,
    }


@app.post("/explain/{site_id}")
def explain_site(
    site_id: str,
    ccs: CCSPathway,
    electrification: ElectrificationPathway,
) -> dict:
    """Return step-by-step calculation traces with LaTeX + citations."""
    site = _site(site_id)
    return {
        "ccs": explain.explain_ccs(site, ccs),
        "electrification": explain.explain_electrification(site, electrification),
    }
