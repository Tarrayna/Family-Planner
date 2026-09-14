# Family Planner — backend specification

Self-hosted family planner. LAN-only. Three Docker containers.

## 1. Shape of the system

- **proxy** — Caddy. TLS (required for the phone PWA's service worker), serves the
  static frontend, routes `/api/*` to the API.
- **api** — application server. Owns all data, recurrence expansion.
- **db** — Postgres.

The Pi runs a kiosk browser at `/tv.html`. Phones open `/` (the PWA). Same
build, the route picks the shell. (Every page is addressed with its `.html`
suffix — Caddy's SPA fallback only knows the literal filename, so an
extensionless `/tv` actually resolves to `index.html`'s phone-identity
redirect, not the TV view. Point the kiosk at `/tv.html` specifically.)

## 2. Data model

### person
`id`, `name`, `color` (stored free-choice hex/oklch, no server-side
palette validation — but the current phone UI only offers a fixed 12-swatch
OKLCH palette by design, not a free color picker), `photo_path` (nullable),
`has_phone` (bool; false = assigned-only, someone else checks their tasks
off), `created_at`.

Anyone can edit anyone. No roles, no permissions.

### task
`id`, `title`, `assignee_id` (nullable), `due_date` (nullable),
`due_time_hint` (morning|afternoon|evening|none), `rrule` (nullable),
`rrule_until` (nullable), `rrule_count` (nullable), `series_id` (nullable),
`completed_at` (nullable), `created_at`, `vacation_id` (nullable, see
vacation section below), `checklist_group` (nullable — the vacation
checklist's "group"; named `checklist_group` in the DB since `group` is a
reserved SQL word), `note` (nullable — used by checklist items, e.g. "USPS
— do 2 days ahead").

Recurrence is an RFC 5545 RRULE string:

| UI                              | RRULE                              |
| ------------------------------- | ---------------------------------- |
| Every 3 weeks on Wednesday      | `FREQ=WEEKLY;INTERVAL=3;BYDAY=WE`  |
| The 2nd Wednesday of each month | `FREQ=MONTHLY;BYDAY=2WE`           |
| Every 3 days                    | `FREQ=DAILY;INTERVAL=3`            |
| …until Oct 28                   | `;UNTIL=20261028T000000Z`          |
| …12 times                       | `;COUNT=12`                        |

Use a library (python-dateutil / rrule.js). Do not hand-roll expansion.

### vacation
`id`, `name`, `starts_on`, `ends_on`, `pause_repeating`, `pause_overdue`,
`hide_tasks_on_tv`, `keep_calendar_events`, `created_at`.

Pre-trip checklist items are ordinary tasks with a `vacation_id` and a
`checklist_group`. New trips get a fixed editable template
(House/Kids/Travel) copied in as real tasks, due 3 days before `starts_on`
— resolved 2026-08-29, see §8 history below.

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

## 4. Identity

No accounts, no passwords, no pairing codes.

First visit serves "Who's using this phone?" — tapping a name sets a long-lived
signed cookie holding the person id. Switchable from Settings.

MAC addresses are **not** available to browsers; don't try. This is only safe
because the service is LAN-only. Do not expose the proxy to the internet without
adding real auth.

## 5. API surface

| Endpoint | Purpose |
| --- | --- |
| `GET /api/day?date=` | Everything Today needs: tasks due, overdue, weather, active vacation |
| `GET /api/range?from=&to=` | Week and month grids |
| `POST /api/tasks` · `PATCH /api/tasks/:id` | Create/edit, including RRULE fields |
| `POST /api/tasks/:id/complete` | Check off (and un-check) |
| `GET/POST/PATCH/DELETE /api/people` | Name, color, photo, has_phone |
| `GET/POST /api/vacations` | Setup, toggles, generated checklist |
| `GET/PATCH /api/settings/display` | Which layout the TV shows; written from the phone |
| `GET /api/stream` | Server-sent events — TV re-renders on any change |

The TV caches the last good `/api/day` and shows it behind a "Showing
yesterday's plan" banner when the API is unreachable.

## 6. Build order

1. Containers, Postgres, Caddy with a working cert. **PWA installability was
   never actually achieved** — Chrome/Brave showed no install option on
   either phone despite every server-side installability check passing;
   confirmed environment-level (not an app bug) by testing a known-good
   third-party PWA (reddit.com), which failed identically. Closed, worked
   around with a link from an existing dashboard instead of home-screen
   install.
2. People + identity cookie.
3. Tasks with plain due dates; TV Today reading `/api/day`.
4. Recurrence. Largest single piece — use a library, write tests for
   "2nd Wednesday" and "every 3 weeks until".
5. Vacations and the pre-trip checklist.
6. Week and month views, then the display-settings switch.

## 7. Open questions

- How does a person without a phone check off their own tasks? Shared tablet,
  a parent doing it, or a touchscreen on the Pi.
- Weather source — needs an outbound call and an API key.
- Backups: nightly `pg_dump` to somewhere off the Pi, from day one. **Not yet
  implemented** — flag again once the db has real data worth losing.
- External calendar sync (importing events from an outside calendar service)
  has no design — see Resolved below on why it isn't Google, and pick a
  different approach if it's ever wanted.

### Resolved

- **Pre-trip checklist source** (2026-08-29): fixed editable template, not
  "learn from past trips" — see the vacation section in §2.
- **No Google Calendar sync** (2026-09-13): ruled out entirely, not just
  deferred — Google gets no access to this app's data. Removed the `event`/
  `calendar` data model, the auto-assign rule, and the `/api/events` ·
  `/api/calendars` endpoints, all of which existed only to support it. If
  external calendar sync is wanted later, it needs a non-Google design
  (e.g. CalDAV, which also covers Fastmail and iCloud) from scratch.
