"""Pathway-card HTML generator — fully data-driven from technologies.json.

To add a new card, add a `card` block to any tech in
data/technologies.json. No code changes needed.

Returns a print-friendly A4 grid that exports to PDF via the browser's
Print → Save as PDF (no weasyprint/wkhtmltopdf dependency).
"""
from __future__ import annotations

from .data_loader import technologies
from .models import Site

CARD_CSS = """
@page { size: A4 landscape; margin: 10mm; }
body { font-family: -apple-system, Segoe UI, Inter, sans-serif; margin: 0; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8mm; }
.card { border: 1.5px solid #222; border-radius: 6mm; padding: 6mm 7mm;
        height: 130mm; display: flex; flex-direction: column;
        page-break-inside: avoid; background: #fff; color: #111; }
.card h2 { margin: 3mm 0 0; font-size: 16pt; }
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
       border-radius: 2mm; font-size: 8pt; align-self: flex-start; }
.tag.ELEC { background: #146c3a; }
.tag.CCS { background: #8a1f1f; }
@media print { button { display: none; } }
"""


def _render_card(card: dict) -> str:
    stats = "".join(
        f'<div class="stat"><div class="k">{k}</div><div class="v">{v}</div></div>'
        for k, v in card["stats"]
    )
    pros = "".join(f"<li>{x}</li>" for x in card["pros"])
    cons = "".join(f"<li>{x}</li>" for x in card["cons"])
    tag = card.get("tag", "")
    return f"""
    <div class="card">
      <span class="tag {tag}">{tag}</span>
      <h2>{card["title"]}</h2>
      <div class="stats">{stats}</div>
      <div class="desc">{card["description"]}</div>
      <div class="row">
        <div><b>Pros</b><ul class="pros">{pros}</ul></div>
        <div><b>Cons</b><ul class="cons">{cons}</ul></div>
      </div>
    </div>
    """


def _applicable_cards(site: Site) -> list[dict]:
    """Walk technologies.json and yield cards relevant to this site's sector."""
    techs = technologies()
    out: list[dict] = []

    # All CCS techs are applicable to all sectors (with varying suitability)
    for _key, t in techs["ccs"].items():
        if "card" in t:
            out.append(t["card"])

    # Electrification techs are sector-gated
    for _key, t in techs["electrification"].items():
        if site.sector in t.get("applicable_sectors", []) and "card" in t:
            out.append(t["card"])

    return out


def render_cards(site: Site) -> str:
    site_sub = (
        f"{site.name} · {site.annual_co2_tonnes/1e6:.1f} MtCO₂/yr · "
        f"{site.workforce_size:,} workers · {site.country}"
    )
    cards_html = "".join(_render_card(c) for c in _applicable_cards(site))

    return f"""<!doctype html><html><head><meta charset="utf-8">
    <title>Pathway Cards — {site.name}</title><style>{CARD_CSS}</style></head>
    <body>
      <div style="padding:6mm 8mm;display:flex;justify-content:space-between;align-items:center">
        <div><h1 style="margin:0;font-size:14pt">Pathway Cards · {site.name}</h1>
             <div style="color:#555;font-size:9pt">{site_sub}</div></div>
        <button onclick="window.print()" style="padding:4mm 8mm;font-size:10pt;background:#111;color:#fff;border:0;border-radius:3mm;cursor:pointer">Print → Save as PDF</button>
      </div>
      <div class="grid" style="padding:0 8mm 8mm">{cards_html}</div>
    </body></html>"""
