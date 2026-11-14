#!/usr/bin/env python3
"""Tool 12: the countries around Mexico, as context for the maps.

Source: Natural Earth, Admin 0 – Countries, 1:50m (public domain), downloaded once into
.cache/natural_earth/ and reused.

    python tools/build_neighbors.py            # reuses the downloaded archive if present
    python tools/build_neighbors.py --refresh  # downloads it again

Writes web/data/vecinos.topojson.
"""
import argparse
import io
import json
import sys
import zipfile
from pathlib import Path

import shapefile

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from informate import geo, neighbors  # noqa: E402
from informate.refresh import new_session, utc_now  # noqa: E402

CACHE = ROOT / ".cache" / "natural_earth"
OUT = ROOT / "web" / "data" / "vecinos.topojson"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--refresh", action="store_true", help="download the archive again")
    parser.add_argument("--tolerance", type=float, default=0.02, help="border simplification in degrees (default: %(default)s)")
    args = parser.parse_args()
    archive = CACHE / f"{neighbors.LAYER}.zip"
    stamp = CACHE / f"{neighbors.LAYER}.json"
    if not archive.exists() or args.refresh:
        print("Descargando Natural Earth (unos 0.8 MB)…")
        response = new_session().get(neighbors.ARCHIVE_URL, timeout=300)
        response.raise_for_status()
        CACHE.mkdir(parents=True, exist_ok=True)
        archive.write_bytes(response.content)
        stamp.write_text(json.dumps({"retrieved_at": utc_now()}), encoding="utf-8")
    retrieved_at = json.loads(stamp.read_text(encoding="utf-8"))["retrieved_at"]
    with zipfile.ZipFile(archive) as z:
        reader = shapefile.Reader(shp=io.BytesIO(z.read(f"{neighbors.LAYER}.shp")), dbf=io.BytesIO(z.read(f"{neighbors.LAYER}.dbf")), shx=io.BytesIO(z.read(f"{neighbors.LAYER}.shx")))
        version = z.read(f"{neighbors.LAYER}.VERSION.txt").decode("utf-8").strip()
    names = [field[0] for field in reader.fields[1:]]
    features = [{"type": "Feature", "properties": dict(zip(names, record)), "geometry": shp.__geo_interface__} for record, shp in zip(reader.records(), reader.shapes())]
    kept = neighbors.select_neighbours(features)
    topology = geo.build_topology(kept, args.tolerance, object_name=neighbors.OBJECT_NAME)
    topology["source"] = {"name": neighbors.SOURCE_NAME, "url": neighbors.PAGE_URL, "file_url": neighbors.ARCHIVE_URL, "version": version, "retrieved_at": retrieved_at}
    OUT.write_text(json.dumps(topology, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"Escrito: {OUT.relative_to(ROOT)}: {', '.join(f['properties']['name'] for f in kept)} ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
