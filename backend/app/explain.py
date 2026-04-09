"""Auto-generated narratives, caveats, and step-by-step calculation traces.

The trace functions return LaTeX-friendly strings so the frontend can
render them with KaTeX. Every line cites the assumption it pulled from
data/assumptions.json — this is the academic-traceability layer.
"""
from __future__ import annotations

from .data_loader import assumptions
from .models import CCSPathway, ElectrificationPathway, PathwayMetrics, Site

CAVEATS = [
    "This tool does not capture political feasibility or permitting risk.",
    "Social acceptance is proxied only by jobs impact — workshops are needed for richer signal.",
    "Supply-chain and critical-mineral risks for renewables/electrolysers are not modelled.",
    "Cost figures are illustrative central estimates from IEA/IEAGHG/IRENA — replace with site-specific data before any real decision.",
]


def narrative(site: Site, ccs: PathwayMetrics, elec: PathwayMetrics, recommended: str) -> str:
    cost_diff = ccs.cost_per_tco2_avoided - elec.cost_per_tco2_avoided
    cheaper = "CCS" if cost_diff < 0 else "Electrification"
    return (
        f"For {site.name}, {cheaper} is approximately £{abs(cost_diff):.0f}/tCO₂ cheaper "
        f"over a 25-year horizon. CCS leaves {ccs.residual_emissions_tco2:,.0f} tCO₂/yr of "
        f"residual emissions and only marginally improves local air quality, while electrification "
        f"abates {elec.abatement_percentage:.0f}% of emissions and eliminates stack combustion. "
        f"On a weighted multi-criteria score the recommended pathway is **{recommended}**, but "
        f"this depends strongly on the weights set in data/assumptions.json — re-run with workshop "
        f"participant priorities for a more legitimate answer."
    )


# ---------- LaTeX-friendly calculation traces -------------------------------

def explain_ccs(site: Site, p: CCSPathway) -> list[dict]:
    a = assumptions()
    capex_per_t = a["ccs_capex_per_tco2_capacity"][site.sector]["central"]
    src_capex = a["ccs_capex_per_tco2_capacity"][site.sector]["source"]
    energy_pen = a["energy_penalty_by_capture_tech"][p.capture_tech]
    captured = site.annual_co2_tonnes * p.capture_rate

    return [
        {
            "step": "CO₂ captured per year",
            "latex": rf"\dot{{m}}_{{captured}} = E_{{site}} \cdot \eta = {site.annual_co2_tonnes:,.0f} \times {p.capture_rate} = {captured:,.0f}\ \text{{tCO}}_2/\text{{yr}}",
            "source": "Definition",
        },
        {
            "step": "CAPEX (sector benchmark)",
            "latex": rf"\text{{CAPEX}} = c_{{capex}} \cdot \dot{{m}}_{{captured}} = {capex_per_t}\ \text{{£/(tCO}}_2/\text{{yr)}} \times {captured:,.0f} = £{capex_per_t * captured:,.0f}",
            "source": src_capex,
        },
        {
            "step": "Energy penalty",
            "latex": rf"\Delta E = {energy_pen['value']:.0%}\ \text{{of thermal input}}",
            "source": energy_pen["source"],
        },
        {
            "step": "OPEX",
            "latex": r"\text{OPEX} = f_{opex} \cdot \text{CAPEX} + c_{transport} \cdot \dot{m} + c_{storage} \cdot \dot{m} + \text{fuel penalty}",
            "source": "Composite — see assumptions.json",
        },
        {
            "step": "Levelised cost / tCO₂ avoided",
            "latex": r"\text{LCOA} = \frac{\text{CAPEX} + \mathrm{NPV}(\text{OPEX}, T, r)}{\mathrm{NPV}(\dot{m}_{captured}, T, r)}",
            "source": "Standard DCF — IEA WEO methodology",
        },
    ]


def explain_electrification(site: Site, p: ElectrificationPathway) -> list[dict]:
    a = assumptions()
    elec_price = p.electricity_price_gbp_mwh or a["default_grid_electricity_price_gbp_per_mwh"]["value"]
    eta = a["electrolyser_efficiency"]
    return [
        {
            "step": "Replaced thermal demand",
            "latex": rf"Q_{{repl}} = Q_{{site}} \cdot f_{{tech}} = {site.thermal_demand_gwh:,.0f}\ \text{{GWh}} \cdot f_{{tech}}",
            "source": "technologies.json → thermal_replacement_fraction",
        },
        {
            "step": "Annual electricity cost",
            "latex": rf"C_{{elec}} = Q_{{repl}} \cdot 1000 \cdot p_{{elec}} = Q \times £{elec_price}/\text{{MWh}}",
            "source": "Direct accounting",
        },
        {
            "step": "Green H₂ electricity demand",
            "latex": rf"E_{{H_2}} = \frac{{m_{{H_2}} \cdot LHV_{{H_2}}}}{{\eta_{{electrolyser}}}},\quad \eta = {eta['value']}",
            "source": eta["source"],
        },
        {
            "step": "Net CO₂ abated",
            "latex": r"\dot{m}_{abated} = E_{site} \cdot f_{tech} - E_{elec} \cdot CI_{grid}",
            "source": "Mass balance",
        },
        {
            "step": "Levelised cost / tCO₂ avoided",
            "latex": r"\text{LCOA} = \frac{\text{CAPEX} + \mathrm{NPV}(\text{OPEX}, T, r)}{\mathrm{NPV}(\dot{m}_{abated}, T, r)}",
            "source": "Standard DCF",
        },
    ]
