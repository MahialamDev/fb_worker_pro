# FB Worker Pro - AI Project Analyzer

## Purpose

This file is the first document an AI coding assistant must read before changing
this project. It describes the current project shape, important invariants, and
the required workflow for every user request.

The durable task history is maintained separately in
[AI_MEMORY.md](./AI_MEMORY.md). Read both files before starting work.

## Project Overview

- **Application type:** Windows desktop automation application.
- **Language/runtime:** Python with Tkinter.
- **Entry point:** `main.py`.
- **UI:** `ui/main_window.py`.
- **Services:** `services/`.
- **Android automation dependency:** LDPlayer and its console tooling.
- **Bundled app:** `apps/fblite.apk`.
- **Configuration:** `config.json` is the active configuration file. `config.txt`
  may contain local or legacy settings.
- **Input data:** `name_list.txt`.

## Current Architecture

1. `main.py` creates the Tkinter root and starts `MainWindow`.
2. `MainWindow` loads `config.json`, creates service objects, builds the UI,
   handles configuration persistence, and forwards UI events.
3. `AutomationService` manages a sequential coordinator thread and coordinates
   LDPlayer launch, boot checks, and window arrangement. Facebook Lite opening
   runs independently in a per-instance background thread. When proxy is
   enabled, that worker first clears all data for the configured Facebook Lite
   package, then opens `com.scheler.superproxy`, fills its UI from the
   configured proxy fields, saves the profile, and finally opens Facebook Lite.
4. `WorkerEngine` provides a separate single-workflow engine for launching an
   instance, waiting for boot, and opening Facebook Lite.
5. `LDPlayerService` owns emulator/console operations.
6. `ProxyService`, `ApiService`, and `SystemService` encapsulate related
   integrations and defaults.
7. `ApiService.search_country()` calls the user-configured public API
   `/getnum` endpoint with the configured range and updates the UI country from
   the response. This is an explicit search action because the documented
   endpoint allocates a number.

Preserve these service boundaries unless the user explicitly requests an
architectural refactor. UI code should not directly implement emulator or API
operations.

## Working Rules

- Read `AI_MEMORY.md`, relevant source files, and configuration structure before
  editing.
- Search for existing helpers and call sites before adding new behavior.
- Keep changes surgical and preserve existing UI labels, callbacks, and service
  contracts unless the request requires a behavior change.
- Never copy passwords, proxy credentials, API keys, tokens, license secrets, or
  other sensitive configuration values into documentation, logs, commits, or
  memory. Redact them as `[REDACTED]`.
- Treat `config.json`, `config.txt`, `name_list.txt`, APKs, and generated
  `__pycache__` files as potentially environment-specific. Do not rewrite or
  delete them without a clear reason.
- Use Windows-compatible paths and commands for this workspace.
- Make errors visible through the existing logging/UI patterns. Do not silently
  swallow exceptions or add broad fallback behavior without documenting why.
- Keep user-facing language and existing Bengali/English terminology consistent.
- Do not add dependencies unless required. If dependencies change, update the
  relevant manifest/documentation and validate installation separately.

## Required Workflow For Every Request

1. **Understand:** Read this file and `AI_MEMORY.md`; identify the exact
   requested outcome and affected files.
2. **Inspect:** Read the relevant implementation and search for callers,
   configuration keys, tests, and existing patterns.
3. **Plan:** State the smallest complete change internally before editing.
4. **Implement:** Make the change with the repository's existing style.
5. **Validate:** Run the smallest relevant syntax check, test, or smoke command.
   Report commands that could not run and why.
6. **Review:** Check for regressions, missing surfaces, sensitive data leakage,
   and unintended file changes.
7. **Record:** Append a concise entry to `AI_MEMORY.md` describing the request,
   files changed, validation, and any decisions or follow-up work.

## Safe Validation Baseline

From the project root, the basic smoke command is:

```powershell
python main.py
```

Only run it when a desktop UI launch is appropriate. For source-only changes,
prefer a non-interactive syntax check such as:

```powershell
python -m compileall main.py services ui
```

Do not claim that a full automation flow was validated unless LDPlayer and all
required external services were actually available.

## Known Risk Areas

- Tkinter callbacks and background threads must not be changed casually; UI
  updates from worker threads can introduce race conditions.
- `AutomationService` starts one daemon coordinator thread. It waits only for
  each requested LDPlayer instance to boot before starting the next; app opening
  and later work must not block other instances.
- `LDPlayerService.arrange_windows()` uses the Windows API to place visible
  LDPlayer windows in a four-column portrait grid. The preferred size is
  400x700 with a 10px gap; for more rows, dimensions scale down uniformly to
  fit the screen. There is no four-window limit: instances 1-4 use row one,
  5-8 use row two, and later instances continue on further rows. Unused slots
  remain empty. Placement runs continuously from launch until the window
  appears, so each instance is positioned while loading. Window slots are
  assigned in detection/launch order. Window titles must contain `LDPlayer`
  for automatic placement. Window arrangement failure must not stop the launch
  sequence.
- Configuration is loaded with relative paths, so the application should be
  launched from the project root.
- External emulator/API/proxy behavior cannot be reliably tested offline.
- Configuration persistence can expose secrets; redact output and avoid logging
  secret-bearing fields.
- Super Proxy credentials must come from the existing configuration/UI fields.
  Never hardcode or log raw proxy credentials. UI automation errors must be
  reported explicitly and must not expose sensitive input.
- Public API URL, header name, header key, and range have documented
  non-secret defaults in `ApiService`; they remain editable in the UI. The
  header key must come from configuration/UI or the `FB_WORKER_NEZ_KEY`
  environment variable and must never be hardcoded. When set, the environment
  variable takes precedence over any local config value. API errors must be
  shown explicitly; do not silently select a fallback country.
- The proxy username may contain a region marker such as `__cr.us`. During
  Super Proxy setup, that two-letter suffix is replaced with the ISO-like
  code for the selected API country. Keep the username template in the UI;
  never hardcode the credential.
- Pressing Enter or leaving the range field searches the configured API. A
  successful live-access lookup now runs automatically as the range changes;
  it does not allocate a number. The result updates the selected country and
  rewrites only the `__cr.xx` region part of the configured proxy username.
- Selecting a country in the UI immediately rewrites the proxy username region
  and persists the current configuration.
- Custom range-to-country-code mappings are editable as JSON, for example
  `{"26134":"cm"}`. Use only provider-confirmed ranges; do not invent
  provider ranges. The bundled
  [country calling-code dataset](./data/country_calling_codes.json) is an
  offline fallback for international calling-code prefixes, not a replacement
  for provider-specific ranges. Range matching normalizes an optional trailing
  `XXX` and otherwise requires an exact digit-for-digit match.
- `/liveaccess` is the source of truth for exact range, country, and
  `country_code`. `/console` is only a global statistics endpoint according to
  the current provider documentation; it must not be parsed as a range feed.
- Facebook Lite data clearing must be confirmed by Android's `pm clear`
  response before the Super Proxy step starts. A failed clear is an explicit
  workflow error; do not proceed as if the reset succeeded.

## Memory Maintenance Contract

`AI_MEMORY.md` is a compact operational record, not a transcript. After each
meaningful user request, update it with:

- date and short request summary;
- interpretation/decision made;
- files changed;
- validation commands and result;
- unresolved risks or next steps.

Keep entries factual, concise, and free of secrets. If an old entry becomes
wrong, add a correction entry instead of silently rewriting history.
