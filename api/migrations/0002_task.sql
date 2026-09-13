CREATE TABLE task (
    id UUID PRIMARY KEY DEFAULT (gen_random_uuid()),
    title TEXT NOT NULL,
    assignee_id UUID REFERENCES person(id) ON DELETE SET NULL,
    due_date DATE,
    due_time_hint TEXT NOT NULL DEFAULT 'none' CHECK (due_time_hint IN ('morning', 'afternoon', 'evening', 'none')),
    rrule TEXT,
    rrule_until TEXT,
    rrule_count INTEGER,
    series_id UUID,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT (now())
);
