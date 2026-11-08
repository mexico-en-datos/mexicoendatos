"""Minimum wage (CONASAMI), employment (INEGI ENOE) and poverty (INEGI PM) per state."""
from pathlib import Path

import pytest

from informate.economy import parse_minimum_wage, border_municipality_codes, parse_enoe_table, parse_poverty_workbook, economy_records

FIXTURES = Path(__file__).parent / "fixtures"
WAGE = (FIXTURES / "conasami_salarios_2026.txt").read_text(encoding="utf-8")
ENOE = (FIXTURES / "inegi_enoe2026_08_cuadro5.txt").read_text(encoding="utf-8")
CATALOG = {"02": {"02001": "Ensenada", "02002": "Mexicali", "02004": "Tijuana", "02006": "San Quintín", "02007": "San Felipe", "02003": "Tecate", "02005": "Playas de Rosarito"},
           "05": {"05014": "Guerrero", "05013": "Hidalgo", "05025": "Piedras Negras", "05002": "Acuña", "05020": "Nava", "05016": "Jiménez", "05022": "Ocampo", "05038": "Zaragoza", "05030": "Saltillo"},
           "08": {"08053": "Manuel Benavides", "08037": "Juárez"}, "28": {"28014": "Guerrero", "28027": "Nuevo Laredo"}, "19": {"19004": "Anáhuac"}, "14": {"14039": "Guadalajara"}}


def test_minimum_wage_amounts_and_border_zone_are_read_from_the_table():
    wage = parse_minimum_wage(WAGE)
    assert wage["general"] == 315.04 and wage["border"] == 440.87 and wage["effective_from"] == "2026-01-01"
    assert wage["border_municipalities"]["Baja California"] == ["Ensenada", "Playas de Rosarito", "Mexicali", "Tecate", "Tijuana", "San Quintín", "San Felipe"]
    assert wage["border_municipalities"]["Nuevo León"] == ["Anáhuac"]
    assert len(wage["border_municipalities"]["Chihuahua"]) == 8  # the PDF breaks one name as "Man uel Benavides"; matching ignores spaces


def test_border_municipalities_are_matched_to_inegi_codes_within_their_state():
    codes = border_municipality_codes(parse_minimum_wage(WAGE), CATALOG)
    assert {"02001", "02004", "02007", "05014", "05013", "08053", "28014", "19004"} <= codes
    assert "05030" not in codes and "14039" not in codes  # Saltillo and Guadalajara are not on the border


def test_enoe_table_gives_every_state_and_the_national_row():
    table = parse_enoe_table(ENOE)
    assert table["national"] == {"employed": 60040094, "unemployed": 1636604, "participation": 59.1, "unemployment": 2.7, "informality": 55.1}
    assert len(table["states"]) == 32
    assert table["states"]["09"]["unemployment"] == 4.2 and table["states"]["20"]["unemployment"] == 0.8
    assert table["states"]["30"] == {"employed": 3310652, "unemployed": 64397, "participation": 52.2, "unemployment": 1.9, "informality": 69.1}  # name split over two lines


def test_poverty_workbook_gives_percent_and_people_for_2024():
    poverty = parse_poverty_workbook(FIXTURES / "inegi_pm_ef_2024.xlsx")
    assert poverty["national"]["poverty_pct"] == pytest.approx(29.56, abs=0.01)
    assert poverty["national"]["poverty_people"] == pytest.approx(38489971, rel=1e-4)
    assert poverty["states"]["14"]["poverty_pct"] == pytest.approx(19.0, abs=0.5)  # Jalisco 2024
    assert poverty["states"]["14"]["poverty_people"] == pytest.approx(1626417, rel=1e-4)
    assert poverty["states"]["07"]["poverty_pct"] == pytest.approx(66.0, abs=0.1)  # Chiapas, the highest
    assert 0 < poverty["states"]["07"]["extreme_pct"] < poverty["states"]["07"]["poverty_pct"]


def test_records_rank_states_and_carry_citations():
    data = economy_records(parse_minimum_wage(WAGE), {"02001", "19004"}, parse_enoe_table(ENOE), parse_poverty_workbook(FIXTURES / "inegi_pm_ef_2024.xlsx"), retrieved_at="2026-11-07T19:00:00Z")
    assert data["minimum_wage"]["general"] == 315.04 and sorted(data["minimum_wage"]["border_municipalities"]) == ["02001", "19004"]
    assert data["employment"]["period"] == "segundo trimestre de 2026"
    assert data["employment"]["states"]["09"]["rank_by_unemployment"] == 1  # Ciudad de México, 4.2 %
    assert data["poverty"]["states"]["07"]["rank_by_poverty"] == 1  # Chiapas
    for key in ("minimum_wage", "employment", "poverty"):
        assert data[key]["citation"]["retrieved_at"] == "2026-11-07T19:00:00Z" and data[key]["citation"]["url"].startswith("https://")


# ----- Income bands of the employed, from each state's ENOE bulletin -----

from informate.economy import parse_income_bands, STATE_BULLETIN  # noqa: E402

JAL = (FIXTURES / "inegi_enoe2026_08_Jal_ingresos.txt").read_text(encoding="utf-8")
CHIS = (FIXTURES / "inegi_enoe2026_08_Chis_ingresos.txt").read_text(encoding="utf-8")


def test_income_bands_are_the_current_quarter_shares():
    bands = parse_income_bands(JAL)
    assert bands == {"up_to_1": 32.3, "from_1_to_2": 44.7, "from_2_to_3": 10.3, "from_3_to_5": 1.9, "over_5": 0.5, "none": 2.3, "unspecified": 8.1}


def test_income_bands_survive_commas_in_the_change_column():
    bands = parse_income_bands(CHIS)
    assert bands["up_to_1"] == 65.1 and bands["none"] == 12.1


def test_every_state_has_a_bulletin_address():
    assert len(STATE_BULLETIN) == 32 and STATE_BULLETIN["09"].endswith("enoe2026_08_CdMx.pdf") and STATE_BULLETIN["23"].endswith("enoe2026_08_QRoo.pdf")


def test_records_include_income_with_ranks(tmp_path):
    data = economy_records(parse_minimum_wage(WAGE), set(), parse_enoe_table(ENOE), parse_poverty_workbook(FIXTURES / "inegi_pm_ef_2024.xlsx"), retrieved_at="2026-11-07T19:00:00Z", income={"14": parse_income_bands(JAL), "07": parse_income_bands(CHIS)})
    assert data["income"]["states"]["07"]["rank_by_up_to_1"] == 1 and data["income"]["states"]["14"]["rank_by_up_to_1"] == 2
    assert data["income"]["period"] == "segundo trimestre de 2026" and data["income"]["citation"]["url"].endswith("enoe2026_08_Ags.pdf")
