"""State GDP from INEGI's PIBE press release (cuadro 1 of comunicado 156/25)."""
from pathlib import Path

import pytest

from informate.gdp import parse_pibe_table, gdp_records

FIXTURES = Path(__file__).parent / "fixtures"
TEXT = (FIXTURES / "inegi_pibe2024_cuadro1.txt").read_text(encoding="utf-8")


def test_table_gives_every_state_and_the_national_total():
    table = parse_pibe_table(TEXT)
    assert len(table["states"]) == 32
    assert table["national"] == {"gdp_previous": 25027, "gdp": 25365, "growth": 1.4}
    assert table["states"]["14"] == {"gdp_previous": 1850, "gdp": 1864, "growth": 0.8}  # Jalisco
    assert table["states"]["09"] == {"gdp_previous": 3806, "gdp": 3886, "growth": 2.1}  # thousands written "3 886"
    assert table["states"]["01"]["growth"] == -1.9  # negative growth keeps its sign


def test_states_add_up_to_the_national_total_within_rounding():
    table = parse_pibe_table(TEXT)
    assert abs(sum(s["gdp"] for s in table["states"].values()) - table["national"]["gdp"]) <= 32


def test_a_page_without_the_table_is_refused():
    with pytest.raises(ValueError):
        parse_pibe_table("Comunicado de prensa sin cuadro")


def test_records_carry_year_units_share_and_citation():
    data = gdp_records(parse_pibe_table(TEXT), retrieved_at="2026-11-07T15:00:00Z")
    assert data["year"] == 2024 and data["unit"] == "miles de millones de pesos a precios de 2018"
    assert data["national"]["gdp"] == 25365
    jalisco = data["states"]["14"]
    assert jalisco["gdp"] == 1864 and jalisco["growth"] == 0.8
    assert jalisco["share"] == pytest.approx(100 * 1864 / 25365, abs=0.01)
    assert data["citation"]["url"].endswith("PIBE2024_CP.pdf")
    assert data["citation"]["published_at"] == "2025-12-05" and data["citation"]["retrieved_at"] == "2026-11-07T15:00:00Z"
