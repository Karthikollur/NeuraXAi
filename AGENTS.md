# Agent rules for NeuraXAi

Who does what:
- **Codex and Antigravity** implement tasks.
- **Claude** plans and reviews.
- **The maintainer** merges.

## Where the work is

- `tasks/todo.md` — the task list. Each task has acceptance criteria, verification steps, dependencies and likely files. Work only on the task you were given.
- `tasks/plan.md` — roadmap, decisions and the defect list (D1–D13). Read it; don't edit it.
- If `CODEX_TASK.md` exists in the repo root, it is an unfinished task handed over mid-way. Continue it, and delete the file when the task is done.

## Doing a task

1. Start from the latest `main`: `git switch main`, `git pull`, `git switch -c task-NN-short-name` (e.g. `task-03-memory-toggle`).
2. Check that the task's dependencies are merged into `main`. If one isn't, stop and say so.
3. Change only what the task needs, within its "Files likely touched". If you need another file, explain why in the PR.
4. Add or update a test for every behaviour change. If the task fixes a D-bug, remove that test's `@unittest.expectedFailure` and make sure the test fails without your fix.
5. Run the tests (below). All must pass before you open the PR.
6. Do **not** tick boxes in `tasks/todo.md`. The reviewer ticks them after checking.
7. Open a PR titled `Task NN: <task title>`. In the body, list each acceptance criterion with its evidence (test name or manual check), plus anything not done or unclear.

## Rules

- Python 3.10+, stdlib `unittest`. No new dependency unless the task names it.
- One task per branch and per PR. Never work on a task, or on files, that another open PR is changing. `chat()` in `app.py` is shared by many tasks, so check open PRs first.
- Never commit `data/`, `.venv/`, uploads or secrets.
- Keep the server bound to `127.0.0.1`. Never weaken validation, safety checks or tests to make something pass.
- If the plan looks wrong, say so in the PR instead of changing it.

## Commands (Windows PowerShell, repo root)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe app.py
```

`app.py` serves http://127.0.0.1:5000 and needs Ollama running for real chat replies. Tests mock Ollama and don't need it.
