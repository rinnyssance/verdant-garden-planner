# Verdant migration plan (Phase 0 audit)

Date: 2026-11-16. Branch: `verdant` (the original `main` branch is the untouched AI110 Module 2 submission).

## Audit of the starting point

| Item | Finding |
| --- | --- |
| `pawpal_system.py` | `Task`, `Pet`, `Owner`, `Plan`, `Scheduler`. Pure Python, no UI imports. Tasks validate themselves; completion returns the next daily/weekly occurrence; `Scheduler` filters, sorts, detects overlaps across *every* pet of one owner and builds a greedy priority plan. |
| `app.py` | Streamlit PawPal UI. State lives only in `st.session_state` and is lost on refresh. |
| `main.py` | CLI demo with a fixed date. |
| `tests/` | 26 engine tests + 3 Streamlit `AppTest` tests. |
| Baseline run | `python -m pytest -q` → **29 passed** (Python 3.10.11, Streamlit 1.65.0, pytest 9.1.1) before any change. |

## Decisions

1. **Nothing in `pawpal_system.py`, `app.py`, `main.py` or the original tests is edited.** Verdant is a new `verdant/` package plus a new entry point, `verdant_app.py`.
2. **Adapter, not rename.** `verdant/scheduling/pawpal_adapter.py` converts `GardenTask` records into PawPal `Task` objects grouped under one PawPal `Owner` per garden (one `Pet`-shaped group per planting / growing space / general care). All validation, recurrence, overlap and plan rules therefore come from the original tested code.
3. **Garden scope.** The adapter is built from one garden's tasks only, so overlap warnings and plans can never mix gardens (PawPal assumed one owner's time; a garden now plays that role).
4. **Durable storage.** A `Repository` interface with a SQLite implementation (`data/verdant.db`, git-ignored) and a versioned SQL migration. Supabase/RLS is Phase 3; the SQLite schema already has `users` and `garden_memberships` so access checks are enforced and tested in the service layer now.
5. **Rules before generative AI.** Recommendations come from deterministic, unit-tested rules that record evidence, unknowns and limitations. They never create, move or complete tasks on their own; the user accepts or dismisses each one.
6. **External data is optional.** Open-Meteo is called through a `WeatherProvider` interface with a cache and timestamps. Any failure shows "Weather unavailable"; no conditions are invented.

## File-level plan

```
verdant/
  domain/        gardens.py, seeds.py, plantings.py, observations.py, recommendations.py, common.py
  scheduling/    pawpal_adapter.py
  persistence/   repository.py, sqlite_repository.py, migrations/001_initial.sql
  services/      access.py, inventory.py, weather.py, recommendation_engine.py, photos.py
  seed_data/     initial_seed_inventory.json, crop_reference.json
verdant_app.py   Streamlit UI (Dashboard, Seed Library, My Plants, Garden Spaces, Calendar, Field Journal, Settings)
tests/           test_garden_domain.py, test_garden_scope.py, test_persistence.py, test_permissions.py,
                 test_seed_import.py, test_weather.py, test_recommendations.py, test_verdant_app.py
scripts/         evaluate_recommendations.py (scenario harness)
```
