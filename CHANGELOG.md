# Changelog

All notable changes to **laidlaw** are documented here. The project follows
[Semantic Versioning](https://semver.org/) and the format is loosely based on
[Keep a Changelog](https://keepachangelog.com/).

> **Note on pre-0.4 versions:** the project did not adopt semver tagging until
> `v0.4.0`. The 0.1 → 0.3 sections below are a retroactive reconstruction of
> the work that landed before tagging began, grouped by feature area for
> readability. Only `v0.4.0` and later correspond to actual git tags.

## [0.4.0] — Engineering pass

### Added
- `pyproject.toml` for the backend with proper dev extras (`ruff`, `mypy`,
  `pytest-cov`, `httpx`).
- `tests/test_engine_edges.py` — 10 new edge-case tests covering discount-rate
  corners, both hydrogen sources, COP-aware electricity demand, country-indexed
  H₂ pipeline proximity, and Pydantic validation of capture-rate bounds.
- Multi-stage `Dockerfile` (builder runs the test suite, runtime is non-root,
  ships a `/health` HEALTHCHECK).
- Expanded GitHub Actions CI: ruff + mypy + pytest matrix on Python 3.11/3.12,
  coverage upload, Docker build job, every action pinned to a full SHA.

### Changed
- `engine.py`: replaced the `COP=1` placeholder with a per-technology COP
  table sourced from IEA *The Future of Heat Pumps* (2022).
- `engine.py`: replaced the `h2_prox=0.5` placeholder with a country-indexed
  table calibrated against the European Hydrogen Backbone (EHB) 2023 plan.
- `engine.py`: switched `Optional[float]` annotations to PEP 604 `float | None`.
- `data/assumptions.json`: added `heat_pump_cop_by_technology` and
  `h2_pipeline_proximity_by_country` blocks (every entry carries a citation).

### Fixed
- Mypy type-arg coverage in `engine.py`.

## [0.3.0] — Decision algorithm

### Added
- `decision.py` multi-criteria scoring (cost, abatement, air quality, jobs,
  infrastructure readiness, implementation speed) with weights in
  `assumptions.json`.
- `explain.py` natural-language narrative generator + caveat list.
- `cards.py` printable site-card HTML for workshop sessions.

## [0.2.0] — REST API

### Added
- FastAPI backend (`main.py`) with `/sites`, `/compare/{site_id}`,
  `/explain/{site_id}`, `/workshop/*` routes.
- `tests/test_api.py` — TestClient coverage for every endpoint.
- `Dockerfile` and `docker-compose.yml` for one-command spin-up with
  workshop-mode volume mounts.
- Static HTML frontend (`index.html`, `workshop.html`).

## [0.1.0] — MVP engine

### Added
- Initial pure-Python calculation kernel (`engine.py`) with NPV, CCS pathway,
  and electrification pathway models.
- Pydantic domain models (`models.py`).
- JSON-driven assumptions and technology databases under `data/`.
- First unit tests for engine invariants.
