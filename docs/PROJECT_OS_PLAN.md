# Vasya Project OS Plan

Vasya Project OS is the product track that turns Vasya from a voice-first
desktop assistant into a cross-platform project operating layer: one local
dashboard for projects, tasks, status, Memory Center context, and safe
agent-backed actions.

The first interface is **Vasya Control Center**: a web dashboard served by the
local FastAPI backend and launched from the desktop shell. The floating avatar
stays valuable as a companion launcher and voice presence, while the richer
project experience moves into a larger window.

## Product Direction

- Show all active projects on the first dashboard.
- Answer voice and text questions such as "what is next?", "what is blocked?",
  and "open ai_pal".
- Start read-only, then add confirmed agent actions.
- Keep the backend local-first and reuse existing FastAPI, Memory Center, voice,
  Obsidian, GitHub, and Codex-adjacent workflows.
- Design for macOS first, but avoid PySide-only dashboard architecture so the
  same UI can work on Windows, Linux, and future mobile/web clients.

## Architecture Decisions

- Use `apps/api` as the local backend surface for project status and dashboard
  data.
- Build the dashboard as a web UI, not a PySide-only window.
- Keep the desktop avatar as a launcher, voice affordance, and lightweight
  status presence.
- Treat mutating actions as agent jobs with confirmation, audit output, and
  clear rollback/escape paths.
- Store the project registry as explicit local configuration first; infer only
  safe, read-only metadata from repositories.
- Distribute an empty application; keep projects, tasks, notes, histories, and
  connector configuration in a user-owned platform app-data directory.
- Treat Project OS as an aggregation and action layer, not the sole source of
  truth for every record.
- Preserve source identity, project mapping, last sync time, and connector
  capability on imported records.
- Add external sources read-only before enabling writes through the approval
  queue.

Detailed data boundary: `docs/adr/ADR-003-public-app-and-private-user-data.md`.


## OpenWorker-Inspired Additions

Keep Vasya distinct from generic AI coworker products: Vasya Project OS should
be a local, voice-aware project operating layer with Memory Center and
Codex-style repository workflows. The useful patterns to adopt are:

- native desktop shell supervising a local Python API server;
- web dashboard UI for dense project surfaces instead of expanding PySide
  dialogs;
- approval inbox for consequential actions such as shell commands, commits,
  pushes, messages, and calendar edits;
- action run history with request, plan, confirmation, command summary, result,
  and linked artifacts;
- connector adapter layer for GitHub, Codex, Obsidian, Calendar, Gmail/Notion
  later, and MCP-compatible tools;
- scheduled project runs such as morning project brief, weekly release status,
  CI/watch summaries, and stale-blocker checks;
- provider/profile settings for model routing by task type: chat, project
  summary, coding, cheap/fast utility calls, and local/offline mode.

Do not copy broad Slack-first coworker behavior or a large connector catalog
until the Project OS dashboard, action queue, and Codex bridge are useful for
one local user.

## Release Track

### v0.8.0: Vasya Control Center MVP

Goal: show one useful, read-only overview of all active projects.

- Project registry with project id, name, path, type, and priority.
- `GET /v1/projects/status` for a safe local status snapshot.
- First web dashboard with project cards.
- Cards show tasks/next action, high-level status, git branch, dirty state, and
  last commit when available.
- Voice/text command routes for "what is next by projects?" and "open project".

### v0.8.1: Project Detail

Goal: make one project page useful enough to replace ad hoc status checks.

- Project detail endpoint and page.
- Status, tasks, recent Memory Center context, latest digest, release notes, and
  local docs links.
- "What is next for this project?" summary.
- Project snapshot persisted as a local artifact for review and history.
- User-owned project registry stored outside the application bundle.
- Selected read-only planning sources, beginning with Eva-synchronized Apple
  Reminders and Apple Calendar on macOS.

### v0.8.2: Agent Action Queue And Approval Inbox

Goal: safely introduce actions without letting voice mutate repositories
directly.

- Action model for `read_status`, `run_tests`, `create_task`, `prepare_commit`,
  and `push`.
- Confirmation layer and approval inbox for every mutating action.
- Dry-run output before commit/push.
- Audit log for requested action, plan, confirmation, command summary, result,
  and linked artifacts.

### v0.8.3: Codex Bridge

Goal: connect Project OS to the existing Codex working style.

- Create or open a Codex task for a selected project.
- Pass project context and requested action to Codex.
- Show task status and final summary in the dashboard.
- Keep commit/push behind explicit confirmation.

### v0.8.4: Project Automations And Run History

Goal: make recurring project operations trustworthy and reviewable.

- Scheduled morning project brief and weekly release status.
- Watch summaries for CI, blockers, and stale project tasks.
- Run history visible from the dashboard with transcript, decisions, commands,
  outputs, and artifacts.
- Paused approval requests stay in the inbox instead of acting unattended.

### v0.8.5: Connector And Model Profiles

Goal: add integrations without turning Project OS into a brittle monolith.

- Expand connector adapters for GitHub, Codex, Obsidian, Calendar, and later
  Gmail/Notion/MCP tools.
- Per-connector capability and permission metadata.
- Model profiles for project summary, coding/task planning, cheap utility work,
  and local/offline mode.

### v0.9.0: Creative Studio Dashboard

Goal: add the first dedicated dashboard for the future AI creative studio.

- Creative projects, assets, scripts, generation queues, and review states.
- Voice navigation across creative work.
- Reuse the same project registry, status cards, and action queue primitives.

## Personal Planning Sources

For the maintainer workflow, Eva remains the convenient task and calendar entry
surface. Project OS should consume those records instead of requiring duplicate
entry.

- macOS first: read selected Eva-synchronized Apple Reminders lists and Apple
  Calendar calendars through EventKit;
- index normalized records in Memory Center with provenance;
- keep the connector opt-in and read-only until conflict and approval semantics
  exist;
- never read Eva's private application database;
- treat Eva archive import as a later discovery item for notes or other records
  not exposed through Apple system services.

## MVP Task List

Completed:
- Task 1: Project Registry Foundation.
- Task 2: Read-Only Project Status Endpoint.
- Task 3: Vasya Control Center Shell.

### Task 1: Project Registry Foundation

Description: Add local project metadata and a service that returns configured
projects without scanning the whole machine.

Acceptance criteria:
- `ai_pal`, `portfolio`, `ai_twin`, `ai_predictor`, `document_ops_ai`, and
  `onboardica` can be represented as opt-in personal presets.
- Installed users get an empty default registry until they add their own
  projects.
- Missing project paths are reported as warnings, not crashes.
- Tests cover valid projects and missing paths.

Verification:
- `.venv/bin/python -m unittest tests.test_project_registry`
- `.venv/bin/python -m compileall config services tests`

Dependencies: None.

Likely files:
- `config/projects.py`
- `services/project_registry_service.py`
- `tests/test_project_registry.py`

Estimated scope: Medium.

### Task 2: Read-Only Project Status Endpoint

Description: Expose a FastAPI route that summarizes each registered project.

Acceptance criteria:
- `GET /v1/projects/status` returns project id, name, path status, branch,
  dirty state, latest commit, and next action placeholder.
- The endpoint never mutates repositories.
- Errors are represented per project instead of failing the whole response.

Verification:
- `.venv/bin/python -m unittest tests.test_api_project_routes`
- `.venv/bin/python -m unittest discover tests`

Dependencies: Task 1.

Likely files:
- `apps/api/routes/projects.py`
- `apps/api/schemas.py`
- `apps/api/main.py`
- `tests/test_api_project_routes.py`

Estimated scope: Medium.

### Task 3: Vasya Control Center Shell

Description: Add the first local web dashboard shell for all projects.

Acceptance criteria:
- The first screen is the all-projects dashboard, not a landing page.
- Cards are dense, scan-friendly, and show project status/next action.
- The UI consumes `/v1/projects/status`.
- The dashboard can be run locally by a documented command.

Verification:
- `.venv/bin/python -m unittest tests.test_control_center_routes tests.test_api_project_routes`
- Manual browser smoke for desktop and narrow viewport at `/control-center`.

Local run:
- `VASYA_API_REQUIRE_AUTH=false COSYVOICE_PYTHON= .venv/bin/python -m uvicorn apps.api.main:app --reload`
- Open `http://127.0.0.1:8000/control-center`.
- With API auth enabled, store the local API token in the dashboard token field.

Dependencies: Task 2.

Likely files:
- `apps/control_center/`
- `apps/api/routes/control_center.py`
- `apps/api/main.py`
- `tests/test_control_center_routes.py`
- `docs/PROJECT_OS_PLAN.md`

Estimated scope: Medium.

### Task 4: Voice Navigation Commands

Description: Route voice/text commands to project dashboard navigation and
read-only status summaries.

Acceptance criteria:
- "What is next by projects?" returns a concise project summary.
- "Open ai_pal" selects the project dashboard/detail target.
- Commands do not start mutating actions.

Verification:
- `.venv/bin/python -m unittest tests.test_project_os_commands`
- Existing voice/orchestrator tests remain green.

Dependencies: Tasks 1 and 2.

Likely files:
- `core/models.py`
- `core/orchestrator.py`
- `services/project_registry_service.py`
- `tests/test_project_os_commands.py`

Estimated scope: Medium.

### Foundation Gate Before Task 5

Before implementing mutating agent actions, complete the ordered foundation
slices in `docs/EXECUTION_PLAN.md`:

- platform app-data paths and migration;
- user-owned project registry;
- backup and restore;
- read-only connector contract;
- Eva ingestion through Apple Reminders and Apple Calendar;
- unified project detail read model;
- public macOS release foundation.

The existing task numbers below are retained to avoid rewriting historical
references. Their execution order is governed by the checklist.

### Task 5: Confirmed Agent Action Queue And Approval Inbox

Description: Add the first action queue and approval inbox contract for project
operations without executing dangerous actions directly from voice.

Acceptance criteria:
- Read-only actions can run immediately.
- Mutating actions require explicit confirmation.
- Commit/push actions show a dry-run summary before execution.
- Every action writes an audit record with request, plan, confirmation, result,
  and linked artifacts.
- Paused confirmations are visible in an approval inbox.

Verification:
- `.venv/bin/python -m unittest tests.test_project_action_queue`
- Manual dry-run for test/commit action.

Dependencies: Task 2.

Likely files:
- `services/project_action_service.py`
- `repositories/project_action_repository.py`
- `apps/api/routes/project_actions.py`
- `tests/test_project_action_queue.py`

Estimated scope: Medium.

### Task 6: Project Run History

Description: Persist and expose reviewable records for agent and automation
runs so users can trust what Vasya did and why.

Acceptance criteria:
- Run records include request text, plan summary, confirmation state, command
  summary, result status, timestamps, and artifact links.
- The API can list recent runs and filter by project id.
- Failed runs preserve enough context for debugging without storing secrets.

Verification:
- `.venv/bin/python -m unittest tests.test_project_run_history`
- Existing project action tests remain green.

Dependencies: Task 5.

Likely files:
- `repositories/project_run_repository.py`
- `services/project_run_history_service.py`
- `apps/api/routes/project_runs.py`
- `tests/test_project_run_history.py`

Estimated scope: Medium.

### Task 7: Scheduled Project Briefs

Description: Add recurring read-only project runs for morning/weekly summaries
without executing mutating actions unattended.

Acceptance criteria:
- Morning project brief summarizes status, blockers, dirty repos, and next
  actions.
- Weekly release status highlights readiness, open risks, and stale work.
- Any action requiring mutation is parked in the approval inbox.

Verification:
- `.venv/bin/python -m unittest tests.test_project_automations`
- Manual local smoke for one scheduled read-only brief.

Dependencies: Tasks 2 and 6.

Likely files:
- `services/project_automation_service.py`
- `tests/test_project_automations.py`
- `docs/PROJECT_OS_PLAN.md`

Estimated scope: Medium.

### Task 8: Connector Adapter Contract

Description: Define a small connector boundary so Project OS can add GitHub,
Codex, Obsidian, Calendar, Gmail/Notion, and MCP-compatible tools gradually.

Acceptance criteria:
- Connectors declare id, display name, capabilities, auth/setup status, and
  whether each operation is read-only or mutating.
- The dashboard can show connector readiness without invoking heavy workflows.
- Mutating connector operations route through the action queue.

Verification:
- `.venv/bin/python -m unittest tests.test_project_connectors`
- Existing Memory Center and GitHub/Obsidian tests remain green.

Dependencies: Task 2 and the app-data/user-registry foundation. Mutating capabilities also depend on Task 5.

Likely files:
- `services/project_connector_service.py`
- `interfaces/project_connectors.py`
- `tests/test_project_connectors.py`

Estimated scope: Medium.

### Task 9: Model Profiles For Project OS

Description: Add explicit model/profile selection for Project OS workloads so
summary, coding, cheap utility, and local/offline tasks can use different
providers safely.

Acceptance criteria:
- Profiles are configured locally and default conservatively.
- Project status/dashboard paths still work without cloud model keys.
- The selected profile is recorded in run history for agent actions.

Verification:
- `.venv/bin/python -m unittest tests.test_project_model_profiles`
- Settings tests remain green.

Dependencies: Tasks 5 and 6.

Likely files:
- `config/settings.py`
- `services/project_model_profile_service.py`
- `tests/test_project_model_profiles.py`

Estimated scope: Medium.

## Not Doing Yet

- Direct reads from Eva's private on-device storage.
- Two-way Eva/Reminders writes before connector conflicts and approval behavior
  are designed.
- Direct commit/push from a single voice command without confirmation.
- Slack-first coworker mode.
- A large 25+ connector catalog before the adapter boundary is proven.
- Browser automation as a default project action.
- Replacing the avatar widget.
- Building a full IDE inside Vasya.
- Cross-platform installers for Project OS before the macOS artifact track is
  repeatable.
- Creative Studio implementation before the all-projects dashboard works.

## Risks

- The dashboard becomes a decorative status page rather than an operational
  tool. Mitigation: prioritize next actions and blockers on every card.
- Voice commands mutate repositories accidentally. Mitigation: read-only first,
  confirmation layer before any write action.
- Project metadata becomes implicit and fragile. Mitigation: start with explicit
  local registry configuration.
- The UI stack adds packaging complexity. Mitigation: keep the dashboard local
  and web-based, then package once the macOS release path is stable.

## Open Questions

- How should Codex task handoff be represented in the dashboard: embedded
  status, link-out, or both?
- Which Eva record types beyond Reminders and Calendar are present in its backup
  archive, and is that format stable enough for an optional importer?

## Execution Order

The strict current sequence, statuses, completion checks, and release gates live
in `docs/EXECUTION_PLAN.md`. This document owns feature architecture and
acceptance detail; it must not become a second active queue.
