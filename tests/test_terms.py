"""When a Senate term starts and ends.

SIL lists when each senator was sworn in but not when their term ends. The end
follows from the Constitution (art. 56): the whole Senate is renewed every six
years, i.e. every second legislature. The LXVI Legislature opened that cycle on
1 September 2024.
"""
import pytest

from informate.terms import DEPUTIES_TERM_RULE, SENATE_TERM_RULE, deputies_term, senate_term


@pytest.mark.parametrize(
    "legislature, start, end",
    [
        (66, "2024-09-01", "2030-08-31"),  # first half of the current Senate term
        (67, "2024-09-01", "2030-08-31"),  # second half: same senators, same term
        (68, "2030-09-01", "2036-08-31"),  # the next full renewal
        (65, "2018-09-01", "2024-08-31"),  # the previous term's second half
    ],
)
def test_senate_term_spans_the_two_legislatures_of_a_six_year_cycle(legislature, start, end):
    assert senate_term(legislature) == (start, end)


def test_the_rule_is_cited_with_a_link_and_dates():
    assert "seis años" in SENATE_TERM_RULE["text"]
    assert SENATE_TERM_RULE["url"].startswith("http")
    assert len(SENATE_TERM_RULE["published_at"]) == 10
    assert len(SENATE_TERM_RULE["checked_at"]) == 10


def test_deputies_serve_exactly_one_three_year_legislature():
    assert deputies_term(66) == ("2024-09-01", "2027-08-31")
    assert deputies_term(67) == ("2027-09-01", "2030-08-31")


def test_the_deputies_rule_is_cited_with_a_link_and_dates():
    assert "tres años" in DEPUTIES_TERM_RULE["text"]
    assert DEPUTIES_TERM_RULE["url"].startswith("http")
    assert len(DEPUTIES_TERM_RULE["checked_at"]) == 10
