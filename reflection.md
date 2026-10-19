# PawPal+ Project Reflection

This is an AI-assisted technical record, not a claim about the student's personal experience. The implementation sections below describe the actual code. Personal prompts at the end need the student's own answers before submission.

## 1. System Design

### a. Initial design

Three core user actions are: add a pet, schedule a care task, and view/complete the day's care. The initial UML uses Owner, Pet, Task, and Scheduler. Owner aggregates pets and exposes their tasks. Pet owns task occurrences. Task stores description, date, time, duration, priority, recurrence, and completion. Scheduler reads through Owner to sort, filter, detect conflicts, and plan across all pets.

### b. Design changes

The final design adds a Plan dataclass to keep selected tasks and skipped reasons together. Stable IDs distinguish pets with the same name and tasks with identical descriptions. Task completion returns a new occurrence, while Scheduler attaches it to the pet. This separates recurrence calculation from collection management. Updating a task creates and validates a replacement before changing the stored list, so a rejected edit leaves the old task intact.

## 2. Scheduling Logic and Tradeoffs

### a. Constraints and priorities

The planner considers the requested date, completion status, priority, available hours, duration, and total care-time budget. All pets share one owner's time. High-priority tasks are considered first, with chronological and stable insertion-order tie breaking. A task is selected only if it fits the hours and budget and overlaps no already selected task.

### b. Tradeoffs

Greedy planning is easy to explain but does not maximize the number of tasks or a mathematical score. A long high-priority task can block several shorter tasks. Conflict checks compare interval pairs rather than only identical starts, catching partially overlapping durations at O(n²) cost. This is acceptable for a small household. The system reports conflicts instead of automatically moving scheduled care. Session-only data simplifies the core project but does not survive a new browser session.

## 3. AI Collaboration

### a. How AI was used

The user supplied the starter repository and assignment PDF, selected “Implement the project requirements,” and then said “go.” Codex read the scanned requirements, inspected the starter, drafted UML, wrote the backend and CLI, connected the Streamlit UI, and authored tests and documentation in this chat. The actual prompt record appears in ai_interactions.md. Separate chats and multiple models were not used.

### b. Judgment and verification

During implementation, the agent changed a conflict explanation that mentioned only priority and earlier time: identical priority/time ties also depend on insertion order. It also changed the backend's default availability end from 23:59 to 24:00 so tasks ending at midnight can fit a full-day plan. These are agent revisions, not claimed student decisions. Tests verify recurrence does not duplicate tasks after repeated completion, invalid edits are atomic, and the planner respects budget and overlap constraints. The student should independently run and inspect these behaviors.

## 4. Testing and Verification

### a. What was tested

The test suite covers the assignment's required completion, addition, sorting, recurrence, and conflict behaviors, plus filters, multiple pets, validation, time budgets, interval boundaries, safe edits, and empty inputs. Streamlit's AppTest checks the actual app forms and state changes, including new recurring occurrences. These tests protect both backend logic and the UI wiring.

### b. Confidence

Technical confidence is 4/5 within the documented scope, subject to the recorded test results. Future tests should cover larger task collections, browser accessibility, persistence failures if storage is added, and explicit timezone handling. No claims are made about production reliability or multi-user storage.

## 5. Reflection

### a. What went well

The UI and CLI reuse one backend, so scheduling rules are testable without launching a browser. Keeping completed occurrences makes recurrence behavior visible and auditable.

### b. What could improve

Add JSON import/export or persistent storage, configurable recurring schedules, and suggested alternative times. Keep those features separate from the UI to preserve testability.

### c. Technical takeaway

A clear ownership model makes cross-pet scheduling straightforward. Tests need to check boundary behavior, not just ordinary examples: repeated completion and touching intervals are especially useful cases.

## Student's personal review — complete before submission

- Which design or AI suggestion did you personally question, reject, or change? Explain your reasoning after reviewing the code.
- Which part did you run or verify yourself, and what did you observe?
- Which AI assistant feature helped you most? Describe your experience rather than repeating the agent's account.
- What did you learn as the lead architect, and what would you change next?
- The work used one chat. Explain whether that helped or hindered your organization; do not claim separate chats were used.
