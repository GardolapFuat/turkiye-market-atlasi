"""Reproducible Turkey province/settlement references, using the Python standard library.

Run ``python geography.py --build`` using bundled source snapshots, or
``python geography.py --download --build`` to fetch fresh upstream snapshots.
``lookup(lon, lat)`` uses the normalized local ``provinces.geojson`` file.
No market coordinate is generated or inferred by this module.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1] / '.cache' / 'geography'
PROVINCES_URL = "https://raw.githubusercontent.com/theaiagent/turkiye_iller_geojson/main/turkiye_iller.geojson"
GEONAMES_URL = "https://download.geonames.org/export/dump/TR.zip"
ACTIVE_PLACE_CODES = {"PPL", "PPLA", "PPLA2", "PPLA3", "PPLA4", "PPLC", "PPLL", "PPLX", "PPLS"}


def _write_json(path: Path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def _download(url: str, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "TurkeyMarketMapGeography/1.0"})
    with urllib.request.urlopen(request, timeout=120) as response:
        path.write_bytes(response.read())


def _point_on_segment(x, y, x1, y1, x2, y2, epsilon=1e-10):
    cross = (x-x1)*(y2-y1) - (y-y1)*(x2-x1)
    return abs(cross) <= epsilon and min(x1, x2)-epsilon <= x <= max(x1, x2)+epsilon and min(y1, y2)-epsilon <= y <= max(y1, y2)+epsilon


def _ring_location(ring, x, y):
    """Return 0 outside, 1 inside, 2 on ring boundary."""
    inside = False
    j = len(ring) - 1
    for i, point in enumerate(ring):
        xi, yi = point[:2]
        xj, yj = ring[j][:2]
        if _point_on_segment(x, y, xi, yi, xj, yj):
            return 2
        if (yi > y) != (yj > y) and x < (xj-xi)*(y-yi)/(yj-yi)+xi:
            inside = not inside
        j = i
    return 1 if inside else 0


def _polygon_contains(polygon, x, y):
    outer = _ring_location(polygon[0], x, y)
    if outer == 0:
        return False
    if outer == 2:
        return True
    for hole in polygon[1:]:
        position = _ring_location(hole, x, y)
        if position == 1:
            return False
        if position == 2:
            return True
    return True


@lru_cache(maxsize=4)
def _prepared_provinces(path: str):
    features = json.loads(Path(path).read_text(encoding="utf-8"))["features"]
    result = []
    for feature in features:
        geometry = feature["geometry"]
        polygons = geometry["coordinates"] if geometry["type"] == "MultiPolygon" else [geometry["coordinates"]]
        points = [point for polygon in polygons for ring in polygon for point in ring]
        bounds = (min(p[0] for p in points), min(p[1] for p in points), max(p[0] for p in points), max(p[1] for p in points))
        result.append((feature["properties"], polygons, bounds))
    return result


def lookup(lon: float, lat: float, boundaries_path=None):
    """Return province/province_code/region for the containing polygon, or None.

    Regions approximate geographic regions using entire province polygons.
    No nearest-province fallback is applied. Exact shared-border points return
    the first containing polygon in ascending province-code order.
    """
    lon, lat = float(lon), float(lat)
    if not math.isfinite(lon) or not math.isfinite(lat):
        return None
    path = str(Path(boundaries_path) if boundaries_path else ROOT / "provinces.geojson")
    for properties, polygons, (xmin, ymin, xmax, ymax) in _prepared_provinces(path):
        if xmin <= lon <= xmax and ymin <= lat <= ymax:
            if any(_polygon_contains(polygon, lon, lat) for polygon in polygons):
                return dict(properties)
    return None


def distance_km(lon1, lat1, lon2, lat2):
    """Great-circle distance between supplied coordinates, in kilometres."""
    lon1, lat1, lon2, lat2 = map(math.radians, (lon1, lat1, lon2, lat2))
    a = math.sin((lat2-lat1)/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin((lon2-lon1)/2)**2
    return 6371.0088 * 2 * math.asin(min(1.0, math.sqrt(a)))


class SettlementIndex:
    """A compact grid index for approximate proximity to GeoNames place points.

    The nearest point supplies geographic context, not administrative membership,
    legal village/belde status, population classification, or a shop coordinate.
    """

    def __init__(self, path=None, cell_size=0.1):
        self.cell_size = cell_size
        data = json.loads((Path(path) if path else ROOT / "settlements.json").read_text(encoding="utf-8"))
        self.records = data["records"]
        self.grid = {}
        for record in self.records:
            key = self._cell(record["lon"], record["lat"])
            self.grid.setdefault(key, []).append(record)

    def _cell(self, lon, lat):
        return math.floor(lon/self.cell_size), math.floor(lat/self.cell_size)

    def nearest(self, lon, lat, max_distance_km=5.0, province_code=None, feature_codes=None):
        """Return nearest supplied place within radius, with distance_km, or None.

        province_code optionally prevents same-name/cross-border confusion.
        feature_codes optionally restricts which GeoNames codes are eligible.
        """
        lon, lat = float(lon), float(lat)
        if max_distance_km <= 0:
            return None
        dy = max_distance_km/110.0
        dx = max_distance_km/(110.0*max(0.1, math.cos(math.radians(lat))))
        xmin, ymin = self._cell(lon-dx, lat-dy)
        xmax, ymax = self._cell(lon+dx, lat+dy)
        best, best_distance = None, max_distance_km
        for ix in range(xmin, xmax+1):
            for iy in range(ymin, ymax+1):
                for record in self.grid.get((ix, iy), []):
                    if province_code and record["provinceCode"] != str(province_code).zfill(2):
                        continue
                    if feature_codes and record["featureCode"] not in feature_codes:
                        continue
                    distance = distance_km(lon, lat, record["lon"], record["lat"])
                    if distance <= best_distance:
                        best, best_distance = record, distance
        return {**best, "distance_km": round(best_distance, 3)} if best else None


def build(download=False):
    source_dir = ROOT / "source"
    source_dir.mkdir(parents=True, exist_ok=True)
    raw_provinces = source_dir / "provinces-raw.geojson"
    raw_places = source_dir / "geonames-TR.zip"
    if download:
        _download(PROVINCES_URL, raw_provinces)
        _download(GEONAMES_URL, raw_places)
    if not raw_provinces.exists() or not raw_places.exists():
        raise FileNotFoundError("Source snapshots missing. Run geography.py --download --build.")

    raw = json.loads(raw_provinces.read_text(encoding="utf-8"))
    normalized = {"type": "FeatureCollection", "features": []}
    for feature in raw["features"]:
        original = feature["properties"]
        code = str(original["il_kodu"]).zfill(2)
        normalized["features"].append({"type": "Feature", "id": code,
            "properties": {"province": original["il_adi"], "province_code": code, "region": original["bolge"]},
            "geometry": feature["geometry"]})
    normalized["features"].sort(key=lambda f: f["id"])
    expected_codes = {f"{i:02d}" for i in range(1, 82)}
    actual_codes = {feature["id"] for feature in normalized["features"]}
    if actual_codes != expected_codes or len(normalized["features"]) != 81:
        raise ValueError("Expected exactly the 81 Turkish province codes.")
    _write_json(ROOT / "provinces.geojson", normalized)
    _prepared_provinces.cache_clear()

    with zipfile.ZipFile(raw_places) as archive:
        rows = archive.read("TR.txt").decode("utf-8").splitlines()
        (source_dir / "geonames-readme.txt").write_bytes(archive.read("readme.txt"))
    records = []
    for line in rows:
        row = line.split("\t")
        if row[6] != "P" or row[7] not in ACTIVE_PLACE_CODES or row[8] != "TR":
            continue
        lat, lon = float(row[4]), float(row[5])
        location = lookup(lon, lat)
        records.append({"id": int(row[0]), "name": row[1], "lat": lat, "lon": lon,
            "featureCode": row[7], "recordedPopulation": int(row[14]) or None,
            "recordUpdated": row[18], "geonamesAdmin1Code": row[10],
            "province": location["province"] if location else None,
            "provinceCode": location["province_code"] if location else None,
            "region": location["region"] if location else None})
    records.sort(key=lambda r: r["id"])
    metadata = {"source": GEONAMES_URL,
        "sourceLicense": "CC BY 4.0 https://creativecommons.org/licenses/by/4.0/",
        "retrievedDate": "2026-10-17" if not download else datetime.now(timezone.utc).date().isoformat(),
        "description": "Populated-place reference points, not shop locations or official village classifications. Coordinates are preserved. Population can be stale or missing; source population 0 becomes null. Province and region are spatially assigned from approximate province polygons; unmatched points retain null assignment.",
        "records": records}
    _write_json(ROOT / "settlements.json", metadata)
    manifest = {"builtDateUtc": datetime.now(timezone.utc).date().isoformat(),
        "provinceCount": 81,
        "provinceRegionCounts": dict(Counter(f["properties"]["region"] for f in normalized["features"])),
        "settlementCount": len(records),
        "settlementFeatureCodeCounts": dict(Counter(r["featureCode"] for r in records)),
        "settlementRegionCounts": dict(Counter(r["region"] or "Unassigned" for r in records)),
        "settlementsWithRecordedPopulation": sum(r["recordedPopulation"] is not None for r in records),
        "unassignedSettlementIds": [r["id"] for r in records if not r["provinceCode"]],
        "sources": [{"url": PROVINCES_URL, "file": "source/provinces-raw.geojson", "sha256": hashlib.sha256(raw_provinces.read_bytes()).hexdigest(), "license": "ODbL 1.0; OpenStreetMap contributors via cihadturhan/tr-geojson and theaiagent/turkiye_iller_geojson"},
                    {"url": GEONAMES_URL, "file": "source/geonames-TR.zip", "sha256": hashlib.sha256(raw_places.read_bytes()).hexdigest(), "license": "CC BY 4.0; GeoNames"}]}
    _write_json(ROOT / "manifest.json", manifest)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", action="store_true", help="Normalize local source snapshots")
    parser.add_argument("--download", action="store_true", help="Download source snapshots before building")
    parser.add_argument("--lookup", nargs=2, type=float, metavar=("LON", "LAT"))
    parser.add_argument("--nearest", nargs=2, type=float, metavar=("LON", "LAT"))
    parser.add_argument("--radius", type=float, default=5.0)
    args = parser.parse_args()
    if args.build or args.download:
        print(json.dumps(build(download=args.download), ensure_ascii=True, indent=2))
    if args.lookup:
        print(json.dumps(lookup(*args.lookup), ensure_ascii=True))
    if args.nearest:
        print(json.dumps(SettlementIndex().nearest(*args.nearest, max_distance_km=args.radius), ensure_ascii=True))
    if not (args.build or args.download or args.lookup or args.nearest):
        parser.print_help()


if __name__ == "__main__":
    main()

