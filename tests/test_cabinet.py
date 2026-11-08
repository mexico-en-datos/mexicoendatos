"""The federal cabinet (gabinete legal), from the Spanish Wikipedia article "Gabinete de México".

Fixture: revision 175533934 (2026-09-26). The table lists each dependency with its head.
"""
from pathlib import Path

import pytest

from informate.cabinet import PAGE_TITLE, parse_cabinet

FIXTURE = Path(__file__).parent / "fixtures" / "wiki_gabinete_rev175533934.wikitext"


@pytest.fixture(scope="module")
def cabinet():
    return parse_cabinet(FIXTURE.read_text(encoding="utf-8"))


def test_the_source_is_the_cabinet_article():
    assert PAGE_TITLE == "Gabinete de México"


def test_reads_every_dependency_with_its_head_in_the_legal_order(cabinet):
    assert cabinet[0] == {"dependency": "Secretaría de Gobernación", "article": "Secretaría de Gobernación (México)", "name": "Rosa Icela Rodríguez", "vacant": None}
    assert cabinet[1]["name"] == "Roberto Velasco Álvarez"
    assert cabinet[-1]["dependency"] == "Agencia de Transformación Digital y Telecomunicaciones"
    assert len(cabinet) >= 20


def test_a_vacant_post_is_kept_and_marked(cabinet):
    women = next(row for row in cabinet if row["dependency"] == "Secretaría de las Mujeres")
    assert women["name"] is None and women["vacant"] == "Vacante"


def test_stray_spaces_in_names_are_tidied(cabinet):
    economy = next(row for row in cabinet if row["dependency"] == "Secretaría de Economía")
    assert economy["name"] == "Marcelo Ebrard"


def test_a_page_without_the_table_is_an_error():
    with pytest.raises(ValueError):
        parse_cabinet("== Historia ==\nSin tabla.")
