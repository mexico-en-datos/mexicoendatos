"""The five regions (circunscripciones) that elect the 200 list deputies.

Fixture: Spanish Wikipedia, "Anexo:Circunscripciones electorales de México",
revision 172276913 (2026-02-28), which states the make-up in force since 29 March 2023.
"""
from pathlib import Path

import pytest

from informate.circunscripciones import CIRCUNSCRIPCIONES, SOURCE, circunscripcion_of, number_of, parse_circunscripciones

FIXTURE = Path(__file__).parent / "fixtures" / "wiki_circunscripciones_rev172276913.wikitext"


def test_the_built_in_table_matches_the_source_page():
    assert parse_circunscripciones(FIXTURE.read_text(encoding="utf-8")) == [c["states"] for c in CIRCUNSCRIPCIONES]


def test_every_state_belongs_to_exactly_one_region():
    states = [code for c in CIRCUNSCRIPCIONES for code in c["states"]]
    assert len(states) == 32 and len(set(states)) == 32


def test_the_2023_changes_are_in():
    assert circunscripcion_of("13")["number"] == 4  # Hidalgo moved to the 4th
    assert circunscripcion_of("22")["number"] == 5  # Querétaro moved to the 5th
    assert circunscripcion_of("14")["seat"] == "Guadalajara"


@pytest.mark.parametrize("ordinal, number", [("Primera", 1), ("Tercera", 3), ("Quinta", 5), ("3.ª", 3), ("Sexta", None)])
def test_ordinals_as_sil_writes_them_become_numbers(ordinal, number):
    assert number_of(ordinal) == number


def test_the_source_is_cited_with_dates():
    assert SOURCE["url"].endswith("&oldid=172276913")
    assert SOURCE["published_at"] == "2026-02-28T11:37:19Z"
    assert len(SOURCE["checked_at"]) == 10
