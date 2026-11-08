"""Gasoline and diesel prices per station, from the CRE's public feed.

Permit holders report their prices to the Comisión Reguladora de Energía, which
publishes them in two XML files: one with each station's location and one with
its current prices. The feed carries no publication date, so the day it was
read is the date. Stations are placed in their municipality with INEGI's
boundaries, and prices are averaged per municipality, state and country.
"""
import xml.etree.ElementTree as ET

from shapely.geometry import Point, shape
from shapely.strtree import STRtree

PLACES_URL = "https://publicacionexterna.azurewebsites.net/publicaciones/places"
PRICES_URL = "https://publicacionexterna.azurewebsites.net/publicaciones/prices"
SOURCE_NAME = "Comisión Reguladora de Energía, precios de gasolinas y diésel reportados por los permisionarios"
FUELS = ("regular", "premium", "diesel")
PLAUSIBLE = (10.0, 60.0)  # pesos per litre; anything outside is a placeholder, not a price


def parse_places(xml_text: str) -> dict[str, dict]:
    """Stations by id: name, CRE permit and coordinates."""
    places = {}
    for place in ET.fromstring(xml_text.lstrip("﻿")).iter("place"):
        location = place.find("location")
        if location is None or location.find("x") is None or location.find("y") is None:
            continue
        try:
            lon, lat = float(location.findtext("x")), float(location.findtext("y"))
        except (TypeError, ValueError):
            continue
        places[place.get("place_id")] = {"name": (place.findtext("name") or "").strip(), "cre_id": (place.findtext("cre_id") or "").strip(), "lon": lon, "lat": lat}
    return places


def parse_prices(xml_text: str) -> dict[str, dict]:
    """Prices by station id, per fuel, keeping only plausible values."""
    prices = {}
    for place in ET.fromstring(xml_text.lstrip("﻿")).iter("place"):
        station = {}
        for node in place.findall("gas_price"):
            fuel = node.get("type")
            try:
                value = float(node.text)
            except (TypeError, ValueError):
                continue
            if fuel in FUELS and PLAUSIBLE[0] <= value <= PLAUSIBLE[1]:
                station[fuel] = value
        if station:
            prices[place.get("place_id")] = station
    return prices


def locate(places: dict[str, dict], municipalities: list[dict]) -> dict[str, tuple[str, str]]:
    """Which (state code, municipality code) each station falls in; stations outside every
    municipality are left out. `municipalities` are GeoJSON features with cvegeo and cve_ent."""
    shapes = [shape(feature["geometry"]) for feature in municipalities]
    codes = [(feature["properties"]["cve_ent"], feature["properties"]["cvegeo"]) for feature in municipalities]
    tree = STRtree(shapes)
    where = {}
    for place_id, place in places.items():
        point = Point(place["lon"], place["lat"])
        for index in tree.query(point, predicate="within"):
            where[place_id] = codes[index]
            break
    return where


def _average(stations: list[dict]) -> dict:
    out = {}
    for fuel in FUELS:
        values = [s[fuel] for s in stations if fuel in s]
        out[fuel] = round(sum(values) / len(values), 2) if values else None
    out["stations"] = len(stations)
    return out


def fuel_records(places: dict, prices: dict, where: dict, retrieved_at: str) -> dict:
    """Average prices per municipality, state and country, with the station counts."""
    by_state: dict[str, list] = {}
    by_muni: dict[str, list] = {}
    everywhere = []
    for place_id, station in prices.items():
        if place_id not in where:
            continue
        state, muni = where[place_id]
        by_state.setdefault(state, []).append(station)
        by_muni.setdefault(muni, []).append(station)
        everywhere.append(station)
    return {
        "unit": "pesos por litro",
        "national": _average(everywhere),
        "states": {code: _average(stations) for code, stations in sorted(by_state.items())},
        "municipalities": {code: _average(stations) for code, stations in sorted(by_muni.items())},
        "citation": {"source": "cre", "source_name": SOURCE_NAME, "url": PRICES_URL, "places_url": PLACES_URL, "published_at": None, "retrieved_at": retrieved_at},
    }
