// Small render helpers shared by every screen. No framework on purpose.

export const $ = (sel, root = document) => root.querySelector(sel);
export const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

export function el(tag, props = {}, ...kids) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(props)) {
    if (v == null || v === false) continue;
    if (k === 'class') n.className = v;
    else if (k === 'style') n.style.cssText = v;
    else if (k.startsWith('on')) n.addEventListener(k.slice(2).toLowerCase(), v);
    else n.setAttribute(k, v === true ? '' : v);
  }
  for (const kid of kids.flat()) {
    if (kid == null || kid === false) continue;
    n.append(kid.nodeType ? kid : document.createTextNode(kid));
  }
  return n;
}

// A person's face. Photo when there is one, initial on a tint of their colour
// when there isn't — same box either way so rows never shift.
export function avatar(person, size = 28, ring = 1.5) {
  const c = person?.color || 'var(--n600)';
  const a = el('div', {
    class: 'ava',
    style: `width:${size}px;height:${size}px;border:${ring}px solid ${c};` +
      `background-color:color-mix(in srgb, ${c} 25%, var(--bg));` +
      (person?.photo_url ? `background-image:url(${person.photo_url})` : ''),
  });
  if (!person?.photo_url && person?.name) {
    a.append(el('div', { style: `font-size:${Math.round(size * 0.42)}px;line-height:1;color:${c}` }, person.name[0]));
  }
  return a;
}

// Same, sized in cqw for the TV (which scales with the screen).
export function avatarCq(person, cq = 2, ring = 0.12) {
  const c = person?.color || 'var(--n600)';
  const a = el('div', {
    class: 'ava',
    style: `width:${cq}cqw;height:${cq}cqw;border:${ring}cqw solid ${c};` +
      `background-color:color-mix(in srgb, ${c} 25%, var(--bg));` +
      (person?.photo_url ? `background-image:url(${person.photo_url})` : ''),
  });
  if (!person?.photo_url && person?.name) {
    a.append(el('div', { style: `font-size:${(cq * 0.45).toFixed(2)}cqw;line-height:1;color:${c}` }, person.name[0]));
  }
  return a;
}

export const byId = (list) => Object.fromEntries((list || []).map((p) => [p.id, p]));

export function fmtTime(iso, use24) {
  const d = new Date(iso);
  if (use24) return d.toTimeString().slice(0, 5);
  let h = d.getHours(); const m = d.getMinutes();
  const mer = h >= 12 ? 'PM' : 'AM';
  h = h % 12 || 12;
  return `${h}:${String(m).padStart(2, '0')} ${mer}`;
}

// Local-date ISO string. Never use toISOString() for a calendar date — it is
// UTC, so it lands on the wrong day for anyone west of Greenwich in the evening.
export const isoDate = (d = new Date()) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;

export const DOW = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
export const WEEKDAY = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
export const MONTH = ['January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December'];

// Re-renders on /api/stream (SSE) for near-instant updates; the interval and
// visibility listener stay as a fallback so a dropped stream still recovers.
export function poll(fn, ms = 60000) {
  fn();
  setInterval(fn, ms);
  document.addEventListener('visibilitychange', () => { if (!document.hidden) fn(); });
  if ('EventSource' in window) new EventSource('/api/stream').onmessage = () => fn();
}

// --- navigation --------------------------------------------------------------
// Four destinations. Today is home; Calendar carries the day/week/month switch;
// Family is people; Settings holds the TV display, Google and vacation mode.
const ICON = {
  today: 'M4 6.5h16M4 6.5a1.5 1.5 0 0 1 1.5-1.5h13A1.5 1.5 0 0 1 20 6.5v12a1.5 1.5 0 0 1-1.5 1.5h-13A1.5 1.5 0 0 1 4 18.5zM8 3v4M16 3v4M8 12h8M8 16h5',
  calendar: 'M3.5 9.5h17M5 5h14a1.5 1.5 0 0 1 1.5 1.5v12A1.5 1.5 0 0 1 19 20H5a1.5 1.5 0 0 1-1.5-1.5v-12A1.5 1.5 0 0 1 5 5M8 13h2M14 13h2M8 16.5h2M14 16.5h2',
  family: 'M9 11a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7M2.5 20a6.5 6.5 0 0 1 13 0M16 5.2a3.5 3.5 0 0 1 0 6.6M18 14.4a6.5 6.5 0 0 1 3.5 5.6',
  settings: 'M12 15.2a3.2 3.2 0 1 0 0-6.4 3.2 3.2 0 0 0 0 6.4M19.4 15a1.7 1.7 0 0 0 .34 1.87l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06A1.7 1.7 0 0 0 15 19.4a1.7 1.7 0 0 0-1 1.56V21a2 2 0 1 1-4 0v-.09A1.7 1.7 0 0 0 9 19.4a1.7 1.7 0 0 0-1.87.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.7 1.7 0 0 0 4.6 15a1.7 1.7 0 0 0-1.56-1H3a2 2 0 1 1 0-4h.09A1.7 1.7 0 0 0 4.6 9a1.7 1.7 0 0 0-.33-1.87l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.7 1.7 0 0 0 9 4.6a1.7 1.7 0 0 0 1-1.56V3a2 2 0 1 1 4 0v.09a1.7 1.7 0 0 0 1 1.51 1.7 1.7 0 0 0 1.87-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.7 1.7 0 0 0 19.4 9v0a1.7 1.7 0 0 0 1.56 1H21a2 2 0 1 1 0 4h-.09a1.7 1.7 0 0 0-1.51 1',
};
const TABS = [
  ['today.html', 'Today', 'today'],
  ['month.html', 'Calendar', 'calendar'],
  ['family.html', 'Family', 'family'],
  ['settings.html', 'Settings', 'settings'],
];
const CALENDAR_PAGES = ['month.html', 'week.html'];

function icon(name) {
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('viewBox', '0 0 24 24');
  svg.setAttribute('aria-hidden', 'true');
  const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
  path.setAttribute('d', ICON[name]);
  svg.append(path);
  return svg;
}

export function tabbar() {
  const here = location.pathname.split('/').pop() || 'today.html';
  const active = CALENDAR_PAGES.includes(here) ? 'month.html'
    : TABS.some(([h]) => h === here) ? here : 'today.html';
  const nav = el('nav', { class: 'tabbar', 'aria-label': 'Main' });
  for (const [href, label, ico] of TABS) {
    nav.append(el('a', { href, ...(href === active ? { 'aria-current': 'page' } : {}) },
      icon(ico), el('span', {}, label)));
  }
  document.body.append(nav);
}

// Week / Month — the two calendar grains. Today is its own destination, not a
// third grain, so it does not appear here.
export function viewSwitch(active) {
  return el('div', { class: 'viewseg', role: 'tablist' },
    ...[['week.html', 'Week'], ['month.html', 'Month']]
      .map(([href, label]) => el('a', {
        href, role: 'tab', ...(label.toLowerCase() === active ? { 'aria-current': 'page' } : {}),
      }, label)));
}
