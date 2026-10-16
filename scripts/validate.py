#!/usr/bin/env python3
"""Check public snapshot integrity and the Karabiga coverage regression."""
import json,math,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
d=json.loads((ROOT/'docs/data.json').read_text(encoding='utf-8'))
s=d['stores'];assert s,'Empty snapshot'
assert len({p['id'] for p in s})==len(s),'Duplicate source IDs'
assert len({p['province_code'] for p in s})==81,'Missing provinces'
assert len({p['region'] for p in s})==7,'Missing regions'
assert {p['brand'] for p in s}=={'A101','BİM','ŞOK','Migros'}
assert all(math.isfinite(p['lat']) and math.isfinite(p['lon']) and p['source_url'].startswith('https://') for p in s)
assert all(35.7<=p['lat']<=42.3 and 25.5<=p['lon']<=45 for p in s)
assert any(p['id']=='a101-I274' and p['coordinate_type']=='official' and abs(p['lat']-40.403607)<1e-7 and abs(p['lon']-27.303282)<1e-7 for p in s),'Karabiga official A101 regression'
js=(ROOT/'docs/data.js').read_text(encoding='utf-8')
assert js.startswith('window.MARKET_DATA=') and js.endswith(';')
assert json.loads(js[len('window.MARKET_DATA='):-1])==d,'JSON/JS snapshots differ'
html=(ROOT/'docs/index.html').read_text(encoding='utf-8')
for src in re.findall(r'(?:src|href)="([^"]+)"',html):
    if not src.startswith(('http','#')) and not (ROOT/'docs'/src).exists():raise AssertionError('Missing asset '+src)
print('Snapshot and assets valid:',len(s),'pins,81 provinces,7 regions; Karabiga official A101 present.')
