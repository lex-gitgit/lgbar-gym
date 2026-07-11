# Gym Logger — AGENTS.md

A private, login-gated gym-tracking app for a small friend group (~4-6 people, not public signup). Accounts are hand-provisioned by the owner — see "Adding users" below.

## Quick start
```sh
# Backend (Django) — from repo root
python manage.py runserver         # dev server on :8000
python manage.py test gym          # run all 70 tests
python manage.py test gym.tests.YourTestClass   # single test class

# Frontend (React + Vite) — in another terminal
cd frontend && npm run dev         # dev server on :5173, proxies /api -> :8000
```

- Python 3.12, Django 5.2, DRF, SQLite (WAL mode enabled — see Quirks). Dependencies are pinned in `requirements.txt` — `pip install -r requirements.txt`.
- Node.js 22 + npm, React 18, Vite 6, React Router 6.
- Demo account: `user` / `1234` (seeded by migration `0002_seed_data`). Owns whatever workout history existed before the multi-user migration.

## Adding users

No signup flow exists by design — the owner provisions each friend directly:
```sh
python manage.py add_friend <username> <password>
```
Creates a normal Django `User`. Each account's data (workouts, presets) is fully isolated from every other account — see "Data model & ownership" below. Errors cleanly if the username already exists.

## Architecture

Two-tier app, single-origin in production: Django REST backend + React SPA, session-cookie auth (DRF `SessionAuthentication` + `IsAuthenticated` by default — every endpoint requires login unless explicitly marked `AllowAny`).

**Backend** (`gym/` app, `helloworld/` project config):
- `gym/api_views.py` — every endpoint, function-based with `@api_view` (no ViewSets, no DRF routers). This is the only view layer — **the old template-based `gym/views.py` and `gym/templates/gym/` were deleted**; don't recreate them.
- `gym/serializers.py` — DRF serializers, used for GET/response output only. POST/PUT bodies are read manually via `request.data.get(...)`, not validated through input serializers — match this pattern for new endpoints rather than introducing serializer-based validation halfway.
- `gym/models.py` — `Exercise`, `DayPreset`, `DayPresetExercise`, `WorkoutDay`, `WorkoutExercise`, `WorkoutSet`, `ChatMessage`.
- `gym/apps.py` — `GymConfig.ready()` wires a `connection_created` signal to force SQLite into WAL mode on every connection.
- `gym/management/commands/` — `add_friend.py`, `seed_workouts.py` (seeds demo Push/Pull/Legs history for a given `--user`, with `--clear` scoped to that user only).

**Frontend** (`frontend/src/`):
- Pages (`src/pages/`): Login, Dashboard, Exercises, DayCreate, DayDetail, PresetForm, PresetDetail, Leaderboard, Chat.
- Components (`src/components/`): Sidebar, MobileTopBar, FlashMessages, Navbar.
- `api.js` — single fetch wrapper for all API calls (JSON body, CSRF header from cookie, redirects to `/` on 401/403 — except `/me/`, whose failure is handled locally by `App.jsx`'s own auth check, to avoid a reload loop for logged-out visitors).
- `index.css` — all styles; dark/light theme via `data-theme` attribute + `localStorage`. No CSS framework/modules — reuse existing classes (`.card`, `.analytics-pr-list`/`.analytics-pr-row`, `.page-header`, `.tabs`/`.tab`, `.empty-state`, `.btn*`) before inventing new ones.

## Data model & ownership

`WorkoutDay` and `DayPreset` each have a `user` FK (`on_delete=CASCADE`). `Exercise` is a **shared global catalog** — not owned by any user — because the leaderboard depends on everyone logging against the same exercise names. `DayPresetExercise` and `WorkoutExercise`/`WorkoutSet` have no direct `user` field; their ownership is derived through the chain (`workout_day__user`, `workout_exercise__workout_day__user`).

**Every API view must filter/scope by `request.user`.** For direct children of `WorkoutDay`/`DayPreset`, filter on the FK directly (`user=request.user`). For grandchildren (`WorkoutExercise`, `WorkoutSet`), filter through the derived chain — it's easy to forget this on endpoints whose URL doesn't include a day id (e.g. `set_add`, `set_delete` take only `we_id`/`set_id`). `DayPreset.name` is unique **per user**, not globally (`UniqueConstraint(fields=["user", "name"])`) — creates/updates must pre-check for a duplicate name under that user and return 400, since letting the DB constraint fire produces an ugly 500.

`gym/tests.py` has a dedicated `UserScopingTests` class that exists specifically to catch regressions here (one user can't read/write another's days, presets, exercises-within-days, or sets — verified via 404s and unchanged-state assertions). Any new user-owned data or endpoint should get equivalent coverage there.

## API endpoints (all under `/api/`, all require login except `csrf`/`login`)
| Method | Path | Notes |
|--------|------|-------|
| GET    | `/api/csrf/` | `AllowAny`; primes the CSRF cookie |
| POST   | `/api/login/` | `AllowAny`; session auth |
| POST   | `/api/logout/` | |
| GET    | `/api/me/` | Current user; used by frontend to probe auth state on load |
| GET/POST | `/api/exercises/` | List (filters: `search`, `body_part`) / create. Global catalog, not user-scoped |
| DELETE | `/api/exercises/<id>/` | **Blocked (400)** if the exercise is referenced by any `WorkoutExercise` or `DayPresetExercise` — anyone's, not just the requester's, since the catalog is shared |
| GET/POST | `/api/days/` | List (own days, 20 most recent) / create |
| GET/DELETE | `/api/days/<id>/` | Detail / delete (own only, else 404) |
| POST   | `/api/days/<id>/add-exercise/` | |
| DELETE | `/api/days/<id>/remove-exercise/<we_id>/` | |
| POST   | `/api/sets/<we_id>/add/` | |
| DELETE | `/api/sets/<id>/delete/` | |
| GET/POST | `/api/presets/` | List (own) / create (400 on duplicate name for that user) |
| GET/PUT/DELETE | `/api/presets/<id>/` | |
| GET    | `/api/leaderboard/` | See "Leaderboard" below |
| GET    | `/api/leaderboard/exercise/<exercise_id>/` | Per-exercise PR ranking; 404 if the exercise doesn't exist |
| GET/POST | `/api/chat/` | See "Chat" below |

## Leaderboard

`gym/api_views.py::leaderboard` computes four boards from existing `WorkoutSet`/`WorkoutDay` data — no dedicated leaderboard model:
- **Consistency** — `week_count`/`month_count`: workouts logged this ISO week (Monday-start, matching the Dashboard's own `startOfWeek()`) and this calendar month. Primary sort key for the response.
- **Volume** — `week_volume_kg`: `Σ weight × reps` for sets logged this week, normalized to kg (`LB_TO_KG = Decimal("0.453592")`).
- **Big lifts** — `prs`: best-ever estimated 1RM (Epley: `weight_kg × (1 + reps/30)`) per user per lift in `BIG_LIFTS = ["Bench Press", "Squat", "Deadlift", "Overhead Press"]`. A user with no logged sets for a lift simply has no key for it in `prs` — the frontend filters accordingly.
- **Streaks** — `streak_weeks`: consecutive weeks (counting back from the current week) with ≥1 workout; stops at the first gap.
- **By Exercise** — a fifth, separate board (`leaderboard_exercise`, own endpoint, not part of the four above): pick any exercise from the full catalog and rank everyone who's logged it by best e1RM. Reuses `_best_prs(exercise_ids, user_ids)`, the same helper the Big Lifts board calls with `BIG_LIFTS` resolved to ids — extend `_best_prs`, don't duplicate its Epley/unit-conversion logic, if you add another PR-based view.

Superusers and inactive users are excluded from all boards. Frontend (`Leaderboard.jsx`) fetches the four-board payload once and derives per-tab sort order client-side; the "By Exercise" tab is the exception — it makes its own request per exercise selected (`ExerciseBoard` sub-component), since the exercise list is large and picking one is user-driven.

## Chat

Single shared room (not per-DM), polling-based — deliberately not WebSockets/Django Channels, which would be disproportionate infra for ~6 users. `ChatMessage.Meta.ordering = ["id"]` (auto-increment doubles as chronological order, immune to clock skew). Protocol: `GET /api/chat/` with no params returns the latest 50 (ascending); `GET /api/chat/?after=<id>` returns everything with `id > after`, capped at 200. `Chat.jsx` polls every 5s via `setInterval` (cleaned up on unmount — required, since React 18 StrictMode double-mounts effects in dev) and dedupes incoming messages by id (a poll and the sender's own POST response can otherwise double-deliver one message).

## Backups

```sh
python manage.py backup_db [--keep N]   # default N=14
```
Snapshots the live SQLite DB into `backups/` (gitignored — contains real user data) using Python's `sqlite3.Connection.backup()` API rather than a plain file copy. This matters because of WAL mode (see Quirks): recent writes can still be sitting in the `-wal` file rather than the main `.sqlite3` file, so a naive `cp` can silently miss them or copy a torn/inconsistent snapshot. The backup API produces a consistent, complete copy safely, even while the app is live and being written to. Prunes to the `N` most recent snapshots each run (default 14).

**This has no automatic schedule — someone has to trigger it.** On PythonAnywhere, wire it up under the **Tasks** tab (free tier gets one daily scheduled task): command `workon gymenv && cd ~/lgbar-gym && python manage.py backup_db`. There's no off-site copy — it's local to the same disk as the live DB, which protects against app-level data loss (bad migration, bug that wipes rows) but not disk-level loss. Periodically pulling a `backups/*.sqlite3` file down manually is the current off-site strategy; there's no automation for that yet.

## Deployment

Live on PythonAnywhere's free tier (persistent disk — required, since the app uses SQLite as a single on-disk file; ephemeral-filesystem PaaS free tiers, e.g. Render/Railway/Fly without a paid volume, would wipe the DB on every redeploy). Single-origin: Django serves the API **and** the built React app.

- **`requirements.txt`** — pinned deps including `whitenoise` (serves `frontend/dist` static assets) and `gunicorn` (not used by PythonAnywhere's WSGI setup, but present for portability to a VPS).
- **`helloworld/settings.py`** — `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS` all read from env vars with dev-safe defaults (see `.env.example`). When `DEBUG=False`, secure cookie flags and `SECURE_PROXY_SSL_HEADER` kick in automatically.
- **`frontend/vite.config.js`** — `base: "/static/"` in production builds (so asset URLs resolve under Django's `STATIC_URL`), `base: "/"` in dev.
- **`helloworld/urls.py`** — a catch-all `re_path` serves `frontend/dist/index.html` for any path not under `api/`, `admin/`, or `static/`, so React Router deep-links survive a page refresh.
- **`frontend/dist/` is committed** (not gitignored) — the deploy host never runs `npm install`/`npm run build`; you build locally and push the built output. **After any frontend change: `cd frontend && npm run build` before committing**, or the live site serves stale JS/CSS.
- Deploying an update: push to GitHub, then on the server `git pull && python manage.py migrate && python manage.py collectstatic --noinput`, then **Reload** the web app from the PythonAnywhere Web tab (code changes don't take effect until the process restarts).

## Important quirks

- **`0 or -1` bug, fixed**: `aggregate(...)["order__max"] or -1` treats order `0` as falsy. `day_add_exercise` uses an explicit `is None` check; `set_add`'s `or 0` pattern is safe only because `set_number` starts at 1. Keep this in mind for any new "next sequence number" logic.
- **WAL mode is on** (`gym/apps.py`) — smooths concurrent reads (chat polling) against writes. Produces `db.sqlite3-wal`/`-shm` sidecar files (gitignored); harmless, no action needed.
- **Seed data**: migration `0002_seed_data` creates 36 exercises + the `user`/`1234` account; `0003`/`0004` add body-part categorization. Exercise names like "Bench Press" collide with what a naive test fixture might pick — **use `ZZ`-prefixed names in tests** (see `EX_ALPHA` etc. in `gym/tests.py`).
- **Tests are API-only now** (`gym/tests.py`, 70 tests) — the old 83 tests against template views were deleted along with `gym/views.py`. Structure: `ApiTestCase` base with `alice`/`bob` fixtures + helpers (`login_as`, `post_json`, `put_json`, `make_day`, `make_preset`), then per-feature classes (`AuthApiTests`, `AuthGatingTests`, `ExerciseApiTests`, `WorkoutDayApiTests`, `UserScopingTests`, `PresetApiTests`, `LeaderboardApiTests`, `LeaderboardExerciseApiTests`, `ChatApiTests`, plus model tests). New endpoints should follow this pattern rather than reintroducing template-view-style tests.
- **`admin.py` is an empty stub** — no models registered.
- Migrations were originally generated by Django 6.0.7 but run on 5.2 — no known issues; regenerate if upgrading Django.
- **Multi-select chip UI must use real `<button type="button">` elements, not `<div onClick>`.** `DayCreate.jsx` and `PresetForm.jsx` both let you tap exercise "chips" to build a selection; they used to be divs with `role="checkbox"`/`tabIndex`, which had a real mobile bug — deselecting the *last* selected exercise silently failed. Root cause: the "Selected Exercises" summary card was conditionally rendered on `selected.size > 0`, so removing the last item unmounted an *ancestor* of the tapped element as a direct, synchronous result of that same tap — a qualitatively bigger DOM mutation than removing one row from a list whose parent stays mounted, and mobile browsers can drop or misfire the click in that situation. Fixed by (1) always rendering the summary card (empty-state message instead of unmounting it), and (2) using native `<button>`s for both the chip grid and the row-level "✕" remove control (`.chip-remove` class, ≥32px tap target) instead of `div`/`span` + `onClick`. Any new tap-to-toggle UI should follow this pattern — don't reintroduce div-as-button chips, and don't gate a container that holds interactive children on the very state those children mutate.

## Conventions

- API views: `@api_view` + DRF `Response`, no ViewSets/routers. Local `get_object_or_404(model, **kwargs)` helper at the bottom of `api_views.py` (shadows Django's own — takes a model + kwargs, raises DRF `NotFound`).
- Creates/updates parse `request.data.get(...)` manually; serializers are output-only. Follow this rather than mixing in input serializers for just one endpoint.
- Frontend pages: `react-router-dom` v6 (`useNavigate`, `useParams`, `Link`), `useState`/`useEffect` + `api.get(...)` for data fetching, a `showFlash(message, type)` prop threaded down from `App.jsx` for toasts.
- CSS variables (`--bg`, `--bg-card`, `--accent`, `--border`, `--radius-sm`, etc.) are defined once in `index.css` for both themes — reuse them rather than hardcoding colors.

## Common commands
```sh
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py add_friend <username> <password>
python manage.py seed_workouts --user <username> [--clear]
python manage.py backup_db [--keep N]
python manage.py test gym
cd frontend && npm run dev            # start React dev server on :5173
cd frontend && npm run build          # production build to frontend/dist/ — commit this after any frontend change
```
