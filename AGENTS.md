# Repository Guidelines

## Project Structure & Module Organization
- ai/: AI analysis core (e.g., `raw_data_analyzer.py`, `analysis_engine.py`).
- data/: Market data access (e.g., `binance_fetcher.py`).
- prompts/: Prompt files organized by domain (`price_action/`, `volume_analysis/`, `ict_concepts/`).
- config/: Runtime settings (`settings.py`, loads `.env`).
- formatters/: Output/data formatting helpers.
- main.py: Typer + Rich CLI entrypoint.
- .env.example → copy to `.env` and fill secrets; never commit `.env`.

## Build, Test, and Development Commands
- Create venv: `python -m venv venv && source venv/bin/activate`
- Install deps: `pip install -r requirements.txt`
- Validate config: `python -c "from config import Settings; Settings.validate()"` or `python main.py config`
- Quick run: `python main.py analyze --method al-brooks --symbol ETHUSDT -v`
- List methods: `python main.py methods`
- Multi‑TF: `python main.py multi-analyze --method al-brooks --timeframes '1h,4h,1d'`
- Realtime: `python main.py realtime --method al-brooks --timeframes '15m,1h,4h'`

## Coding Style & Naming Conventions
- Python 3.8+, PEP 8, 4‑space indent; prefer type hints and concise docstrings.
- snake_case for modules/functions/variables; CamelCase for classes; UPPER_SNAKE for constants.
- CLI flags use kebab-case (e.g., `--analysis-type`); prompt filenames use snake_case (e.g., `al_brooks_analysis.txt`).
- Keep domain logic in `ai/`, integration in `data/`, configuration in `config/`.

## Testing Guidelines
- No formal test suite yet. Use CLI integration checks:
  - `python main.py analyze --method al-brooks --verbose`
  - `python main.py methods` and `python main.py config`
- If adding tests, prefer `pytest`, place under `tests/` as `test_*.py`, and keep fixtures small/deterministic.

## Commit & Pull Request Guidelines
- Conventional Commits style: `feat:`, `fix:`, `docs:`, `refactor:`, optional scopes (e.g., `feat(ws): ...`). Bilingual messages accepted.
- PRs include: clear description, linked issues, reproduction and test steps, sample CLI output (or screenshots), and notes on config changes.

## Security & Configuration Tips
- Required: `OPENROUTER_API_KEY` in `.env`. Optional: Binance keys for authenticated data.
- Never log or commit secrets. Use `.env.example` as the template.
- Logs live in `logs/`; scrub sensitive data before sharing.

## Agent-Specific Instructions (Prompts & Methods)
- Add prompts under `prompts/<category>/<method>.txt`.
- Map new methods in `prompts/prompt_manager.py:get_method_info` with `{category, method, display_name}`.
- Current verification phase enables only Al Brooks; enable others by extending the mapping when validated.
