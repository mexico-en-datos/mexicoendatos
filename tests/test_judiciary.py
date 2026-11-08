"""The other two elected bodies of the federal judiciary, from Spanish Wikipedia."""
from pathlib import Path

import pytest

from informate.judiciary import parse_electoral_tribunal, parse_discipline_tribunal, electoral_term_end, TDJ_TERM_NOTE
from informate.dataset import magistrate_records

FIXTURES = Path(__file__).parent / "fixtures"
TEPJF = (FIXTURES / "wiki_tepjf_rev175170851.wikitext").read_text(encoding="utf-8")
TDJ = (FIXTURES / "wiki_tdj_rev175170915.wikitext").read_text(encoding="utf-8")


def test_electoral_tribunal_lists_seven_seats_including_the_vacant_one():
    rows = parse_electoral_tribunal(TEPJF)
    assert len(rows) == 7
    assert rows[0] == {"role": "Magistrada presidenta", "name": "Mónica Aralí Soto Fregoso", "elected": "2016-11-04", "vacant": False}
    assert rows[2] == {"role": None, "name": None, "elected": None, "vacant": True}
    assert rows[5] == {"role": "Magistrada", "name": "Claudia Valle Aguilasocho", "elected": "2025-06-01", "vacant": False}
    assert rows[6]["name"] == "Gilberto De Guzmán Bátiz García"


def test_electoral_terms_follow_the_fourth_transitional_article():
    assert electoral_term_end("2016-11-04") == "2027"  # in office at the reform: until 2027
    assert electoral_term_end("2025-06-01") == "2033"  # elected in 2025: eight years


def test_discipline_tribunal_lists_five_magistrates_with_their_start():
    rows = parse_discipline_tribunal(TDJ)
    assert [r["name"] for r in rows] == ["Celia Maya García", "Eva Verónica De Gyves Zárate", "Bernardo Bátiz", "Indira Isabel García Pérez", "Rufino H. León Tovar"]
    assert rows[0]["role"] == "Magistrada presidenta" and rows[1]["role"] is None
    assert all(r["term_start"] == "2025-09-01" for r in rows)


def test_pages_without_the_tables_are_refused():
    with pytest.raises(ValueError):
        parse_electoral_tribunal("== Otra cosa ==")
    with pytest.raises(ValueError):
        parse_discipline_tribunal("== Composición ==\nsin tabla")


def test_records_name_the_body_and_carry_rule_based_terms():
    revision = {"id": 175170851, "timestamp": "2026-09-03T05:54:46Z"}
    electoral = magistrate_records(parse_electoral_tribunal(TEPJF), "tepjf", revision, retrieved_at="2026-11-07T17:00:00Z")
    assert len(electoral) == 6  # the vacant seat is not a person
    soto = electoral[0]
    assert soto["office"] == "magistrate_tepjf" and soto["title"] == "Magistrada presidenta del Tribunal Electoral"
    assert soto["term_start"] == "2016-11-04" and soto["term_end"] == "2027" and soto["term_end_basis"] == "rule"
    valle = next(p for p in electoral if p["name"] == "Claudia Valle Aguilasocho")
    assert valle["term_start"] == "2025-09-01" and valle["term_end"] == "2033"  # sworn in on 1 Sept 2025 by the second transitional
    assert soto["citation"]["source"] == "wikipedia_tepjf" and soto["citation"]["url"].endswith("oldid=175170851")

    discipline = magistrate_records(parse_discipline_tribunal(TDJ), "tdj", {"id": 175170915, "timestamp": "2026-09-03T06:00:38Z"}, retrieved_at="2026-11-07T17:00:00Z")
    assert len(discipline) == 5
    assert discipline[0]["title"] == "Magistrada presidenta del Tribunal de Disciplina Judicial"
    assert discipline[1]["title"] == "Magistratura del Tribunal de Disciplina Judicial"
    assert discipline[1]["term_end"] is None and discipline[1]["term_end_note"] == TDJ_TERM_NOTE
