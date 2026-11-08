"""The President, from the Spanish Wikipedia article on the office (and the
person's own article for their party)."""
from pathlib import Path

import pytest

from informate.president import PRESIDENT_TERM_RULE, parse_office, parse_party, presidential_term

FIXTURES = Path(__file__).parent / "fixtures"


def test_reads_who_holds_the_office_and_since_when():
    office = parse_office((FIXTURES / "wiki_presidente_de_mexico_rev176178323_inicio.wikitext").read_text(encoding="utf-8"))
    assert office == {"name": "Claudia Sheinbaum Pardo", "article": "Claudia Sheinbaum", "term_start": "2024-10-01"}


def test_reads_the_current_party_from_the_persons_article():
    party = parse_party((FIXTURES / "wiki_claudia_sheinbaum_rev175797791_inicio.wikitext").read_text(encoding="utf-8"))
    assert party == "Morena (partido político)"  # the first party listed is the current one


def test_pages_without_the_fields_are_errors():
    with pytest.raises(ValueError):
        parse_office("{{Ficha de cargo político\n| nombre = Presidente\n}}")
    with pytest.raises(ValueError):
        parse_party("{{Ficha de persona\n| nombre = Alguien\n}}")


def test_the_term_is_six_years_from_taking_office():
    assert presidential_term("2024-10-01") == ("2024-10-01", "2030-09-30")
    assert "seis años" in PRESIDENT_TERM_RULE["text"] and PRESIDENT_TERM_RULE["url"].startswith("http")
