CREATE TABLE person (
    id UUID PRIMARY KEY DEFAULT (gen_random_uuid()),
    name TEXT NOT NULL,
    color TEXT NOT NULL,
    photo_path TEXT,
    has_phone BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT (now())
);
