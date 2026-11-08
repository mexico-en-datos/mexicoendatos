"""The nine justices of the Supreme Court, from the Spanish Wikipedia article.

Fixture: the article as of revision 176164501 (2026-11-05). Its table lists the
justices in order of votes received in the 2025 judicial election.
"""
from pathlib import Path

import pytest

from informate.scjn import JUSTICES_TERM_RULE, PAGE_TITLE, parse_justices, term_end_by_rank

FIXTURE = Path(__file__).parent / "fixtures" / "wiki_scjn_rev176164501.wikitext"


@pytest.fixture(scope="module")
def justices():
    return parse_justices(FIXTURE.read_text(encoding="utf-8"))


def test_the_source_is_the_courts_article():
    assert PAGE_TITLE == "Suprema Corte de Justicia de la Nación"


def test_reads_the_nine_justices_in_the_pages_order(justices):
    assert len(justices) == 9
    assert [j["name"] for j in justices][:3] == ["Hugo Aguilar Ortiz", "Lenia Batres Guadarrama", "Yasmín Esquivel Mossa"]
    assert justices[-1]["name"] == "Sara Irene Herrerías Guerra"


def test_reads_role_home_state_and_start_of_term(justices):
    president = justices[0]
    assert president["role"] == "Ministro presidente"
    assert president["home_state_raw"] == "Oaxaca"
    assert president["term_start"] == "2025-09-01"
    assert justices[1]["role"] == "Ministra"
    assert justices[5]["role"] == "Ministro"


def test_a_page_without_the_composition_table_is_an_error():
    with pytest.raises(ValueError):
        parse_justices("== Historia ==\nTexto sin tabla.")


def test_terms_end_by_vote_rank_as_the_2024_transitional_rule_says():
    assert [term_end_by_rank(rank) for rank in range(9)] == ["2036"] * 5 + ["2033"] * 4


def test_the_rule_is_cited_with_a_link_and_dates():
    assert "2033" in JUSTICES_TERM_RULE["text"] and "2036" in JUSTICES_TERM_RULE["text"]
    assert JUSTICES_TERM_RULE["url"].startswith("http")
    assert len(JUSTICES_TERM_RULE["checked_at"]) == 10
