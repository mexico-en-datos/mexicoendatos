"""The Mesa Directiva and the group coordinators of each chamber, from the Wikipedia annex on
the legislature.

Fixture: revision 176247279 (2026-11-11) of "Anexo:LXVI Legislatura del Congreso de la Unión de
México": the third legislative year (2026-27) of the LXVI Legislature.
"""
from pathlib import Path

import pytest

from informate.congress import BOARD_RULE, JUCOPO_RULE, find_member, jucopo_president, legislative_year, page_title, parse_leadership

FIXTURE = Path(__file__).parent / "fixtures" / "wiki_lxvi_legislatura_rev176247279.wikitext"


@pytest.fixture(scope="module")
def leadership():
    return parse_leadership(FIXTURE.read_text(encoding="utf-8"))


def test_the_annex_is_named_after_the_legislature():
    assert page_title(66) == "Anexo:LXVI Legislatura del Congreso de la Unión de México"
    assert page_title(67) == "Anexo:LXVII Legislatura del Congreso de la Unión de México"


def test_senate_board_of_the_current_legislative_year(leadership):
    senate = leadership["senator"]
    assert senate["period"] == "2026-27"
    assert senate["board"][0] == {"name": "Higinio Martínez Miranda", "aliases": [], "role": "Presidente", "party": "MORENA", "party_name": "Movimiento Regeneración Nacional", "state": "Estado de México"}
    assert [m["role"] for m in senate["board"]] == ["Presidente", "Primera Vicepresidenta", "Segundo Vicepresidente", "Tercer Vicepresidente"]
    assert senate["board"][2]["name"] == "Mauricio Vila Dosal" and senate["board"][2]["party"] == "PAN"


def test_deputies_board_keeps_the_article_title_as_the_name_and_the_shown_form_as_alias(leadership):
    president = leadership["deputy"]["board"][0]
    assert president["name"] == "Raúl Bolaños Cacho Cué"
    assert president["aliases"] == []  # the shown text misspells the first name ("Rául"), but folds to the same words
    assert president["role"] == "Presidente" and president["party"] == "PVEM" and president["state"] == "Oaxaca"
    assert len(leadership["deputy"]["board"]) == 4


def test_every_group_has_a_coordinator_in_each_chamber(leadership):
    senate = {c["party"]: c["name"] for c in leadership["senator"]["coordinators"]}
    assert senate == {
        "PAN": "Ricardo Anaya Cortés",
        "PRI": "Manuel Añorve Baños",
        "PT": "Alberto Anaya Gutiérrez",
        "PVEM": "Manuel Velasco Coello",
        "MC": "Clemente Castañeda Hoeflich",
        "MORENA": "Ignacio Mier Velazco",
    }
    deputies = {c["party"]: c for c in leadership["deputy"]["coordinators"]}
    assert deputies["MORENA"]["name"] == "Ricardo Monreal Ávila"
    assert deputies["PRI"]["name"] == "Rubén Moreira" and deputies["PRI"]["aliases"] == ["Rubén Moreira Valdez"]
    assert deputies["PAN"]["party_name"] == "Partido Acción Nacional"


def test_legislative_year_runs_from_september_to_august():
    assert legislative_year("2026-27") == ("2026-09-01", "2027-08-31")
    with pytest.raises(ValueError):
        legislative_year("2026-28")


ROSTER = [
    {"name": "Moisés Ignacio Mier Velazco", "party": "MORENA", "state": "Puebla"},
    {"name": "Carlos Ignacio Mier Bañuelos", "party": "MORENA", "state": "Puebla"},
    {"name": "Rubén Ignacio Moreira Valdez", "party": "PRI", "state": None},
    {"name": "Raúl Bolaños-Cacho Cué", "party": "PVEM", "state": "Oaxaca"},
    {"name": "Ana López García", "party": "PAN", "state": "Jalisco"},
    {"name": "Ana López García", "party": "MORENA", "state": "Sonora"},
]


def test_find_member_matches_when_every_word_of_the_annex_name_is_in_the_roster_name():
    assert find_member({"name": "Ignacio Mier Velazco", "aliases": []}, ROSTER)["name"] == "Moisés Ignacio Mier Velazco"
    assert find_member({"name": "Rubén Moreira", "aliases": ["Rubén Moreira Valdez"]}, ROSTER)["name"] == "Rubén Ignacio Moreira Valdez"
    assert find_member({"name": "Raúl Bolaños Cacho Cué", "aliases": ["Rául Bolaños Cacho Cué"]}, ROSTER)["name"] == "Raúl Bolaños-Cacho Cué"


def test_find_member_uses_party_and_state_to_tell_namesakes_apart_and_gives_up_otherwise():
    assert find_member({"name": "Ana López García", "party": "MORENA"}, ROSTER)["state"] == "Sonora"
    assert find_member({"name": "Ana López García", "party": "PRI", "state": "Jalisco"}, ROSTER)["state"] == "Jalisco"
    assert find_member({"name": "Ana López García"}, ROSTER) is None
    assert find_member({"name": "Nadie Conocido"}, ROSTER) is None


def test_jucopo_is_presided_by_the_coordinator_of_the_group_with_an_absolute_majority(leadership):
    coordinators = leadership["senator"]["coordinators"]
    head = jucopo_president(coordinators, {"MORENA": 66, "PAN": 21, "PRI": 14, "PVEM": 14, "PT": 6, "MC": 5, "SP": 2}, 128)
    assert head["name"] == "Ignacio Mier Velazco" and head["seats"] == 66
    assert jucopo_president(coordinators, {"MORENA": 64, "PAN": 64}, 128) is None


def test_the_rules_cite_the_organic_law_with_its_dates():
    for rule in (BOARD_RULE, JUCOPO_RULE):
        assert rule["url"].startswith("http://www.ordenjuridico.gob.mx/")
        assert rule["published_at"] == "2022-12-19" and rule["checked_at"]
    assert "artículos 31 y 81" in JUCOPO_RULE["text"]
    assert "artículos 17 y 62" in BOARD_RULE["text"]
