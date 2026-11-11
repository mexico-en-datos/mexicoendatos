"""The five constitutionally autonomous bodies and their heads, from Wikipedia, with term ends
from the Constitution and the laws.

Fixtures (infobox and lead of each article, revisions of 2026-09 to 2026-11): the five bodies'
articles and the five heads' articles. In October 2026 the INE's president resigned and the
Consejo General named a provisional one; the CNDH's president was re-elected in 2024.
"""
from pathlib import Path

import pytest

from informate.autonomous import BODIES, BODY, parse_head, parse_tenure, term_end

FIXTURES = Path(__file__).parent / "fixtures"
BODY_PAGES = {"ine": "wiki_ine_rev176072137_inicio.wikitext", "banxico": "wiki_banxico_rev176248146_inicio.wikitext", "cndh": "wiki_cndh_rev176178020_inicio.wikitext", "inegi": "wiki_inegi_rev175890478_inicio.wikitext", "fgr": "wiki_fgr_rev175169509_inicio.wikitext"}
HEAD_PAGES = {"ine": "wiki_blanca_cruz_rev176101919_inicio.wikitext", "banxico": "wiki_victoria_rodriguez_rev176059627_inicio.wikitext", "cndh": "wiki_rosario_piedra_rev175186881_inicio.wikitext", "inegi": "wiki_graciela_marquez_rev176107791_inicio.wikitext", "fgr": "wiki_ernestina_godoy_rev176059444_inicio.wikitext"}


def read(name):
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_the_five_bodies_in_constitutional_order():
    assert [b["short"] for b in BODIES] == ["INEGI", "Banxico", "INE", "FGR", "CNDH"]
    for body in BODIES:
        assert body["mandate"].startswith(("«", "Organismo")) and "Constitución" in body["basis"]
        assert body["term"]["url"] and body["term"]["published_at"] and body["term"]["checked_at"]


@pytest.mark.parametrize(
    "key, name, title",
    [
        ("ine", "Blanca Cruz García", "Consejera Presidenta"),
        ("banxico", "Victoria Rodríguez Ceja", None),
        ("cndh", "Rosario Piedra Ibarra", "Presidenta"),
        ("inegi", "Graciela Márquez Colín", "Presidenta"),
        ("fgr", "Ernestina Godoy Ramos", "Fiscal general"),
    ],
)
def test_each_body_article_names_its_head(key, name, title):
    head = parse_head(read(BODY_PAGES[key]), BODY[key])
    assert head["name"] == name and head["article"] == name
    assert head["title"] == title


def test_head_article_gives_the_post_as_worded_and_its_start():
    cruz = parse_tenure(read(HEAD_PAGES["ine"]), BODY["ine"])
    assert cruz == {"title": "Presidenta del Instituto Nacional Electoral", "start": "2026-10-27", "end": None, "provisional": True, "reelected": None}
    rodriguez = parse_tenure(read(HEAD_PAGES["banxico"]), BODY["banxico"])
    assert rodriguez["title"] == "Gobernadora del Banco de México" and rodriguez["start"] == "2022-01-01" and not rodriguez["provisional"]
    godoy = parse_tenure(read(HEAD_PAGES["fgr"]), BODY["fgr"])
    assert godoy["title"] == "Fiscal General de la República" and godoy["start"] == "2025-12-03"
    marquez = parse_tenure(read(HEAD_PAGES["inegi"]), BODY["inegi"])
    assert marquez["start"] == "2022-01-01" and marquez["title"].startswith("Presidenta del Instituto Nacional de Estadística")


def test_the_lead_records_a_reelection():
    piedra = parse_tenure(read(HEAD_PAGES["cndh"]), BODY["cndh"])
    assert piedra["start"] == "2019-11-16" and piedra["reelected"] == (2024, 2029)


def test_term_ends_follow_each_law():
    assert term_end(BODY["banxico"], parse_tenure(read(HEAD_PAGES["banxico"]), BODY["banxico"])) == ("2027-12-31", "rule", None)
    assert term_end(BODY["inegi"], parse_tenure(read(HEAD_PAGES["inegi"]), BODY["inegi"])) == ("2027-12-31", "rule", None)
    assert term_end(BODY["fgr"], parse_tenure(read(HEAD_PAGES["fgr"]), BODY["fgr"])) == ("2034-12-02", "rule", None)
    end, basis, note = term_end(BODY["cndh"], parse_tenure(read(HEAD_PAGES["cndh"]), BODY["cndh"]))
    assert (end, basis) == ("2029-11-15", "rule") and note == "Reelección para 2024-2029 registrada por la fuente"


def test_a_provisional_head_has_no_computed_end_but_says_who_must_fill_the_post():
    end, basis, note = term_end(BODY["ine"], parse_tenure(read(HEAD_PAGES["ine"]), BODY["ine"]))
    assert end is None and basis is None
    assert note.startswith("Designación provisional, según la fuente; corresponde a la Cámara de Diputados")


def test_a_missing_start_is_said_rather_than_guessed():
    assert term_end(BODY["fgr"], {"start": None, "end": None, "provisional": False, "reelected": None}) == (None, None, "La fuente no da la fecha de inicio")
