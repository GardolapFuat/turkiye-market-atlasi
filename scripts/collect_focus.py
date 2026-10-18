#!/usr/bin/env python3
"""Read 12 public province pages; no Google scraping, geocoding or private APIs."""
import argparse, hashlib, html, json, re, time
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
PROVINCES = {'balikesir': 'Balıkesir', 'canakkale': 'Çanakkale', 'izmir': 'İzmir',
             'mugla': 'Muğla', 'aydin': 'Aydın', 'bursa': 'Bursa'}
BASE = 'https://enyakinsubesi.com'

def plain(value):
    return html.unescape(re.sub('<[^>]+>', '', value)).strip()

def parse_page(content, slug, brand):
    records, excluded = [], []
    for article in re.findall(r'<article\b[^>]*>(.*?)</article>', content, re.S):
        title = re.search(r'<h4\b[^>]*>\s*<a href="([^"]+)"[^>]*>(.*?)</a>', article, re.S)
        coord = re.search(r'destination=([-\d.]+),([-\d.]+)', article)
        address = re.search(r'>Adres</span>\s*<span[^>]*>(.*?)</span>', article, re.S)
        locality = re.search(r'</h4>\s*<p[^>]*>(.*?)</p>', article, re.S)
        if not title or not coord or not address or not locality:
            excluded.append({'url': title.group(1) if title else '', 'reason': 'missing_fields'})
            continue
        source_url = html.unescape(title.group(1))
        if not source_url.startswith(f'{BASE}/{brand}/{slug}/'):
            raise ValueError('Unexpected source URL: ' + source_url)
        lat, lon = map(float, coord.groups())
        location = plain(locality.group(1)).rsplit(',', 1)
        if len(location) != 2 or location[1].strip() != PROVINCES[slug]:
            excluded.append({'url': source_url, 'reason': 'province_label_mismatch'})
            continue
        if not (35 < lat < 43 and 25 < lon < 46):
            excluded.append({'url': source_url, 'reason': 'invalid_coordinate'})
            continue
        name = plain(title.group(2))
        records.append({'id': 'directory-' + hashlib.sha256(source_url.encode()).hexdigest()[:16],
                        'brand': 'A101' if brand == 'a101' else 'BİM',
                        'name': ('A101 ' if brand == 'a101' else 'BİM ') + name,
                        'lat': lat, 'lon': lon, 'address': plain(address.group(1)),
                        'district': location[0].strip(), 'expected_province': PROVINCES[slug],
                        'source': 'En Yakın Şubesi · ek dizin kaydı', 'source_url': source_url,
                        'coordinate_type': 'directory', 'checked_at': '2026-10-18',
                        'verification': 'Kaynak sayfasındaki koordinat ve il/ilçe alanları kontrol edildi; bağımsız saha doğrulaması değildir.'})
    expected = re.search(r'"numberOfItems"\s*:\s*(\d+)', content)
    if expected and int(expected.group(1)) != len(records) + len(excluded):
        raise ValueError(f'Page inventory mismatch: {brand}/{slug}')
    if not records:
        raise ValueError(f'No records: {brand}/{slug}')
    return records, excluded

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cached-only', action='store_true')
    args = parser.parse_args()
    cache = ROOT / '.cache/focus-pages'
    cache.mkdir(parents=True, exist_ok=True)
    rows, exclusions, pages = [], [], []
    for slug in PROVINCES:
        for brand in ('a101', 'bim'):
            url = f'{BASE}/{brand}/{slug}'
            path = cache / f'{brand}-{slug}.html'
            if not path.exists():
                if args.cached_only:
                    raise FileNotFoundError(path)
                try:
                    with urlopen(Request(url, headers={'User-Agent': 'TurkeyMarketAtlas/1.0 (public province pages)'}), timeout=35) as response:
                        data = response.read()
                except HTTPError as error:
                    if error.code in (403, 429):
                        raise SystemExit(f'Access limited ({error.code}); collection stopped without retries.')
                    raise
                path.write_bytes(data)
                time.sleep(.8)
            content = path.read_text(encoding='utf-8')
            records, skipped = parse_page(content, slug, brand)
            rows.extend(records)
            exclusions.extend(skipped)
            pages.append({'url': url, 'records': len(records), 'excluded': len(skipped),
                          'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
            print(f'{brand}/{slug}: {len(records)} source records', flush=True)
    result = {'metadata': {'checked_at': '2026-10-18', 'provinces': list(PROVINCES.values()),
                           'source': BASE, 'pages': pages,
                           'note': 'Third-party directory, not direct official retrieval or Google Places data. Completeness and current operation are not guaranteed.'},
              'stores': rows, 'excluded': exclusions}
    destination = ROOT / 'data/focus-source-snapshot.json'
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'source_records': len(rows), 'excluded': len(exclusions)}))

if __name__ == '__main__':
    main()
