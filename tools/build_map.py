#!/usr/bin/env python3
"""Tool 1: build the map of Mexico with all its municipalities.

Source: INEGI, Marco Geoestadístico, served by INEGI's web service at
https://gaia.inegi.org.mx/wscatgeo/v2/geo/mgem/<state code>.

    python tools/build_map.py            # reuses earlier downloads if present
    python tools/build_map.py --refresh  # downloads everything again

Writes web/data/municipios.topojson and web/data/map_source.json.
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from informate import geo  # noqa: E402
from informate.refresh import build_map, new_session  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--refresh", action="store_true", help="download again instead of using local copies")
    parser.add_argument("--tolerance", type=float, default=geo.DEFAULT_TOLERANCE,
                        help="border simplification in degrees (default: %(default)s)")
    args = parser.parse_args()

    meta = build_map(ROOT / "web" / "data", ROOT / ".cache" / "inegi", new_session(),
                     refresh=args.refresh, tolerance=args.tolerance)
    size_mb = (ROOT / "web" / "data" / "municipios.topojson").stat().st_size / 1e6
    print()
    print(f"Mapa listo: {meta['municipality_count']} municipios en {len(meta['states'])} entidades ({size_mb:.1f} MB)")
    print(f"{meta['attribution']}")
    print(f"Servicio: {meta['service_url']}  (consultado: {meta['retrieved_at']})")


if __name__ == "__main__":
    main()
