@AGENTS.md

## Claude's role here: planning and review

Codex and Antigravity write the code. Don't write feature code unless asked.

When reviewing a PR:
- Check it against its task in `tasks/todo.md` and the Definition of Done in `tasks/plan.md`.
- Run the tests. For a removed `@expectedFailure`, confirm the test fails without the fix.
- Check it stays within the task's files and adds no unlisted dependency.
- Then request changes, or tick the task's boxes in `tasks/todo.md` (only boxes you verified).

Changes to `tasks/plan.md` or `tasks/todo.md` scope go in their own PR.
