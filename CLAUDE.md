# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Read [AGENTS.md](AGENTS.md) first — it's the authoritative, up-to-date doc (commands, architecture, data model/ownership rules, API endpoint table, leaderboard/chat protocols, deployment, quirks, conventions). This file only adds Claude-Code-specific notes.

## Claude Code specifics

- Skills live in `.agents/skills/` (django-patterns, frontend-design, ui-ux-pro-max, vercel-react-best-practices, web-design-guidelines, data-visualization) — consult the relevant one for UI or Django pattern work before writing from scratch.
- Custom subagents live in `.claude/agents/` (`django-backend`, `frontend`, `ux-ui`, `verifier`, `code-reviewer`, `security-auditor`), each pinned to a model suited to its role — delegate matching work to them rather than doing everything in the main thread. A `PostToolUse` hook in `.claude/settings.json` reminds about the `frontend/dist` rebuild (see below) after any `frontend/src/` edit, but that's a backstop, not a substitute for actually doing it.
- The repo is deployed (PythonAnywhere) from `frontend/dist`, which is **committed, not built on the server**. If you touch anything under `frontend/src/`, run `cd frontend && npm run build` and include the resulting `frontend/dist/` changes in the same commit — otherwise the next deploy ships stale JS/CSS with no error to signal it.
- Before changing anything in `gym/api_views.py` that touches `WorkoutDay`, `DayPreset`, `WorkoutExercise`, or `WorkoutSet`, re-read the "Data model & ownership" section in AGENTS.md — the user-scoping rules there are security-relevant (cross-user data leakage), not just style.
- A passing `npm run build` and green test suite do **not** catch layout regressions (see the flex `min-width` quirk in AGENTS.md — a real bug shipped once this way). For any UI change, drive the app with a headless browser (Playwright is available; see the project's dev-server ports in AGENTS.md) and screenshot both a desktop and a 375px-wide mobile viewport before calling the task done — don't rely on reading the CSS and reasoning about it.
