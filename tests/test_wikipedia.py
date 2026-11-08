"""Parsing the Spanish Wikipedia table of sitting governors.

Fixture: wikitext of "Anexo:Gobernantes de las entidades federativas de México",
revision 175719290 (2026-10-08).
"""
from pathlib import Path

import pytest

from informate.wikipedia import parse_governors

FIXTURE = Path(__file__).parent / "fixtures" / "wikipedia_gobernantes_rev175719290.wikitext"


@pytest.fixture(scope="module")
def governors():
    return parse_governors(FIXTURE.read_text(encoding="utf-8"))


def test_finds_one_head_of_government_per_state(governors):
    assert len(governors) == 32
    assert len({g["state_raw"] for g in governors}) == 32


def test_reads_name_state_and_party(governors):
    ags = governors[0]
    assert ags["state_raw"] == "Aguascalientes"
    assert ags["name"] == "María Teresa Jiménez Esquivel"
    assert ags["party_raw"] == "Partido Acción Nacional"


def test_reads_the_office_title_as_written(governors):
    assert governors[0]["title"] == "Gobernadora"
    cdmx = next(g for g in governors if g["state_raw"] == "Ciudad de México")
    assert cdmx["title"] == "Jefa de Gobierno"
    assert cdmx["name"] == "Clara Marina Brugada Molina"


def test_reads_term_dates_as_iso(governors):
    ags = governors[0]
    assert ags["term_start"] == "2022-10-01"
    assert ags["term_end"] == "2027-09-30"


def test_name_without_a_display_alias_is_read_from_the_link_itself(governors):
    bc = next(g for g in governors if g["state_raw"] == "Baja California")
    assert bc["name"] == "Marina del Pilar Ávila Olmeda"


def test_stray_whitespace_in_cells_is_trimmed(governors):
    mor = next(g for g in governors if g["state_raw"] == "Morelos")
    assert mor["name"] == "Margarita González Saravia Calderón"
    mich = next(g for g in governors if g["state_raw"] == "Michoacán")
    assert mich["term_end"] == "2027-09-30"


def test_a_page_without_the_table_is_an_error_not_an_empty_list():
    with pytest.raises(ValueError):
        parse_governors("== Otra sección ==\nSin tabla.")
