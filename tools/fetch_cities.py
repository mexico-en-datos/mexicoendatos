#!/usr/bin/env python3
"""Tool 9: Mexico's main cities (100,000 people or more), placed in their municipalities.

Source: Spanish Wikipedia, «Anexo:Ciudades más pobladas de México» (secondary; cited to
the revision read). Runs on demand.

    python tools/fetch_cities.py

Writes web/data/cities.json.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from informate import cities, wikipedia  # noqa: E402
from informate.refresh import load_catalog, new_session, utc_now, write_json  # noqa: E402


def main() -> None:
    text, revision = wikipedia.fetch_page(new_session(), cities.PAGE_TITLE)
    data = cities.city_records(cities.parse_cities(text), load_catalog(ROOT / "web" / "data" / "municipios.topojson"), revision, utc_now())
    out = ROOT / "web" / "data" / "cities.json"
    write_json(out, data)
    missing = [c["name"] for c in data["cities"] if not c["municipality_code"] and c["state_code"] != "09"]
    print(f"{len(data['cities'])} ciudades; sin municipio: {missing or 'ninguna'}. Fuente: {data['citation']['url']} (consultada {data['citation']['retrieved_at']})")
    print(f"Escrito: {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
