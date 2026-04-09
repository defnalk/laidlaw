# Laidlaw — Industrial Decarbonisation Pathway Comparator (IDPC)

Decision-support tool for the Laidlaw research project
**"Carbon Capture vs. Electrification: Which Wins for Industry?"**

Compares CCS retrofits vs. full electrification for hard-to-abate sectors
(steel, cement, chemicals) on cost, abatement, jobs, air quality,
infrastructure readiness, and timeline. Designed for participatory workshops
under the *Industrial Transitions, Human Stories* Leadership in Action project.

## Why this architecture

Everything that could be a "fact about the world" lives in `data/` as JSON.
The Python code in `backend/app/engine.py` is a **pure calculation kernel** —
it does not hardcode cost numbers, energy penalties, or sector parameters.
This means:

- You can add a new sector, technology, or assumption **without writing code**.
- Every number in the output is traceable to a cited entry in `data/assumptions.json`.
- A future "decision algorithm" (e.g. multi-criteria scoring, ML ranking) plugs
  in cleanly above the engine — see `backend/app/decision.py`.

## Layout

```
laidlaw/
├── data/                       # ← edit these to add knowledge, no code changes
│   ├── assumptions.json        # every parameter + IEA/IPCC/IEAGHG citation
│   ├── technologies.json       # CCS + electrification tech catalogue
│   ├── sites.json              # seed industrial sites
│   └── sdg_mapping.json        # metric → SDG tags
├── backend/
│   ├── app/
│   │   ├── main.py             # FastAPI app + endpoints
│   │   ├── models.py           # Pydantic domain types
│   │   ├── data_loader.py      # loads + validates data/ at startup
│   │   ├── engine.py           # pure calculation kernel (DCF, abatement, etc.)
│   │   ├── decision.py         # weighted multi-criteria decision algorithm
│   │   └── explain.py          # step-by-step calculation trace (LaTeX-friendly)
│   └── tests/
│       └── test_engine.py      # pytest: edge cases + invariants
└── frontend/                   # (Phase 2 — Next.js, not yet scaffolded)
```

## URLs

| Route | Purpose |
|-------|---------|
| `/ui/`              | Main analyst dashboard (Plotly + KaTeX traces) |
| `/ui/workshop.html` | Workshop mode — projection-friendly live voting |
| `/cards/{site_id}`  | Printable A5 pathway cards (Print → Save as PDF) |
| `/docs`             | FastAPI auto-generated API docs |
| `/explain/{id}`     | Step-by-step LaTeX calculation trace |

## Run

```bash
cd backend
pip install fastapi uvicorn pydantic pytest
uvicorn app.main:app --reload
# → http://localhost:8000/docs
pytest tests/
```

## Adding new knowledge

| You want to…                            | Edit this file              |
|-----------------------------------------|-----------------------------|
| Add a new sector or site                | `data/sites.json`           |
| Add a new capture or electrification tech | `data/technologies.json`  |
| Update an IEA cost benchmark            | `data/assumptions.json`     |
| Change decision-algorithm weights       | `data/assumptions.json` → `decision_weights` |
| Tag a metric to a different SDG         | `data/sdg_mapping.json`     |

The engine reloads `data/` on startup. Restart the server after edits.
For hot-reload during workshops, run with `uvicorn --reload`.

## Decision algorithm

`backend/app/decision.py` implements a weighted multi-criteria score:

```
score(pathway) = Σ wᵢ · normalise(metricᵢ)
```

Weights live in `data/assumptions.json` under `decision_weights` so you (or
workshop participants) can re-weight cost vs. health vs. jobs without
touching code. This is the hook for a richer algorithm later (e.g. AHP,
TOPSIS, or a learned ranker over workshop voting data).

## Caveats (this tool does NOT capture)

- Political feasibility & permitting risk
- Social acceptance beyond a jobs proxy
- Supply-chain and geopolitical risk on critical minerals / hydrogen
- Behavioural change and demand-side measures

Always present results alongside these caveats in workshops.

## License

MIT
