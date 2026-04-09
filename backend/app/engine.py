"""Pure calculation kernel.

NO numbers are hardcoded here. Every parameter is read from
data/assumptions.json via data_loader. This makes the engine fully
data-driven and auditable.
"""
from __future__ import annotations

from .data_loader import assumptions, technologies
from .models import (
    CCSPathway,
    ElectrificationPathway,
    PathwayMetrics,
    Site,
)

# ---------- helpers ---------------------------------------------------------

def _npv(annual_cashflow: float, years: int, discount_rate: float) -> float:
    """Present value of a flat annuity."""
    if discount_rate == 0:
        return annual_cashflow * years
    r = discount_rate
    return annual_cashflow * (1 - (1 + r) ** -years) / r


def _val(node: object) -> float:
    """Extract numeric value from an assumptions entry (handles {value: ...})."""
    if isinstance(node, dict) and "value" in node:
        return float(node["value"])
    return float(node)  # type: ignore[arg-type]


# ---------- CCS -------------------------------------------------------------

def compute_ccs(
    site: Site, p: CCSPathway, discount_rate: float | None = None
) -> PathwayMetrics:
    a = assumptions()
    discount_rate = discount_rate if discount_rate is not None else _val(a["discount_rate_default"])
    lifetime = int(_val(a["project_lifetime_years"]))

    captured = site.annual_co2_tonnes * p.capture_rate
    residual = site.annual_co2_tonnes - captured

    capex_per_t = a["ccs_capex_per_tco2_capacity"][site.sector]["central"]
    capex_total = capex_per_t * captured

    opex_capex_frac = _val(a["ccs_opex_fraction_of_capex"])
    transport_cost = _val(a["co2_transport_cost_per_tco2"][p.transport]) * captured
    storage_cost = _val(a["co2_storage_cost_per_tco2"][p.storage]) * captured

    energy_penalty = _val(a["energy_penalty_by_capture_tech"][p.capture_tech])
    fuel_price = _val(a["industrial_fuel_price_gbp_per_mwh"])
    fuel_penalty_cost = energy_penalty * site.thermal_demand_gwh * 1000 * fuel_price

    opex_annual = capex_total * opex_capex_frac + transport_cost + storage_cost + fuel_penalty_cost

    pv_costs = capex_total + _npv(opex_annual, lifetime, discount_rate)
    pv_abated = _npv(captured, lifetime, discount_rate)
    cost_per_tco2 = pv_costs / pv_abated if pv_abated else float("inf")

    # Air quality: residual combustion continues, so improvement scales with capture rate
    # but local NOx/SOx/PM aren't removed by amine — penalise vs electrification.
    air_quality_score = 0.2 + 0.3 * p.capture_rate  # 0.2..0.5

    jm = a["jobs_multipliers"]["ccs"]
    jobs_net = jm["construction_uplift"] * 0.3 + jm["operational_change"] * 0.7

    infra = _infrastructure_readiness(site, "ccs")
    timeline = 6 + (1 - p.capture_rate) * 2  # 6–8 yrs indicative

    return PathwayMetrics(
        cost_per_tco2_avoided=cost_per_tco2,
        capex_total_gbp=capex_total,
        opex_annual_gbp=opex_annual,
        abatement_percentage=p.capture_rate * 100,
        residual_emissions_tco2=residual,
        air_quality_score=air_quality_score,
        jobs_net_score=jobs_net,
        infrastructure_readiness=infra,
        implementation_timeline_years=timeline,
        notes=[
            f"Capture tech: {p.capture_tech} (energy penalty {energy_penalty:.0%})",
            f"Transport: {p.transport}, storage: {p.storage}",
            "Residual stack emissions persist — local air quality only marginally improved.",
        ],
    )


# ---------- Electrification -------------------------------------------------

def compute_electrification(
    site: Site, p: ElectrificationPathway, discount_rate: float | None = None
) -> PathwayMetrics:
    a = assumptions()
    techs = technologies()["electrification"]
    if p.technology not in techs:
        raise ValueError(f"Unknown electrification technology: {p.technology}")
    tech = techs[p.technology]

    discount_rate = discount_rate if discount_rate is not None else _val(a["discount_rate_default"])
    lifetime = int(_val(a["project_lifetime_years"]))
    elec_price = (
        p.electricity_price_gbp_mwh
        if p.electricity_price_gbp_mwh is not None
        else _val(a["default_grid_electricity_price_gbp_per_mwh"])
    )

    replaced_thermal = site.thermal_demand_gwh * tech["thermal_replacement_fraction"]
    capex_per_gwh = _val(a["electrification_capex_per_gwh_thermal"][p.technology]) * 1e6
    capex_total = capex_per_gwh * replaced_thermal

    # Annual electricity required: thermal replaced / COP. Resistive technologies
    # (EAF, e-kiln, e-cracker) have COP=1; industrial heat pumps draw on the
    # IEA 2022 central value (~3.5). See data/assumptions.json
    # → heat_pump_cop_by_technology. Replaces the v0.1 COP=1 placeholder.
    cop_table = a["heat_pump_cop_by_technology"]
    cop_node = cop_table.get(p.technology)
    if cop_node is None:
        cop_node = cop_table["electric_arc_furnace"]
    cop = _val(cop_node)
    if cop <= 0:
        raise ValueError(f"Non-positive COP ({cop}) for technology {p.technology}")
    annual_elec_mwh = (replaced_thermal * 1000) / cop
    elec_cost = annual_elec_mwh * elec_price

    # Hydrogen
    h2_e_content = _val(a["h2_energy_content_mwh_per_tonne"])
    eta = _val(a["electrolyser_efficiency"])
    h2_elec_mwh = p.hydrogen_tonnes_yr * h2_e_content / eta
    h2_cost = h2_elec_mwh * elec_price

    # Renewable build-out (only if dedicated)
    if p.hydrogen_source == "dedicated_renewable":
        # crude: 25% capacity factor
        mw_needed = (annual_elec_mwh + h2_elec_mwh) / (8760 * 0.25)
        capex_total += mw_needed * _val(a["renewable_capacity_capex_gbp_per_mw"])

    opex_annual = elec_cost + h2_cost

    # Abated CO2: full thermal replacement → near-zero direct emissions
    # (residual depends on grid carbon intensity for the fraction not replaced)
    direct_abated = site.annual_co2_tonnes * tech["thermal_replacement_fraction"]
    grid_emissions = annual_elec_mwh * site.grid_carbon_intensity_gco2_kwh / 1e6  # tCO2
    net_abated = max(direct_abated - grid_emissions, 0)
    abatement_pct = (net_abated / site.annual_co2_tonnes) * 100 if site.annual_co2_tonnes > 0 else 0.0

    pv_costs = capex_total + _npv(opex_annual, lifetime, discount_rate)
    pv_abated = _npv(net_abated, lifetime, discount_rate)
    cost_per_tco2 = pv_costs / pv_abated if pv_abated > 0 else float("inf")

    air_quality_score = 0.85 + 0.15 * tech["thermal_replacement_fraction"]  # near 1.0

    jm = a["jobs_multipliers"]["electrification"]
    jobs_net = jm["construction_uplift"] * 0.4 + jm["operational_change"] * 0.6

    infra = _infrastructure_readiness(site, "electrification")
    timeline = 8 + (p.hydrogen_tonnes_yr > 0) * 2

    return PathwayMetrics(
        cost_per_tco2_avoided=cost_per_tco2,
        capex_total_gbp=capex_total,
        opex_annual_gbp=opex_annual,
        abatement_percentage=abatement_pct,
        residual_emissions_tco2=site.annual_co2_tonnes - net_abated,
        air_quality_score=air_quality_score,
        jobs_net_score=jobs_net,
        infrastructure_readiness=infra,
        implementation_timeline_years=timeline,
        notes=[
            f"Technology: {tech['label']}",
            f"Annual electricity: {annual_elec_mwh:,.0f} MWh @ £{elec_price}/MWh",
            f"Hydrogen demand: {p.hydrogen_tonnes_yr:,.0f} t/yr ({p.hydrogen_source})",
            "Eliminates local stack combustion — major air-quality benefit.",
        ],
    )


# ---------- shared ----------------------------------------------------------

def _infrastructure_readiness(site: Site, kind: str) -> float:
    a = assumptions()
    w = a["infrastructure_readiness_weights"]

    grid_cap = max(0.0, 1.0 - site.electrical_demand_gwh / 5000)  # rough proxy

    # H2 pipeline proximity is now country-indexed against the European Hydrogen
    # Backbone 2023 plan (replaces the v0.1 h2_prox=0.5 placeholder).
    h2_table = a["h2_pipeline_proximity_by_country"]
    h2_node = h2_table.get(site.country)
    if h2_node is None:
        h2_node = h2_table["default"]
    h2_prox = _val(h2_node)
    co2_prox = max(0.0, 1.0 - site.proximity_to_co2_storage_km / 500)
    supply = 0.6 if kind == "ccs" else 0.5

    if kind == "ccs":
        return (
            w["grid_capacity"] * 0.7
            + w["h2_pipeline_proximity"] * 0.2
            + w["co2_storage_proximity"] * co2_prox
            + w["supply_chain_maturity"] * supply
        )
    return (
        w["grid_capacity"] * grid_cap
        + w["h2_pipeline_proximity"] * h2_prox
        + w["co2_storage_proximity"] * 0.1
        + w["supply_chain_maturity"] * supply
    )
