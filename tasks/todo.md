# NeuraXAi — Task List

Plan, decisions, and risks: `tasks/plan.md`. D-numbers (D1…D13) refer to the defect table there.

Common commands (Windows PowerShell, from the repo root, venv active):

```powershell
python -m unittest discover -s tests -v     # tests
python -c "import app"                      # import/"build" check
python app.py                               # run → http://127.0.0.1:5000  (Ollama must be running)
```

Sizes: XS 1 file · S 1–2 · M 3–5 · L 5–8 (split further).

---

## Phase 0: Safety net

### [ ] Task 1: Reproducible local baseline, characterization tests, CI
**Description:** Clone the repo, get v0.3.0 running on the laptop, pin dependencies, and add a test harness that locks in current behaviour (including the known bugs, marked as expected failures) so later refactors are safe. First resolve Open Question 1 (does a v0.4.0 ZIP exist?).
**Acceptance criteria:**
- [ ] Fresh clone + `python -m venv .venv` + `pip install -r requirements.txt` + `python app.py` serves the page and answers one real chat turn.
- [ ] `tests/` exists with a Flask test-client test for `GET /` (200) and for the "hi" shortcut (reply text, no Ollama call).
- [ ] Known bugs D1 (missing `data/`), D2 ("I am a student"), D3 (memory-off name leak) each have a test marked `@unittest.expectedFailure` with a comment naming the task that fixes it.
- [ ] `requirements.txt` pins compatible ranges (e.g. `flask>=3.0,<4`, `requests>=2.31,<3`).
- [ ] GitHub Actions workflow runs the unittest command on push/PR.
**Verification:**
- [ ] Tests pass: `python -m unittest discover -s tests -v` (expected failures reported as "expected failures", not errors).
- [ ] Build succeeds: `python -c "import app"`.
- [ ] Manual: CI run on GitHub is green.
**Dependencies:** None
**Files likely touched:** `requirements.txt`, `tests/__init__.py`, `tests/test_baseline.py`, `.github/workflows/ci.yml`
**Estimated scope:** Small–Medium (4 files)

---

## Phase 1: v0.4.0 — Stability and correctness

### [ ] Task 2: Storage that cannot lose or corrupt memory (D1, D6)
**Description:** Make `core/memory.py` safe: absolute path anchored to the project (not cwd), auto-create `data/`, validate structure, serialize access with a lock, write atomically, and back up an unreadable file instead of silently replacing it.
**Acceptance criteria:**
- [ ] Saving a message on a fresh clone (no `data/`) succeeds, and the file is created next to the project regardless of cwd.
- [ ] Two threads calling `save_message` 100 times each yield exactly 200 history entries.
- [ ] A corrupt `memory.json` is renamed to `memory.json.corrupt-<timestamp>` and a fresh structure is used; the original bytes are preserved.
- [ ] Writes use temp file + `os.replace`; killing the process mid-write cannot leave a truncated file (test via simulated exception between write and replace).
- [ ] `MEMORY_FILE` path can be overridden (env var or module attribute) so tests use a temp dir.
- [ ] Task 1's D1 expected-failure test now passes and the decorator is removed.
**Verification:**
- [ ] Tests pass: `python -m unittest tests.test_memory -v`
- [ ] Manual: delete `data/`, send a message, restart app, confirm history is still used.
**Dependencies:** Task 1
**Files likely touched:** `core/memory.py`, `tests/test_memory.py`, `tests/test_baseline.py`
**Estimated scope:** Small (3 files)

### [ ] Task 3: Memory toggle works end to end (D3)
**Description:** Every memory read and write in `/chat` honours the `memory` flag, and the UI exposes it as a checkbox. Memory OFF means: no history in the prompt, no saved name lookup, no writes. It does not delete stored data.
**Acceptance criteria:**
- [ ] With `memory:false`, "what is my name" does not return the stored name and nothing is written to disk.
- [ ] With `memory:true`, the stored name is returned and the turn is saved.
- [ ] The page has a "Memory" checkbox (default ON, state persisted in `localStorage`) whose value is sent as `memory` in every `/chat` request.
- [ ] Non-boolean `memory` values are treated as invalid input (400) — wired fully in Task 6, but the type check lives here.
- [ ] D3 expected-failure test passes and is un-marked.
**Verification:**
- [ ] Tests pass: `python -m unittest tests.test_memory_toggle -v` (assert file mtime/contents unchanged when off).
- [ ] Manual: set name with memory ON, toggle OFF, ask name → "I don't know."; toggle ON → name returned.
**Dependencies:** Task 2
**Files likely touched:** `app.py`, `web/templates/index.html`, `web/static/app.js`, `web/static/style.css`, `tests/test_memory_toggle.py`
**Estimated scope:** Medium (5 files)

### [ ] Task 4: Name capture that doesn't corrupt facts (D2)
**Description:** Create `core/intent.py` with `extract_name(text) -> str | None`. Only explicit phrases count ("my name is …", "call me …"); capture multi-word names; "I am a student" must never touch the saved name. When memory is off, say the name wasn't saved rather than "Got it".
**Acceptance criteria:**
- [ ] `extract_name("My name is Alex Kumar")` → `"Alex Kumar"`; `"call me Sam"` → `"Sam"`.
- [ ] `extract_name("I am a student")`, `"I am tired"`, `"My name is"` (empty) → `None`.
- [ ] Trailing punctuation and over-long input (>60 chars, >4 words) are rejected or trimmed per documented rule.
- [ ] `/chat` saves the name only when memory is ON; reply differs when OFF.
- [ ] D2 expected-failure test passes and is un-marked.
**Verification:**
- [ ] Tests pass: `python -m unittest tests.test_intent -v` (table-driven cases, at least 12).
- [ ] Manual: "I am a student" after setting a name → name unchanged.
**Dependencies:** Task 2 (for the save path), Task 3 (flag handling)
**Files likely touched:** `core/intent.py`, `app.py`, `tests/test_intent.py`
**Estimated scope:** Small (3 files)

### [ ] Task 5: Ollama client hardening with visible errors (D4, D5, D12)
**Description:** Rewrite `core/llm.py` so failures are explicit and Stop actually stops generation. Config via env (`NEURAXAI_MODEL`, `OLLAMA_URL`), connect/read timeouts, status check, handling of `{"error":...}` lines, and closing the upstream response when the consumer disconnects. The route fetches the first chunk before replying so "Ollama offline" / "model not found" become a 503 JSON body, and the UI shows it.
**Acceptance criteria:**
- [ ] Ollama not running → `/chat` returns 503 `{"error": "Ollama is not reachable at …"}`; UI shows it in the bubble.
- [ ] Unknown model → 503/502 with the model name and the hint `ollama pull <model>`.
- [ ] Read timeout is configurable and defaults to something finite (e.g. connect 3s, read 120s).
- [ ] Closing the generator (client abort) closes the `requests` response (test with a fake response object recording `.close()`).
- [ ] `NEURAXAI_MODEL=foo` changes the model sent in the payload.
- [ ] `app.js` checks `response.ok`, reads the JSON error, and renders it.
**Verification:**
- [ ] Tests pass: `python -m unittest tests.test_llm -v` (mock `requests.post`; cover connection error, HTTP 404, error line mid-stream, normal stream, close-on-abort).
- [ ] Manual: stop Ollama → message → readable error; start Ollama → works; click Stop mid-answer and confirm via `ollama ps`/CPU that generation ends.
**Dependencies:** Task 1
**Files likely touched:** `core/llm.py`, `app.py`, `web/static/app.js`, `tests/test_llm.py`
**Estimated scope:** Medium (4 files)

### [ ] Task 6: Request validation and server hardening (D7, D8)
**Description:** Make `/chat` reject bad input with 4xx instead of 500, cap request size, and make debug mode opt-in. Bind explicitly to localhost.
**Acceptance criteria:**
- [ ] Non-JSON body → 400 (or 415) JSON error; JSON that isn't an object → 400; `message` not a string → 400; empty/whitespace message → 400 with `{"error": ...}` (replaces the current empty 200).
- [ ] `message` over a limit (e.g. 4000 chars) → 413 or 400; `MAX_CONTENT_LENGTH` set.
- [ ] `app.run(host="127.0.0.1", debug=os.getenv("NEURAXAI_DEBUG") == "1")`.
- [ ] The frontend does not send empty messages (already true) and shows validation errors via Task 5's path.
**Verification:**
- [ ] Tests pass: `python -m unittest tests.test_validation -v`
- [ ] Manual: `Invoke-RestMethod -Uri http://127.0.0.1:5000/chat -Method Post -ContentType 'application/json' -Body '{"message":123}'` → 400.
**Dependencies:** Task 5 (shared error shape)
**Files likely touched:** `app.py`, `tests/test_validation.py`
**Estimated scope:** Small (2 files)

### [ ] Task 7: Language detection module (Telugu + Roman Telugu)
**Description:** Move detection out of `app.py` into `core/language.py`. Keep the Telugu Unicode check; add keyword/pattern heuristics for Roman Telugu ("naa peru enti", "ante enti", …). Return a small enum/string and be conservative: unknown/short text → English.
**Acceptance criteria:**
- [ ] `detect_language("తెలుగులో చెప్పు")` → telugu; `"Python ante enti?"` → telugu (romanized); `"What is Python?"` → english; `""` → english.
- [ ] Mixed text with any Telugu script → telugu.
- [ ] Documented false-positive guard: a single ambiguous English word that is also a Telugu keyword (list in the module docstring) does not flip the language alone.
- [ ] `app.py` imports from `core.language`; old regex/func removed.
**Verification:**
- [ ] Tests pass: `python -m unittest tests.test_language -v` (≥15 table cases incl. the README example prompts).
- [ ] Manual: the README Telugu prompts produce a Telugu-language rule in the prompt (log or test the built prompt).
**Dependencies:** Task 1
**Files likely touched:** `core/language.py`, `app.py`, `tests/test_language.py`
**Estimated scope:** Small (3 files)

### [ ] Task 8: Deterministic intent shortcuts (D9)
**Description:** Extend `core/intent.py` with `classify(text, language) -> Intent` for no-LLM replies: greetings (case/punctuation tolerant, time-of-day), thanks, farewell, "what is your name"/identity, "what is my name". Replies exist in English and Telugu. `app.py` dispatches on the result so `chat()` shrinks to routing + LLM fallback.
**Acceptance criteria:**
- [ ] "Hi!", "HELLO", "hey there", "good morning", "thanks", "thank you!", "bye", "good night", "who are you" each resolve without calling the LLM (assert with a mock that `ask_llm_stream` is not called).
- [ ] "high school", "hello world program in python" do **not** match the greeting shortcut (full-message/anchored match only).
- [ ] Telugu equivalents return Telugu replies.
- [ ] Shortcut replies still save to history when memory is ON, and not when OFF.
- [ ] `chat()` in `app.py` is under ~60 lines after this task.
**Verification:**
- [ ] Tests pass: `python -m unittest tests.test_intent tests.test_chat_routes -v`
- [ ] Manual: send the README's greeting/thanks/bye/identity prompts; responses are immediate.
**Dependencies:** Task 4, Task 7
**Files likely touched:** `core/intent.py`, `app.py`, `tests/test_intent.py`, `tests/test_chat_routes.py`
**Estimated scope:** Medium (4 files)

### [ ] Task 9: Prompt builder with separated facts and history (D10)
**Description:** Replace the inline f-string in `chat()` with a pure `build_prompt(user_msg, language, intent_flags, facts, history)` in `core/prompt.py`. Separate `KNOWN FACTS` (e.g. user name) from `RECENT CONVERSATION`; support detail levels (brief default, "in detail", bullets, paragraph); add explicit uncertainty guidance; keep the README's identity rules.
**Acceptance criteria:**
- [ ] "Explain Python in detail" yields a prompt without the "Maximum 3 lines" rule; "in bullet points" keeps the 5-bullet rule; default stays brief.
- [ ] Stored name appears under facts only when memory is ON and a name exists.
- [ ] Memory OFF → prompt contains no facts and no history (assert by string search).
- [ ] History lines are delimited so a user message containing "Assistant:" or "FORMAT RULES:" cannot be mistaken for structure (e.g. each turn is quoted/indented; test with an injection string).
- [ ] `build_prompt` has no I/O and is covered by unit tests.
**Verification:**
- [ ] Tests pass: `python -m unittest tests.test_prompt -v`
- [ ] Manual: run the README example prompts against Ollama and eyeball answers; note results in the checkpoint log.
**Dependencies:** Task 3, Task 7, Task 8
**Files likely touched:** `core/prompt.py`, `app.py`, `tests/test_prompt.py`
**Estimated scope:** Small (3 files)

### [ ] Task 10: Safe streaming renderer, stop and error states (D11, D12)
**Description:** Replace the regex-to-HTML `formatAIResponse` with DOM construction: plain text via `textContent`, fenced code blocks as `<pre><code>` with a copy button attached by `addEventListener`. Handle an unclosed fence while streaming, and make Stop/finish/error states reset the button correctly.
**Acceptance criteria:**
- [ ] A reply containing `<img src=x onerror=alert(1)>` or `<script>` renders as visible text; nothing executes (no `innerHTML` with model text anywhere).
- [ ] Fenced code (```` ```python … ``` ````) renders as a code block with working Copy; a half-streamed fence doesn't break layout or flicker the whole message.
- [ ] Stop → button back to ➤, "Generation stopped" shown, next message works.
- [ ] Network/HTTP errors render as an error bubble (styled), not an empty one.
- [ ] No inline `onclick` remains in generated markup.
**Verification:**
- [ ] Tests pass: Python suite still green (`python -m unittest discover -s tests -v`).
- [ ] Manual checklist: XSS payload above; long code block copy; stop mid-stream then send again; Ollama offline error; Telugu text renders correctly; very long reply keeps autoscroll behaviour.
**Dependencies:** Task 5 (error format)
**Files likely touched:** `web/static/app.js`, `web/static/style.css`
**Estimated scope:** Small (2 files)

### ◆ Checkpoint A: v0.4.0 validated (after Tasks 1–10)
- [ ] All tests green locally and in CI.
- [ ] README's manual acceptance checklist fully ticked on the target Windows laptop with real Ollama.
- [ ] `data/` auto-created on a fresh clone; memory survives an app restart; memory OFF writes nothing.
- [ ] README updated: the v0.4.0 file list matches what is actually in the repo; "testing pending" removed.
- [ ] Tag `v0.4.0` created. **Review with human before Phase 2.**

---

## Phase 2: v0.5.0 — Memory that scales

### [ ] Task 11: SQLite storage with one-time JSON migration
**Description:** Add `core/db.py` (stdlib `sqlite3`) with tables `sessions`, `messages`, `facts`. Re-implement the memory functions on top of it, keeping the public function names. On first start, if `memory.json` exists and the DB is new, import it into a default session and copy the original to `memory.json.bak`.
**Acceptance criteria:**
- [ ] Fresh start creates the DB and schema (versioned with `PRAGMA user_version`).
- [ ] A fixture `memory.json` (facts + history) imports completely and idempotently (running twice doesn't duplicate).
- [ ] All Task 2/3 memory tests pass against the SQLite backend unchanged (same interface).
- [ ] Concurrent writes (threaded test) succeed; `data/*.db*` is gitignored.
**Verification:**
- [ ] Tests pass: `python -m unittest tests.test_db tests.test_memory -v`
- [ ] Manual: start v0.4.0 with real history, upgrade, confirm history is intact and `.bak` exists.
**Dependencies:** Checkpoint A
**Files likely touched:** `core/db.py`, `core/memory.py`, `.gitignore`, `tests/test_db.py`, `tests/fixtures/memory_v1.json`
**Estimated scope:** Medium (5 files)

### [ ] Task 12: Chat sessions (create / list / switch / delete)
**Description:** Vertical slice: backend endpoints (`GET/POST /sessions`, `DELETE /sessions/<id>`, `GET /sessions/<id>/messages`), `/chat` accepts `session_id`, history is scoped per session, and the page gets a sidebar with "New chat" and the session list.
**Acceptance criteria:**
- [ ] New chat starts with empty context; switching sessions loads that session's messages into the view and the next prompt uses only that session's history.
- [ ] Session title defaults to the first user message (truncated); rename is optional (can be deferred).
- [ ] Deleting a session removes its messages; facts remain.
- [ ] Unknown `session_id` → 404 JSON.
**Verification:**
- [ ] Tests pass: `python -m unittest tests.test_sessions -v`
- [ ] Manual: two sessions with different topics don't leak context; reload page restores the last session.
**Dependencies:** Task 11
**Files likely touched:** `app.py`, `core/memory.py`, `web/templates/index.html`, `web/static/app.js`, `web/static/style.css`
**Estimated scope:** Medium (5 files)

### [ ] Task 13: Editable facts and "forget me"
**Description:** Expose facts (name, plus free-form key/value) as a small "Memory" panel: list, edit, delete one, and "Delete all memory" with a confirm step. Backend `GET/PUT/DELETE /facts`, `DELETE /memory`.
**Acceptance criteria:**
- [ ] Editing the name in the panel changes what "what is my name" returns.
- [ ] "Delete all memory" removes facts, messages and sessions, asks for confirmation in the UI, and returns the app to a clean state.
- [ ] Memory toggle semantics unchanged (OFF doesn't read or write).
**Verification:**
- [ ] Tests pass: `python -m unittest tests.test_facts -v`
- [ ] Manual: edit, delete, wipe all; confirm DB rows are gone.
**Dependencies:** Task 11 (Task 12 for the UI shell; can share the panel layout)
**Files likely touched:** `app.py`, `core/memory.py`, `web/static/app.js`, `web/templates/index.html`, `tests/test_facts.py`
**Estimated scope:** Medium (5 files)

### [ ] Task 14: `/api/chat` migration and context budget
**Description:** Change `core/llm.py` to call Ollama `/api/chat` with a `system` message and role-tagged history instead of one concatenated prompt. Add a context budget (character/token estimate) that trims oldest turns first while always keeping the system message, facts, and the latest user turn.
**Acceptance criteria:**
- [ ] Payload to Ollama has `messages=[system, …history…, user]`; `build_prompt` is reshaped (or replaced by `build_messages`) with its tests updated.
- [ ] A 200-message session never produces a payload above the configured budget; the newest turns survive.
- [ ] Quality check: the README example prompts still follow format/language rules at least as well as before (record before/after in the checkpoint log).
- [ ] Task 5 error handling and abort-closing still work on the new endpoint.
**Verification:**
- [ ] Tests pass: `python -m unittest tests.test_prompt tests.test_llm -v`
- [ ] Manual: 30-turn conversation; early facts mentioned in first turns still behave sensibly; no truncation errors from Ollama.
**Dependencies:** Task 12 (history is per session), Task 9
**Files likely touched:** `core/llm.py`, `core/prompt.py`, `app.py`, `tests/test_prompt.py`, `tests/test_llm.py`
**Estimated scope:** Medium (5 files)

### [ ] Task 15: Rolling summary of old turns
**Description:** When a session exceeds the budget, summarize the oldest turns with the local model (non-streaming call) and store the summary on the session; inject it as a system-side "Conversation so far" block.
**Acceptance criteria:**
- [ ] Summary is generated only when the threshold is crossed, stored in the DB, and reused (not regenerated every turn).
- [ ] If summarization fails (Ollama error), chat still works using plain truncation.
- [ ] Summary text is stored per session and deleted with it; memory OFF never reads or writes it.
**Verification:**
- [ ] Tests pass: `python -m unittest tests.test_summary -v` (mock the summarizer call).
- [ ] Manual: long conversation; ask about something from the early part; check the summary row.
**Dependencies:** Task 14
**Files likely touched:** `core/memory.py`, `core/summary.py`, `app.py`, `tests/test_summary.py`
**Estimated scope:** Small–Medium (4 files)

### ◆ Checkpoint B: v0.5.0
- [ ] Upgrade path from a real v0.4.0 `memory.json` verified on the laptop; `.bak` exists.
- [ ] Sessions, facts panel, memory toggle all work together; wipe-all leaves no data.
- [ ] Quality comparison log (README prompt list) attached to the tag notes.
- [ ] Tag `v0.5.0`. **Review with human before Phase 3.**

---

## Phase 3: v0.6.0 — Tools and documents

### [ ] Task 16: Tool registry with permission levels, plus calculator
**Description:** First tool slice end to end. `core/tools/registry.py` defines a `Tool` (name, description, permission level `read`/`write`/`exec`, run function). Only `read` tools run automatically; anything else must be approved by the user in the UI (the approval path can be stubbed but the gate must exist and be tested). Implement `calculator` with an AST-based evaluator (no `eval`). "calculate 12*(3+4)" → tool result → natural reply. Every tool call is logged (name, args, result, approved?).
**Acceptance criteria:**
- [ ] Calculator handles `+ - * / ** %` and parentheses; rejects names, calls, attributes, huge exponents (`9**9**9`), and division by zero without crashing.
- [ ] A registered `exec`-level dummy tool is **refused** unless an approval flag from the UI is present (test).
- [ ] Tool calls are written to a log table/file; user can see the last calls in the UI or via an endpoint.
- [ ] Tool output is inserted into the prompt as clearly labelled untrusted data.
**Verification:**
- [ ] Tests pass: `python -m unittest tests.test_tools tests.test_calculator -v` (include an adversarial expression list).
- [ ] Manual: "calculate 12*(3+4)" → 84; "calculate __import__('os')" → refused.
**Dependencies:** Checkpoint B
**Files likely touched:** `core/tools/__init__.py`, `core/tools/registry.py`, `core/tools/calculator.py`, `app.py`, `tests/test_tools.py`
**Estimated scope:** Medium (5 files)

### [ ] Task 17: Date/time tool and tool routing
**Description:** Add `datetime` (read-level) and the router that decides when a tool runs. Start deterministic (regex/intent: "what time is it", "today's date", "calculate …"). Optionally, behind a flag, let the model propose a tool call as constrained JSON (`format: "json"`), validated against the registry; record how often Phi-3 gets it right.
**Acceptance criteria:**
- [ ] "What is the date today?" and Telugu equivalent answer from the system clock, not the model.
- [ ] Router never invokes a tool that isn't in the registry or whose arguments fail schema validation.
- [ ] If the model-chosen-tool flag is on, malformed JSON falls back to a normal chat reply (test with a mock returning junk).
- [ ] Measured tool-selection accuracy on ≥20 scripted prompts is recorded in `tasks/notes-tool-eval.md`.
**Verification:**
- [ ] Tests pass: `python -m unittest tests.test_router -v`
- [ ] Manual: run the 20-prompt script; save results.
**Dependencies:** Task 16
**Files likely touched:** `core/tools/datetime_tool.py`, `core/router.py`, `app.py`, `tests/test_router.py`
**Estimated scope:** Medium (4 files)

### [ ] Task 18: File upload with PDF/CSV/XLSX extraction
**Description:** Vertical slice for documents: an upload button, `POST /upload` saving to a sandboxed `data/uploads/` dir with size/type limits, and extractor read-tools (`pypdf`, stdlib `csv`, `openpyxl`) that return bounded text. The user can ask "summarize this file" and the extracted text goes into the prompt as untrusted data (truncated to the context budget; full RAG is v0.7).
**Acceptance criteria:**
- [ ] Only `.pdf .csv .xlsx .txt` accepted; max size (e.g. 10 MB) enforced; filenames sanitized (`secure_filename`); path traversal attempts (`../x`) rejected.
- [ ] Extraction returns text for a sample PDF, CSV, and XLSX in `tests/fixtures/`; encrypted/corrupt files return a clear error, not a 500.
- [ ] Extracted text is capped, and the prompt marks it as untrusted. A fixture PDF containing "ignore previous instructions…" does not change assistant identity rules (documented best-effort test with the mocked prompt builder).
- [ ] Uploads dir is gitignored and listed/deletable in the UI.
**Verification:**
- [ ] Tests pass: `python -m unittest tests.test_upload tests.test_extractors -v`
- [ ] Build: `pip install -r requirements.txt` adds only `pypdf` and `openpyxl`.
- [ ] Manual: upload each type, ask for a summary, confirm sensible output on the laptop.
**Dependencies:** Task 16 (registry/permissions), Task 14 (context budget)
**Files likely touched:** `app.py`, `core/files.py`, `core/tools/extractors.py`, `web/static/app.js`, `requirements.txt` (+ tests, fixtures)
**Estimated scope:** Large → split in two if it passes ~6 files: **18a** upload endpoint + CSV/TXT, **18b** PDF/XLSX extractors + UI list.

### ◆ Checkpoint C: v0.6.0 and re-plan
- [ ] All tests green; manual checklist for chat, sessions, memory, tools, uploads ticked on the laptop.
- [ ] Security pass: no tool runs without passing the registry; uploads can't escape `data/uploads/`; server still bound to localhost, debug off.
- [ ] Tool-selection accuracy numbers and model-quality notes written down.
- [ ] Tag `v0.6.0`. **Stop. Re-plan Phase 4 (RAG and later) using real measurements; decide whether to switch to a larger model first.**

---

## Phase 4: v0.7.0 → v1.0.0
Epics only; see the table in `tasks/plan.md`. Do not start before Checkpoint C.
