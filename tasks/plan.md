# Implementation Plan: NeuraXAi (v0.3.0 → v0.6.0 detailed, v1.0 roadmap)

Source spec: none separate. The repo's own `README.md` (roadmap + "v0.4.0 prepared update" section) acts as the spec.
Code analysed: v0.3.0 at `main` commit `2b2b84b`.
Task details and checkboxes live in `tasks/todo.md`. This file holds the analysis, decisions, order, and risks.

## Overview

NeuraXAi is a local-first chat assistant: Flask backend → Ollama (`phi3:mini`) → streamed plain text to a vanilla HTML/CSS/JS chat page, with JSON-file memory and English/Telugu handling. About 400 lines of real code across 9 files.

The goal is a permission-controlled personal agent (README roadmap, v1.0). That is a long way from here, so this plan does three things:

1. Details the work up to v0.6.0 (stability → memory/sessions → tools/documents) as small vertical tasks.
2. Lists v0.7.0–v1.0.0 as epics only. They depend on what Phi-3 Mini can actually do, so they should be broken down after Checkpoint C.
3. Starts with the biggest finding below, because it changes everything else.

## What the repo actually contains (analysis)

### Finding 0 — the repo is v0.3.0; the README describes v0.4.0

The README documents `core/language.py`, `core/intent.py`, `tests/test_app.py`, a memory checkbox, atomic writes, and Ollama timeouts. **None of those files exist in the repo.** The repo has exactly: `app.py`, `core/{llm,memory,prompt}.py`, `web/{templates,static}`, `requirements.txt`, `.gitignore`, `README.md`. The README says v0.4.0 was "prepared" but never validated, so the author may hold it as a ZIP outside Git.

**Decision (2026-11-26, user):** no v0.4.0 source exists. v0.4.0 is rebuilt from the README spec against the real v0.3.0 code (Tasks 2–10).

### Architecture today

```
Browser (index.html + app.js)
   │  POST /chat {message, memory}  →  text/plain stream
   ▼
app.py  chat()
   ├─ detect_language()      Telugu Unicode regex only
   ├─ shortcuts (no LLM):    exact "hi/hello/hey"; "my name is"/"i am"; "what is my name"
   ├─ format_rule / language_rule   (keyword checks on "bullet", "points", "paragraph")
   ├─ get_history()          last 10 msgs from data/memory.json
   └─ ask_llm_stream(prompt) → requests.post(localhost:11434/api/generate, stream=True)
core/memory.py   JSON file: {facts:{user_name}, history:[...]}  (read-modify-write per message)
core/prompt.py   one SYSTEM_PROMPT string
```

### Defects found in the current code (these drive Phase 1)

| # | Where | Defect | Effect |
|---|---|---|---|
| D1 | `memory.py:4` | `MEMORY_FILE = "data/memory.json"` is cwd-relative and `data/` is not in the repo (the file is gitignored). `save_memory` never creates the folder. | **Fresh clone: the first memory write raises `FileNotFoundError` after the reply has streamed**, so the turn is silently not saved. Running from another cwd writes elsewhere. |
| D2 | `app.py:66-70` | Name = last word after "my name is" / "i am". | "My name is Alex Kumar" saves "Kumar". **"I am a student" saves "student"** and overwrites the real name. |
| D3 | `app.py:73-76` | "what is my name" ignores `memory_on`. | Memory-off leaks the stored name. UI has no toggle at all (`memoryEnabled` is hard-coded `true`). |
| D4 | `llm.py` | No timeout, no `raise_for_status`, no handling of Ollama's `{"error": ...}` lines, no exception handling. | Ollama down → 500 / hung request. Model missing → empty reply with no message. |
| D5 | `llm.py` / `app.py` | On stop/disconnect, the upstream Ollama request is never closed. | Model keeps generating after the user clicks Stop. |
| D6 | `memory.py` | Read-modify-write of the whole file per message, no lock, no atomic replace; history grows forever. Flask runs threaded. | Concurrent requests or a crash mid-write can corrupt/lose history. |
| D7 | `app.py:25-27,36-41` | `request.json or {}` → 415 on non-JSON; a non-string `message` → `.strip()` 500. | Bad input gives 500s. |
| D8 | `app.py:154` | `app.run(debug=True)`. | Werkzeug debugger/reloader on. Fine only because it binds localhost. |
| D9 | `app.py:44` | Greeting match is exact (`"hi"`), so "Hi!" or "hello there" go to the LLM. Identity ("what is your name") has no shortcut. | Inconsistent behaviour, slow replies for trivial turns. |
| D10 | `app.py:103-117` | History lines and user text are pasted into one raw prompt string for `/api/generate`; the "FACTUAL MEMORY" block is really chat history, and the stored name is never injected. | Weak prompt structure; the name only works through the shortcut; prompt-injection surface grows once tools and documents arrive. |
| D11 | `app.js` `formatAIResponse` | Regex HTML builder. The `<li>` → `<ul>` regex is greedy with the `s` flag, so it can wrap text between bullets; unclosed fences during streaming render badly; the copy button uses inline `onclick`. Escaping happens before markup, so XSS is *currently* contained, but this is fragile. | Rendering glitches while streaming; risk if anyone edits the order. |
| D12 | `app.js` | `fetch` never checks `response.ok`; non-abort errors are swallowed. | Server errors show an empty bubble. |
| D13 | repo | No tests, no CI, unpinned `flask` / `requests`, no LICENSE. | No safety net before refactoring. |

## Architecture Decisions

1. **Stay on Flask + vanilla JS + Ollama.** No framework migration. The app is small, and every roadmap feature fits this stack. A rewrite would burn weeks for no user-visible gain.
2. **Tests first, using stdlib `unittest`** (what the README already promises). Characterization tests for current behaviour come before any refactor (Task 1). No new test dependency.
3. **Pure functions in `core/`, thin routes in `app.py`.** `language.py`, `intent.py`, and a `build_prompt()` in `prompt.py` take plain inputs and return plain outputs, so they are testable without Flask or Ollama. `app.py` only orchestrates.
4. **Plain-text streaming stays through v0.4.0**, but the first chunk is pulled eagerly so connection and model errors become a real HTTP 503 JSON response before streaming starts. Mid-stream failures are rarer; revisit SSE/NDJSON only if Task 5 shows they matter (Open Question 4).
5. **Storage path: harden JSON in v0.4.0, then migrate to SQLite in v0.5.0** behind the same small function interface, with a one-time import of `memory.json` and a backup. Sessions, editable facts and summaries need relational queries; hardened JSON is enough until then.
6. **Move from `/api/generate` + one big string to `/api/chat` with a system message and role-tagged messages in v0.5.0** (Task 14). It matches Phi-3's chat template, cuts prompt injection through history, and enables token budgeting.
7. **Tools: deterministic routing first, model-chosen tools second.** Phi-3 Mini is unreliable at free-form tool calling. Start with explicit intents ("calculate …", file uploads) and a registry with permission levels (`read` = auto, `write`/`exec` = needs user approval, nothing unrestricted). Let the model pick tools only if Checkpoint C testing shows it can do so reliably (Ollama `format: "json"` helps).
8. **Everything stays bound to `127.0.0.1`** with debug off by default. Anything that reads files or runs actions (v0.6+) goes through the permission registry. This is the README's own rule ("do not give future tools unrestricted filesystem or shell access") made enforceable.

## Dependency Graph

```
T1 baseline + test harness + CI
 │
 ├── T2 storage hardening ──┬── T3 memory toggle (backend + UI) ──┐
 │                          └── T4 name capture (intent.py) ──────┤
 ├── T5 Ollama client + error surface ── T6 request validation ──┤
 ├── T7 language.py ── T8 intent shortcuts ── T9 build_prompt() ──┤
 └── T10 frontend rendering + error/stop states ─────────────────┘
                                                                  ▼
                                      ◆ Checkpoint A: v0.4.0 validated on laptop, tag
                                                                  │
 T11 SQLite layer + JSON migration ── T12 chat sessions ── T13 facts/profile editor
                                  └── T14 /api/chat + context budget ── T15 rolling summary
                                                                  ▼
                                      ◆ Checkpoint B: v0.5.0
                                                                  │
 T16 tool registry + permissions + calculator ── T17 date/time + intent routing
                                              └── T18 upload + PDF/CSV/XLSX extraction
                                                                  ▼
                                      ◆ Checkpoint C: v0.6.0 → re-plan v0.7+
```

Parallel-safe groups inside Phase 1 (disjoint files): {T2→T3, T4}, {T5→T6}, {T7→T8→T9}, {T10}. They all touch `app.py`, so merge T3/T4/T6/T8 sequentially even if the rest are done in parallel. The collision point is the `chat()` function.

## Task List

(Index only. Acceptance criteria, verification, files, and sizes are in `tasks/todo.md`.)

### Phase 0: Safety net
- [ ] Task 1: Reproducible local baseline, characterization tests, CI

### Phase 1: v0.4.0 — Stability and correctness
- [ ] Task 2: Storage that cannot lose or corrupt memory (D1, D6)
- [ ] Task 3: Memory toggle works end to end (D3)
- [ ] Task 4: Name capture that doesn't corrupt facts (D2)
- [ ] Task 5: Ollama client hardening with visible errors (D4, D5, D12)
- [ ] Task 6: Request validation and server hardening (D7, D8)
- [ ] Task 7: Language detection module (Telugu + Roman Telugu)
- [ ] Task 8: Deterministic intent shortcuts (D9)
- [ ] Task 9: Prompt builder with separated facts and history (D10)
- [ ] Task 10: Safe streaming renderer, stop and error states (D11, D12)
- [ ] **Checkpoint A** — v0.4.0 acceptance on the target laptop, tag `v0.4.0`

### Phase 2: v0.5.0 — Memory that scales
- [ ] Task 11: SQLite storage with one-time JSON migration
- [ ] Task 12: Chat sessions (create / list / switch / delete)
- [ ] Task 13: Editable facts and "forget me"
- [ ] Task 14: `/api/chat` migration and context budget
- [ ] Task 15: Rolling summary of old turns
- [ ] **Checkpoint B** — v0.5.0

### Phase 3: v0.6.0 — Tools and documents
- [ ] Task 16: Tool registry with permission levels, plus calculator
- [ ] Task 17: Date/time tool and tool routing
- [ ] Task 18: File upload with PDF/CSV/XLSX extraction
- [ ] **Checkpoint C** — v0.6.0, then re-plan Phase 4

### Phase 4: v0.7.0 → v1.0.0 (epics — not yet broken down)

| Version | Epic | Entry condition | Biggest risk |
|---|---|---|---|
| v0.7.0 | Document intelligence and RAG (embeddings via Ollama, local vector store, citations) | T18 extraction works on real files | Retrieval quality with a 3.8B model; prompt injection via document text (treat as data, never instructions) |
| v0.8.0 | Live web search; optional cloud model fallback | Settings and secret handling exist | Breaks the "local-first, private" promise; needs an explicit per-request opt-in and key storage outside Git |
| v0.9.0 | Coding assistant and freelance workflows (e.g. invoice extraction) | RAG + file tools | Accuracy on client data; README itself says review before client use |
| v0.10.0 | Voice and approved desktop actions | Permission registry proven in v0.6 | Desktop control is the highest-risk capability; approval UI must come first |
| v0.11.0 | Multi-step planner, scheduled automation | Reliable tool calling | Small-model planning errors; every step needs human approval hooks |
| v1.0.0 | Security review, packaging (installer/launcher), performance, license | All of the above | Windows packaging of Flask+Ollama dependency |

## Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| v0.4.0 source exists elsewhere and we duplicate or clash with it | Med | Resolve Open Question 1 before starting Task 2 |
| Phi-3 Mini follows format/language rules poorly (README admits this) | High | Keep deterministic shortcuts for everything that can be deterministic; evaluate against a fixed prompt list at each checkpoint; consider a larger model via `NEURAXAI_MODEL` (Open Question 3) |
| `chat()` becomes a merge-conflict magnet | Med | Task 8 moves routing into `intent.py`; do Phase 1 `app.py` changes sequentially |
| JSON → SQLite migration loses data | High | One-time import, copy original to `memory.json.bak`, idempotent, covered by a migration test with a fixture file |
| Tools or uploads open a local attack surface (path traversal, huge files, prompt injection from PDFs) | High | Upload dir sandbox, size/type limits, tool outputs labelled as untrusted data in the prompt, permission levels (Decision 7) |
| Windows-specific issues (PowerShell policy, file locks on atomic replace, paths) | Med | Use `pathlib`, `os.replace`, test on the target Windows laptop at every checkpoint |
| No JS test tooling; frontend regressions slip through | Med | Keep JS small and DOM-based; maintain a written manual checklist per checkpoint; add `node --test` only if the JS grows (not planned) |
| Scope creep: 20 README workstreams | High | Only Phases 0–3 are committed. Re-plan at Checkpoint C with real measurements |

## Open Questions

1. ~~Do you have the v0.4.0 ZIP/folder locally?~~ **Resolved:** no; rebuild from the README spec.
2. **How far do you want to commit?** This plan details through v0.6.0. Confirm that stopping at Checkpoint C is the right planning horizon.
3. **Hardware and model:** how much RAM/GPU does the target laptop have? Phi-3 Mini (3.8B) is the weak link for Telugu and tool use. A 7–8B model (e.g. Llama 3.1 8B, Qwen 2.5 7B) may change which tool-calling approach is viable.
4. **Streaming format:** keep plain text and eager first-chunk error handling (current decision), or move to SSE/NDJSON events now so errors and "done" can be signalled in-band?
5. **License:** README says none is chosen. Pick one before any public release (MIT is the usual default for personal projects).
6. **Should `"I am X"` name capture be dropped entirely?** The README says yes (only explicit phrases like "my name is" / "call me"). Task 4 follows the README unless you say otherwise.

## Definition of Done (applies to every task)

- `python -m unittest discover -s tests -v` passes, with at least one new test per behaviour change.
- App starts (`python app.py`) and a real chat turn works with Ollama running, for any task that touches `/chat`.
- No new dependency unless the task says so and `requirements.txt` is updated.
- README section for the changed behaviour is updated; no claim in the README is left unverified.
- `data/memory.json`, `data/*.db`, `.venv/`, uploads are never committed.
