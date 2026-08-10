# Family Planner — handoff

Design lives in the Omelette project; this folder is the buildable scaffolding.

## Contents

- `SPEC.md` — the backend specification. Hand this to Claude Code as the brief.
- `docker-compose.yml` — proxy / api / db.
- `Caddyfile` — TLS + static frontend + `/api` proxy. Read the comment at the
  top: the PWA will not install without a trusted certificate.
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

Then, on each phone: open the site, trust the CA if you used `tls internal`,
tap your name, and Add to Home Screen.

## Next

`api/` is empty on purpose — build it against `SPEC.md`. Start with people +
identity, then plain tasks, then recurrence.
