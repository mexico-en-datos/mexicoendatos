"""Parsing the SIL (Secretaría de Gobernación) roster of sitting senators.

Fixture: the real page as served on 2026-11-06 (ISO-8859-1), LXVI Legislature.
"""
from collections import Counter
from pathlib import Path

import pytest

from informate import sil
from informate.sil import parse_election_region, parse_roster

FIXTURE = Path(__file__).parent / "fixtures" / "sil_senadores_lxvi_2026-11-06.html"


@pytest.fixture(scope="module")
def senators():
    return parse_roster(FIXTURE.read_bytes().decode("iso-8859-1"))


def test_finds_all_128_senators(senators):
    assert len(senators) == 128


def test_reads_name_party_state_and_election_type(senators):
    first = senators[0]
    assert first["name"] == "Heriberto Marcelo Aguilar Castillo"
    assert first["party_raw"] == "Morena"
    assert first["state_raw"] == "Sonora"
    assert first["election_type"] == "Mayoría Relativa"


def test_each_senator_carries_their_own_sil_profile_link(senators):
    first = senators[0]
    assert first["sil_id"] == "9229132"
    assert first["profile_url"] == (
        "http://sil.gobernacion.gob.mx/Librerias/pp_PerfilLegislador.php?SID=&Referencia=9229132"
    )
    assert len({s["profile_url"] for s in senators}) == 128


def test_national_list_senators_have_no_state(senators):
    anaya = next(s for s in senators if s["name"] == "Ricardo Anaya Cortés")
    assert anaya["election_type"] == "Representación Proporcional"
    assert anaya["state_raw"] == ""


def test_every_state_has_three_senators_and_32_come_from_the_national_list(senators):
    per_state = Counter(s["state_raw"] for s in senators)
    assert per_state.pop("") == 32
    assert len(per_state) == 32
    assert set(per_state.values()) == {3}


def test_reads_swearing_in_date_and_substitute_status(senators):
    first = senators[0]
    assert first["sworn_in"] == "2024-08-29"
    assert first["seat_status"] == "Propietario"
    arias = next(s for s in senators if s["name"] == "Alejandra Berenice Arias Trevilla")
    assert arias["seat_status"] == "Suplente"


def test_a_page_without_the_roster_is_an_error_not_an_empty_list():
    with pytest.raises(ValueError):
        parse_roster("<html><body>Request unsuccessful.</body></html>")


# ----- Deputies: same roster layout; the district is only on each person's profile page -----

DEPUTIES = Path(__file__).parent / "fixtures" / "sil_diputados_lxvi_muestra_2026-11-06.html"


def read(name):
    return (Path(__file__).parent / "fixtures" / name).read_bytes().decode("iso-8859-1")


def test_roster_urls_differ_only_by_chamber():
    assert "Camara=2" in sil.ROSTER_URL
    assert sil.DEPUTIES_ROSTER_URL == sil.ROSTER_URL.replace("Camara=2", "Camara=1")


def test_the_same_parser_reads_the_deputies_roster():
    deputies = parse_roster(DEPUTIES.read_bytes().decode("iso-8859-1"))
    assert [d["name"] for d in deputies][:2] == ["Yerico Abramo Masso", "Rocío Adriana Abreu Artiñano"]
    first = deputies[0]
    assert (first["role"], first["party_raw"], first["state_raw"], first["election_type"]) == (
        "Diputado LXVI", "PRI", "Coahuila", "Mayoría Relativa")
    assert len(deputies) == 6


def test_profile_of_a_district_deputy_gives_the_district_number_and_seat():
    assert parse_election_region(read("sil_perfil_diputado_distrito.html")) == {
        "district": 4, "district_seat": "Saltillo", "circunscription": None}


def test_profile_of_a_list_deputy_gives_the_circunscription():
    assert parse_election_region(read("sil_perfil_diputada_lista.html")) == {
        "district": None, "district_seat": None, "circunscription": "Tercera"}


def test_profile_that_names_no_region_gives_nothing_rather_than_a_guess():
    assert parse_election_region(read("sil_perfil_diputado_lista_sin_entidad.html")) == {
        "district": None, "district_seat": None, "circunscription": None}


def test_a_page_that_is_not_a_profile_is_an_error_not_an_empty_answer():
    # What SIL's protection serves (with status 200) when it refuses a request.
    blocked = "<html><body>Error. This page can't be displayed. Contact support for additional information.</body></html>"
    with pytest.raises(ValueError):
        parse_election_region(blocked)


# ----- The whole profile: where elected, and how to reach the office -----

from informate.sil import parse_profile  # noqa: E402


def test_profile_gives_official_contact_details_and_schooling():
    profile = parse_profile(read("sil_perfil_senador.html"))  # Heriberto Marcelo Aguilar Castillo, Sonora
    assert profile["email"] == "heriberto.aguilar@senado.gob.mx"
    assert profile["phone"] == "55 5345 3000 Ext.3245 y 3915"
    assert profile["office"].startswith("Edif., del Hemiciclo Piso 4 Oficina 17")
    assert profile["education"] == "Licenciatura, Ingeniería Civil"
    assert profile["district"] is None and profile["circunscription"] is None


def test_profile_of_a_deputy_has_both_region_and_contact():
    profile = parse_profile(read("sil_perfil_diputado_distrito.html"))
    assert (profile["district"], profile["district_seat"]) == (4, "Saltillo")
    assert profile["email"] == "yerico.abramo@diputados.gob.mx"
    assert profile["office"] == "Edificio H, Planta Baja."


def test_a_profile_without_contact_rows_still_parses_when_it_is_a_profile():
    stripped = read("sil_perfil_diputado_distrito.html").replace("Correo electrónico:", "Otro dato:")
    assert parse_profile(stripped)["email"] is None
