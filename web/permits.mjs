import {$, el, download, csv, dateLabel, fillSelect} from './common.mjs';

const size = 8;
const clock = new Intl.DateTimeFormat('en-CA', {dateStyle:'medium', timeStyle:'short', timeZone:'America/Vancouver'});
const checked = stamp => clock.format(new Date(stamp));
let data, matches = [], page = 0;

function result(record) {
    const periods = record.periods;
    const latest = periods.at(-1);
    const card = el('details', '', 'permit-record');
    const summary = el('summary');
    summary.append(el('strong', record.id), el('span', record.addresses[0] +
        (record.addresses.length > 1 ? ' (+' + (record.addresses.length - 1) + ' more)' : '')),
        el('small', latest.first_absent ? 'No longer listed' : 'Listed'));
    card.append(summary, el('p', record.kind + ' · Issued ' + dateLabel(record.issued)));
    for (const description of record.descriptions) card.append(el('p', description));
    if (record.addresses.length > 1) card.append(el('p', 'Listed addresses · ' + record.addresses.join(', ')));
    const events = el('ul');
    for (const p of periods) {
        const first = p.first_seen === data.baseline_at ? 'Present at baseline' : 'First seen in this listing period';
        events.append(el('li', first + ' · ' + checked(p.first_seen)),
            el('li', 'Last seen · ' + checked(p.last_seen)));
        if (p.first_absent) events.append(el('li', 'First check showing absence · ' + checked(p.first_absent)));
    }
    card.append(events);
    const url = new URL(location.href);
    url.searchParams.set('permit', record.id);
    url.hash = 'permits';
    const permalink = el('a', 'Link to this folder');
    permalink.href = url.href;
    card.append(permalink);
    return card;
}

function display() {
    const start = page * size;
    $('permit-rows').replaceChildren(...matches.slice(start, start + size).map(result));
    $('permit-count').textContent = matches.length ? matches.length.toLocaleString() + ' matching folders' : 'No folders match these filters.';
    $('permit-page').textContent = matches.length ? (page+1) + ' of ' + Math.ceil(matches.length/size) : '';
    $('permit-prev').disabled = page === 0;
    $('permit-next').disabled = start + size >= matches.length;
    $('permit-download').disabled = !matches.length;
}

function filter() {
    if (!data) return;
    const query = $('permit-search').value.trim().toLowerCase();
    const kind = $('permit-type').value;
    const state = $('permit-state').value;
    matches = data.records.filter(r => {
        if (kind && kind !== r.kind) return false;
        const absent = Boolean(r.periods.at(-1).first_absent);
        if (state === 'listed' && absent || state === 'absent' && !absent ||
            state === 'returned' && r.periods.length < 2 ||
            state === 'new' && r.periods[0].first_seen === data.baseline_at) return false;
        return !query || [r.id, r.kind, ...r.addresses, ...r.descriptions].join(' ').toLowerCase().includes(query);
    });
    page = 0;
    display();
}

$('permit-search').oninput = filter;
$('permit-type').onchange = filter;
$('permit-state').onchange = filter;
$('permit-next').onclick = () => { page++; display(); };
$('permit-prev').onclick = () => { page--; display(); };
$('permit-download').onclick = () => {
    const rows = matches.map(r => {
        const latest = r.periods.at(-1);
        return [r.id,r.addresses.join(' | '),r.kind,r.issued,r.descriptions.join(' | '),r.periods[0].first_seen,
            latest.last_seen,latest.first_absent || '',r.periods.length,data.checked_at];
    });
    download('township-permit-folders.csv', csv([['folder','addresses','type','issued','description','first_observed_utc',
        'last_observed_utc','first_absent_current_period_utc','listing_periods','retrieved_utc'], ...rows]), 'text/csv');
};

try {
    const response = await fetch('./data/permits.json');
    if (!response.ok) throw Error('Permit snapshot unavailable');
    data = await response.json();
    data.records.sort((a,b) => b.issued.localeCompare(a.issued) || a.id.localeCompare(b.id));
    fillSelect('permit-type', data.records.map(r => r.kind));
    $('permit-source').textContent = data.listed_folders.toLocaleString() + ' listed folders · ' +
        data.source_rows.toLocaleString() + ' source rows · Checked ' + checked(data.checked_at) +
        ' Pacific · Tracking began ' + checked(data.baseline_at) + ' Pacific.';
    const id = new URLSearchParams(location.search).get('permit');
    if (id) $('permit-search').value = id;
    filter();
    if (id && matches.length === 1 && matches[0].id === id) $('permit-rows').firstElementChild.open = true;
} catch {
    $('permit-source').textContent = 'The permit snapshot could not load. Use the Township list linked below.';
}
