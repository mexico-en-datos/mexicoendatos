"""Turning parsed source rows into the published dataset: one record per person,
each with a citation (link + dates)."""
from pathlib import Path

import pytest

from informate.dataset import build_dataset, check_dataset, deputy_records, governor_records, senator_records
from informate.sil import parse_roster
from informate.wikipedia import parse_governors

FIXTURES = Path(__file__).parent / "fixtures"
RETRIEVED = "2026-11-06T19:00:00Z"
REVISION = {"id": 175719290, "timestamp": "2026-10-08T04:24:51Z"}


@pytest.fixture(scope="module")
def senators():
    page = (FIXTURES / "sil_senadores_lxvi_2026-11-06.html").read_bytes().decode("iso-8859-1")
    return senator_records(parse_roster(page), retrieved_at=RETRIEVED)


@pytest.fixture(scope="module")
def governors():
    wikitext = (FIXTURES / "wikipedia_gobernantes_rev175719290.wikitext").read_text(encoding="utf-8")
    return governor_records(parse_governors(wikitext), revision=REVISION, retrieved_at=RETRIEVED)


def test_senator_record_has_party_code_and_inegi_state_code(senators):
    first = senators[0]
    assert first["office"] == "senator"
    assert first["name"] == "Heriberto Marcelo Aguilar Castillo"
    assert first["party"] == "MORENA"
    assert first["state_code"] == "26"
    assert first["state"] == "Sonora"


def test_senator_district_says_state_and_how_the_seat_was_won(senators):
    assert senators[0]["district"] == "Sonora (mayoría relativa)"
    anorve = next(s for s in senators if s["name"] == "Manuel Añorve Baños")
    assert anorve["district"] == "Guerrero (primera minoría)"


def test_national_list_senator_has_no_state_and_says_so(senators):
    anaya = next(s for s in senators if s["name"] == "Ricardo Anaya Cortés")
    assert anaya["state_code"] is None
    assert anaya["state"] is None
    assert anaya["district"] == "Lista nacional (representación proporcional)"


def test_senator_is_cited_to_their_own_sil_profile_with_the_retrieval_date(senators):
    citation = senators[0]["citation"]
    assert citation["url"] == (
        "http://sil.gobernacion.gob.mx/Librerias/pp_PerfilLegislador.php?SID=&Referencia=9229132"
    )
    assert citation["retrieved_at"] == RETRIEVED
    assert citation["source"] == "sil"
    assert citation["published_at"] is None  # SIL pages carry no date of their own


def test_governor_record_has_party_code_state_code_and_term(governors):
    ags = governors[0]
    assert ags["office"] == "governor"
    assert ags["title"] == "Gobernadora"
    assert ags["name"] == "María Teresa Jiménez Esquivel"
    assert ags["party"] == "PAN"
    assert ags["state_code"] == "01"
    assert ags["district"] == "Aguascalientes"
    assert ags["term_start"] == "2022-10-01"
    assert ags["term_end"] == "2027-09-30"


def test_governor_from_a_wikipedia_estado_de_title_gets_the_inegi_name(governors):
    edomex = next(g for g in governors if g["state_code"] == "15")
    assert edomex["state"] == "México"
    assert edomex["name"] == "Delfina Gómez Álvarez"


def test_governor_is_cited_to_the_exact_wikipedia_revision_with_both_dates(governors):
    citation = governors[0]["citation"]
    assert citation["url"] == (
        "https://es.wikipedia.org/w/index.php"
        "?title=Anexo:Gobernantes_de_las_entidades_federativas_de_M%C3%A9xico&oldid=175719290"
    )  # percent-encoded so the link survives being pasted anywhere
    assert citation["published_at"] == "2026-10-08T04:24:51Z"
    assert citation["retrieved_at"] == RETRIEVED
    assert citation["source"] == "wikipedia"


def test_every_person_has_a_link_and_a_date(senators, governors):
    for person in senators + governors:
        assert person["citation"]["url"].startswith("http")
        assert person["citation"]["retrieved_at"]


def test_complete_rosters_raise_no_warnings(senators, governors):
    assert check_dataset(senators + governors) == []


def test_a_state_missing_a_senator_is_reported(senators, governors):
    one_short = [p for p in senators if p["name"] != "Heriberto Marcelo Aguilar Castillo"]
    warnings = check_dataset(one_short + governors)
    assert any("Sonora" in w and "2" in w for w in warnings)


def test_a_state_without_a_governor_is_reported(senators, governors):
    warnings = check_dataset(senators + governors[1:])
    assert any("Aguascalientes" in w for w in warnings)


def test_dataset_lists_each_source_with_its_link_and_dates(senators, governors):
    dataset = build_dataset(senators, governors, revision=REVISION, retrieved_at=RETRIEVED)
    assert dataset["generated_at"] == RETRIEVED
    assert len(dataset["people"]) == 160
    assert dataset["warnings"] == []
    sil = dataset["sources"]["sil"]
    assert sil["url"].startswith("http://sil.gobernacion.gob.mx/")
    assert sil["retrieved_at"] == RETRIEVED
    assert sil["official"] is True
    wiki = dataset["sources"]["wikipedia"]
    assert wiki["url"].endswith("&oldid=175719290")
    assert wiki["published_at"] == "2026-10-08T04:24:51Z"
    assert wiki["official"] is False


def test_senator_has_the_date_they_took_the_seat_and_the_date_the_senate_term_ends(senators):
    first = senators[0]
    assert first["term_start"] == "2024-08-29"  # sworn in, as SIL lists it
    assert first["term_end"] == "2030-08-31"
    assert first["term_end_basis"] == "rule"  # not listed by SIL: follows from the six-year rule


def test_a_substitute_who_took_the_seat_later_still_ends_with_the_senate_term(senators):
    late = next(s for s in senators if s["term_start"] > "2025-01-01")
    assert late["term_end"] == "2030-08-31"


def test_governor_term_dates_are_the_ones_the_source_lists(governors):
    ags = governors[0]
    assert (ags["term_start"], ags["term_end"]) == ("2022-10-01", "2027-09-30")
    assert ags["term_end_basis"] == "source"


def test_dataset_explains_the_rule_behind_calculated_dates(senators, governors):
    dataset = build_dataset(senators, governors, revision=REVISION, retrieved_at=RETRIEVED)
    rule = dataset["rules"]["senate_term"]
    assert "seis años" in rule["text"]
    assert rule["url"].startswith("http") and rule["checked_at"]


# ----- Federal deputies -----

REGIONS = {
    "9228260": {"district": 4, "district_seat": "Saltillo", "circunscription": None},   # Yerico Abramo Masso
    "9228868": {"district": None, "district_seat": None, "circunscription": "Tercera"},  # Rocío Adriana Abreu Artiñano
}


@pytest.fixture(scope="module")
def deputies():
    page = (FIXTURES / "sil_diputados_lxvi_muestra_2026-11-06.html").read_bytes().decode("iso-8859-1")
    return deputy_records(parse_roster(page), regions=REGIONS, retrieved_at=RETRIEVED)


def by_name(people, name):
    return next(p for p in people if p["name"] == name)


def test_district_deputy_belongs_to_a_state_and_names_the_district(deputies):
    abramo = by_name(deputies, "Yerico Abramo Masso")
    assert (abramo["office"], abramo["title"], abramo["party"]) == ("deputy", "Diputado", "PRI")
    assert abramo["state_code"] == "05"
    assert abramo["district_number"] == 4
    assert abramo["district"] == "Coahuila de Zaragoza, distrito 4 (Saltillo)"


def test_list_deputy_belongs_to_no_state_and_names_the_circunscription(deputies):
    abreu = by_name(deputies, "Rocío Adriana Abreu Artiñano")
    assert abreu["state_code"] is None  # elected from a regional list, not by a state
    assert abreu["district"] == "Tercera circunscripción (representación proporcional)"


def test_district_deputy_whose_profile_was_not_read_still_shows_the_state(deputies):
    acosta = by_name(deputies, "Anabel Acosta Islas")
    assert acosta["state_code"] == "26"
    assert acosta["district_number"] is None
    assert acosta["district"] == "Sonora (mayoría relativa)"


def test_list_deputy_without_region_information_says_only_what_is_known(deputies):
    assert by_name(deputies, "Erubiel Lorenzo Alonso Que")["district"] == "Lista plurinominal (representación proporcional)"


def test_an_independent_deputy_counts_as_without_party(deputies):
    assert by_name(deputies, "Guadalupe Araceli Mendoza Arias")["party"] == "SP"


def test_deputy_is_cited_to_their_sil_profile_and_ends_with_the_legislature(deputies):
    abramo = by_name(deputies, "Yerico Abramo Masso")
    assert abramo["citation"]["url"].endswith("Referencia=9228260")
    assert abramo["citation"]["retrieved_at"] == RETRIEVED
    assert (abramo["term_start"], abramo["term_end"], abramo["term_end_basis"]) == ("2024-08-29", "2027-08-31", "rule")


def test_a_short_deputies_roster_is_reported(senators, governors, deputies):
    warnings = check_dataset(governors + senators + deputies)
    assert any("Cámara de Diputados" in w and "6" in w and "500" in w for w in warnings)


def test_dataset_with_deputies_lists_their_roster_and_rule(senators, governors, deputies):
    dataset = build_dataset(senators, governors, revision=REVISION, retrieved_at=RETRIEVED, deputies=deputies)
    assert len(dataset["people"]) == 166
    assert "Camara=1" in dataset["sources"]["sil"]["deputies_url"]
    assert "tres años" in dataset["rules"]["deputies_term"]["text"]


# ----- Municipal presidents -----

from informate.dataset import mayor_records  # noqa: E402
from informate.mayors import PAGES  # noqa: E402

AGUASCALIENTES = {  # INEGI's municipalities of the state: {code: name}
    "01001": "Aguascalientes", "01002": "Asientos", "01003": "Calvillo", "01004": "Cosío",
    "01005": "Jesús María", "01006": "Pabellón de Arteaga", "01007": "Rincón de Romos",
    "01008": "San José de Gracia", "01009": "Tepezalá", "01010": "El Llano",
    "01011": "San Francisco de los Romo",
}
PAGE_REVISION = {"id": 172212877, "timestamp": "2026-02-24T03:18:36Z"}


def mayor_page(fixture, state="01", revision=PAGE_REVISION):
    return {state: {"title": PAGES[state], "wikitext": (FIXTURES / fixture).read_text(encoding="utf-8"), "revision": revision}}


@pytest.fixture(scope="module")
def mayors():
    records, notes = mayor_records(
        mayor_page("wiki_pm_aguascalientes_rev172212877.wikitext"), {"01": AGUASCALIENTES}, retrieved_at=RETRIEVED)
    return records, notes


def test_mayor_record_places_the_person_in_an_inegi_municipality(mayors):
    first = mayors[0][0]
    assert (first["office"], first["title"]) == ("mayor", "Presidencia municipal")
    assert first["name"] == "Leonardo Montañez Castro"
    assert first["party"] == "PAN"
    assert (first["state_code"], first["municipality_code"], first["municipality"]) == ("01", "01001", "Aguascalientes")
    assert first["district"] == "Aguascalientes"
    assert len(mayors[0]) == 11


def test_mayor_term_dates_come_from_the_page(mayors):
    first = mayors[0][0]
    assert (first["term_start"], first["term_end"], first["term_end_basis"]) == ("2024-10-15", "2027-10-14", "source")


def test_mayor_is_cited_to_the_exact_revision_of_the_states_page(mayors):
    citation = mayors[0][0]["citation"]
    assert citation["url"] == (
        "https://es.wikipedia.org/w/index.php"
        "?title=Anexo:Presidentes_municipales_de_Aguascalientes_(2024-2027)&oldid=172212877")
    assert citation["published_at"] == "2026-02-24T03:18:36Z"
    assert citation["retrieved_at"] == RETRIEVED
    assert citation["source"] == "wikipedia"


def test_an_independent_mayor_is_without_party_and_a_small_party_keeps_its_own_name(mayors):
    by_town = {m["municipality"]: m for m in mayors[0]}
    assert by_town["Cosío"]["party"] == "SP"
    others = [m for m in mayors[0] if m["party"] == "OTRO"]
    assert [m["party_name"] for m in others] == ["Partido de la Revolución Democrática"]


def test_complete_coverage_of_a_state_raises_no_note(mayors):
    assert mayors[1] == []


def test_mexico_citys_heads_are_alcaldias():
    records, _ = mayor_records(
        mayor_page("wiki_alcaldes_cdmx_rev176043626.wikitext", state="09"),
        {"09": {"09010": "Álvaro Obregón", "09004": "Cuajimalpa de Morelos"}}, retrieved_at=RETRIEVED)
    assert records[0]["title"] == "Alcaldía"
    assert records[0]["municipality_code"] == "09010"


def test_gaps_in_the_source_are_counted_and_named():
    catalog = {"30": {"30013": "Naranjos Amatlán", "30087": "Xalapa"}, "20": {"20001": "Abejones"}}
    records, notes = mayor_records(mayor_page("wiki_pm_casos_especiales.wikitext", state="30"), catalog, retrieved_at=RETRIEVED)
    placed = [r for r in records if r["municipality_code"]]
    assert [r["name"] for r in placed] == ["Humberto Ancelin Cruz"]
    # three municipalities exist in the catalogue; one has a president in the source
    assert any("1 de 3" in note and "faltan 2" in note and "1 de ellos en Oaxaca" in note for note in notes)
    # the vacant post is named, and so are the presidents whose municipality could not be placed
    assert any("Tancanhuitz" in note and "sin titular" in note for note in notes)
    assert any("no se pudieron ubicar" in note and "Ocampo" in note for note in notes)
    assert any(r["name"] == "Rafael Solís Martínez" and r["municipality_code"] is None for r in records)


def test_a_municipality_listed_twice_by_the_source_gives_one_record():
    page = mayor_page("wiki_pm_aguascalientes_rev172212877.wikitext")
    table_end = page["01"]["wikitext"].rfind("\n|}")
    duplicate_row = "\n|-\n| [[Municipio de Calvillo|Calvillo]]\n| Daniel Romo Urrutia\n| bgcolor=#05338D|\n| [[Partido Acción Nacional]]"
    page["01"]["wikitext"] = page["01"]["wikitext"][:table_end] + duplicate_row + page["01"]["wikitext"][table_end:]
    records, _ = mayor_records(page, {"01": AGUASCALIENTES}, retrieved_at=RETRIEVED)
    assert len([r for r in records if r["municipality_code"] == "01003"]) == 1


def test_dataset_with_mayors_lists_every_page_read_with_its_dates(senators, governors, mayors):
    pages = mayor_page("wiki_pm_aguascalientes_rev172212877.wikitext")
    dataset = build_dataset(senators, governors, revision=REVISION, retrieved_at=RETRIEVED,
                            mayors=mayors[0], mayor_pages=pages, mayors_retrieved_at="2026-11-06T10:00:00Z")
    assert len(dataset["people"]) == 171
    source = dataset["sources"]["wikipedia_mayors"]
    assert source["official"] is False
    assert source["retrieved_at"] == "2026-11-06T10:00:00Z"
    assert source["pages"] == [{
        "state_code": "01",
        "state": "Aguascalientes",
        "url": "https://es.wikipedia.org/w/index.php?title=Anexo:Presidentes_municipales_de_Aguascalientes_(2024-2027)&oldid=172212877",
        "published_at": "2026-02-24T03:18:36Z",
    }]


# ----- Supreme Court justices -----

from informate.dataset import justice_records  # noqa: E402
from informate.scjn import parse_justices  # noqa: E402

SCJN_REVISION = {"id": 176164501, "timestamp": "2026-11-05T19:12:01Z"}


@pytest.fixture(scope="module")
def justices():
    wikitext = (FIXTURES / "wiki_scjn_rev176164501.wikitext").read_text(encoding="utf-8")
    return justice_records(parse_justices(wikitext), revision=SCJN_REVISION, retrieved_at=RETRIEVED)


def test_justice_record_has_no_party_no_state_and_a_court_wide_district(justices):
    president = justices[0]
    assert (president["office"], president["title"], president["name"]) == ("justice", "Ministro presidente", "Hugo Aguilar Ortiz")
    assert president["party"] == "SP"
    assert president["party_name"] == "Cargo sin partido"
    assert president["state_code"] is None
    assert president["district"] == "Suprema Corte de Justicia de la Nación"


def test_justice_terms_follow_vote_rank(justices):
    assert (justices[0]["term_start"], justices[0]["term_end"], justices[0]["term_end_basis"]) == ("2025-09-01", "2036", "rule")
    assert justices[8]["term_end"] == "2033"


def test_justice_is_cited_to_the_articles_revision(justices):
    citation = justices[0]["citation"]
    assert citation["url"] == "https://es.wikipedia.org/w/index.php?title=Suprema_Corte_de_Justicia_de_la_Naci%C3%B3n&oldid=176164501"
    assert citation["published_at"] == "2026-11-05T19:12:01Z"
    assert citation["retrieved_at"] == RETRIEVED


def test_a_court_without_nine_justices_is_reported(senators, governors, justices):
    assert check_dataset(governors + senators + justices) == []
    warnings = check_dataset(governors + senators + justices[:8])
    assert any("Suprema Corte" in w and "8" in w and "9" in w for w in warnings)


def test_dataset_with_justices_lists_the_article_and_the_rule(senators, governors, justices):
    dataset = build_dataset(senators, governors, revision=REVISION, retrieved_at=RETRIEVED, justices=justices, scjn_revision=SCJN_REVISION)
    assert len(dataset["people"]) == 169
    source = dataset["sources"]["wikipedia_scjn"]
    assert source["url"].endswith("&oldid=176164501")
    assert source["published_at"] == "2026-11-05T19:12:01Z"
    assert source["official"] is False
    assert "2036" in dataset["rules"]["justices_term"]["text"]


# ----- List deputies belong to a region; the President -----

from informate.dataset import president_records  # noqa: E402
from informate.president import parse_office, parse_party  # noqa: E402


def test_list_deputy_carries_the_number_of_their_region(deputies):
    abreu = by_name(deputies, "Rocío Adriana Abreu Artiñano")
    assert abreu["region_number"] == 3
    assert by_name(deputies, "Erubiel Lorenzo Alonso Que")["region_number"] is None  # profile not read yet
    assert by_name(deputies, "Yerico Abramo Masso")["region_number"] is None  # district seats have none


PRESIDENT_REVISIONS = {
    "office": {"id": 176178323, "timestamp": "2026-11-06T17:08:56Z"},
    "person": {"id": 175797791, "timestamp": "2026-10-12T23:28:02Z"},
}


@pytest.fixture(scope="module")
def president():
    office = parse_office((FIXTURES / "wiki_presidente_de_mexico_rev176178323_inicio.wikitext").read_text(encoding="utf-8"))
    party = parse_party((FIXTURES / "wiki_claudia_sheinbaum_rev175797791_inicio.wikitext").read_text(encoding="utf-8"))
    return president_records(office, party, PRESIDENT_REVISIONS, retrieved_at=RETRIEVED)


def test_president_record(president):
    assert len(president) == 1
    p = president[0]
    assert (p["office"], p["title"], p["name"], p["party"]) == ("president", "Presidencia de la República", "Claudia Sheinbaum Pardo", "MORENA")
    assert p["state_code"] is None and p["district"] == "Presidencia de la República"
    assert (p["term_start"], p["term_end"], p["term_end_basis"]) == ("2024-10-01", "2030-09-30", "rule")


def test_president_is_cited_to_both_articles(president):
    citation = president[0]["citation"]
    assert citation["url"].endswith("&oldid=176178323")
    assert citation["published_at"] == "2026-11-06T17:08:56Z"
    assert citation["party_url"].endswith("&oldid=175797791")


def test_dataset_with_president_lists_the_regions_and_the_rule(senators, governors, president):
    dataset = build_dataset(senators, governors, revision=REVISION, retrieved_at=RETRIEVED, president=president, president_revisions=PRESIDENT_REVISIONS)
    assert len(dataset["people"]) == 161
    assert dataset["sources"]["wikipedia_president"]["url"].endswith("&oldid=176178323")
    assert "seis años" in dataset["rules"]["president_term"]["text"]
    regions = dataset["circunscripciones"]
    assert len(regions["list"]) == 5 and regions["source"]["checked_at"]
    assert "13" in regions["list"][3]["states"]


def test_more_or_fewer_than_one_president_is_reported(senators, governors, president):
    assert check_dataset(governors + senators + president) == []
    assert any("Presidencia" in w for w in check_dataset(governors + senators + president * 2))


# ----- The cabinet -----

from informate.cabinet import parse_cabinet  # noqa: E402
from informate.dataset import cabinet_records  # noqa: E402

CABINET_REVISION = {"id": 175533934, "timestamp": "2026-09-26T07:31:15Z"}


@pytest.fixture(scope="module")
def cabinet():
    wikitext = (FIXTURES / "wiki_gabinete_rev175533934.wikitext").read_text(encoding="utf-8")
    return cabinet_records(parse_cabinet(wikitext), revision=CABINET_REVISION, retrieved_at=RETRIEVED)


def test_secretary_record_names_the_dependency_and_admits_what_the_source_lacks(cabinet):
    records, notes = cabinet
    first = records[0]
    assert (first["office"], first["title"], first["name"]) == ("secretary", "Secretaría de Gobernación", "Rosa Icela Rodríguez")
    assert first["party"] == "SP" and first["party_name"] == "Partido no indicado en la fuente"
    assert first["state_code"] is None and first["district"] == "Secretaría de Gobernación"
    assert first["term_start"] is None and first["term_end"] is None and first["term_end_basis"] is None
    assert first["citation"]["url"].endswith("&oldid=175533934")
    assert first["citation"]["published_at"] == "2026-09-26T07:31:15Z"


def test_vacant_dependencies_are_not_people_but_are_reported(cabinet):
    records, notes = cabinet
    assert not any(r["title"] == "Secretaría de las Mujeres" for r in records)
    assert any("Secretaría de las Mujeres" in note and "vacante" in note.lower() for note in notes)


def test_dataset_with_cabinet_lists_its_source(senators, governors, cabinet):
    dataset = build_dataset(senators, governors, revision=REVISION, retrieved_at=RETRIEVED, cabinet=cabinet[0], cabinet_revision=CABINET_REVISION)
    assert len(dataset["people"]) == 160 + len(cabinet[0])
    assert dataset["sources"]["wikipedia_cabinet"]["url"].endswith("&oldid=175533934")


# ----- Legislators carry their office's contact details when their profile was read -----

PROFILES = {
    "9229132": {"district": None, "district_seat": None, "circunscription": None, "email": "heriberto.aguilar@senado.gob.mx", "phone": "55 5345 3000 Ext.3245 y 3915", "office": "Edif., del Hemiciclo Piso 4 Oficina 17", "education": "Licenciatura, Ingeniería Civil"},
}


def test_senator_with_a_profile_gets_contact_details_and_schooling():
    page = (FIXTURES / "sil_senadores_lxvi_2026-11-06.html").read_bytes().decode("iso-8859-1")
    records = senator_records(parse_roster(page), retrieved_at=RETRIEVED, profiles=PROFILES)
    first = records[0]
    assert first["contact"] == {"email": "heriberto.aguilar@senado.gob.mx", "phone": "55 5345 3000 Ext.3245 y 3915", "office": "Edif., del Hemiciclo Piso 4 Oficina 17"}
    assert first["education"] == "Licenciatura, Ingeniería Civil"
    assert records[1]["contact"] is None  # profile not read yet


def test_deputy_with_a_profile_gets_contact_details_too(deputies):
    assert by_name(deputies, "Yerico Abramo Masso")["contact"] is None  # REGIONS carries no contact fields
    rich = dict(REGIONS)
    rich["9228260"] = dict(REGIONS["9228260"], email="yerico.abramo@diputados.gob.mx", phone="55 5036 0000 Ext. 59144.", office="Edificio H, Planta Baja.", education="Licenciatura, Administración de Empresas")
    page = (FIXTURES / "sil_diputados_lxvi_muestra_2026-11-06.html").read_bytes().decode("iso-8859-1")
    abramo = by_name(deputy_records(parse_roster(page), regions=rich, retrieved_at=RETRIEVED), "Yerico Abramo Masso")
    assert abramo["contact"]["email"] == "yerico.abramo@diputados.gob.mx"
    assert abramo["education"] == "Licenciatura, Administración de Empresas"
