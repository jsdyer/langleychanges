"""Collect the Township's complete, paginated list of currently listed permit folders."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import build_opener, HTTPCookieProcessor, Request
from urllib.error import URLError
import json
import re
import time

from bs4 import BeautifulSoup, SoupStrainer

URL = 'https://apps.tol.ca/bpact.aspx'
RULES = 'https://www.tol.ca/en/building-development/building-permit-activity-information.aspx'
OUT = Path(__file__).resolve().parents[1] / 'web/data/permits.json'
HEADINGS = ['Folder #', 'Address', 'Issued Date', 'Type', 'Builder', 'Project Description']
PAGER = re.compile(r"^javascript:__doPostBack\('gvPermitList','Page\$(\d+|First|Last)'\)$")


def parse_page(body):
    soup = BeautifulSoup(body, 'html.parser', parse_only=SoupStrainer('form', id='form1'))
    table = soup.find('table', id='gvPermitList')
    if not table or [c.get_text(strip=True) for c in table.find_all('th')] != HEADINGS:
        raise ValueError('Township table headings changed')
    pager = table.select_one('tr.myPager')
    current = int(pager.select_one('span').get_text(strip=True)) if pager else 1
    links = set()
    for link in pager.select('a') if pager else []:
        match = PAGER.fullmatch(link.get('href', ''))
        if not match:
            raise ValueError('Township paging controls changed')
        links.add(match[1])
    rows = []
    for tr in table.find_all('tr', recursive=False):
        cells = tr.find_all('td', recursive=False)
        if not cells or tr == pager:
            continue
        if len(cells) != len(HEADINGS):
            raise ValueError('Unexpected Township permit row')
        folder, address, issued, kind, _, description = [' '.join(c.stripped_strings) for c in cells]
        if not re.fullmatch(r'BP[0-9]+', folder) or not address or not kind:
            raise ValueError(f'Incomplete permit folder {folder!r}')
        issued = datetime.strptime(issued, '%b-%d-%Y').date().isoformat()
        rows.append((folder, address, issued, kind, description))
    if not rows:
        raise ValueError('Empty Township permit page')
    fields = {el['name']: el.get('value', '') for el in soup.select('input[type="hidden"][name]')}
    if not {'__VIEWSTATE', '__EVENTVALIDATION'} <= fields.keys():
        raise ValueError('Township form state missing')
    return current, links, rows, fields


def fetch_pages():
    opener = build_opener(HTTPCookieProcessor())
    opener.addheaders = [('User-Agent', 'CoolCode public-data explorer (+https://coolcode.ca/langleychanges/)')]

    def read(page=None, target=None):
        data = None
        if page:
            if str(target) not in page[1]:
                raise ValueError('Unadvertised page target')
            fields = dict(page[3], __EVENTTARGET='gvPermitList', __EVENTARGUMENT='Page$'+str(target),
                          txtFolderNumber='', txtPermitAddress='', ddlPermitType='')
            data = urlencode(fields).encode()
        for attempt in range(3):
            try:
                with opener.open(Request(URL, data=data, headers={'Referer': URL}), timeout=50) as response:
                    result = parse_page(response.read())
                break
            except (URLError, TimeoutError, ConnectionError):
                if attempt == 2:
                    raise
                time.sleep(2 ** attempt)
        if (target is None and result[0] != 1) or (isinstance(target, int) and result[0] != target):
            raise ValueError('Unexpected page returned by Township')
        return result

    first = read()
    last = read(first, 'Last') if 'Last' in first[1] else first
    total = last[0]
    if 'Last' in last[1]:
        raise ValueError('Malformed final page')
    if any(k.isdigit() and int(k)>total for k in first[1]):
        raise ValueError('Missing final-page control')
    pages = {1: first, total: last}
    print(f'Township listing has {total} pages', flush=True)
    with ThreadPoolExecutor(max_workers=3) as pool:
        while len(pages) < total:
            available = {}
            for p in pages.values():
                for raw in p[1]:
                    if raw.isdigit() and 1 <= int(raw) <= total and int(raw) not in pages:
                        available[int(raw)] = p
            if not available:
                raise ValueError('Incomplete permit page chain')
            jobs = {i: pool.submit(read, parent, i) for i,parent in sorted(available.items())}
            pages.update((i,job.result()) for i,job in jobs.items())
            print(f'Checked {len(pages)} of {total} permit pages', flush=True)
    end_first = read()
    end_last = read(end_first, 'Last') if 'Last' in end_first[1] else end_first
    if first[:3] != end_first[:3] or last[:3] != end_last[:3]:
        raise ValueError('Listing changed during collection')
    rows = []
    for i in range(1,total+1):
        page_rows=pages[i][2]
        if i < total and len(page_rows) != len(first[2]):
            raise ValueError('Short interior page')
        rows.extend(page_rows)
    if len({tuple(p[2]) for p in pages.values()}) != total:
        raise ValueError('Duplicate page contents')
    return rows, total


def group_folders(rows):
    folders = {}
    for folder, address, issued, kind, description in rows:
        record = folders.setdefault(folder, dict(id=folder, addresses=set(), issued=issued, kind=kind, descriptions=set()))
        if record['issued'] != issued or record['kind'] != kind:
            raise ValueError(f'Conflicting rows for folder {folder}')
        record['addresses'].add(address)
        if description:
            record['descriptions'].add(description)
    for record in folders.values():
        record['addresses']=sorted(record['addresses'])
        record['descriptions']=sorted(record['descriptions'])
    return folders


def reconcile(current, previous, checked_at):
    old = {r['id']:r for r in previous.get('records', [])}
    result = []
    for folder in sorted(old.keys() | current.keys()):
        prior = old.get(folder)
        entry = dict(current.get(folder) or prior)
        periods = [dict(p) for p in prior['periods']] if prior else []
        if folder in current:
            if not periods or periods[-1].get('first_absent'):
                periods.append({'first_seen':checked_at, 'last_seen':checked_at})
            else:
                periods[-1]['last_seen'] = checked_at
        elif not periods[-1].get('first_absent'):
            periods[-1]['first_absent'] = checked_at
        entry['periods'] = periods
        result.append(entry)
    return result


def main():
    previous = json.loads(OUT.read_text()) if OUT.exists() else {}
    rows, pages = fetch_pages()
    folders = group_folders(rows)
    if previous and (len(folders) < 0.8 * previous['listed_folders'] or
                     len(rows) < 0.8 * previous['source_rows']):
        raise ValueError('Permit source lost over 20% of rows or listed folders; review before publication')
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    snapshot = {'source':URL,'rules':RULES,'checked_at':now,
                'baseline_at':previous.get('baseline_at',now),'source_pages':pages,
                'source_rows':len(rows),'listed_folders':len(folders),'records':reconcile(folders,previous,now)}
    tmp=OUT.with_suffix('.tmp')
    tmp.write_text(json.dumps(snapshot,ensure_ascii=False,separators=(',',':'))+'\n')
    tmp.replace(OUT)
    print(f'Retrieved {len(rows)} rows for {len(folders)} active permit folders')


if __name__ == '__main__':
    main()
