# Verdant model card

## System overview

| Item | Detail |
| --- | --- |
| Name | Verdant advisory engine (rules v1) |
| Type | Deterministic, retrieval-grounded rule system with human approval. No machine-learned model and no LLM in the decision path. |
| Inputs | One garden's cached forecast (Open-Meteo), growing spaces, plantings and stages, seed varieties, crop reference table, pending tasks |
| Outputs | Recommendations: category, severity (`info`/`watch`/`action`), suitability (`suitable`/`needs_adjustment`/`unsuitable`/`insufficient_data`), explanation, evidence, unknowns, limitations, expiry, optional suggested task |
| Intended use | Prompt a home gardener to *check* something (cold protection, soil moisture, missing light data). The gardener decides. |
| Not intended for | Disease diagnosis, exact watering amounts, commercial crop decisions, automatic irrigation, or deciding sowing dates from a hardiness zone |

## Evaluation

`python scripts/evaluate_recommendations.py` → **12/12 scenarios** matched the expected advice and **12/12** passed all guardrails (same output on a rerun; no task created, moved or completed; evidence present unless reporting insufficient data; unknowns stated). Results: [docs/evaluation_results.txt](docs/evaluation_results.txt).

| Test input | Evaluation criteria | Result |
| --- | --- | --- |
| Outdoor basil (tender), forecast low 31 °F | Frost *action*, needs adjustment, high-priority suggested task | Pass |
| Covered tomato, low 35 °F | Frost *watch*; limitation notes the cover | Pass |
| Low exactly 36 °F / 37 °F | Watch at the threshold; nothing above it | Pass / Pass |
| Indoor basil, low 25 °F | No frost advice (not exposed) | Pass |
| Kale (frost-tolerant), low 30 °F | No frost advice | Pass |
| Rosemary (sensitivity unknown), low 30 °F | `insufficient_data`, no suggested task | Pass |
| Pepper still *planned*, low 28 °F | No advice (nothing in the ground) | Pass |
| 80 % rain, outdoor bean bed with a watering task | Check-soil advice; watering task untouched | Pass |
| 80 % rain, greenhouse | No rain advice | Pass |
| Grow light with hours but no PPFD | `insufficient_data` | Pass |
| Weather provider outage | Weather advice paused; says so | Pass |

The 80 pytest tests (29 original, 51 new) also pass. A manual run against the live Open-Meteo forecast for a Richmond, VA test location on 2026-11-16 (low 35 °F) produced a frost *watch* only for outdoor basil.

## Limitations and biases

- **Thresholds are not validated.** Frost watch ≤ 36 °F and action ≤ 32 °F, rain ≥ 60 % or ≥ 0.25 in are conservative defaults chosen because forecast air temperature (≈2 m) is not plant-level temperature. They may over-warn in mild microclimates and under-warn in frost pockets.
- **Crop reference is coarse and unverified.** Frost sensitivity is one of three classes per crop, not per cultivar, drafted with AI help and flagged `needs_review` until checked against the cited Virginia Cooperative Extension guide. Perennial herbs and mixes are deliberately `unknown`.
- **Regional bias.** The reference and the defaults reflect U.S., temperate, extension-service conventions (°F, USDA framing). Gardeners in other climates may get less relevant advice.
- **Area forecasts.** Open-Meteo gives gridded estimates; coordinates are rounded to about 1 km for privacy, which slightly reduces precision.
- **Seed list from photos.** Names were transcribed from packet photos; 8 of 26 are flagged *needs review*, and brands, counts and growing facts were intentionally left blank.
- **Not built yet:** sign-in and row-level security (one local operator only), *Can I plant now?*, USDA zone lookup.

## Misuse and safeguards

| Risk | Safeguard |
| --- | --- |
| Treating advice as a guarantee | Every item lists unknowns and limitations; frost dates and forecasts are called estimates |
| App silently changing someone's care plan | Advice never edits tasks; accepting creates one task (idempotency key); dismissals are remembered |
| Acting on invented or outdated weather | Missing location / outage → "Weather unavailable"; stale cache is shown with its timestamp but not used for advice |
| Seeing another person's garden | Every service call checks membership; non-members get the same error as for a non-existent garden; tested |
| Exposing a home location | City-level search, coordinates rounded to ~1 km and not displayed |
| Unsafe uploads | Photos checked by content signature (PNG/JPEG/WebP), max 5 MB, stored per garden, shown only in that garden |

## What surprised me while testing

Facts from the build (edit into your own words): the automated Streamlit tests all passed while the real app had a navigation bug. `st.tabs` reset to the first tab after every button press, so actions in Settings appeared to do nothing. Clicking through the live app also exposed a hot-reload class-identity error and a CSS rule that replaced icons with text such as "arrow_right".

> TODO (student): add your own observations here.

## AI collaboration (student to complete)

> This section is graded as **your** reflection, so it is left for you to write. Describe how you used AI (Claude Code) on this project, one suggestion you accepted, and one you rejected or changed, and why.
>
> Candidates you may want to evaluate, if they match your experience:
> - Accepted: running garden tasks through the unmodified PawPal scheduler via an adapter instead of renaming classes.
> - Changed: the AI-drafted crop frost table. It is kept but marked `needs_review`, so you still need to check it against VCE 426-331.
> - Scoped down: Supabase/RLS was deferred to Phase 3 in favour of SQLite plus service-layer access checks.
>
> TODO (student): replace this block with your own account.
