#!/usr/bin/env python3
"""Tool 6: gasoline and diesel prices per municipality, state and country.

Source: Comisión Reguladora de Energía, prices reported by the permit holders,
published as two XML feeds (stations and prices). Stations are placed in their
municipality with the INEGI boundaries downloaded by tools/build_map.py.

    python tools/fetch_fuel.py

Writes web/data/fuel.json.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from informate import fuel, topo  # noqa: E402
from informate.refresh import new_session, utc_now, write_json  # noqa: E402


def municipalities(cache_dir: Path, published: Path) -> tuple[list[dict], str]:
    """INEGI's municipal boundaries: the full-detail downloads when the map tool's cache is
    at hand, otherwise the simplified published map. Returns the features and which it was."""
    features = []
    for path in sorted(cache_dir.glob("mgem_*.json")):
        response = json.loads(path.read_text(encoding="utf-8"))["response"]
        features.extend(response["features"])
    if features:
        return features, "límites completos del INEGI"
    if published.exists():
        return topo.features(json.loads(published.read_text(encoding="utf-8")), "municipios"), "límites simplificados del mapa publicado"
    raise SystemExit(f"No boundaries in {cache_dir} nor {published}; run tools/build_map.py first.")


def main() -> None:
    session = new_session()
    print(f"Descargando {fuel.PLACES_URL} y {fuel.PRICES_URL} …")
    # The server labels the feeds text/html; read the bytes and decode them as the UTF-8 they are.
    places_xml = session.get(fuel.PLACES_URL, timeout=120).content.decode("utf-8-sig")
    prices_xml = session.get(fuel.PRICES_URL, timeout=120).content.decode("utf-8-sig")
    retrieved_at = utc_now()
    places = fuel.parse_places(places_xml)
    prices = fuel.parse_prices(prices_xml)
    boundaries, detail = municipalities(ROOT / ".cache" / "inegi", ROOT / "web" / "data" / "municipios.topojson")
    where = fuel.locate(places, boundaries)
    data = fuel.fuel_records(places, prices, where, retrieved_at)
    out = ROOT / "web" / "data" / "fuel.json"
    write_json(out, data)
    n = data["national"]
    print(f"{len(places):,} estaciones, {len(prices):,} con precio, {n['stations']:,} ubicadas en un municipio ({detail}).")
    print(f"Promedio nacional: regular {n['regular']}, premium {n['premium']}, diésel {n['diesel']} pesos por litro (consultado {retrieved_at}).")
    print(f"Escrito: {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
