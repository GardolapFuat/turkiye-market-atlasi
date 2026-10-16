#!/usr/bin/env python3
"""Collect public ŞOK and Migros store-locator coordinates for Turkey.

Python 3.10+, standard library only. No account, cookie, API key or paid API.
Example: python collect_official.py --output official --workers 3 --refresh

Coordinates are copied from the official source. This is source verification,
not an independent physical/Google Maps check. Invalid coordinates are retained
in anomaly files and are never silently swapped, geocoded or invented.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
import random
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

VERSION = "1.0.0"
CITY_URLS = {
    "sok": "https://kurumsal.sokmarket.com.tr/api/public/stores/cities",
    "migros": "https://www.migros.com.tr/rest/delivery-bff/locations/cities",
}
LOCATORS = {
    "sok": "https://kurumsal.sokmarket.com.tr/tr/magazalar",
    "migros": "https://www.migros.com.tr/en-yakin-migros",
}
BRANDS = {"sok": "ŞOK", "migros": "Migros"}
BOUNDS = {"min_lat": 35.7, "max_lat": 42.3, "min_lon": 25.5, "max_lon": 45.0}
PRINT_LOCK = threading.Lock()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def tr_upper(value: str) -> str:
    return value.replace("i", "İ").replace("ı", "I").upper()


def fold(value: str) -> str:
    return value.translate(str.maketrans("çğıöşüÇĞİÖŞÜı", "cgiosuCGIOSUi")).casefold()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def fetch_json(url: str, timeout: float, retries: int) -> tuple[object, str]:
    for attempt in range(retries + 1):
        retry_after = None
        try:
            request = Request(url, headers={
                # These public locator APIs reject a custom non-browser agent.
                # No authentication, session cookie or challenge token is used.
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json",
            })
            with urlopen(request, timeout=timeout) as response:
                payload = response.read().decode("utf-8-sig")
            return json.loads(payload), utc_now()
        except HTTPError as error:
            if error.code not in (408, 425, 429, 500, 502, 503, 504):
                raise
            retry_after = error.headers.get("Retry-After")
            last_error = error
        except (URLError, TimeoutError, OSError, json.JSONDecodeError) as error:
            last_error = error
        if attempt >= retries:
            raise RuntimeError(f"Could not read {url}: {last_error}") from last_error
        try:
            delay = min(60.0, float(retry_after)) if retry_after else 2.0 ** attempt
        except ValueError:
            delay = 2.0 ** attempt
        time.sleep(delay + random.uniform(0.1, 0.5))
    raise AssertionError("unreachable")


def endpoint(brand: str, city: str) -> str:
    encoded = quote(city, safe="")
    if brand == "sok":
        return f"https://kurumsal.sokmarket.com.tr/api/public/stores?city={encoded}"
    return "https://www.migros.com.tr/rest/delivery-bff/external-warehouses/cities/" + encoded


def numeric(value: object) -> float:
    if value is None or isinstance(value, bool):
        raise ValueError("missing coordinate")
    result = float(str(value).strip().replace(",", "."))
    if not math.isfinite(result):
        raise ValueError("non-finite coordinate")
    return result


def normalize(brand: str, city: str, province: str, url: str, fetched_at: str,
              checked_at: str, raw: dict) -> tuple[dict, str | None]:
    lat_field, lon_field = ("ltd", "lng") if brand == "sok" else ("latitude", "longitude")
    label = BRANDS[brand]
    name = str(raw.get("name") or "").strip()
    address = str(raw.get("address" if brand == "sok" else "addressDetail") or "").strip()
    district = str(raw.get("ilce" if brand == "sok" else "townName") or "").strip()
    raw_id = raw.get("id")
    identity = json.dumps([city, name, address, raw.get(lat_field), raw.get(lon_field)],
                          ensure_ascii=False, separators=(",", ":"))
    stable_id = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20]
    item = {
        "id": f"migros-{raw_id}" if brand == "migros" and raw_id is not None else f"{brand}-{stable_id}",
        "brand": label, "name": name, "lat": None, "lon": None,
        "address": address, "province": province, "district": district,
        "source": f"{label} resmî mağaza bulucu", "source_url": url,
        "coordinate_type": "official", "checked_at": checked_at,
        "fetched_at": fetched_at, "original": raw,
    }
    try:
        item["lat"] = numeric(raw.get(lat_field))
        item["lon"] = numeric(raw.get(lon_field))
    except (ValueError, TypeError, OverflowError):
        return item, "missing_or_invalid_coordinate"
    if not name:
        return item, "missing_store_name"
    lat, lon = item["lat"], item["lon"]
    if not (BOUNDS["min_lat"] <= lat <= BOUNDS["max_lat"] and
            BOUNDS["min_lon"] <= lon <= BOUNDS["max_lon"]):
        return item, "outside_turkey_bbox"
    return item, None


def collect_city(brand: str, city: str, province: str, args: argparse.Namespace) -> dict:
    url = endpoint(brand, city)
    slug = fold(city).replace(" ", "-")
    raw_path = args.output / "raw" / brand / f"{slug}.json"
    meta_path = raw_path.with_suffix(".meta.json")
    if not args.refresh and raw_path.exists() and meta_path.exists():
        payload = json.loads(raw_path.read_text(encoding="utf-8-sig"))
        fetched_at = json.loads(meta_path.read_text(encoding="utf-8-sig"))["fetched_at"]
    else:
        payload, fetched_at = fetch_json(url, args.timeout, args.retries)
        write_json(raw_path, payload)
        write_json(meta_path, {"source_url": url, "fetched_at": fetched_at, "brand": BRANDS[brand],
                               "requested_city": city, "collector_version": VERSION})
        time.sleep(args.pause)
    if brand == "sok":
        if not isinstance(payload, dict) or payload.get("status") is not True or not isinstance(payload.get("subeler"), list):
            raise ValueError(f"Unexpected ŞOK response structure: {url}")
        records = payload["subeler"]
    else:
        if not isinstance(payload, list):
            raise ValueError(f"Unexpected Migros response structure: {url}")
        records = payload
    rows, anomalies = [], []
    seen = set()
    for raw in records:
        if not isinstance(raw, dict):
            anomalies.append({"reason": "non_object_record", "source_url": url, "original": raw})
            continue
        item, reason = normalize(brand, city, province, url, fetched_at, args.checked_at, raw)
        exact_identity = json.dumps(raw, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        if exact_identity in seen:
            reason = "exact_duplicate_source_record"
        seen.add(exact_identity)
        if reason:
            anomalies.append({"reason": reason, **item})
        else:
            rows.append(item)
    with PRINT_LOCK:
        print(f"{BRANDS[brand]} {province}: {len(rows)} pins, {len(anomalies)} anomalies", flush=True)
    return {"brand": brand, "city": city, "province": province, "source_url": url,
            "fetched_at": fetched_at, "source_count": len(records), "rows": rows, "anomalies": anomalies}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent / "official")
    parser.add_argument("--workers", type=int, choices=range(1, 5), default=3, help="Concurrent GET requests, maximum 4")
    parser.add_argument("--timeout", type=float, default=30)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--pause", type=float, default=0.2, help="Seconds between requests per worker")
    parser.add_argument("--checked-at", default=datetime.now(timezone(timedelta(hours=3))).date().isoformat())
    parser.add_argument("--refresh", action="store_true", help="Refetch province store responses instead of reusing local cache")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    started_at = utc_now()
    source_lists = {}
    for brand, url in CITY_URLS.items():
        payload, fetched_at = fetch_json(url, args.timeout, args.retries)
        source_lists[brand] = payload
        write_json(args.output / f"{brand}-cities.json", payload)
        write_json(args.output / f"{brand}-cities.meta.json", {"source_url": url, "fetched_at": fetched_at})
    sok_cities = source_lists["sok"]["cities"]
    migros_cities = source_lists["migros"]
    if len(sok_cities) != 81 or len(migros_cities) != 81:
        raise ValueError("Official locator city lists did not each contain 81 provinces")
    standard_names = {fold(item["name"]): item["name"] for item in migros_cities}
    standard_names["afyon"] = "Afyonkarahisar"
    tasks = [("sok", city, standard_names.get(fold(city), city.title())) for city in sok_cities]
    tasks += [("migros", tr_upper(item["name"]), item["name"]) for item in migros_cities]
    results, errors = [], []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(collect_city, brand, city, province, args): (brand, city) for brand, city, province in tasks}
        for future in as_completed(futures):
            brand, city = futures[future]
            try:
                results.append(future.result())
            except Exception as error:
                errors.append({"brand": BRANDS[brand], "requested_city": city, "error": str(error)})
                with PRINT_LOCK:
                    print(f"ERROR {brand} {city}: {error}", flush=True)
    coverage, all_rows, all_anomalies = [], [], []
    for brand in BRANDS:
        selected = sorted((result for result in results if result["brand"] == brand), key=lambda result: fold(result["province"]))
        rows = [row for result in selected for row in result["rows"]]
        anomalies = [row for result in selected for row in result["anomalies"]]
        write_json(args.output / f"{brand}-normalized.json", rows)
        write_json(args.output / f"{brand}-anomalies.json", anomalies)
        for result in selected:
            coverage.append({key: result[key] for key in ("brand", "city", "province", "source_url", "fetched_at", "source_count")}
                            | {"kept_count": len(result["rows"]), "anomaly_count": len(result["anomalies"])})
        all_rows.extend(rows)
        all_anomalies.extend(anomalies)
    write_json(args.output / "official-normalized.json", all_rows)
    write_json(args.output / "anomalies.json", all_anomalies)
    reasons = {}
    for anomaly in all_anomalies:
        reasons[anomaly["reason"]] = reasons.get(anomaly["reason"], 0) + 1
    metadata = {
        "collector_version": VERSION, "started_at": started_at, "completed_at": utc_now(),
        "checked_at": args.checked_at, "scope": "Türkiye, resmî il listelerindeki 81 il",
        "sources": [{"brand": BRANDS[brand], "locator_url": LOCATORS[brand], "cities_url": CITY_URLS[brand],
                     "coordinate_fields": ["ltd", "lng"] if brand == "sok" else ["latitude", "longitude"]}
                    for brand in BRANDS],
        "province_requests": len(tasks), "successful_province_requests": len(results),
        "source_count": sum(result["source_count"] for result in results), "kept_count": len(all_rows),
        "brand_counts": {BRANDS[brand]: sum(len(result["rows"]) for result in results if result["brand"] == brand) for brand in BRANDS},
        "anomaly_count": len(all_anomalies), "anomaly_reasons": reasons,
        "validation_bbox": BOUNDS, "coverage": coverage, "errors": errors,
        "provenance_note": "Koordinatlar resmî mağaza buluculardan aynen alınmıştır. Bağımsız saha veya Google Maps doğrulaması yapılmamıştır.",
        "limits": ["İl ve ilçe etiketleri, adresler ve koordinatlar kaynakta hatalı olabilir.",
                   "Kapanmış mağazaların kaynakta kalması veya yeni mağazaların eksik olması mümkündür.",
                   "Sınır kutusu Türkiye ülke poligonu kontrolü değildir; komşu ülkede veya denizde hatalı nokta olabilir.",
                   "Bu toplayıcı arazi, imar, gelişim potansiyeli veya yatırım değerlendirmesi yapmaz."],
    }
    write_json(args.output / "source-metadata.json", metadata)
    print(json.dumps({key: metadata[key] for key in ("source_count", "kept_count", "brand_counts", "anomaly_count", "anomaly_reasons", "errors")}, ensure_ascii=False), flush=True)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
