# Family Planner — backend specification

Self-hosted family planner. LAN-only. Three Docker containers.

## 1. Shape of the system

- **proxy** — Caddy. TLS (required for the phone PWA's service worker), serves the
  static frontend, routes `/api/*` to the API.
- **api** — application server. Owns all data, recurrence expansion, Google sync.
- **db** — Postgres.

The Pi runs a kiosk browser at `/tv`. Phones open `/` (the PWA). Same build, the
route picks the shell.

## 2. Data model

### person
`id`, `name`, `color` (free-choice hex/oklch — not limited to the app palette),
`photo_path` (nullable), `has_phone` (bool; false = assigned-only, someone else
checks their tasks off), `created_at`.

Anyone can edit anyone. No roles, no permissions.

### task
`id`, `title`, `assignee_id` (nullable), `due_date` (nullable),
`due_time_hint` (morning|afternoon|evening|none), `rrule` (nullable),
`rrule_until` (nullable), `rrule_count` (nullable), `series_id` (nullable),
`completed_at` (nullable), `created_at`.

Recurrence is an RFC 5545 RRULE string:

| UI                              | RRULE                              |
| ------------------------------- | ---------------------------------- |
| Every 3 weeks on Wednesday      | `FREQ=WEEKLY;INTERVAL=3;BYDAY=WE`  |
| The 2nd Wednesday of each month | `FREQ=MONTHLY;BYDAY=2WE`           |
| Every 3 days                    | `FREQ=DAILY;INTERVAL=3`            |
| …until Oct 28                   | `;UNTIL=20261028T000000Z`          |
| …12 times                       | `;COUNT=12`                        |

Use a library (python-dateutil / rrule.js). Do not hand-roll expansion.

### event
`id`, `title`, `starts_at`, `ends_at`, `all_day`, `calendar_id`,
`google_event_id` (null = created here), `assignee_id` (nullable),
`assignee_locked` (bool — true once a human reassigned it, so sync never
overwrites the choice), `series_key`, `updated_at`.

### calendar
`id`, `owner_person_id`, `google_calendar_id`, `name`, `enabled`,
`auto_assign`, `sync_token`, `last_synced_at`.

Shared calendars get `auto_assign = false` so their events stay unassigned.

### vacation
`id`, `name`, `starts_on`, `ends_on`, `pause_repeating`, `pause_overdue`,
`hide_tasks_on_tv`, `keep_calendar_events`.

Pre-trip checklist items are ordinary tasks with a `vacation_id` and a `group`.

## 3. Rules the server owns

Computed server-side so the TV and phone can never disagree.

- **Overdue.** `due_date < today` and not completed. Keeps its **original** due
  date — UI shows "Due Aug 6 · 3 days late" — and appears inside *today's* panel,
  not a separate bucket. Nothing auto-rolls.
- **Vacation pausing.** While a vacation is active with `pause_overdue`, days
  inside the range don't count toward lateness. With `pause_repeating`, no
  instances are generated for dates in the range; generation resumes on return.
- **Recurrence expansion.** Materialize concrete rows for a rolling window
  (today − 30d → today + 90d) on write and via a nightly job. Completing one
  instance never affects the series.
- **Auto-assign.** On sync, an event from a calendar with `auto_assign` gets
  `assignee_id = calendar.owner_person_id` — only when `assignee_locked` is
  false. Reassignment sets the lock. "Remember this series" applies the choice to
  every event sharing `series_key`, present and future.

## 4. Google Calendar sync

- OAuth per person; refresh token encrypted at rest. Each person authorizes from
  their own phone.
- Scope `calendar.events` (planner-created events write back to the chosen
  calendar). Everything else is read.
- Incremental sync via `syncToken`, polled every 2–5 min. Full re-sync on HTTP 410.
- **Reassignment never writes back to Google.** Google owns event content; the
  planner owns who it belongs to.
- Dead refresh token → mark the calendar stale, show "Google Calendar
  disconnected". Tasks keep working; events freeze at last sync.

## 5. Identity

No accounts, no passwords, no pairing codes.

First visit serves "Who's using this phone?" — tapping a name sets a long-lived
signed cookie holding the person id. Switchable from Settings.

MAC addresses are **not** available to browsers; don't try. This is only safe
because the service is LAN-only. Do not expose the proxy to the internet without
adding real auth.

## 6. API surface

| Endpoint | Purpose |
| --- | --- |
| `GET /api/day?date=` | Everything Today needs: events, tasks due, overdue, weather, active vacation |
| `GET /api/range?from=&to=` | Week and month grids |
| `POST /api/tasks` · `PATCH /api/tasks/:id` | Create/edit, including RRULE fields |
| `POST /api/tasks/:id/complete` | Check off (and un-check) |
| `POST /api/events` · `PATCH /api/events/:id` | Create in planner; reassign (sets lock) |
| `GET/POST/PATCH /api/people` | Name, color, photo, has_phone |
| `GET /api/calendars` · `PATCH /api/calendars/:id` | Per-person list, enable / auto-assign |
| `GET/POST /api/vacations` | Setup, toggles, generated checklist |
| `GET /api/settings/display` | Which layout the TV shows; written from the phone |
| `GET /api/stream` | Server-sent events — TV re-renders on any change |

The TV caches the last good `/api/day` and shows it behind a "Showing
yesterday's plan" banner when the API is unreachable.

## 7. Build order

1. Containers, Postgres, Caddy with a working cert — prove the PWA installs on
   both phones before anything else.
2. People + identity cookie.
3. Tasks with plain due dates; TV Today reading `/api/day`.
4. Recurrence. Largest single piece — use a library, write tests for
   "2nd Wednesday" and "every 3 weeks until".
5. Google OAuth and sync, one account first.
6. Vacations and the pre-trip checklist.
7. Week and month views, then the display-settings switch.

## 8. Open questions

- How does a person without a phone check off their own tasks? Shared tablet,
  a parent doing it, or a touchscreen on the Pi.
- Weather source — needs an outbound call and an API key.
- Should the pre-trip checklist learn from past trips, or start from a fixed
  editable template?
- Backups: nightly `pg_dump` to somewhere off the Pi, from day one.
