# Repository Guidelines

## Project Structure & Module Organization
- `main.py` is the desktop entry point; it wires cache setup, database checks, and launches `StartupWindow`.
- `src/core/` handles infrastructure such as `window_manager.py`, cache configuration, database access, and language/theme managers.
- `src/windows/` groups CustomTkinter views and dialogs; match new UI flows with the existing `*_window.py` naming.
- `src/components/` hosts reusable map and panel widgets; prefer extending these before creating bespoke widgets.
- `src/utils/` contains project helpers (cache, project data, SbN prioritization) and command-line scripts; `src/locales/` stores translation CSV/JSON assets.
- `reports/` and `Dummy/` house sample outputs and fixtures—keep generated artefacts out of source folders.

## Build, Test, and Development Commands
- Create a virtual environment: `python -m venv .venv` then activate (`source .venv/bin/activate` or `.venv\Scripts\activate`).
- Install dependencies: `pip install -r requirements.txt`.
- Run the app locally from the repo root: `python main.py`.
- Clear stale map tiles if troubleshooting cache issues: `python -m src.utils.clear_map_cache`.
- Preload map tiles for offline demos: `python -m src.utils.precache` (optional but shortens first-load delays).

## Coding Style & Naming Conventions
- Follow PEP 8 with 4-space indentation; keep imports grouped by stdlib, third-party, then internal (`src.`).
- Classes use `CamelCase`, modules/functions/variables use `snake_case`; mirror existing `*_window.py` and `*_manager.py` patterns.
- Prefer f-strings for interpolation and keep user-facing strings routed through the locale managers.
- Run `python -m compileall src` before submitting large refactors to catch syntax errors.

## Testing Guidelines
- No automated test suite is present; verify changes manually by launching `python main.py` and walking through affected windows.
- When editing data tools, rerun representative CSV workflows stored in `Dummy/` and confirm generated content under `reports/`.
- Document manual test steps in the pull request when touching critical flows (database setup, cache handling, map rendering).

## Commit & Pull Request Guidelines
- Existing history favors version-tag commits (`v.0.x`); keep using concise, present-tense messages, adding a scope prefix when practical (e.g., `ui: adjust startup layout`).
- Isolate logical changes per commit and update requirements or locale assets in the same commit when they must stay in sync.
- Pull requests should outline the problem, the solution, manual verification steps, and link any tracking tickets; include before/after screenshots for UI updates.

## Configuration & Assets Notes
- Map caching defaults to the path configured in `src/core/map_cache_config.py`; confirm disk quotas on shared machines.
- Locale CSV/JSON files back the multilingual UI—keep headers intact and align keys across languages when editing.
