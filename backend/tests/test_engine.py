"""Engine invariants and edge cases."""
from __future__ import annotations

import pytest

from app.data_loader import sites
from app.engine import compute_ccs, compute_electrification
from app.models import CCSPathway, ElectrificationPathway, Site


def _site(sector: str) -> Site:
    return Site(**next(s for s in sites() if s["sector"] == sector))


def test_full_capture_zero_residual():
    site = _site("steel")
    p = CCSPathway(capture_rate=1.0, capture_tech="amine", transport="pipeline", storage="saline_aquifer")
    m = compute_ccs(site, p)
    assert m.residual_emissions_tco2 == pytest.approx(0)
    assert m.abatement_percentage == 100


def test_zero_capture_no_abatement_infinite_cost():
    site = _site("cement")
    p = CCSPathway(capture_rate=0.0, capture_tech="amine", transport="pipeline", storage="saline_aquifer")
    m = compute_ccs(site, p)
    assert m.abatement_percentage == 0
    assert m.cost_per_tco2_avoided == float("inf")


def test_free_electricity_makes_electrification_cheap():
    site = _site("steel")
    p = ElectrificationPathway(technology="electric_arc_furnace", electricity_price_gbp_mwh=0)
    m = compute_electrification(site, p)
    # OPEX should collapse to zero, cost dominated by CAPEX only
    assert m.opex_annual_gbp == pytest.approx(0)
    assert m.cost_per_tco2_avoided > 0


def test_zero_grid_carbon_intensity_maximises_abatement():
    raw = next(s for s in sites() if s["sector"] == "chemicals")
    raw = {**raw, "grid_carbon_intensity_gco2_kwh": 0}
    site = Site(**raw)
    p = ElectrificationPathway(technology="e_cracker")
    m = compute_electrification(site, p)
    assert m.abatement_percentage == pytest.approx(100, abs=0.01)


def test_extreme_discount_rates_dont_crash():
    site = _site("steel")
    p = CCSPathway(capture_rate=0.9, capture_tech="amine", transport="pipeline", storage="saline_aquifer")
    for r in (0.0, 0.01, 0.50):
        m = compute_ccs(site, p, discount_rate=r)
        assert m.cost_per_tco2_avoided > 0


def test_electrification_better_air_quality_than_ccs():
    site = _site("cement")
    ccs = compute_ccs(
        site,
        CCSPathway(capture_rate=0.9, capture_tech="amine", transport="pipeline", storage="saline_aquifer"),
    )
    elec = compute_electrification(site, ElectrificationPathway(technology="electric_kiln"))
    assert elec.air_quality_score > ccs.air_quality_score
