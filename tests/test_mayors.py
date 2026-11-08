"""Municipal presidents, from the Spanish Wikipedia list kept for each state.

Fixtures are real pages (their revision is in the file name) plus one table made of
real rows copied from several pages to cover the uncommon cases.
"""
from pathlib import Path

import pytest

from informate.mayors import PAGES, match_municipality, parse_mayors, parse_term

FIXTURES = Path(__file__).parent / "fixtures"


def read(name):
    return (FIXTURES / name).read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def aguascalientes():
    return parse_mayors(read("wiki_pm_aguascalientes_rev172212877.wikitext"))


@pytest.fixture(scope="module")
def special():
    return {row["municipality"]: row for row in parse_mayors(read("wiki_pm_casos_especiales.wikitext"))}


def test_there_is_one_page_per_state_and_one_for_mexico_city():
    assert len(PAGES) == 32
    assert PAGES["01"] == "Anexo:Presidentes municipales de Aguascalientes (2024-2027)"
    assert PAGES["09"] == "Anexo:Alcaldes de la Ciudad de México (2024-2027)"


def test_reads_each_municipality_with_its_president_and_party(aguascalientes):
    assert len(aguascalientes) == 11
    first = aguascalientes[0]
    assert first["municipality"] == "Aguascalientes"
    assert first["article"] == "Municipio de Aguascalientes"
    assert first["name"] == "Leonardo Montañez Castro"
    assert first["party_raw"] == "Partido Acción Nacional"
    assert first["vacant"] is None


def test_footnotes_are_not_part_of_the_name(aguascalientes):
    cosio = next(row for row in aguascalientes if row["municipality"] == "Cosío")
    assert cosio["name"] == "Francisco Javier Domínguez López"
    assert cosio["party_raw"] == "Candidaturas independientes de México"


def test_the_municipal_table_is_chosen_not_the_party_summary_above_it():
    guanajuato = parse_mayors(read("wiki_pm_guanajuato_rev174229637.wikitext"))
    assert len(guanajuato) == 46
    assert all(row["municipality"] for row in guanajuato)


def test_mexico_citys_alcaldias_use_the_same_layout_with_other_headings():
    cdmx = parse_mayors(read("wiki_alcaldes_cdmx_rev176043626.wikitext"))
    assert len(cdmx) == 16
    assert (cdmx[0]["municipality"], cdmx[0]["name"]) == ("Álvaro Obregón", "Javier López Casarín")
    cuajimalpa = next(row for row in cdmx if row["municipality"] == "Cuajimalpa")
    assert cuajimalpa["article"] == "Cuajimalpa de Morelos"


def test_when_a_president_was_replaced_the_current_one_is_listed():
    campeche = {row["municipality"]: row for row in parse_mayors(read("wiki_pm_campeche_rev176041100.wikitext"))}
    assert len(campeche) == 13  # 13 municipalities, though the table has 16 rows
    assert campeche["Carmen"]["name"] == "Priscila Heredia Novelo"
    assert campeche["Palizada"]["name"] == "Ambrosio Gutiérrez Pérez"
    assert campeche["Palizada"]["party_raw"] == "Morena (partido político)"  # the replacement's party, not the predecessor's


def test_when_the_same_person_changed_party_the_current_party_is_listed(special):
    naranjos = special["Naranjos Amatlán"]
    assert naranjos["name"] == "Humberto Ancelin Cruz"
    assert naranjos["party_raw"] == "Movimiento Regeneración Nacional"


def test_a_president_who_followed_a_municipal_council_is_listed(special):
    ocampo = special["Ocampo"]
    assert ocampo["name"] == "Rafael Solís Martínez"
    assert ocampo["article"] == "Municipio de Ocampo (Chihuahua)"


def test_a_vacant_post_has_no_person_and_says_why(special):
    tancanhuitz = special["Tancanhuitz"]
    assert tancanhuitz["name"] is None
    assert tancanhuitz["vacant"] == "Vacante"


def test_an_interim_president_is_listed_without_a_party(special):
    teuchitlan = special["Teuchitlán"]
    assert teuchitlan["name"] == "Jaime Rodríguez Ballesteros"
    assert teuchitlan["party_raw"] == "Interino"


def test_a_page_without_the_municipal_table_is_an_error():
    with pytest.raises(ValueError):
        parse_mayors("== Presidentes ==\nSin tabla.")


def test_term_dates_are_read_from_the_pages_opening_sentence():
    assert parse_term(read("wiki_pm_aguascalientes_rev172212877.wikitext")) == ("2024-10-15", "2027-10-14")
    assert parse_term(read("wiki_alcaldes_cdmx_rev176043626.wikitext"))[0] == "2024-10-01"


def test_term_dates_are_left_empty_when_the_page_does_not_state_them():
    assert parse_term("Los presidentes municipales fueron elegidos en 2024.\n== Lista ==") == (None, None)


# ----- Matching Wikipedia's municipality names to INEGI's -----

def official(codes_by_name):
    """INEGI's municipalities of one state as the matcher takes them: {code: name}."""
    return {code: name for name, code in codes_by_name.items()}


CHIAPAS = official({"Cintalapa de Figueroa": "07017", "Comitán de Domínguez": "07019", "San Juan Cancuc": "07112", "San Fernando": "07079"})


def test_same_name_matches():
    assert match_municipality("San Fernando", "Municipio de San Fernando (Chiapas)", CHIAPAS) == "07079"


def test_spelling_differences_in_accents_and_case_do_not_matter():
    assert match_municipality("comitan de dominguez", "", CHIAPAS) == "07019"


def test_a_short_everyday_name_matches_the_one_official_name_that_contains_it():
    assert match_municipality("Cintalapa", "Municipio de Cintalapa", CHIAPAS) == "07017"
    oaxaca = official({"Heroica Ciudad de Ejutla de Crespo": "20028", "Santiago Juxtlahuaca": "20469"})
    assert match_municipality("Ejutla de Crespo", "Municipio de Ejutla de Crespo", oaxaca) == "20028"


def test_the_article_title_is_tried_when_the_shown_name_is_shortened():
    cdmx = official({"Cuajimalpa de Morelos": "09004", "Cuauhtémoc": "09015"})
    assert match_municipality("Cuajimalpa", "Cuajimalpa de Morelos", cdmx) == "09004"


def test_a_name_that_could_be_several_municipalities_is_not_guessed():
    several = official({"San Pedro Tlaquepaque": "14098", "San Pedro del Gallo": "10031", "Tonalá": "14101"})
    assert match_municipality("San Pedro", "Municipio de San Pedro", several) is None


def test_an_unknown_name_is_not_matched():
    assert match_municipality("Atlántida", "Municipio de Atlántida", CHIAPAS) is None


def test_a_replacement_listed_without_a_party_has_no_party_rather_than_their_own_name(special):
    tlachichuca = special["Tlachichuca"]  # three presidents in a row; the last two rows give only a name
    assert tlachichuca["name"] == "Carmelo Amador Fuentes Bailón"
    assert tlachichuca["party_raw"] == ""


def test_an_official_name_inside_the_everyday_one_matches():
    assert match_municipality("Villa de Zaragoza", "Municipio de Villa de Zaragoza", official({"Zaragoza": "24055", "Xilitla": "24054"})) == "24055"


def test_a_one_letter_or_one_word_spelling_difference_still_matches():
    assert match_municipality("Tixpéhual", "Municipio de Tixpéhual", official({"Tixpéual": "31095", "Tixmehuac": "31094"})) == "31095"
    assert match_municipality("San José Iturbide", "", official({"San José de Iturbide": "11032", "San Felipe": "11030"})) == "11032"


def test_two_official_names_equally_close_are_not_guessed_between():
    close = official({"San Juan Mixtepec -Dto. 08 -": "20208", "San Juan Mixtepec -Dto. 26 -": "20209"})
    assert match_municipality("San Juan Mixtepec", "Municipio de San Juan Mixtepec", close) is None


def test_a_renamed_municipality_is_found_under_its_new_official_name():
    assert match_municipality("Solidaridad", "Municipio de Solidaridad", official({"Playa del Carmen": "23008", "Tulum": "23009"}), state_code="23") == "23008"


def test_two_municipalities_with_the_same_official_name_are_not_guessed_between():
    # INEGI lists two "San Pedro Mixtepec" in Oaxaca (20318 and 20319).
    twins = {"20318": "San Pedro Mixtepec", "20319": "San Pedro Mixtepec", "20001": "Abejones"}
    assert match_municipality("San Pedro Mixtepec", "Municipio de San Pedro Mixtepec", twins) is None
