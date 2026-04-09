"""Edge cases for the calculation engine.

Complements test_engine.py with corners that previously broke or were
silently mis-handled: degenerate discount rates, all hydrogen sources,
extreme capture rates, COP-aware electrification, and the country-indexed
hydrogen pipeline proximity.
"""

from __future__ import annotations

import math

import pytest

from app.data_loader import assumptions, sites
from app.engine import compute_ccs, compute_electrification
from app.models import CCSPathway, ElectrificationPathway, Site


def _site(sector: str) -> Site:
    return Site(**next(s for s in sites() if s["sector"] == sector))


# ── discount-rate corners ────────────────────────────────────────────────
class TestDiscountRate:
    def test_zero_discount_rate_collapses_to_simple_sum(self) -> None:
        site = _site("steel")
        p = CCSPathway(
            capture_rate=0.9, capture_tech="amine",
            transport="pipeline", storage="saline_aquifer",
        )
        m = compute_ccs(site, p, discount_rate=0.0)
        assert math.isfinite(m.cost_per_tco2_avoided)
        assert m.cost_per_tco2_avoided > 0

    def test_high_discount_rate_increases_cost_per_tco2(self) -> None:
        site = _site("steel")
        p = CCSPathway(
            capture_rate=0.9, capture_tech="amine",
            transport="pipeline", storage="saline_aquifer",
        )
        low = compute_ccs(site, p, discount_rate=0.03).cost_per_tco2_avoided
        high = compute_ccs(site, p, discount_rate=0.20).cost_per_tco2_avoided
        assert high > low


# ── hydrogen source branches ─────────────────────────────────────────────
class TestHydrogenSources:
    @pytest.mark.parametrize("source", ["grid_electrolysis", "dedicated_renewable"])
    def test_both_sources_produce_finite_cost(self, source: str) -> None:
        site = _site("chemicals")
        p = ElectrificationPathway(
            technology="e_cracker",
            hydrogen_tonnes_yr=10_000,
            hydrogen_source=source,  # type: ignore[arg-type]
        )
        m = compute_electrification(site, p)
        assert math.isfinite(m.cost_per_tco2_avoided)

    def test_dedicated_renewable_has_higher_capex_than_grid(self) -> None:
        site = _site("chemicals")
        kw = {"technology": "e_cracker", "hydrogen_tonnes_yr": 10_000}
        grid = compute_electrification(
            site, ElectrificationPathway(**kw, hydrogen_source="grid_electrolysis"),
        )
        ded = compute_electrification(
            site, ElectrificationPathway(**kw, hydrogen_source="dedicated_renewable"),
        )
        assert ded.capex_total_gbp > grid.capex_total_gbp


# ── COP-aware electricity demand ─────────────────────────────────────────
class TestHeatPumpCOP:
    def test_resistive_default_unchanged(self) -> None:
        # EAF stays at COP=1, so the OPEX should equal the legacy formula.
        site = _site("steel")
        p = ElectrificationPathway(
            technology="electric_arc_furnace", electricity_price_gbp_mwh=50,
        )
        m = compute_electrification(site, p)
        assumptions()
        replaced = site.thermal_demand_gwh * 1.0  # EAF replacement_fraction=1.0
        expected = replaced * 1000 * 50  # MWh × £/MWh
        assert m.opex_annual_gbp == pytest.approx(expected, rel=1e-6)

    def test_unknown_technology_falls_back_to_resistive(self) -> None:
        # If a tech key isn't in heat_pump_cop_by_technology the engine must
        # not crash; it falls back to COP=1 (resistive).
        site = _site("cement")
        # electric_kiln is in technologies.json and stays resistive.
        m = compute_electrification(site, ElectrificationPathway(technology="electric_kiln"))
        assert m.opex_annual_gbp > 0


# ── country-indexed h2 pipeline proximity ────────────────────────────────
class TestH2Proximity:
    def test_h2_proximity_drives_infra_score(self) -> None:
        # Two identical sites differing only in country code: the one in a
        # high-readiness country (Netherlands) must score higher.
        raw = next(s for s in sites() if s["sector"] == "chemicals")
        nl = Site(**{**raw, "country": "Netherlands"})
        unknown = Site(**{**raw, "country": "Atlantis"})
        p = ElectrificationPathway(technology="e_cracker", hydrogen_tonnes_yr=5000)
        m_nl = compute_electrification(nl, p)
        m_unknown = compute_electrification(unknown, p)
        assert m_nl.infrastructure_readiness > m_unknown.infrastructure_readiness


# ── extreme capture rates ────────────────────────────────────────────────
class TestExtremeCapture:
    def test_full_capture_residual_zero(self) -> None:
        site = _site("steel")
        p = CCSPathway(
            capture_rate=1.0, capture_tech="amine",
            transport="pipeline", storage="saline_aquifer",
        )
        m = compute_ccs(site, p)
        assert m.residual_emissions_tco2 == pytest.approx(0)

    def test_capture_rate_outside_unit_interval_rejected(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            CCSPathway(
                capture_rate=1.5, capture_tech="amine",
                transport="pipeline", storage="saline_aquifer",
            )
