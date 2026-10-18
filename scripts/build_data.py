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
    # Enrich only the six requested provinces. Existing source coordinates win.
    focus=read(ROOT/'data/focus-source-snapshot.json') if (ROOT/'data/focus-source-snapshot.json').exists() else {'stores':[],'metadata':{'provinces':[]}}
    before=Counter((s['province'],s['brand']) for s in stores)
    focusgrid=defaultdict(list);focus_review=[];focus_merged=[];focus_added=[]
    for s in stores:focusgrid[(s['brand'],math.floor(s['lon']*100),math.floor(s['lat']*100))].append(s)
    for s in focus['stores']:
        p=lookup(s)
        if not p or p['province']!=s['expected_province']:
            focus_review.append({'id':s['id'],'source_url':s['source_url'],'reason':'province_polygon_mismatch'});continue
        gx,gy=math.floor(s['lon']*100),math.floor(s['lat']*100)
        nearby=[n for x in range(gx-1,gx+2) for y in range(gy-1,gy+2) for n in focusgrid[(s['brand'],x,y)]]
        match=min(nearby,key=lambda n:distance(s,n)) if nearby else None
        d=distance(s,match) if match else float('inf')
        if d<.070:
            match.setdefault('additional_sources',[]).append(s['source_url'])
            focus_merged.append({'id':s['id'],'matched_id':match['id'],'distance_m':round(d*1000,1),'source_url':s['source_url']});continue
        if d<.180:
            focus_review.append({'id':s['id'],'source_url':s['source_url'],'reason':'possible_duplicate_70_to_180m','nearby_id':match['id'],'distance_m':round(d*1000,1)});continue
        n={k:v for k,v in s.items() if k!='expected_province'}|p
        if s['source_url']=='https://enyakinsubesi.com/a101/mugla/selimiye':
            n['note']='Kaynak adresi Milas Söke Yolu No:1; kullanıcının Google Maps örneğinde Atatürk Bulvarı No:62-A yazıyor. Kaynak konumları yaklaşık 15 m yakın; adres farkı bağımsız olarak çözümlenmedi.'
        stores.append(n);focus_added.append(n['id']);focusgrid[(s['brand'],gx,gy)].append(n)
    after=Counter((s['province'],s['brand']) for s in stores)
    focus_summary=[{'province':p,'brand':b,'before':before[(p,b)],'after':after[(p,b)],'added':after[(p,b)]-before[(p,b)]} for p in focus['metadata']['provinces'] for b in ('A101','BİM')]
    write(ROOT/'data/focus-report.json',{'checked_at':focus['metadata'].get('checked_at'),'source_records':len(focus['stores']),'added_count':len(focus_added),'merged_count':len(focus_merged),'review_count':len(focus_review),'source_missing_fields':len(focus.get('excluded',[])),'summary':focus_summary,'added_ids':focus_added,'merged':focus_merged,'review':focus_review})
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
          'focus_provinces':focus['metadata']['provinces'],'focus_enrichment':{'checked_at':focus['metadata'].get('checked_at'),'added_count':len(focus_added),'merged_count':len(focus_merged),'review_count':len(focus_review)},
          'coverage_note':'Bu harita tam şube envanteri değildir. Balıkesir, Çanakkale, İzmir, Muğla, Aydın ve Bursa için A101/BİM kapsamı ek bir işletme diziniyle genişletildi. Bu kayıtlar doğrudan resmî veri veya Google Places verisi değildir; kartlarında ek dizin kaydı olarak belirtilir. Diğer illerde önceki veriler korunur. Koordinatsız ve konumu çelişkili ek kayıtlar pine dönüştürülmez. ŞOK ve Migros koordinatları resmî mağaza bulucularından alınır. Pin olmaması mağaza olmadığı anlamına gelmez; tüm şubeler sahada doğrulanmış sayılmaz.',
          'licenses':{'OpenStreetMap':'ODbL 1.0 © OpenStreetMap contributors','province_boundaries':'OSM-derived, ODbL; theaiagent/turkiye_iller_geojson / cihadturhan/tr-geojson','nearby_place_names':'GeoNames CC BY 4.0'},
          'osm_source':osm.get('metadata',{})}
    payload={'metadata':meta,'stores':stores};output.mkdir(parents=True,exist_ok=True)
    write(output/'data.json',payload)
    (output/'data.js').write_text('window.MARKET_DATA='+json.dumps(payload,ensure_ascii=False,separators=(',',':'))+';',encoding='utf-8')
    with (output/'markets.csv').open('w',encoding='utf-8-sig',newline='') as f:
        fields=['brand','name','province','province_code','district','region','lat','lon','address','source','source_url','coordinate_type','nearby_place']
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(stores)
    focus_stores=[s for s in stores if s['province'] in focus['metadata']['provinces']]
    with (output/'focus-markets.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(focus_stores)
    locality_groups=defaultdict(list)
    for s in focus_stores:
        if s.get('locality'):locality_groups[(s['province'],s['locality']['source_url'])].append(s)
    with (output/'focus-localities.csv').open('w',encoding='utf-8-sig',newline='') as f:
        fields=['province','locality','osm_place_type','store_count','brands','a101','bim','sok','migros','directory_records','locality_source_url','atlas_url']
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        from urllib.parse import urlencode
        for (province,url),rows in sorted(locality_groups.items()):
            place=rows[0]['locality'];counts=Counter(s['brand'] for s in rows)
            w.writerow({'province':province,'locality':place['name'],'osm_place_type':place['type'],'store_count':len(rows),'brands':' | '.join(sorted(counts)),'a101':counts['A101'],'bim':counts['BİM'],'sok':counts['ŞOK'],'migros':counts['Migros'],'directory_records':sum(s['coordinate_type']=='directory' for s in rows),'locality_source_url':url,'atlas_url':'https://gardolapfuat.github.io/turkiye-market-atlasi/#'+urlencode({'region':'focus','province':province,'q':place['name'],'small':'1'})})
    write(ROOT/'data/build-report.json',{'metadata':meta,'excluded_count':len(excluded),'excluded':excluded})
    print(json.dumps({'stores':len(stores),'brands':meta['brands'],'provinces':meta['province_count'],'regions':dict(Counter(s['region'] for s in stores)),'excluded':len(excluded)},ensure_ascii=True))
    return payload
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cache',type=Path,default=ROOT/'.cache');p.add_argument('--output',type=Path,default=ROOT/'docs');p.add_argument('--repo-url',default='');a=p.parse_args();build(a.cache,a.output,a.repo_url)
