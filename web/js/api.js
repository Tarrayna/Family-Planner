// Data access. Tries the real API first, falls back to the bundled mock so the
// whole frontend runs before the backend exists. Delete the fallback once
// /api is live.

const MOCK = {
  '/api/day': 'mock/day.json',
  '/api/range': 'mock/range.json',
  '/api/people': 'mock/people.json',
  '/api/vacations': 'mock/vacations.json',
  '/api/settings/display': 'mock/display.json',
};

export async function get(path) {
  const key = path.split('?')[0];
  try {
    const res = await fetch(path, { headers: { Accept: 'application/json' } });
    if (!res.ok) throw new Error(res.status);
    return await res.json();
  } catch (e) {
    if (!MOCK[key]) throw e;
    const res = await fetch(MOCK[key]);
    const shifted = shiftMockDates(await res.json());
    return key === '/api/day' ? fakeOverdue(shifted) : shifted;
  }
}

export async function send(method, path, body) {
  try {
    const res = await fetch(path, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!res.ok) throw new Error(res.status);
    return res.status === 204 ? null : await res.json();
  } catch (e) {
    console.warn('[api] offline, change not persisted:', method, path, body);
    return null;
  }
}

export const post = (p, b) => send('POST', p, b);
export const patch = (p, b) => send('PATCH', p, b);

// Who this device is. The server sets a signed cookie; this mirrors the id
// locally so the UI can render before the first request returns.
export const whoami = () => localStorage.getItem('planner.person');
export const setWhoami = (id) => localStorage.setItem('planner.person', id);

// --- mock only ---------------------------------------------------------------
// The fixture is written around a fixed anchor day; slide every date in it so
// the demo always lands on today. Delete along with the MOCK map.
const MOCK_ANCHOR = '2026-08-09';

export function mockToday() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

function shiftMockDates(data) {
  const offset = Math.round((new Date(mockToday()) - new Date(MOCK_ANCHOR)) / 86400000);
  if (!offset) return data;
  const bump = (s) => {
    const d = new Date(s.slice(0, 10) + 'T00:00:00');
    d.setDate(d.getDate() + offset);
    return d.toISOString().slice(0, 10) + s.slice(10);
  };
  const walk = (v) =>
    Array.isArray(v) ? v.map(walk)
      : v && typeof v === 'object' ? Object.fromEntries(Object.entries(v).map(([k, x]) => [k, walk(x)]))
      : typeof v === 'string' && /^\d{4}-\d{2}-\d{2}/.test(v) ? bump(v)
      : v;
  return walk(data);
}

// The real /api/day computes days_late and due_label server-side (SPEC.md §3)
// — the frontend never re-derives them. Fake that computation here, after
// shiftMockDates, so the mock's baked-in labels don't go stale once the
// dates slide. Delete along with the MOCK map.
const MOCK_MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];

function fakeOverdue(day) {
  const today = new Date(mockToday() + 'T00:00:00');
  for (const t of day.tasks || []) {
    if (!t.due_date || t.completed_at) { t.days_late = 0; continue; }
    const due = new Date(t.due_date + 'T00:00:00');
    t.days_late = Math.max(0, Math.round((today - due) / 86400000));
    t.due_label = t.days_late > 0
      ? `Due ${MOCK_MONTHS[due.getMonth()]} ${due.getDate()} · ${t.days_late} day${t.days_late > 1 ? 's' : ''} late`
      : (t.repeat_label ? `Due today · ${t.repeat_label}` : 'Due today');
  }
  return day;
}
