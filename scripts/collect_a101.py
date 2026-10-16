#!/usr/bin/env python3
"""Collect A101's public official nearest-store coordinates with adaptive coverage.

Python 3.10+ standard library only. The official locator returns at most 20
nearby stores for a geohash. This collector queries geographic tiles and splits
tiles where that cap can hide stores. It never fabricates or geocodes a pin.
No account, cookie, Google key, or other credential is used.
"""

from __future__ import annotations

import argparse
import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
import json
import math
from pathlib import Path
import random
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

VERSION = "1.0.1"
API = "https://rio.a101.com.tr/dbmk89vnr/CALL/StoreContentManager/nearestStores/default"
LOCATOR = "https://www.a101.com.tr/en-yakin-magazalar"
ALPHABET = "0123456789bcdefghjkmnpqrstuvwxyz"
STOP_AFTER_FORBIDDEN = threading.Event()


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def geohash(lat, lon, precision=9):
    bounds, coords, bits = [[-180.0, 180.0], [-90.0, 90.0]], [lon, lat], []
    for index in range(precision * 5):
        axis = index % 2
        midpoint = sum(bounds[axis]) / 2
        bit = int(coords[axis] >= midpoint)
        bits.append(bit)
        bounds[axis][1 - bit] = midpoint
    return "".join(ALPHABET[sum(bits[index + offset] << (4 - offset) for offset in range(5))]
                   for index in range(0, precision * 5, 5))


def url_for(lat, lon):
    body = json.dumps({"geoHash": geohash(lat, lon)}, sort_keys=True, separators=(",", ":"))
    return API + "?" + urlencode({"__culture": "tr-TR", "__platform": "web",
                                   "data": base64.b64encode(body.encode()).decode(), "__isbase64": "true"})


def distance(lat1, lon1, lat2, lon2):
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi, dlon = phi2 - phi1, math.radians(lon2 - lon1)
    term = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlon / 2) ** 2
    return 6371008.8 * 2 * math.asin(min(1.0, math.sqrt(term)))


def vertices(geometry):
    if geometry["type"] == "Polygon":
        return [point for ring in geometry["coordinates"] for point in ring]
    if geometry["type"] == "MultiPolygon":
        return [point for polygon in geometry["coordinates"] for ring in polygon for point in ring]
    raise ValueError("Only Polygon/MultiPolygon geography is supported")


def geography(path):
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    bounds, names = [], {}
    for feature in data["features"]:
        points = vertices(feature["geometry"])
        bounds.append((min(point[0] for point in points), min(point[1] for point in points),
                       max(point[0] for point in points), max(point[1] for point in points)))
        properties = feature.get("properties", {})
        code = properties.get("province_code")
        if code:
            names[str(code).zfill(2)] = properties.get("province", "")
    return bounds, names


def intersects(tile, bounds):
    west, south, size, _ = tile
    return any(west <= east and west + size >= left and south <= north and south + size >= bottom
               for left, bottom, east, north in bounds)


def read_tile(tile, args):
    west, south, size, depth = tile
    lat, lon = south + size / 2, west + size / 2
    query_hash = geohash(lat, lon)
    raw_path = args.output / "raw" / (query_hash + ".json")
    meta_path = raw_path.with_suffix(".meta.json")
    url = url_for(lat, lon)
    if not args.refresh and raw_path.exists() and meta_path.exists():
        data = json.loads(raw_path.read_text(encoding="utf-8-sig"))
        fetched_at = json.loads(meta_path.read_text(encoding="utf-8-sig"))["fetched_at"]
    else:
        if STOP_AFTER_FORBIDDEN.is_set():
            raise InterruptedError("Not requested: collection stopped after HTTP 403")
        last_error = None
        for attempt in range(args.retries + 1):
            if STOP_AFTER_FORBIDDEN.is_set():
                raise InterruptedError("Not requested: collection stopped after HTTP 403")
            try:
                request = Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json",
                                                "A101-User-Agent": "web-3.0.4"})
                with urlopen(request, timeout=args.timeout) as response:
                    data = json.loads(response.read().decode("utf-8-sig"))
                fetched_at = utc_now()
                break
            except HTTPError as error:
                # A refusal is a hard stop. Do not rotate identities, retry a
                # challenge, change hosts or continue queued network requests.
                if error.code == 403:
                    STOP_AFTER_FORBIDDEN.set()
                    raise
                if error.code not in (408, 425, 429, 500, 502, 503, 504, 570):
                    raise
                last_error = error
                if error.code == 429:
                    time.sleep(min(60, float(error.headers.get("Retry-After", "5"))))
            except (URLError, TimeoutError, OSError, json.JSONDecodeError) as error:
                last_error = error
            if attempt == args.retries:
                raise RuntimeError(f"Failed {query_hash}: {last_error}") from last_error
            time.sleep(2 ** attempt + random.uniform(0.1, 0.5))
        if not isinstance(data, dict) or not isinstance(data.get("stores"), list):
            raise ValueError(f"Unexpected official response structure: {url}")
        write_json(raw_path, data)
        write_json(meta_path, {"source_url": url, "fetched_at": fetched_at, "query_lat": lat,
                               "query_lon": lon, "collector_version": VERSION})
        time.sleep(args.pause)
    stores = data["stores"]
    radius = max(distance(lat, lon, corner_lat, corner_lon)
                 for corner_lat in (south, south + size) for corner_lon in (west, west + size))
    reported_distances = [float(store["distance"]) for store in stores
                          if isinstance(store, dict) and isinstance(store.get("distance"), (int, float))]
    cutoff = max(reported_distances) if reported_distances else 0
    # A conservative margin covers source distance rounding and projection error.
    cap_may_hide_stores = len(stores) >= 20 and cutoff < radius * 1.1 + 50
    split = cap_may_hide_stores and size / 2 >= args.min_step
    return {"tile": tile, "query_lat": lat, "query_lon": lon, "geoHash": query_hash,
            "source_url": url, "fetched_at": fetched_at, "stores": stores,
            "store_count": len(stores), "tile_radius_m": radius, "cutoff_m": cutoff,
            "split": split, "unresolved_cap": cap_may_hide_stores and not split}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--geography", type=Path, required=True, help="Province GeoJSON, Polygon/MultiPolygon")
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / ".cache" / "a101")
    parser.add_argument("--workers", type=int, choices=range(1, 5), default=3)
    parser.add_argument("--pause", type=float, default=1.0)
    parser.add_argument("--timeout", type=float, default=30)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--initial-step", type=float, default=0.5)
    parser.add_argument("--min-step", type=float, default=0.00390625)
    parser.add_argument("--checked-at", default=datetime.now(timezone(timedelta(hours=3))).date().isoformat())
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    if not (0 < args.min_step <= args.initial_step <= 2):
        parser.error("Expected 0 < min-step <= initial-step <= 2")
    bounds, province_names = geography(args.geography)
    started = utc_now()
    min_lon, min_lat = min(b[0] for b in bounds), min(b[1] for b in bounds)
    max_lon, max_lat = max(b[2] for b in bounds), max(b[3] for b in bounds)
    origin_lon = math.floor(min_lon / args.initial_step) * args.initial_step
    origin_lat = math.floor(min_lat / args.initial_step) * args.initial_step
    tiles = []
    for x in range(math.ceil((max_lon - origin_lon) / args.initial_step)):
        for y in range(math.ceil((max_lat - origin_lat) / args.initial_step)):
            tile = (origin_lon + x * args.initial_step, origin_lat + y * args.initial_step, args.initial_step, 0)
            if intersects(tile, bounds):
                tiles.append(tile)
    results, errors, unique, anomalies, conflicts = [], [], {}, [], []
    round_number = 0
    while tiles:
        round_number += 1
        new_tiles = []
        print(f"Round {round_number}: {len(tiles)} queries; {len(unique)} unique official stores so far", flush=True)
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {pool.submit(read_tile, tile, args): tile for tile in tiles}
            for future in as_completed(futures):
                tile = futures[future]
                try:
                    result = future.result()
                except Exception as error:
                    errors.append({"tile": tile, "error": str(error),
                                   "http_status": error.code if isinstance(error, HTTPError) else None,
                                   "request_status": "not_requested_after_403" if isinstance(error, InterruptedError) else "failed",
                                   "source_url": url_for(tile[1] + tile[2] / 2, tile[0] + tile[2] / 2)})
                    if not isinstance(error, InterruptedError):
                        print(f"ERROR tile {tile}: {error}", flush=True)
                    continue
                results.append({key: value for key, value in result.items() if key != "stores"})
                for raw in result["stores"]:
                    try:
                        store_id = str(raw["id"])
                        lat, lon = float(raw["lat"]), float(raw["lng"])
                        if not (35.7 <= lat <= 42.3 and 25.5 <= lon <= 45):
                            raise ValueError("coordinate_outside_turkey_bbox")
                        if not raw.get("name"):
                            raise ValueError("missing_store_name")
                    except (ValueError, KeyError, TypeError) as error:
                        anomalies.append({"reason": str(error), "original": raw, "source_url": result["source_url"]})
                        continue
                    code = str(raw.get("plateCode", "")).zfill(2)
                    row = {"id": "a101-" + store_id, "brand": "A101", "name": raw["name"],
                           "lat": lat, "lon": lon, "address": raw.get("address", ""),
                           "province": province_names.get(code) or raw.get("city", ""),
                           "district": raw.get("townShip", ""), "source": "A101 resmî mağaza bulucu",
                           "source_url": result["source_url"], "locator_url": LOCATOR,
                           "coordinate_type": "official", "checked_at": args.checked_at,
                           "fetched_at": result["fetched_at"], "original": raw}
                    if store_id in unique:
                        previous = unique[store_id]
                        if abs(previous["lat"] - lat) > 0.000001 or abs(previous["lon"] - lon) > 0.000001:
                            conflicts.append({"id": row["id"], "first": previous, "other": row})
                    else:
                        unique[store_id] = row
                if result["split"]:
                    west, south, size, depth = result["tile"]
                    for dx in (0, size / 2):
                        for dy in (0, size / 2):
                            child = (west + dx, south + dy, size / 2, depth + 1)
                            if intersects(child, bounds):
                                new_tiles.append(child)
                if len(results) % 100 == 0:
                    print(f"Progress: {len(results)} queries completed; {len(unique)} unique official stores", flush=True)
        tiles = new_tiles
        rows = sorted(unique.values(), key=lambda row: row["id"])
        write_json(args.output / "a101-normalized.json", rows)
        write_json(args.output / "query-coverage.json", results)
        write_json(args.output / "anomalies.json", anomalies)
        write_json(args.output / "conflicts.json", conflicts)
        write_json(args.output / "errors.json", errors)
    rows = sorted(unique.values(), key=lambda row: row["id"])
    by_province = {}
    for row in rows:
        by_province[row["province"]] = by_province.get(row["province"], 0) + 1
    metadata = {"collector_version": VERSION, "started_at": started, "completed_at": utc_now(),
                "checked_at": args.checked_at, "locator_url": LOCATOR, "api_url": API,
                "coordinate_fields": ["lat", "lng"], "store_id_field": "id", "query_count": len(results),
                "store_count": len(rows), "province_count": len(by_province), "counts_by_province": by_province,
                "initial_step_degrees": args.initial_step, "min_step_degrees": args.min_step,
                "unresolved_capped_tiles": sum(result["unresolved_cap"] for result in results),
                "unresolved_tile_count": len(errors) + sum(result["unresolved_cap"] for result in results),
                "geographic_sampling_complete": not errors and not any(result["unresolved_cap"] for result in results),
                "national_store_inventory_complete": False,
                "blocked_http_status": 403 if STOP_AFTER_FORBIDDEN.is_set() else None,
                "errors_count": len(errors), "anomaly_observations": len(anomalies), "coordinate_conflicts": len(conflicts),
                "coverage_method": "A101 resmî yakın mağaza sorgusunun 20 sonuç sınırına göre uyarlanan coğrafi örnekleme; kayıtlar resmî mağaza ID'siyle birleştirilir.",
                "limits": ["Bu uç nokta toplu mağaza envanteri değildir; ülke genelindeki eksiksiz şube sayısı garanti edilemez.",
                           "Konumlar kaynaktan alınmıştır; bağımsız saha veya Google Maps doğrulaması değildir.",
                           "Koordinat/adres hataları kaynakta bulunabilir; ülke ve il poligonu ayrıca denetlenmelidir.",
                           "Ham yanıtlardaki distance alanı yalnızca o sorgu merkezine göre mesafedir."]}
    write_json(args.output / "source-metadata.json", metadata)
    write_json(args.output / "unresolved-tiles.json", errors + [
        {"tile": result["tile"], "reason": "nearest20_cap_at_minimum_tile_size", "source_url": result["source_url"]}
        for result in results if result["unresolved_cap"]
    ])
    print(json.dumps(metadata, ensure_ascii=True), flush=True)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
