CREATE TABLE vacation (
    id UUID PRIMARY KEY DEFAULT (gen_random_uuid()),
    name TEXT NOT NULL,
    starts_on DATE NOT NULL,
    ends_on DATE NOT NULL,
    pause_repeating BOOLEAN NOT NULL DEFAULT true,
    pause_overdue BOOLEAN NOT NULL DEFAULT true,
    hide_tasks_on_tv BOOLEAN NOT NULL DEFAULT true,
    keep_calendar_events BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT (now())
);

-- Pre-trip checklist items are ordinary tasks tagged with a trip and a
-- group (SPEC.md §2). "checklist_group" avoids the reserved word GROUP.
ALTER TABLE task ADD COLUMN vacation_id UUID REFERENCES vacation(id) ON DELETE CASCADE;
ALTER TABLE task ADD COLUMN checklist_group TEXT;
ALTER TABLE task ADD COLUMN note TEXT;
