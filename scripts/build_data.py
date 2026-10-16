#!/usr/bin/env python3
"""Build the public map from cached, source-bound store coordinates. Python 3.10+."""
from __future__ import annotations
import argparse,csv,json,math
from pathlib import Path
from collections import Counter,defaultdict
from datetime import datetime,timezone,timedelta
import geography

ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
def distance(a,b):return geography.distance_km(a['lon'],a['lat'],b['lon'],b['lat'])
def build(cache,output,repo_url=''):
    boundaries=cache/'geography/provinces.geojson'
    lookup=lambda s:geography.lookup(s['lon'],s['lat'],boundaries)
    stores=[];excluded=[];seen=set()
    official=read(cache/'official/official-normalized.json')
    a101_path=cache/'a101/a101-normalized.json'
    official.extend(read(a101_path if a101_path.exists() else ROOT/'data/a101-source-snapshot.json'))
    for s in official:
        p=lookup(s)
        if not p:excluded.append({'id':s['id'],'reason':'outside_province_polygons'});continue
        key=(s['brand'],s['lat'],s['lon'])
        if key in seen:excluded.append({'id':s['id'],'reason':'duplicate_brand_coordinate'});continue
        seen.add(key)
        stores.append({k:s[k] for k in ('id','brand','name','lat','lon','address','district','source','source_url','coordinate_type')}|p|{'checked_at':s['checked_at']})
    officialgrid=defaultdict(list)
    for s in stores:officialgrid[(s['brand'],math.floor(s['lon']*100),math.floor(s['lat']*100))].append(s)
    osm=read(cache/'osm/stores-normalized.json');grid=defaultdict(list)
    for s in osm['stores']:
        p=lookup(s)
        if not p:excluded.append({'id':s['id'],'reason':'outside_province_polygons'});continue
        ax,ay=math.floor(s['lon']*100),math.floor(s['lat']*100)
        matches=[n for x in range(ax-1,ax+2) for y in range(ay-1,ay+2) for n in officialgrid[(s['brand'],x,y)] if distance(s,n)<.025]
        if matches:
            match=min(matches,key=lambda n:distance(s,n));match.setdefault('additional_sources',[]).append(s['osmUrl'])
            excluded.append({'id':s['id'],'reason':'official_same_brand_within_25m','matched_id':match['id']});continue
        gx,gy=math.floor(s['lon']*2000),math.floor(s['lat']*2000)
        nearby=[n for x in range(gx-1,gx+2) for y in range(gy-1,gy+2) for n in grid[(s['brand'],x,y)]]
        if any(distance(s,n)<.012 for n in nearby):excluded.append({'id':s['id'],'reason':'same_brand_osm_within_12m'});continue
        grid[(s['brand'],gx,gy)].append(s)
        stores.append({'id':s['id'],'brand':s['brand'],'name':s['name'],'lat':s['lat'],'lon':s['lon'],'address':s.get('address',''),'district':s.get('addressTags',{}).get('addr:district',''),'source':'OpenStreetMap','source_url':s['osmUrl'],'coordinate_type':'node' if s['coordinateType']=='osm_node' else 'area_center','source_edited_at':s.get('osmTimestamp'),**p})
    # Small, reviewed factual corrections require a directly inspected source URL.
    corrections=read(ROOT/'data/verified-corrections.json')
    for s in corrections:
        p=lookup(s)
        if not p:raise ValueError('Correction lies outside Turkey province polygons: '+s['id'])
        if not s.get('source_url','').startswith('https://') or not s.get('checked_at'):raise ValueError('Correction needs a checked source: '+s['id'])
        if any(n['brand']==s['brand'] and distance(n,s)<.04 for n in stores):continue
        stores.append(s|p)
    places=read(cache/'osm/places-normalized.json')['places'];placegrid=defaultdict(list)
    for p in places:
        loc=lookup(p)
        if loc:placegrid[(math.floor(p['lon']*10),math.floor(p['lat']*10))].append(p|loc)
    geonames=read(cache/'geography/settlements.json')['records'];geogrid=defaultdict(list)
    for p in geonames:geogrid[(math.floor(p['lon']*10),math.floor(p['lat']*10))].append(p)
    for s in stores:
        gx,gy=math.floor(s['lon']*10),math.floor(s['lat']*10)
        nearby=[p for x in range(gx-1,gx+2) for y in range(gy-1,gy+2) for p in placegrid[(x,y)] if p['province_code']==s['province_code']]
        if nearby:
            p=min(nearby,key=lambda p:distance(s,p));d=distance(s,p)
            if d<=2:s['locality']={'name':p['name'],'type':p.get('type',p.get('place')),'distance_km':round(d,3),'source_url':p.get('osmUrl','https://www.openstreetmap.org')}
        nearby=[p for x in range(gx-1,gx+2) for y in range(gy-1,gy+2) for p in geogrid[(x,y)] if p['provinceCode']==s['province_code']]
        if nearby:
            p=min(nearby,key=lambda p:distance(s,p));d=distance(s,p)
            if d<5:s['nearby_place']=p['name']
    assert len({s['id'] for s in stores})==len(stores),'Duplicate source IDs'
    assert all(math.isfinite(s['lat']) and math.isfinite(s['lon']) and s['source_url'].startswith('https://') for s in stores)
    assert set(s['brand'] for s in stores)=={'A101','BİM','ŞOK','Migros'}
    date=datetime.now(timezone(timedelta(hours=3))).strftime('%d.%m.%Y')
    meta={'retrieved_at':date,'brands':dict(Counter(s['brand'] for s in stores)),'sources':dict(Counter(s['source'] for s in stores)),'coordinate_types':dict(Counter(s['coordinate_type'] for s in stores)),'province_count':len({s['province_code'] for s in stores}),'has_localities':True,'small_locality_store_count':sum(bool(s.get('locality')) for s in stores),'repo_url':repo_url,
          'coverage_note':'Bu harita tam şube envanteri değildir. A101 için kısmi resmî veri ile OpenStreetMap, BİM için OpenStreetMap kullanılır; kapsam eksiktir. ŞOK ve Migros koordinatları resmî mağaza bulucularından alınır. Pin olmaması mağaza olmadığı anlamına gelmez. Kaynaklarda eski, taşınmış veya hatalı konumlar bulunabilir; tüm şubeler sahada doğrulanmış sayılmaz.',
          'licenses':{'OpenStreetMap':'ODbL 1.0 © OpenStreetMap contributors','province_boundaries':'OSM-derived, ODbL; theaiagent/turkiye_iller_geojson / cihadturhan/tr-geojson','nearby_place_names':'GeoNames CC BY 4.0'},
          'osm_source':osm.get('metadata',{})}
    payload={'metadata':meta,'stores':stores};output.mkdir(parents=True,exist_ok=True)
    write(output/'data.json',payload)
    (output/'data.js').write_text('window.MARKET_DATA='+json.dumps(payload,ensure_ascii=False,separators=(',',':'))+';',encoding='utf-8')
    with (output/'markets.csv').open('w',encoding='utf-8-sig',newline='') as f:
        fields=['brand','name','province','province_code','district','region','lat','lon','address','source','source_url','coordinate_type','nearby_place']
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(stores)
    write(ROOT/'data/build-report.json',{'metadata':meta,'excluded_count':len(excluded),'excluded':excluded})
    print(json.dumps({'stores':len(stores),'brands':meta['brands'],'provinces':meta['province_count'],'regions':dict(Counter(s['region'] for s in stores)),'excluded':len(excluded)},ensure_ascii=True))
    return payload
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cache',type=Path,default=ROOT/'.cache');p.add_argument('--output',type=Path,default=ROOT/'docs');p.add_argument('--repo-url',default='');a=p.parse_args();build(a.cache,a.output,a.repo_url)
