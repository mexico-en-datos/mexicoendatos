"""Pueblos Mágicos from the Wikipedia annex and World Heritage sites from UNESCO's list.

Fixtures: revision 176046290 (2026-10-28) of "Anexo:Pueblos mágicos"; the Mexican rows of the
World Heritage Centre's Spanish XML list, read on 2026-11-12.
"""
from pathlib import Path

import pytest

from informate.heritage import PUEBLOS_TITLE, UNESCO_XML_URL, parse_pueblos, parse_unesco

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="module")
def pueblos():
    return parse_pueblos((FIXTURES / "wiki_pueblos_magicos_rev176046290.wikitext").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def sites():
    return parse_unesco((FIXTURES / "unesco_lista_mx_2026-11-12.xml").read_text(encoding="utf-8"))


def test_sources_are_the_annex_and_the_centres_spanish_list():
    assert PUEBLOS_TITLE == "Anexo:Pueblos mágicos"
    assert UNESCO_XML_URL == "https://whc.unesco.org/es/list/xml/"


def test_every_pueblo_magico_has_its_state_date_and_coordinates(pueblos):
    towns, warnings = pueblos
    assert len(towns) == 177
    assert warnings == []
    calvillo = next(t for t in towns if t["name"] == "Calvillo")
    assert calvillo == {"name": "Calvillo", "state_code": "01", "state": "Aguascalientes", "named_on": "2012-11-01", "lat": 21.846944, "lon": -102.718611}
    assert all(t["lat"] and t["lon"] and t["named_on"] for t in towns)
    assert len({t["state_code"] for t in towns}) == 31  # every state but Ciudad de México


def test_pueblos_are_ordered_by_state_then_name_and_links_lose_their_qualifiers(pueblos):
    towns, _ = pueblos
    assert towns[0]["state_code"] == "01" and towns[-1]["state_code"] == "32"
    gracia = next(t for t in towns if t["name"].startswith("San José de Gracia") and t["state_code"] == "01")
    assert gracia["name"] == "San José de Gracia"  # the link said "San José de Gracia (municipio)"


def test_world_heritage_sites_of_mexico_with_category_year_and_points(sites):
    assert len(sites) == 36
    assert sites[0]["inscribed"] == 1987 and sites[-1]["inscribed"] >= 2021  # oldest first
    first = next(s for s in sites if s["name"] == "Sian Ka'an")
    assert first["category"] == "natural" and first["inscribed"] == 1987
    assert first["points"] == [[19.38333, -87.79167]]
    assert first["url"].startswith("https://whc.unesco.org/") and first["location"].startswith("Quintana Roo")
    assert all(s["points"] for s in sites)
    assert {s["category"] for s in sites} <= {"cultural", "natural", "mixto"}


def test_a_site_spread_over_several_places_keeps_every_point(sites):
    centre = next(s for s in sites if s["name"].startswith("Centro histórico de México"))
    assert len(centre["points"]) == 4 and centre["inscribed"] == 1987
    assert centre["summary"] and "<" not in centre["summary"]
