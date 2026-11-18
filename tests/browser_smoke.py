"""CI checks real bundled data and project-subpath flows; external tiles are stubbed."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json, shutil, tempfile, threading
from urllib.parse import parse_qs, urlsplit
from playwright.sync_api import sync_playwright, expect
ROOT=Path(__file__).resolve().parents[1]
class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self,*args): pass

def main():
    slug=json.loads((ROOT/'tool.json').read_text())['id']
    shots=ROOT/'browser-checks'; shots.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as temp:
        shutil.copytree(ROOT/'dist',Path(temp)/slug)
        server=ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=temp))
        threading.Thread(target=server.serve_forever,daemon=True).start()
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch(); page=browser.new_page(viewport={'width':1440,'height':1050})
                errors=[]; page.on('pageerror',lambda e:errors.append(str(e)))
                svg='<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256"><rect width="256" height="256" fill="#dce4d5"/></svg>'
                page.route('https://tile.openstreetmap.org/**',lambda r:r.fulfill(content_type='image/svg+xml',body=svg))
                wms=[]
                def imagery(route):
                    q=parse_qs(urlsplit(route.request.url).query)
                    assert q.get('layers')==['halifax'] and q.get('time') in [['1947-07-01T12:00:00Z'],['1977-07-01T12:00:00Z']]
                    wms.append(q); route.fulfill(content_type='image/svg+xml',body=svg)
                page.route('https://datacube.services.geo.ca/ows/aerial*',imagery)
                base=f'http://127.0.0.1:{server.server_port}/{slug}/'
                page.goto(base)
                if slug=='halifaxtimelens':
                    expect(page.locator('#status')).to_contain_text('Comparison ready')
                    assert {q['time'][0][:4] for q in wms}=={'1947','1977'}
                    page.locator('#reveal').fill('70')
                    assert '70%' in page.locator('#right-map').get_attribute('style')
                    page.locator('#right-year').select_option('streets')
                    expect(page.locator('#right-label')).to_have_text('Modern street map')
                    page.locator('[data-place="dartmouth"]').click()
                    expect(page.locator('#place-title')).to_have_text('Downtown Dartmouth')
                    page.locator('#share').click(); url=page.locator('#share-url').input_value()
                    assert 'right=streets' in url and 'split=70' in url
                    page.goto(url); expect(page.locator('#right-year')).to_have_value('streets')
                    expect(page.locator('#reveal')).to_have_value('70')
                    page.locator('#swap').click(); expect(page.locator('#left-year')).to_have_value('streets')
                elif slug=='hiddenwater':
                    page.locator('.result').first.wait_for()
                    page.locator('#in-view').uncheck(); page.locator('#query').fill('Yorkson')
                    page.locator('#filters button[type="submit"]').click()
                    page.locator('.result').first.wait_for(); assert 'Yorkson' in page.locator('.result').first.inner_text()
                    page.locator('.result').first.click(); page.locator('#detail h2').wait_for()
                    page.get_by_role('button',name='Share this segment').click()
                    url=page.locator('#share-url').input_value(); assert '#record=' in url
                    with page.expect_download() as info:page.locator('#geojson').click()
                    data=json.loads(Path(info.value.path()).read_text()); assert data['features'] and data['sources']
                    page.goto(url); page.locator('#detail h2').wait_for()
                    page.locator('#query').fill('nonexistentwaterwayzzzz'); page.locator('#filters button[type="submit"]').click()
                    expect(page.locator('#status')).to_contain_text('No matching'); assert page.locator('#csv').is_disabled()
                    page.locator('[data-place="city"]').click(); page.locator('.result').first.wait_for()
                else:
                    page.locator('.result').first.wait_for(); expect(page.locator('#count')).to_have_text(f"{len(json.loads((ROOT/'web/data/applications.json').read_text())['records']):,}")
                    page.locator('#changed').check(); assert int(page.locator('#count').inner_text().replace(',','')) <= len(json.loads((ROOT/'web/data/applications.json').read_text())['records'])
                    page.locator('#city-preset').click(); page.locator('.result').first.wait_for()
                    assert '0 Township' in page.locator('#map-caption').inner_text()
                    page.locator('.result').first.click(); page.locator('#detail h2').wait_for()
                    page.get_by_role('button',name='☆ Save application',exact=True).click()
                    page.locator('#saved').check(); expect(page.locator('.result')).to_have_count(1)
                    page.get_by_role('button',name='Share',exact=True).click(); url=page.locator('#share-url').input_value()
                    page.goto(url); page.get_by_role('button',name='★ Remove from saved',exact=True).wait_for()
                    with page.expect_download() as info:page.locator('#csv').click()
                    assert 'snapshot_retrieved' in Path(info.value.path()).read_text()
                    page.locator('#query').fill('nonexistentprojectzzzz'); page.locator('#filters button[type="submit"]').click()
                    expect(page.locator('#status')).to_contain_text('No matching')
                    page.locator('#willoughby').click(); page.locator('.result').first.wait_for()
                page.screenshot(path=str(shots/'desktop.png'),full_page=True)
                page.set_viewport_size({'width':390,'height':844})
                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), 'Mobile page overflows horizontally'
                page.screenshot(path=str(shots/'mobile.png'),full_page=True)
                if slug!='halifaxtimelens':
                    page.route('**/data/*.json',lambda r:r.fulfill(status=503,body='Unavailable'))
                    page.reload(); expect(page.locator('#status')).to_contain_text('could not load')
                assert not errors, errors
                browser.close()
            print('Browser flows, source links, exports, saved/deep-link state, failure handling and mobile layout passed')
        finally:server.shutdown()
if __name__=='__main__': main()
