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
    a.append(el('div', { style: `font-size:${Math.round(size * 0.42)}px;color:${c}` }, person.name[0]));
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
    a.append(el('div', { style: `font-size:${(cq * 0.45).toFixed(2)}cqw;color:${c}` }, person.name[0]));
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

// Every 60 seconds, as chosen. Swap for /api/stream when it exists.
export function poll(fn, ms = 60000) {
  fn();
  setInterval(fn, ms);
  document.addEventListener('visibilitychange', () => { if (!document.hidden) fn(); });
}
