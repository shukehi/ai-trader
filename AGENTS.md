# Repository Guidelines

## Project Structure & Module Organization
- `main.py`: CLI entry point for analyses and demo trading.
- `ai/`: LLM orchestration (validation, prompts, realtime monitors).
- `data/`: Exchange clients and data processing (`binance_fetcher.py`, `binance_websocket.py`).
- `formatters/`: Data formatting for LLM prompts (standard and executive).
- `trading/`: Signal execution, risk/position management, simulators.
- `config/`: Runtime settings (`settings.py`, `trading_config.py`).
- `tests/` and root `test_*.py`: Integration-style test scripts.
- `scripts/`: Ops helpers (health checks, fixes) and `manage.sh` for services.
- `docs/`, `examples/`, `data/samples/`: Reference materials and demos.

## Build, Test, and Development Commands
- Setup env: `python -m venv venv && source venv/bin/activate`
- Install deps (core/all): `pip install -r requirements-core.txt` or `pip install -r requirements.txt`
- Run analysis: `python main.py --symbol ETHUSDT --timeframe 1h --limit 50 --model gpt4o-mini`
- REST VPA test: `python test_rest_vpa.py`
- WebSocket VPA test (5 min): `python test_websocket_vpa.py 5`
- Service ops (on servers): `./manage.sh {start|stop|restart|status|logs|health|update}`

## Coding Style & Naming Conventions
- Python, PEP 8, 4‑space indent; add type hints where practical.
- Files/modules: `snake_case.py`; classes: `PascalCase`; functions/vars: `snake_case`.
- Keep modules cohesive: data in `data/`, LLM logic in `ai/`, trading logic in `trading/`.
- Optional tools: if available, run `ruff check .` and `black .` before PRs.

## Testing Guidelines
- Tests are executable scripts; prefer focused runs during development:
  - `python tests/test_multi_model_validation.py`
  - `python tests/test_vpa_enhancement.py`
- Many tests hit live APIs; ensure `.env` is configured and expect network/latency.
- Naming: `test_*.py`; place new integration tests under `tests/`.

## Commit & Pull Request Guidelines
- Use Conventional Commits: `feat:`, `fix:`, `docs:`, etc. (see `git log`).
- PRs include: clear description, scope, rationale, and any linked issues.
- Verify locally: run key scripts/tests above and include brief output snippets if relevant.
- Keep changes scoped; avoid unrelated refactors in the same PR.

## Security & Configuration Tips
- Copy `.env.example` → `.env` and set `OPENROUTER_API_KEY` (required). Optional: `BINANCE_API_KEY`, `BINANCE_SECRET_KEY`.
- Do not commit secrets or real keys. Add new config to `config/settings.py` and document defaults.
- For long‑running/production use, prefer `./manage.sh` and monitor logs.

