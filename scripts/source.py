"""Small, bounded ArcGIS reader. Reject partial responses rather than publish them."""
import json
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen

def read(url):
    for attempt in range(3):
        try:
            with urlopen(Request(url, headers={'User-Agent':'CoolCode public-data explorer; https://coolcode.ca/'}), timeout=60) as response:
                data = json.load(response)
            if 'error' in data:
                raise ValueError(f"Source error: {data['error']}")
            return data
        except (OSError, ValueError):
            if attempt == 2: raise
            time.sleep(2 ** attempt)

def features(url, fields, where='1=1'):
    def query(**params):
        return read(url + '/query?' + urlencode(dict(where=where, **params)))
    expected = query(returnCountOnly='true', f='json')['count']
    if not 1 <= expected <= 100000:
        raise ValueError(f'Unexpected source count: {expected}')
    found = []
    for offset in range(0, expected, 1000):
        data = query(outFields=fields, outSR=4326, f='geojson', orderByFields='OBJECTID',
                     resultOffset=offset, resultRecordCount=1000, geometryPrecision=6)
        page = data.get('features', [])
        if not page: raise ValueError('Empty page before the expected end')
        found.extend(page)
    if len(found) != expected or len({f['id'] for f in found}) != expected:
        raise ValueError('Incomplete or duplicate source records')
    return found

def points(coords):
    if coords and isinstance(coords[0], (int,float)):
        yield coords[:2]
    else:
        for child in coords: yield from points(child)

def bounds(geometry):
    coords = list(points(geometry['coordinates']))
    if not coords or not all(-123.2 < x < -122 and 48.8 < y < 49.5 for x,y in coords):
        raise ValueError('Geometry outside Langley region')
    return [min(x for x,y in coords),min(y for x,y in coords),max(x for x,y in coords),max(y for x,y in coords)]
