#!/usr/bin/env python3
"""Tool 10: which municipalities each federal district covers.

Overlays INE's district polygons (already downloaded by tools/build_map.py) on INEGI's
municipal polygons (same cache) and measures the share of each municipality inside each
district. Needs both caches: run tools/build_map.py first.

    python tools/build_district_index.py

Writes web/data/distritos_municipios.json.
"""
import json
import sys
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from informate import district_index, districts, geo  # noqa: E402

CACHE = ROOT / ".cache" / "inegi"
OUT = ROOT / "web" / "data" / "distritos_municipios.json"


def main() -> None:
    shp = next(CACHE.rglob(f"{districts.LAYER}.shp"), None)
    state_files = sorted(CACHE.glob("mgem_*.json"))
    if not shp or not state_files:
        sys.exit("Faltan los límites en .cache/inegi: ejecuta primero tools/build_map.py")
    responses = [json.loads(path.read_text(encoding="utf-8"))["response"] for path in state_files]
    municipalities = geo.slim_features(responses)
    district_features = districts.read_districts(shp)
    print(f"{len(district_features)} distritos sobre {len(municipalities)} municipios…")
    result = district_index.overlay(district_features, municipalities)
    stamp = json.loads((CACHE / "ine_mgs_seccional.json").read_text(encoding="utf-8"))
    payload = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "method": district_index.METHOD,
        "whole_threshold": district_index.WHOLE,
        "minimum_share": district_index.MINIMUM,
        "sources": {
            "districts": {"name": "INE, Marco Geográfico Seccional, capa DISTRITO_FEDERAL", "url": districts.ARCHIVE_URL, "published_at": parsedate_to_datetime(stamp["last_modified"]).date().isoformat() if stamp.get("last_modified") else None, "retrieved_at": stamp.get("retrieved_at")},
            "municipalities": {"name": "INEGI, Marco Geoestadístico, servicio web", "url": geo.SERVICE_URL},
        },
        **result,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    shared = sum(1 for rows in result["municipalities"].values() if len(rows) > 1)
    print(f"Escrito: {OUT.relative_to(ROOT)}: {len(result['districts'])} distritos; {shared} municipios repartidos entre varios distritos")


if __name__ == "__main__":
    main()
