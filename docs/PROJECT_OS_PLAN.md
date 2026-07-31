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

### v0.8.2: Agent Action Queue

Goal: safely introduce actions without letting voice mutate repositories
directly.

- Action model for `read_status`, `run_tests`, `create_task`, `prepare_commit`,
  and `push`.
- Confirmation layer for every mutating action.
- Dry-run output before commit/push.
- Audit log for requested action, confirmation, command summary, and result.

### v0.8.3: Codex Bridge

Goal: connect Project OS to the existing Codex working style.

- Create or open a Codex task for a selected project.
- Pass project context and requested action to Codex.
- Show task status and final summary in the dashboard.
- Keep commit/push behind explicit confirmation.

### v0.9.0: Creative Studio Dashboard

Goal: add the first dedicated dashboard for the future AI creative studio.

- Creative projects, assets, scripts, generation queues, and review states.
- Voice navigation across creative work.
- Reuse the same project registry, status cards, and action queue primitives.

## MVP Task List

Completed:
- Task 1: Project Registry Foundation.

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
- Frontend build/test command once the web stack is selected.
- Manual browser smoke for desktop and narrow viewport.

Dependencies: Task 2.

Likely files:
- `apps/control_center/`
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

### Task 5: Confirmed Agent Action Queue

Description: Add the first action queue contract for project operations without
executing dangerous actions directly from voice.

Acceptance criteria:
- Read-only actions can run immediately.
- Mutating actions require explicit confirmation.
- Commit/push actions show a dry-run summary before execution.
- Every action writes an audit record.

Verification:
- `.venv/bin/python -m unittest tests.test_project_action_queue`
- Manual dry-run for test/commit action.

Dependencies: Task 2.

Likely files:
- `services/project_action_service.py`
- `repositories/project_action_repository.py`
- `tests/test_project_action_queue.py`

Estimated scope: Medium.

## Not Doing Yet

- Direct commit/push from a single voice command without confirmation.
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

- Which frontend stack should power `apps/control_center`?
- Should project registry live in `.env`, a JSON file under `storage/`, or a
  tracked default config with local overrides?
- How should Codex task handoff be represented in the dashboard: embedded
  status, link-out, or both?
