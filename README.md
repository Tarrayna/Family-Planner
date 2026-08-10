# Family Planner

A self-hosted family planner app made up of a couple of Docker containers.

## Overview

- **Frontend**
  - A read-only display view, meant to be shown on a Raspberry Pi (e.g. a wall-mounted dashboard).
  - Displays a calendar and other at-a-glance info.
  - UI will be designed with Claude.
  - A phone-friendly version for viewing and editing the calendar and tasks.

- **Backend**
  - Server that owns the calendar and task data.
  - Syncs with Google Calendar, with the goal of supporting additional external sources over time.

## Status

Early planning / setup. Containers and app structure are still to come.
