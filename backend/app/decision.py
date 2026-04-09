"""Multi-criteria decision algorithm.

Reads weights from data/assumptions.json → decision_weights.
This is the extension point for richer algorithms (AHP, TOPSIS,
or a learned ranker over workshop voting data).
"""
from __future__ import annotations

from .data_loader import assumptions
from .models import PathwayMetrics


def _normalise(value: float, lo: float, hi: float, higher_is_better: bool = True) -> float:
    if hi == lo:
        return 0.5
    x = (value - lo) / (hi - lo)
    x = max(0.0, min(1.0, x))
    return x if higher_is_better else 1.0 - x


def score_pathway(m: PathwayMetrics, cost_lo: float, cost_hi: float) -> float:
    """Weighted multi-criteria score in [0, 1]. Higher = better."""
    w = assumptions()["decision_weights"]
    components = {
        "cost_per_tco2":            _normalise(m.cost_per_tco2_avoided, cost_lo, cost_hi, higher_is_better=False),
        "abatement_percentage":     _normalise(m.abatement_percentage, 0, 100, higher_is_better=True),
        "air_quality_score":        _normalise(m.air_quality_score, 0, 1, higher_is_better=True),
        "jobs_net_score":           _normalise(m.jobs_net_score, -0.2, 0.3, higher_is_better=True),
        "infrastructure_readiness": _normalise(m.infrastructure_readiness, 0, 1, higher_is_better=True),
        "implementation_speed":     _normalise(m.implementation_timeline_years, 4, 15, higher_is_better=False),
    }
    return sum(w[k] * v for k, v in components.items() if k in w)


def compare(ccs: PathwayMetrics, elec: PathwayMetrics) -> tuple[float, float, str]:
    cost_lo = min(ccs.cost_per_tco2_avoided, elec.cost_per_tco2_avoided)
    cost_hi = max(ccs.cost_per_tco2_avoided, elec.cost_per_tco2_avoided)
    s_ccs = score_pathway(ccs, cost_lo, cost_hi)
    s_elec = score_pathway(elec, cost_lo, cost_hi)
    if abs(s_ccs - s_elec) < 0.02:
        verdict = "tie"
    else:
        verdict = "ccs" if s_ccs > s_elec else "electrification"
    return s_ccs, s_elec, verdict
