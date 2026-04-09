"""Pathway-card HTML generator.

Returns a print-friendly A5 grid that can be exported to PDF via the
browser's Print → Save as PDF. Avoids a heavy weasyprint/wkhtmltopdf
dependency for now.
"""
from __future__ import annotations

from .data_loader import assumptions, technologies
from .models import Site

CARD_CSS = """
@page { size: A4 landscape; margin: 10mm; }
body { font-family: -apple-system, Segoe UI, Inter, sans-serif; margin: 0; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8mm; }
.card { border: 1.5px solid #222; border-radius: 6mm; padding: 6mm 7mm;
        height: 130mm; display: flex; flex-direction: column;
        page-break-inside: avoid; background: #fff; color: #111; }
.card h2 { margin: 0; font-size: 16pt; }
.card .sub { color: #555; font-size: 9pt; margin-top: 1mm; }
.stats { display: flex; gap: 4mm; margin: 5mm 0; }
.stat { flex: 1; background: #f3f5f7; border-radius: 3mm; padding: 3mm; }
.stat .k { font-size: 7pt; color: #555; text-transform: uppercase; }
.stat .v { font-size: 13pt; font-weight: 700; }
.desc { font-size: 10pt; line-height: 1.4; }
.pros, .cons { font-size: 9pt; margin: 1mm 0 0; padding-left: 4mm; }
.pros li { color: #146c3a; } .cons li { color: #8a1f1f; }
.row { display: flex; gap: 4mm; margin-top: auto; }
.row > div { flex: 1; }
.tag { display: inline-block; background: #111; color: #fff; padding: 1mm 3mm;
       border-radius: 2mm; font-size: 8pt; }
@media print { button { display: none; } }
"""


def _card(title: str, sub: str, tag: str, stats: list[tuple[str, str]],
          desc: str, pros: list[str], cons: list[str]) -> str:
    s = "".join(f'<div class="stat"><div class="k">{k}</div><div class="v">{v}</div></div>' for k, v in stats)
    p = "".join(f"<li>{x}</li>" for x in pros)
    c = "".join(f"<li>{x}</li>" for x in cons)
    return f"""
    <div class="card">
      <span class="tag">{tag}</span>
      <h2 style="margin-top:3mm">{title}</h2>
      <div class="sub">{sub}</div>
      <div class="stats">{s}</div>
      <div class="desc">{desc}</div>
      <div class="row">
        <div><b>Pros</b><ul class="pros">{p}</ul></div>
        <div><b>Cons</b><ul class="cons">{c}</ul></div>
      </div>
    </div>
    """


def render_cards(site: Site) -> str:
    techs = technologies()
    sector_to_elec = {
        "steel": "electric_arc_furnace",
        "cement": "electric_kiln",
        "chemicals": "e_cracker",
    }
    elec_key = sector_to_elec[site.sector]
    elec = techs["electrification"][elec_key]

    site_sub = f"{site.name} · {site.annual_co2_tonnes/1e6:.1f} MtCO₂/yr · {site.workforce_size:,} workers"

    cards_html = ""
    cards_html += _card(
        "Retrofit with Carbon Capture (Amine)",
        site_sub, "CCS",
        [("Capture", "90%"), ("Cost £/tCO₂", "£80–120"), ("Build time", "6–8 yr")],
        "Bolt a post-combustion capture plant onto the existing site. Keep current jobs and assets; ship CO₂ to offshore storage.",
        ["Preserves existing jobs & assets", "Mature technology (TRL 9)", "Fast vs. full rebuild"],
        ["10% residual stack emissions", "No local air-quality benefit", "Long-term CO₂ storage liability"],
    )
    cards_html += _card(
        "Retrofit with Oxy-fuel Capture",
        site_sub, "CCS",
        [("Capture", "95%"), ("Energy penalty", "~18%"), ("TRL", "7")],
        "Burn fuel in pure oxygen to produce a near-pure CO₂ stream that's cheap to capture. Lower penalty than amines.",
        ["Higher capture rate", "Lower energy penalty", "Compatible with cement"],
        ["Less mature than amine", "Requires air-separation unit", "Still combustion-based"],
    )
    cards_html += _card(
        f"Switch to {elec['label']}",
        site_sub, "ELEC",
        [("Abatement", "~95%+"), ("Air quality", "Major ↑"), ("Build time", "8–10 yr")],
        "Replace the fossil-fired core process with electric heat (and green H₂ where needed). Eliminates stack combustion.",
        ["Eliminates local air pollution", "Aligns with zero-carbon grid", "Future-proof"],
        ["Huge new grid / renewables build-out", "Higher upfront CAPEX", "Workforce reskilling needed"],
    )
    cards_html += _card(
        "Green Hydrogen + Electrification",
        site_sub, "ELEC+H₂",
        [("H₂ source", "Renewable"), ("Electrolyser η", "70%"), ("Land", "High")],
        "Use renewable electricity to produce green hydrogen for high-temperature processes (e.g. DRI for steel) plus direct electrification elsewhere.",
        ["Replaces coke in steelmaking", "Zero direct CO₂", "Creates new H₂ economy jobs"],
        ["Needs hydrogen pipeline / storage", "Highest cost today", "Renewable land footprint"],
    )

    return f"""<!doctype html><html><head><meta charset="utf-8">
    <title>Pathway Cards — {site.name}</title><style>{CARD_CSS}</style></head>
    <body>
      <div style="padding:6mm 8mm">
        <button onclick="window.print()" style="padding:6mm 10mm;font-size:11pt;background:#111;color:#fff;border:0;border-radius:3mm;cursor:pointer">Print → Save as PDF</button>
      </div>
      <div class="grid" style="padding:0 8mm 8mm">{cards_html}</div>
    </body></html>"""
