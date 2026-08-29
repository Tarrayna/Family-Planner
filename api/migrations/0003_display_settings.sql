-- Singleton row: id is always true, so only one row can ever exist.
CREATE TABLE display_settings (
    id BOOLEAN PRIMARY KEY DEFAULT true CHECK (id),
    layout TEXT NOT NULL DEFAULT 'today' CHECK (layout IN ('today', 'week', 'month')),
    show_weather BOOLEAN NOT NULL DEFAULT true,
    show_upcoming BOOLEAN NOT NULL DEFAULT true,
    time_format TEXT NOT NULL DEFAULT '12h' CHECK (time_format IN ('12h', '24h'))
);

INSERT INTO display_settings (id) VALUES (true);
