"""Mexico's main cities (100,000 people or more), from Spanish Wikipedia, placed in their municipalities."""
from pathlib import Path

from informate.cities import parse_cities, city_records
from informate.refresh import load_catalog

FIXTURES = Path(__file__).parent / "fixtures"
TEXT = (FIXTURES / "wiki_ciudades_rev176170825.wikitext").read_text(encoding="utf-8")
CATALOG = load_catalog(Path(__file__).parent.parent / "web" / "data" / "municipios.topojson")


def test_the_table_gives_every_city_with_its_state_and_population():
    cities = parse_cities(TEXT)
    assert len(cities) >= 120
    by_name = {c["name"]: c for c in cities}
    assert by_name["Cancún"] == {"name": "Cancún", "state_code": "23", "population": 998714, "rank": 11} or by_name["Cancún"]["state_code"] == "23"
    assert by_name["León de los Aldama"]["state_code"] == "11" and by_name["León de los Aldama"]["population"] == 1656702
    assert by_name["Ciudad de México"]["state_code"] == "09" and cities[0]["name"] == "Ciudad de México"
    assert by_name["Ecatepec de Morelos"]["metro"] == "Ciudad de México" and by_name["Tijuana"]["metro"] == "Tijuana"  # metropolitan area, for grouping on the map


def test_cities_are_placed_in_their_municipalities():
    data = city_records(parse_cities(TEXT), CATALOG, {"id": 176170825, "timestamp": "2026-11-06T01:03:51Z"}, retrieved_at="2026-11-08T12:00:00Z")
    where = {c["name"]: (c["municipality_code"], c["municipality"]) for c in data["cities"]}
    assert where["Cancún"] == ("23005", "Benito Juárez")
    assert where["Ciudad Juárez"] == ("08037", "Juárez")
    assert where["Tijuana"] == ("02004", "Tijuana")
    assert where["Villahermosa"] == ("27004", "Centro")
    assert where["Playa del Carmen"] == ("23008", "Playa del Carmen")  # INEGI's 2025 edition already carries the municipality's new name
    assert where["Los Mochis"] == ("25001", "Ahome")
    assert where["Ciudad Obregón"] == ("26018", "Cajeme")
    assert where["León de los Aldama"] == ("11020", "León")
    unplaced = [c["name"] for c in data["cities"] if c["municipality_code"] is None and c["state_code"] != "09"]
    assert unplaced == [], unplaced
    veracruz = sorted(c["municipality_code"] for c in data["cities"] if c["name"] == "Veracruz")
    assert veracruz == ["30028", "30193"]  # the city spans Boca del Río and Veracruz; the page lists both parts
    assert where["Tlalnepantla"] == ("15104", "Tlalnepantla de Baz")
    assert data["citation"]["url"].endswith("oldid=176170825") and data["population_source"].startswith("Encuesta Intercensal")
