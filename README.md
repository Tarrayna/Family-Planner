# Family Planner — handoff

Design lives in the Omelette project; this folder is the buildable scaffolding.

## Contents

- `SPEC.md` — the backend specification. Hand this to Claude Code as the brief.
- `docker-compose.yml` — proxy / api. The api owns a SQLite database file
  (`api/app/db.py`) — no separate database service to run.
- `Caddyfile` — TLS + static frontend + `/api` proxy, split into two
  hostnames (`calendar.home` for the app, `calendar-read.home` for the
  read-only TV view — see the comment at the top). The PWA will not install
  without a trusted certificate.
- `.env.example` — copy to `.env` and fill in.
- `web/manifest.json`, `web/sw.js` — the PWA pieces. Drop your built frontend
  alongside them in `web/`; you still need to add `icons/` (192, 512, and a
  maskable 512) and link the manifest + register the worker from `index.html`:

```html
<link rel="manifest" href="/manifest.json">
<meta name="theme-color" content="#161826">
<script>
  if ('serviceWorker' in navigator) {
    addEventListener('load', () => navigator.serviceWorker.register('/sw.js'));
  }
</script>
```

## First run

```sh
cp .env.example .env      # fill it in
docker compose up -d
```

Then, on each phone: open `https://calendar.home`, tap your name, and Add
to Home Screen. If you're connecting directly rather than through a
front-door proxy with its own cert (see Caddyfile), you'll hit a
certificate warning first — Settings → Security → Download certificate
grabs Caddy's root CA (`/ca.crt`) so you can install it once per device and
stop seeing that warning.

Point the wall display / TV kiosk at `https://calendar-read.home` instead —
same app, but it always lands on the read-only calendar view (no "who's
using this" prompt) and the layout it shows (today/week/month) is whatever
the phone last set in Settings.

## Deploy & backup (on the VM)

Two scripts, each meant to run from a systemd timer on the deploy server:

- `deploy.sh` — polls `origin/main`; if there's a new commit, fast-forwards
  and rebuilds/restarts (`git merge --ff-only` — never resets or discards).
  A sample timer:

  ```ini
  # /etc/systemd/system/planner-deploy.timer
  [Timer]
  OnBootSec=1min
  OnUnitActiveSec=1min

  [Install]
  WantedBy=timers.target
  ```

  paired with a `.service` unit whose `ExecStart` runs `deploy.sh` from the
  repo checkout.

- `backup.sh` — nightly; takes a consistent SQLite backup (`.backup`, safe
  against the live WAL-mode database) plus a tarball of the `photos` volume,
  writes both to the NAS mount, and prunes old copies. Same pattern, on a
  once-daily timer (`OnCalendar=daily`). Needs the `sqlite3` CLI on the host
  (just for the post-backup integrity check) and `NAS_BACKUP_DIR` set to
  wherever the NAS share is mounted — set it in the `.service` unit's
  `Environment=`.

## The frontend

`web/` is a complete, buildless frontend — plain HTML, CSS and ES modules. Caddy
serves it as-is; there is nothing to compile.

| File | Screen |
| --- | --- |
| `index.html` | Entry — redirects to who / today |
| `who.html` | "Who's using this phone?" — one tap, then a cookie |
| `today.html` | Phone Today — schedule + due-today (overdue included) |
| `month.html` | Phone month calendar with faces per day |
| `task.html` | Add / edit a task |
| `repeat.html` | Repeat rule builder — emits a real RRULE |
| `family.html` · `person.html` | Family list; edit anyone (name, colour, photo, phone) |
| `vacation.html` | Vacation setup and the pre-trip checklist |
| `settings.html` | This phone, TV layout, options |
| `tv.html` · `tv-week.html` · `tv-month.html` | The Pi display — point the kiosk at `https://calendar-read.home` |

Supporting files: `css/app.css` (all styling, one file), `js/api.js` (fetch with
mock fallback), `js/ui.js` (render helpers, avatars), `js/tv.js` (TV chrome —
clock, weather, tasks rail, QR).

### It runs right now

`mock/*.json` mirrors the API shapes in SPEC.md. `js/api.js` tries the real
endpoint first and silently falls back to the mock, so every screen works before
the backend exists. Serve the folder and open it:

```sh
cd web && python3 -m http.server 8000
```

Phone at `localhost:8000`, TV at `localhost:8000/tv.html`.

Delete the `MOCK` map in `js/api.js` once `/api` is live.

### Notes for the build

- **Fluid TV.** The TV pages size everything in `cqw` against a
  `container-type: size` root, so one page fills 1080p, 4K or a laptop window
  with no breakpoints. Don't add fixed px to `.tv` descendants.
- **The layout switch.** `tv.html` reads `/api/settings/display` and redirects
  to the week or month page. The phone writes that setting.
- **Refresh.** `poll()` in `js/ui.js` re-fetches every 60s and on tab focus.
  Swap it for `/api/stream` (SSE) when that exists — one function to change.
- **Overdue.** Server-computed only (SPEC.md §3) — `/api/day` tasks carry
  `days_late` (int) and a ready-to-render `due_label` (e.g. "Due Aug 6 · 3
  days late"). The frontend never recomputes this; it just reads the fields.
- **Mock dates slide.** `shiftMockDates()` in `js/api.js` moves every date in the
  fixture so the demo always lands on today — no editing JSON to see it work.
  `fakeOverdue()` then re-derives `days_late`/`due_label` for the shifted
  dates, standing in for the server. Delete both with the `MOCK` map.
- **Never `toISOString()` for a calendar date.** It is UTC and lands on the wrong
  day in the evening. Use `isoDate()` from `js/ui.js`.
- **Testing one TV layout.** `?layout=week` (or `today`/`month`) overrides the
  server setting, so you can open any Pi screen without changing settings.
- **Photos** are `background-image` on the avatar, never `<img>`, so a missing
  photo can't break a row. No photo → initial on a tint of their colour, same box.
- **Icons.** None yet. The design system calls for Phosphor
  (https://phosphoricons.com) — the chevrons and pluses here are text glyphs.

## Next

`api/` is empty on purpose — build it against `SPEC.md`. Start with people +
identity, then plain tasks, then recurrence.
