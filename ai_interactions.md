# AI Interactions Log

## Agent Workflow (SF7)

### Task given to the agent

The user supplied `https://github.com/codepath/ai110-module2show-pawpal-starter` and `AI Engineering Project 2.pdf`, selected **Implement the project requirements**, and followed up with **go**.

### What the agent did

Codex inspected the repository and rendered the scanned PDF pages to read the requirements. It implemented `pawpal_system.py`, a CLI in `main.py`, the Streamlit interface in `app.py`, backend and UI tests, a theme, draft/final Mermaid UML, and project documentation. It used the terminal to run the CLI and pytest. The extra planning algorithm ranks tasks by priority and selects non-overlapping tasks within availability and a care-time budget.

### Verification and revisions

The agent reviewed interval boundaries and repeat completion behavior, revised conflict explanations to include insertion-order ties, and allowed the backend's full-day availability window to end at midnight. Actual test output is saved in `test-results.txt`. UI tests check real Streamlit forms and state transitions.

### Human review

No manual corrections or personal learning experiences are attributed to the user. The student should run the app, review the tests and scheduling tradeoffs, and add their own observations to `reflection.md` before submitting.

## Prompt Comparison

Not attempted. No second model or alternate-prompt experiment is claimed.

## Verdant extension (final project)

### Task given to the agent

The user supplied `VERDANT_DESIGN_DOCUMENT.md` (v1.0), the PawPal+ and AI110 final-project PDFs, and the PawPal+ GitHub repository, and asked Claude Code to help build the project.

### What the agent did

Claude Code cloned the repository, ran the original tests (29 passed) before changing anything, and created a `verdant` branch. It added the `verdant/` package (domain models, a PawPal adapter, SQLite persistence with migrations, membership-checked services, seed import, Open-Meteo weather with caching, deterministic advisory rules and photo validation), a Streamlit app (`verdant_app.py`), 51 new tests, an evaluation script, a reproducible demo, an architecture diagram, and documentation. `pawpal_system.py`, `app.py`, `main.py` and the original tests were not modified.

### Verification and revisions

Every commit was preceded by a test run (final: 80 passed). The agent also ran the app in a browser against a throwaway database and the live Open-Meteo forecast, at desktop and 375 px widths. That exposed three bugs the unit tests missed: `st.tabs` resetting after each action (replaced by a stateful segmented control), a cached repository rejecting hot-reloaded classes (lookups now by class name), and a CSS rule that broke the icon font. All three were fixed and re-checked.

### Human review needed

The crop frost-sensitivity table and the transcribed seed names are flagged `needs_review`. The reflection sections in `model_card.md` are left for the student to write.
