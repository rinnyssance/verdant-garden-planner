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
