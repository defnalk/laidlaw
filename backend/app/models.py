"""Pydantic domain models for sites, pathways, and comparison results."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Sector = Literal["steel", "cement", "chemicals"]


class Site(BaseModel):
    id: str
    name: str
    sector: Sector
    country: str
    annual_co2_tonnes: float
    current_fuel_mix: dict[str, float]
    thermal_demand_gwh: float
    electrical_demand_gwh: float
    workforce_size: int
    proximity_to_co2_storage_km: float
    grid_carbon_intensity_gco2_kwh: float
    local_air_quality_index: float = Field(
        description="0=worst, 100=best (illustrative composite)"
    )


class CCSPathway(BaseModel):
    kind: Literal["ccs"] = "ccs"
    capture_rate: float = Field(ge=0, le=1)
    capture_tech: Literal["amine", "oxy-fuel", "calcium-looping"]
    transport: Literal["pipeline", "ship"]
    storage: Literal["saline_aquifer", "depleted_field"]


class ElectrificationPathway(BaseModel):
    kind: Literal["electrification"] = "electrification"
    technology: str  # key from technologies.json electrification block
    hydrogen_tonnes_yr: float = 0
    hydrogen_source: Literal["grid_electrolysis", "dedicated_renewable"] = "dedicated_renewable"
    electricity_price_gbp_mwh: float | None = None  # override default


class PathwayMetrics(BaseModel):
    cost_per_tco2_avoided: float
    capex_total_gbp: float
    opex_annual_gbp: float
    abatement_percentage: float
    residual_emissions_tco2: float
    air_quality_score: float  # 0..1, higher = better local air
    jobs_net_score: float     # signed, indicative
    infrastructure_readiness: float  # 0..1
    implementation_timeline_years: float
    notes: list[str] = []


class ComparisonResult(BaseModel):
    site_id: str
    ccs: PathwayMetrics
    electrification: PathwayMetrics
    decision_score_ccs: float
    decision_score_electrification: float
    recommended: Literal["ccs", "electrification", "tie"]
    narrative: str
    caveats: list[str]
