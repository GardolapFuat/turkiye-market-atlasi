#!/usr/bin/env python3
"""Download source-bound OSM A101/BIM stores and locality nodes for Turkey.

Python 3.9+, standard library only. Queries run sequentially and are cached as
raw JSON so the published map never needs to query Overpass during normal use.

Examples:
    python collect_osm.py
    python collect_osm.py --only stores
    python collect_osm.py --offline
    python collect_osm.py --output-dir ./data/osm

The default bounding box encloses Turkey, with a small margin. It also contains
neighboring countries; apply Turkey province polygons downstream. OSM data is
community-maintained and incomplete. No address geocoding, inferred store
coordinates, or claims of current official branch verification are generated.

OSM data: https://www.openstreetmap.org/copyright (ODbL 1.0).
"""

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
import unicodedata
import urllib.parse
import urllib.request


DEFAULT_ENDPOINT = 'https://overpass-api.de/api/interpreter'
DEFAULT_BBOX = (35.7, 25.5, 42.3, 45.0)
BRAND_WIKIDATA = {'Q6034496': 'A101', 'Q1022075': 'BİM'}
SHOP_TYPES = {'supermarket', 'convenience'}


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def ascii_name(value):
    value = value.replace('ı', 'i').replace('İ', 'I').upper()
    return ''.join(c for c in unicodedata.normalize('NFD', value)
                   if unicodedata.category(c) != 'Mn')


def brand_of(tags):
    if tags.get('brand:wikidata') in BRAND_WIKIDATA:
        return BRAND_WIKIDATA[tags['brand:wikidata']]
    for text in (tags.get('brand', ''), tags.get('name', ''), tags.get('operator', '')):
        value = ascii_name(text)
        if re.match(r'^A[ ._-]?101(?:\b|\s|_|$)', value):
            return 'A101'
        if re.match(r'^B[ ._-]*I[ ._-]*M(?:\b|\s|_|$)', value):
            return 'BİM'
    return None


def queries(bbox):
    bounds = ','.join(str(v) for v in bbox)
    pattern = '^(A[ ._-]?101|B[ ._-]*[İIıi][ ._-]*M)'
    stores = f'''[out:json][timeout:240];
(
 nwr["shop"~"^(supermarket|convenience)$"]["name"~"{pattern}",i]({bounds});
 nwr["shop"~"^(supermarket|convenience)$"]["brand"~"{pattern}",i]({bounds});
 nwr["shop"~"^(supermarket|convenience)$"]["brand:wikidata"~"^(Q6034496|Q1022075)$"]({bounds});
);
out meta center;
'''
    places = f'''[out:json][timeout:240];
node["place"~"^(village|town|hamlet)$"]({bounds});
out meta;
'''
    return {'stores': stores, 'places': places}


def write_json(path, value, indent=None):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=indent,
                               separators=None if indent else (',', ':')), encoding='utf-8')


def collect(kind, query, output, endpoint, bbox, timeout, offline):
    raw_path = output / f'raw-{kind}.json'
    (output / f'query-{kind}.overpass').write_text(query, encoding='utf-8')
    if offline:
        return json.loads(raw_path.read_text(encoding='utf-8-sig'))
    # GET works with standard-library TLS on Windows. This is one request per
    # dataset, with no automatic retries or parallel Overpass queries.
    url = endpoint + '?' + urllib.parse.urlencode({'data': query})
    request = urllib.request.Request(url, headers={
        'User-Agent': 'TurkiyeMarketAtlasi/1.0 (cached public OSM data collector)',
        'Accept': 'application/json',
    })
    print(f'Fetching {kind}...', flush=True)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read()
    raw = json.loads(body)
    if raw.get('remark'):
        # A timeout can return HTTP 200 with partial elements. Do not silently
        # publish a partial result as a completed collection.
        raise RuntimeError(f'Overpass returned a remark: {raw["remark"]}')
    if not isinstance(raw.get('elements'), list):
        raise ValueError('Overpass response has no elements array')
    raw_path.write_bytes(body)
    write_json(output / f'retrieval-{kind}.json', {
        'fetchedAt': utc_now(), 'endpoint': endpoint, 'bbox': list(bbox),
        'bytes': len(body), 'osmBaseTimestamp': raw.get('osm3s', {}).get('timestamp_osm_base'),
    }, indent=2)
    print(f'{kind}: {len(body):,} bytes; {len(raw["elements"]):,} raw objects', flush=True)
    return raw


def common_metadata(kind, raw, output, endpoint, bbox):
    retrieval_path = output / f'retrieval-{kind}.json'
    retrieval = json.loads(retrieval_path.read_text(encoding='utf-8')) if retrieval_path.exists() else {}
    return {
        'fetchedAt': retrieval.get('fetchedAt'),
        'osmBaseTimestamp': raw.get('osm3s', {}).get('timestamp_osm_base'),
        'source': 'OpenStreetMap via Overpass API', 'endpoint': endpoint,
        'license': 'ODbL 1.0', 'copyright': '© OpenStreetMap contributors',
        'bbox': list(bbox), 'query': f'query-{kind}.overpass',
        'rawCount': len(raw.get('elements', [])),
    }


def normalize_stores(raw, output, endpoint, bbox):
    stores, excluded = [], []
    for element in raw.get('elements', []):
        tags = element.get('tags', {})
        reason = None
        if (tags.get('abandoned') == 'yes' or tags.get('disused') == 'yes'
                or tags.get('opening_hours') in ('closed', 'off')
                or any(tags.get(key) in SHOP_TYPES for key in
                       ('abandoned:shop', 'disused:shop', 'demolished:shop', 'removed:shop'))):
            reason = 'OSM tagged abandoned, disused, removed or closed'
        brand = brand_of(tags)
        if not reason and not brand:
            reason = 'Brand ambiguous'
        point = element if element['type'] == 'node' else element.get('center', {})
        if not reason and not all(isinstance(point.get(k), (float, int))
                                  and math.isfinite(point[k]) for k in ('lat', 'lon')):
            reason = 'Missing or invalid source coordinate'
        if reason:
            excluded.append({'type': element['type'], 'id': element['id'],
                             'tags': tags, 'reason': reason})
            continue
        address_tags = {k: v for k, v in tags.items() if k.startswith('addr:')}
        street = ' '.join(tags[k] for k in ('addr:street', 'addr:housenumber') if tags.get(k))
        locality = ', '.join(dict.fromkeys(tags[k] for k in (
            'addr:suburb', 'addr:quarter', 'addr:neighbourhood', 'addr:village',
            'addr:town', 'addr:district', 'addr:city', 'addr:province') if tags.get(k)))
        address = tags.get('addr:full') or ', '.join(p for p in (street, locality) if p)
        stores.append({
            'id': f'osm-{element["type"]}-{element["id"]}',
            'osmType': element['type'], 'osmId': element['id'],
            'osmVersion': element.get('version'), 'osmTimestamp': element.get('timestamp'),
            'brand': brand, 'name': tags.get('name') or tags.get('brand') or brand,
            'lat': point['lat'], 'lon': point['lon'],
            'coordinateType': 'osm_node' if element['type'] == 'node'
                else f'osm_{element["type"]}_bbox_center',
            'address': address, 'addressTags': address_tags,
            'osmUrl': f'https://www.openstreetmap.org/{element["type"]}/{element["id"]}',
            'source': 'OpenStreetMap',
            'verification': 'community_mapped_not_officially_revalidated', 'tags': tags,
        })
    metadata = common_metadata('stores', raw, output, endpoint, bbox)
    metadata.update({
        'count': len(stores), 'brands': dict(Counter(s['brand'] for s in stores)),
        'coordinateTypes': dict(Counter(s['coordinateType'] for s in stores)),
        'coverageNote': 'Turkey bounding box, also including neighboring countries. '
            'Apply Turkey province polygons downstream. OSM coverage is incomplete. '
            'No geocoded or inferred store coordinates are added. Ways/relations use '
            'the bounding box center returned by Overpass, not a surveyed entrance.',
        'verificationNote': 'Existing OSM source coordinates were retrieved. Current '
            'operation and official branch status have not been independently confirmed.',
        'excludedCount': len(excluded),
    })
    write_json(output / 'stores-normalized.json', {'metadata': metadata, 'stores': stores})
    write_json(output / 'excluded-stores.json', excluded, indent=2)
    print(json.dumps(metadata, ensure_ascii=False), flush=True)


def normalize_places(raw, output, endpoint, bbox):
    places = []
    for e in raw.get('elements', []):
        tags = e.get('tags', {})
        if not tags.get('name') or not all(k in e for k in ('lat', 'lon')):
            continue
        places.append({
            'id': f'osm-{e["type"]}-{e["id"]}', 'osmId': e['id'],
            'name': tags['name'], 'lat': e['lat'], 'lon': e['lon'],
            'type': tags.get('place'), 'timestamp': e.get('timestamp'), 'tags': tags,
            'osmUrl': f'https://www.openstreetmap.org/{e["type"]}/{e["id"]}',
        })
    metadata = common_metadata('places', raw, output, endpoint, bbox)
    metadata.update({'count': len(places), 'types': dict(Counter(p['type'] for p in places)),
        'note': 'OSM village/town/hamlet tags are community classifications, not current '
            'official Turkish administrative status. Place nodes are locality center '
            'labels, not boundaries. The bbox also includes neighboring countries.'})
    write_json(output / 'places-normalized.json', {'metadata': metadata, 'places': places})
    print(json.dumps(metadata, ensure_ascii=False), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--endpoint', default=DEFAULT_ENDPOINT)
    parser.add_argument('--bbox', type=float, nargs=4, default=DEFAULT_BBOX,
                        metavar=('SOUTH', 'WEST', 'NORTH', 'EAST'))
    parser.add_argument('--only', choices=('all', 'stores', 'places'), default='all')
    parser.add_argument('--timeout', type=float, default=300)
    parser.add_argument('--offline', action='store_true', help='Normalize saved raw JSON without network')
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for kind, query in queries(args.bbox).items():
        if args.only not in ('all', kind):
            continue
        raw = collect(kind, query, args.output_dir, args.endpoint, args.bbox, args.timeout, args.offline)
        normalizer = normalize_stores if kind == 'stores' else normalize_places
        normalizer(raw, args.output_dir, args.endpoint, args.bbox)


if __name__ == '__main__':
    main()
