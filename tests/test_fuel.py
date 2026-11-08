"""Fuel prices per station from the CRE's public feed, placed in their municipalities."""
import pytest

from informate.fuel import parse_places, parse_prices, locate, fuel_records

PLACES = """<?xml version="1.0" encoding="utf-8"?>
<places>
  <place place_id="1"><name>A</name><cre_id>PL/1</cre_id><location><x>-102.30</x><y>21.88</y></location></place>
  <place place_id="2"><name>B</name><cre_id>PL/2</cre_id><location><x>-102.31</x><y>21.89</y></location></place>
  <place place_id="3"><name>C</name><cre_id>PL/3</cre_id><location><x>-103.35</x><y>20.67</y></location></place>
  <place place_id="4"><name>At sea</name><cre_id>PL/4</cre_id><location><x>-120.0</x><y>10.0</y></location></place>
</places>"""
PRICES = """<?xml version="1.0" encoding="utf-8"?>
<places>
  <place place_id="1"><gas_price type="regular">23.00</gas_price><gas_price type="premium">26.00</gas_price></place>
  <place place_id="2"><gas_price type="regular">25.00</gas_price><gas_price type="diesel">27.50</gas_price></place>
  <place place_id="3"><gas_price type="regular">24.00</gas_price><gas_price type="premium">0.01</gas_price></place>
  <place place_id="4"><gas_price type="regular">22.00</gas_price></place>
  <place place_id="9"><gas_price type="regular">22.00</gas_price></place>
</places>"""
# Two square municipalities: one around Aguascalientes city, one around Guadalajara.
MUNICIPALITIES = [
    {"type": "Feature", "properties": {"cvegeo": "01001", "cve_ent": "01"}, "geometry": {"type": "Polygon", "coordinates": [[[-102.5, 21.7], [-102.1, 21.7], [-102.1, 22.1], [-102.5, 22.1], [-102.5, 21.7]]]}},
    {"type": "Feature", "properties": {"cvegeo": "14039", "cve_ent": "14"}, "geometry": {"type": "Polygon", "coordinates": [[[-103.5, 20.5], [-103.2, 20.5], [-103.2, 20.8], [-103.5, 20.8], [-103.5, 20.5]]]}},
]


def test_places_and_prices_parse_by_station_id():
    places = parse_places(PLACES)
    assert places["1"] == {"name": "A", "cre_id": "PL/1", "lon": -102.30, "lat": 21.88}
    prices = parse_prices(PRICES)
    assert prices["2"] == {"regular": 25.0, "diesel": 27.5}
    assert "premium" not in prices["3"]  # 0.01 is not a price; dropped


def test_stations_are_placed_in_their_municipality_or_left_out():
    where = locate(parse_places(PLACES), MUNICIPALITIES)
    assert where["1"] == ("01", "01001") and where["3"] == ("14", "14039")
    assert "4" not in where  # at sea


def test_records_average_per_level_and_count_stations():
    data = fuel_records(parse_places(PLACES), parse_prices(PRICES), locate(parse_places(PLACES), MUNICIPALITIES), retrieved_at="2026-11-07T18:00:00Z")
    assert data["national"]["regular"] == pytest.approx(24.0) and data["national"]["stations"] == 3  # stations 1, 2, 3; not 4 (at sea) nor 9 (unknown)
    ags = data["states"]["01"]
    assert ags["regular"] == pytest.approx(24.0) and ags["premium"] == pytest.approx(26.0) and ags["diesel"] == pytest.approx(27.5) and ags["stations"] == 2
    assert data["municipalities"]["14039"] == {"regular": 24.0, "premium": None, "diesel": None, "stations": 1}
    assert data["citation"]["source"] == "cre" and data["citation"]["retrieved_at"] == "2026-11-07T18:00:00Z"
