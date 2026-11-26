# Implementation Plan: NeuraXAi v0.4.0 → v1.0.0

Sources:
- **Team roadmap** (20 stages, v0.1.0 → v1.0.0): the *what*. Its stage names and version numbers are used throughout.
- **Code analysis** of v0.3.0 at `main` commit `2b2b84b`: the *how* and *in what order*.
- `README.md` "v0.4.0 prepared update" section: the spec for Stage 4. No v0.4.0 source exists; it is rebuilt from that spec.

Task details and checkboxes live in `tasks/todo.md`. This file holds the roadmap, analysis, decisions, order and risks.

## Overview

NeuraXAi is a local-first chat assistant: Flask backend → Ollama → plain text streamed to a vanilla HTML/CSS/JS chat page, with JSON-file memory and English/Telugu handling. About 400 lines of real code across 9 files.

The plan has two layers:

1. **Roadmap:** all 20 stages from the team roadmap, with a few order changes (listed under "Changes to the team roadmap").
2. **Execution:** Stages 4–8 are broken into 36 tasks with acceptance criteria and verification (`tasks/todo.md`). Stages 9–20 stay at roadmap level; each is broken down when the stage before it reaches its checkpoint.

Stage 4 is fully specified and Task 1 is implemented (branch `rebuild/v0.4.0`, not yet on `main`). Stages 6–8 are drafted in less detail and get re-checked at each checkpoint.

## Roadmap

Time estimates come from the team roadmap. Stages 4–20 add up to **149–234 working days** (roughly 7–11 months full-time).

| Stage | Version | Phase | Status | Est. days | Plan detail |
|---|---|---|---|---|---|
| 1 | v0.1.0 | Project foundation | Implemented (reconstructed) | — | — |
| 2 | v0.2.0 | Basic intelligence & memory | Implemented (reconstructed) | — | — |
| 3 | v0.3.0 | Web-based local AI assistant | Implemented (`main`) | — | — |
| 4 | v0.4.0 | Intelligence & stability | **Next** | 5–7 | Tasks 1–11 |
| 5 | v0.5.0 | Advanced memory system | Pending | 7–10 | Tasks 12–20 |
| 6 | v0.6.0 | Multi-model AI engine | Pending | 5–8 | Tasks 21–27 |
| 7 | v0.7.0 | Intent routing & tool calling | Pending | 7–12 | Tasks 28–32 |
| 8 | v0.8.0 | PDF, Excel & file processing | Pending | 10–15 | Tasks 33–36 |
| 9 | v0.9.0 | RAG & knowledge base | Pending | 10–15 | Roadmap |
| 10 | v0.10.0 | Real-time internet intelligence | Pending | 7–10 | Roadmap |
| 11 | v0.11.0 | Voice assistant | Pending | 10–15 | Roadmap |
| 12 | v0.12.0 | Safety & permission engine (hardening) | Pending | 7–12 | Roadmap |
| 13 | v0.13.0 | Windows computer automation | Pending | 10–15 | Roadmap |
| 14 | v0.14.0 | Advanced AI agent workflows | Pending | 12–20 | Roadmap |
| 15 | v0.15.0 | MCP & external app integration | Pending | 7–12 | Roadmap |
| 16 | v0.16.0 | Freelancing automation | Pending | 10–15 | Roadmap |
| 17 | v0.17.0 | Local + cloud hybrid AI | Pending | 5–8 | Roadmap |
| 18 | v0.18.0 | Desktop application | Pending | 10–15 | Roadmap |
| 19 | v0.19.0 | Learning & performance optimization | Pending | 12–20 | Roadmap |
| 20 | v0.20.0 → v1.0.0 | Production engineering & final release | Pending | 15–25 | Roadmap |

## Changes to the team roadmap

The stage list and numbering are kept. These changes fix ordering problems and trim scope.

| Change | From → to | Why |
|---|---|---|
| **Safety core moves earlier** | Stage 12 → Stage 7 (Task 28) | Tool calling (7), file processing (8) and web access (10) all let the model act before the permission engine exists. Stage 7's "file listing in an approved folder" already needs Stage 12's path validation. Stage 7 gets tiers T0–T3, path allowlist, audit log and an approval gate. Stage 12 becomes hardening: sandbox, dry-run, undo, emergency stop, secret storage. |
| **CI from day one** | Stage 20 → Stage 4 (Task 1, done) | Every stage needs a regression net. Ruff and Bandit can join CI at Checkpoint A. |
| **Evaluation set early** | Stage 19 → Stage 6 (Task 21) | "Route each task to the best model" (Stage 6) and JSON tool calling (Stage 7) are guesses without measurements. |
| **Performance tracking early** | Stage 19 → Stage 6 (Task 26) | Latency per model is needed to choose models; Stage 19 builds on this data. |
| **Tool schema follows MCP's format** | Stage 15 design → Stage 7 (Task 29) | If tools are described as name + description + JSON Schema input, Stage 15 is an adapter, not a rewrite. Existing MCP servers (fetch, filesystem) may also cover parts of Stages 10 and 13. |
| **OCR, invoice extraction, batch processing** | Stage 8 → Stage 16 | Stage 8 had 14 features in 10–15 days. These three are freelancing workflows that need the Stage 8 basics first. |
| **RAG stack kept small** | Stage 9 | Use Ollama embeddings (`nomic-embed-text`) + SQLite (FTS5 for keyword search) before Sentence Transformers + FAISS/ChromaDB, which pull in PyTorch. |
| **Deferred** | Stages 5, 11, 18 | Multiple profiles (adds a user ID to every table; single-user app), wake word (push-to-talk first, as the roadmap already says), system tray and auto-start. Revisit after Stage 18. |
| **Automatic memory extraction needs approval** | Stage 5 | The model proposes facts; the user approves before anything is saved (matches the roadmap's "user-approved storage"). Explicit commands ("Remember that …") come first. |

## What the code actually contains (analysis)

### Finding 0 — the repo is v0.3.0; the README describes v0.4.0

The README documents `core/language.py`, `core/intent.py`, `tests/test_app.py`, a memory checkbox, atomic writes and Ollama timeouts. None of those files exist in the repo. **Decision (2026-11-26):** no v0.4.0 source exists, so Stage 4 rebuilds it from the README spec and the team roadmap's Stage 4 feature list.

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

### Defects found in the current code (fixed in Stage 4)

| # | Where | Defect | Effect | Fixed by |
|---|---|---|---|---|
| D1 | `memory.py:4` | `MEMORY_FILE = "data/memory.json"` is cwd-relative and `data/` is not in the repo. `save_memory` never creates the folder. | On a fresh clone, the first memory write raises `FileNotFoundError` after the reply has streamed, so the turn is silently lost. | Task 2 |
| D2 | `app.py:66-70` | Name = last word after "my name is" / "i am". | "My name is Alex Kumar" saves "Kumar". "I am a student" saves "student" and overwrites the real name. | Task 4 |
| D3 | `app.py:73-76` | "what is my name" ignores `memory_on`; the UI has no toggle (`memoryEnabled` hard-coded `true`). | Memory-off leaks the stored name. | Task 3 |
| D4 | `llm.py` | No timeout, no `raise_for_status`, no handling of Ollama `{"error": ...}` lines. | Ollama down → 500 or hung request. Missing model → empty reply. | Task 6 |
| D5 | `llm.py` / `app.py` | The upstream Ollama request is never closed on stop/disconnect. | The model keeps generating after Stop. | Task 6 |
| D6 | `memory.py` | Whole-file read-modify-write per message, no lock, no atomic replace; history grows forever. | Concurrent requests or a crash mid-write can lose history. | Task 2 |
| D7 | `app.py:36-41` | `request.json or {}` → 415 on non-JSON; non-string `message` → 500. | Bad input gives 500s. | Task 7 |
| D8 | `app.py:154` | `app.run(debug=True)`. | Debugger and reloader always on. | Task 7 |
| D9 | `app.py:44` | Greeting match is exact; no identity shortcut. | "Hi!" goes to the LLM; slow trivial turns. | Task 9 |
| D10 | `app.py:103-117` | History and user text pasted into one raw prompt; the stored name is never injected. | Weak prompt structure; prompt-injection surface grows once tools and documents arrive. | Task 10 |
| D11 | `app.js` `formatAIResponse` | Regex HTML builder; greedy `<ul>` wrapping; unclosed fences break while streaming; inline `onclick`. | Rendering glitches; fragile XSS protection. | Task 11 |
| D12 | `app.js` | `fetch` never checks `response.ok`; non-abort errors swallowed. | Server errors show an empty bubble. | Tasks 6, 11 |
| D13 | repo | No tests, no CI, unpinned dependencies, no LICENSE. | No safety net before refactoring. | Task 1 (license: open question) |

## Architecture Decisions

1. **Stay on Flask + vanilla JS + Ollama.** No framework migration. Stage 18's desktop app wraps the same Python backend (PySide6 or a lightweight wrapper, as the roadmap suggests).
2. **Tests and CI first** with stdlib `unittest`. Characterization tests before any refactor (Task 1, done). Live-model checks live in a separate evaluation runner (Task 21), not in CI.
3. **Pure functions in `core/`, thin routes in `app.py`.** `language.py`, `intent.py`, `prompt.py` take plain inputs and return plain outputs, so they test without Flask or Ollama.
4. **One config module** (`core/config.py`, Task 5) reads environment variables for model, Ollama URL, timeouts, limits, debug and data paths. Stage 6's model registry builds on it.
5. **Plain-text streaming stays for Stage 4,** with the first chunk pulled eagerly so connection and model errors become an HTTP 503 JSON response before streaming starts. Revisit SSE/NDJSON if mid-stream failures matter (Open Question 3).
6. **Storage: harden JSON in Stage 4, migrate to SQLite in Stage 5** behind the same function interface, with a one-time import and backup.
7. **`/api/chat` with role-tagged messages** replaces one big prompt string in Stage 5 (Task 18). Stage 6 moves this client behind an engine interface so models and runtimes can change without touching the rest of the app.
8. **Tools: deterministic routing first, model-chosen tools second,** only if the evaluation set shows the model does it reliably. Tool definitions use MCP's shape (name, description, JSON Schema input).
9. **Safety tiers from the first tool:** T0 read-only (allowed within scope), T1 low-risk reversible (configured permission), T2 sensitive (explicit confirmation), T3 blocked (always denied). Every tool call goes through the policy check and is written to the audit log.
10. **Everything binds to `127.0.0.1`** with debug off by default. Tool output, uploaded documents and web pages are passed to the model as labelled untrusted data, never as instructions.

## Dependency Graph

```
Stage 4  T1 harness+CI
          ├─ T2 storage ─┬─ T3 memory toggle
          │              └─ T4 name capture
          ├─ T5 config ── T6 Ollama client ── T7 validation
          ├─ T8 language ── T9 intents ── T10 prompt builder
          └─ T11 renderer (after T6)
                         ◆ Checkpoint A (v0.4.0)
                 ┌────────────────┴────────────────┐
Stage 5  T12 SQLite                        Stage 6  T21 eval set
          ├─ T13 sessions                           T22 engine abstraction (needs T18)
          ├─ T14 fact commands ── T15 dashboard     ├─ T23 registry + selector
          ├─ T16 search   T17 export/import         ├─ T24 health + fallback
          └─ T18 /api/chat + budget ── T19 summary  ├─ T25 hardware detection
                       └─ T20 suggested memories    ├─ T26 perf tracking
                         ◆ Checkpoint B             └─ T27 routing (needs T21, T26)
                                                         ◆ Checkpoint C
                 └────────────────┬────────────────┘
Stage 7  T28 safety core ── T29 registry+executor+calculator ─┬─ T30 date/time/units + router
                                                              ├─ T31 system/file/text tools
                                                              └─ T32 model-proposed tool calls (needs T21)
                         ◆ Checkpoint D
Stage 8  T33 upload + CSV/TXT ── T34 PDF/XLSX/DOCX ─┬─ T35 PDF tables → Excel
                                                    └─ T36 data cleaning
                         ◆ Checkpoint E → break down Stage 9
```

### Parallel work (two people)

- **Stage 4:** {T2→T3, T4}, {T5→T6→T7}, {T8→T9→T10} and {T11} touch mostly separate files. They all meet in `chat()` in `app.py`, so merge the `app.py` changes one at a time.
- **Stages 5 and 6 can run side by side** after Checkpoint A: Stage 5 lives in `core/db.py` / `core/memory.py`, Stage 6 in `engines/`. Do T21 (eval set) and T25 (hardware) first on the Stage 6 side; T22 waits for T18 and T26 for T12.
- **Stage 7 is sequential** until T29 lands; then T30 and T31 are independent.

## Task List

(Index only. Acceptance criteria, verification, files and sizes are in `tasks/todo.md`.)

### Stage 4 — v0.4.0: Intelligence & stability
- [ ] Task 1: Reproducible baseline, characterization tests, CI *(done on branch `rebuild/v0.4.0`)*
- [ ] Task 2: Storage that cannot lose or corrupt memory (D1, D6)
- [ ] Task 3: Memory toggle works end to end (D3)
- [ ] Task 4: Name capture that doesn't corrupt facts (D2)
- [ ] Task 5: Config module for model and runtime settings
- [ ] Task 6: Ollama client hardening with visible errors (D4, D5, D12)
- [ ] Task 7: Request validation and server hardening (D7, D8)
- [ ] Task 8: Language detection (English, Telugu, Roman Telugu)
- [ ] Task 9: Deterministic intents: greetings, thanks, bye, identity (D9)
- [ ] Task 10: Prompt builder with dynamic response length (D10)
- [ ] Task 11: Safe streaming renderer, stop and error states (D11, D12)
- [ ] **Checkpoint A** — v0.4.0

### Stage 5 — v0.5.0: Advanced memory system
- [ ] Task 12: SQLite storage with one-time JSON migration
- [ ] Task 13: Chat sessions
- [ ] Task 14: Structured facts and memory commands
- [ ] Task 15: Memory dashboard
- [ ] Task 16: Conversation search (FTS5)
- [ ] Task 17: Memory export and import
- [ ] Task 18: `/api/chat` messages and context budget
- [ ] Task 19: Rolling summary of old turns
- [ ] Task 20: Suggested memories with user approval
- [ ] **Checkpoint B** — v0.5.0

### Stage 6 — v0.6.0: Multi-model AI engine
- [ ] Task 21: Evaluation prompt set and runner
- [ ] Task 22: Engine abstraction (`engines/base.py`, Ollama engine)
- [ ] Task 23: Model registry and model selector
- [ ] Task 24: Model health check and fallback
- [ ] Task 25: Hardware detection and model recommendation
- [ ] Task 26: Performance tracking
- [ ] Task 27: Rule-based model routing
- [ ] **Checkpoint C** — v0.6.0

### Stage 7 — v0.7.0: Intent routing & tool calling
- [ ] Task 28: Safety core (tiers, path allowlist, audit log, approval gate)
- [ ] Task 29: Tool registry, executor, calculator
- [ ] Task 30: Date, time, time zone and unit tools with deterministic routing
- [ ] Task 31: System info, approved-folder listing, text tools
- [ ] Task 32: Model-proposed tool calls (behind a flag)
- [ ] **Checkpoint D** — v0.7.0

### Stage 8 — v0.8.0: PDF, Excel & file processing
- [ ] Task 33: Upload endpoint with CSV/TXT extraction
- [ ] Task 34: PDF, XLSX and DOCX extraction
- [ ] Task 35: PDF tables to Excel, with downloads
- [ ] Task 36: Data cleaning for CSV/XLSX
- [ ] **Checkpoint E** — v0.8.0, then break down Stage 9

### Stages 9–20
Roadmap level only (see the Roadmap table and "Changes to the team roadmap"). Each is broken into tasks after the previous checkpoint, using the measurements gathered by then.

## Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Scope: 20 stages, 149–234 working days by the roadmap's own estimates | High | Detail only the next stages; each checkpoint is a real stopping point with a tagged release; deferrals listed above |
| Small local models follow format/language rules poorly; Telugu quality varies | High | Deterministic shortcuts wherever possible; evaluation set from Stage 6; model choice via registry, not hard-coded |
| The default `phi3:mini` may not be installed (one dev machine has only `qwen3.5:2b/4b/9b`) | Med | Task 5 makes the model configurable; Task 24 adds fallback; README documents the setting |
| Model acts before safety exists | High | Safety core (Task 28) is the first task of Stage 7; no tool runs outside the policy check |
| `chat()` becomes a merge-conflict magnet | Med | Task 9 moves routing into `intent.py`; `app.py` changes merged one at a time |
| JSON → SQLite migration loses data | High | One-time idempotent import, original kept as `memory.json.bak`, migration test with a fixture file |
| Uploads, tools and web pages carry prompt injection | High | Labelled untrusted data in prompts; path allowlist; size/type limits; T3 actions always blocked |
| Windows-specific issues (PowerShell policy, file locks on `os.replace`, paths) | Med | `pathlib`, CI on `windows-latest`, laptop test at every checkpoint |
| No JS test tooling; frontend regressions slip through | Med | Keep JS small and DOM-based; manual checklist per checkpoint; revisit if the UI grows (Stage 18) |

## Open Questions

1. ~~Do you have the v0.4.0 ZIP/folder locally?~~ **Resolved:** no; rebuild from the README spec.
2. **Target hardware:** the roadmap says an Intel i5 laptop. How much RAM, and is there a GPU? This decides which models Stage 6 registers by default.
3. **Streaming format:** keep plain text with eager first-chunk errors, or move to SSE/NDJSON events now?
4. **License:** none chosen. Needed before any public release; MIT is the usual default for personal projects.
5. **"I am X" name capture:** drop it entirely (README's v0.4.0 behaviour, used in Task 4) unless you say otherwise.
6. **README roadmap:** the README still shows the older 12-stage roadmap. Update it to the 20 stages once this plan is agreed.
7. **Who owns which stage?** Stages 5 and 6 can run in parallel if two people work on them.

## Definition of Done (applies to every task)

- `python -m unittest discover -s tests -v` passes, with at least one new test per behaviour change.
- The app starts (`python app.py`) and a real chat turn works with Ollama running, for any task that touches `/chat`.
- No new dependency unless the task says so and `requirements.txt` is updated.
- The README section for the changed behaviour is updated; no claim in the README is left unverified.
- `data/memory.json`, `data/*.db`, `.venv/` and uploads are never committed.
