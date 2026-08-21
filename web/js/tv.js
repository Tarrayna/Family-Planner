// Shared TV chrome: clock, weather, the tasks rail, the offline banner.
import { el, avatarCq } from './ui.js';

export function clock(use24, small) {
  const wrap = el('div', { style: 'text-align:right' });
  const time = el('div', { class: 'tv-clock' + (small ? ' sm' : '') });
  const mer = el('div', { class: 'tv-mer' });
  const tick = () => {
    const d = new Date();
    let h = d.getHours();
    const m = String(d.getMinutes()).padStart(2, '0');
    if (use24) { time.textContent = `${String(h).padStart(2, '0')}:${m}`; mer.textContent = ''; }
    else {
      const ampm = h >= 12 ? 'PM' : 'AM';
      h = h % 12 || 12;
      if (small) { time.innerHTML = `${h}:${m} <span style="font-size:1.45cqw;color:var(--n500);letter-spacing:0">${ampm}</span>`; mer.textContent = ''; }
      else { time.textContent = `${h}:${m}`; mer.textContent = ampm; }
    }
  };
  tick();
  setInterval(tick, 10000);
  wrap.append(time, mer);
  return wrap;
}

export function weather(w, big) {
  if (!w) return null;
  return el('div', { class: 'tv-weather' },
    el('div', { class: 'sun' }),
    el('div', {},
      el('div', { class: 'tv-temp' }, w.temp + '°'),
      big && el('div', { class: 'tv-cond' }, `${w.condition} · H ${w.high}° L ${w.low}°`)));
}

export function legend(people) {
  return el('div', { class: 'tv-legend' },
    ...people.map((p) => el('div', {}, avatarCq(p, 1.9, 0.14), p.name)));
}

export function rail(day, people, phoneUrl) {
  const tasks = [...day.tasks].sort((a, b) => (b.days_late || 0) - (a.days_late || 0));
  const late = tasks.filter((t) => t.days_late > 0).length;

  if (day.vacation && day.vacation.hide_tasks_on_tv) {
    const daysOut = Math.max(0, Math.round((new Date(day.vacation.starts_on) - new Date(day.date)) / 86400000));
    return el('div', { class: 'rail', style: 'border:1px solid var(--a800)' },
      el('div', { class: 'rail-head' },
        el('div', { class: 'tv-label', style: 'color:var(--a300)' }, 'Vacation'),
        el('div', { style: 'font-size:1.05cqw;color:var(--n500)' }, `${day.vacation.starts_on.slice(5)} – ${day.vacation.ends_on.slice(5)}`)),
      el('div', {},
        el('div', { style: 'font-size:3cqw;font-weight:500;line-height:1' }, daysOut + ' days'),
        el('div', { style: 'font-size:1.1cqw;color:var(--n500);margin-top:.3cqw' }, 'until ' + day.vacation.name)),
      el('div', { class: 'grow' }),
      el('div', { style: 'font-size:1cqw;color:var(--n600);line-height:1.5' }, 'Chores paused · nothing goes overdue'),
      qr(phoneUrl));
  }

  return el('div', { class: 'rail' },
    el('div', { class: 'rail-head' },
      el('div', { class: 'tv-label' }, 'Tasks today'),
      late ? el('div', { class: 'rail-late' }, late + ' late') : null),
    el('div', { class: 'grow', style: 'display:flex;flex-direction:column;gap:.9cqw' },
      ...tasks.map((t) => {
        const done = !!t.completed_at;
        return el('div', { class: 'rail-task' + (t.days_late ? ' late' : ''), 'data-done': done ? '1' : '0' },
          el('div', { class: 'box' }, done ? '✓' : ''),
          el('div', { class: 'grow', style: 'min-width:0' },
            el('div', { class: 't' }, t.title),
            el('div', { class: 'm' }, t.due_label)),
          avatarCq(people[t.assignee_id], 2));
      })),
    qr(phoneUrl));
}

function qr(url) {
  const src = 'https://api.qrserver.com/v1/create-qr-code/?size=224x224&color=e9e9ed&bgcolor=232532&qzone=2&data=' +
    encodeURIComponent(url || location.origin + '/');
  return el('div', { class: 'rail-qr' },
    el('img', { src, alt: 'Scan to open on your phone' }),
    el('span', {}, 'Scan to edit on your phone'));
}

export function staleBanner(since) {
  return el('div', { class: 'tv-banner' },
    el('div', { class: 'dot' }),
    el('div', { class: 'grow' }, "Showing the last known plan — can't reach the server"),
    el('div', { style: 'color:var(--n600)' }, since));
}
