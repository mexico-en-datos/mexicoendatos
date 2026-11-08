"""Each state's capital, from Spanish Wikipedia, matched to INEGI's municipality."""
from pathlib import Path

from informate.capitals import parse_capitals, capital_records
from informate.refresh import load_catalog

FIXTURES = Path(__file__).parent / "fixtures"
TEXT = (FIXTURES / "wiki_entidades_rev175410084.wikitext").read_text(encoding="utf-8")
CATALOG = load_catalog(Path(__file__).parent.parent / "web" / "data" / "municipios.topojson")


def test_every_state_has_a_capital_name():
    capitals = parse_capitals(TEXT)
    assert len(capitals) == 32
    assert capitals["01"] == "Aguascalientes" and capitals["02"] == "Mexicali" and capitals["27"] == "Villahermosa" and capitals["09"] == "Ciudad de México"


def test_capitals_are_placed_in_a_municipality_of_their_state():
    records = capital_records(parse_capitals(TEXT), CATALOG, {"id": 175410084, "timestamp": "2026-09-18T02:09:31Z"}, retrieved_at="2026-11-08T10:00:00Z")
    assert records["states"]["27"] == {"capital": "Villahermosa", "municipality_code": "27004", "municipality": "Centro"}
    assert records["states"]["28"]["municipality"] == "Victoria" and records["states"]["23"]["municipality"] == "Othón P. Blanco"
    assert records["states"]["09"]["municipality_code"] is None  # the capital is the whole entity
    placed = [r for c, r in records["states"].items() if c != "09"]
    assert len(placed) == 31 and all(r["municipality_code"] and r["municipality_code"][:2] == code for code, r in records["states"].items() if code != "09")
    assert records["citation"]["url"].endswith("oldid=175410084")
