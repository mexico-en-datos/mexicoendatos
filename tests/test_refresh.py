"""Downloading from the sources and writing the files the web page reads.

No network here: a stand-in session serves the saved real responses.
"""
import io
import json
from pathlib import Path

import py7zr
import pytest

from informate import cabinet, districts, geo, president, scjn, sil, wikipedia, judiciary
from informate.refresh import build_map, refresh_politicians

FIXTURES = Path(__file__).parent / "fixtures"
NOW = "2026-11-06T19:00:00Z"


class Response:
    def __init__(self, content=b"", payload=None):
        self.content = content
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


class Session:
    """Answers GET requests from a {url_prefix: Response} table and records them."""

    def __init__(self, routes):
        self.routes = routes
        self.requested = []
        self.asked = []  # (url, params) of every request

    def get(self, url, params=None, timeout=None):
        self.requested.append(url)
        self.asked.append((url, params))
        for prefix, response in self.routes.items():
            if url.startswith(prefix):
                return response(params) if callable(response) else response
        raise AssertionError(f"Unexpected request: {url}")


class ArchiveResponse(Response):
    headers = {"Last-Modified": "Fri, 31 Jan 2025 23:24:32 GMT"}


class DownSession:
    def get(self, url, params=None, timeout=None):
        raise ConnectionError("source is down")


def wikipedia_payload(wikitext, title=wikipedia.PAGE_TITLE, revid=175719290, timestamp="2026-10-08T04:24:51Z"):
    revision = {"revid": revid, "timestamp": timestamp, "slots": {"main": {"content": wikitext}}}
    return {"query": {"pages": [{"title": title, "revisions": [revision]}]}}


@pytest.fixture
def sources():
    roster = (FIXTURES / "sil_senadores_lxvi_2026-11-06.html").read_bytes()
    wikitext = (FIXTURES / "wikipedia_gobernantes_rev175719290.wikitext").read_text(encoding="utf-8")
    deputies = (FIXTURES / "sil_diputados_lxvi_muestra_2026-11-06.html").read_bytes()
    profile = (FIXTURES / "sil_perfil_diputado_distrito.html").read_bytes()
    scjn_text = (FIXTURES / "wiki_scjn_rev176164501.wikitext").read_text(encoding="utf-8")
    scjn_payload = wikipedia_payload(scjn_text, title=scjn.PAGE_TITLE, revid=176164501, timestamp="2026-11-05T19:12:01Z")
    governors_payload = wikipedia_payload(wikitext)
    office_payload = wikipedia_payload((FIXTURES / "wiki_presidente_de_mexico_rev176178323_inicio.wikitext").read_text(encoding="utf-8"),
                                       title=president.OFFICE_TITLE, revid=176178323, timestamp="2026-11-06T17:08:56Z")
    person_payload = wikipedia_payload((FIXTURES / "wiki_claudia_sheinbaum_rev175797791_inicio.wikitext").read_text(encoding="utf-8"),
                                       title="Claudia Sheinbaum", revid=175797791, timestamp="2026-10-12T23:28:02Z")
    cabinet_payload = wikipedia_payload((FIXTURES / "wiki_gabinete_rev175533934.wikitext").read_text(encoding="utf-8"),
                                        title=cabinet.PAGE_TITLE, revid=175533934, timestamp="2026-09-26T07:31:15Z")
    tepjf_payload = wikipedia_payload((FIXTURES / "wiki_tepjf_rev175170851.wikitext").read_text(encoding="utf-8"),
                                      title=judiciary.TEPJF_PAGE_TITLE, revid=175170851, timestamp="2026-09-03T05:54:46Z")
    tdj_payload = wikipedia_payload((FIXTURES / "wiki_tdj_rev175170915.wikitext").read_text(encoding="utf-8"),
                                    title=judiciary.TDJ_PAGE_TITLE, revid=175170915, timestamp="2026-09-03T06:00:38Z")
    pages = {scjn.PAGE_TITLE: scjn_payload, president.OFFICE_TITLE: office_payload, "Claudia Sheinbaum": person_payload, cabinet.PAGE_TITLE: cabinet_payload,
             judiciary.TEPJF_PAGE_TITLE: tepjf_payload, judiciary.TDJ_PAGE_TITLE: tdj_payload}
    return Session({
        sil.ROSTER_URL: Response(content=roster),
        sil.DEPUTIES_ROSTER_URL: Response(content=deputies),
        sil.PROFILE_URL: Response(content=profile),
        wikipedia.API_URL: lambda params: Response(payload=pages.get(params["titles"], governors_payload)),
    })


def test_sil_roster_is_decoded_as_latin1_so_accents_survive():
    session = Session({sil.ROSTER_URL: Response(content="Añorve Baños".encode("iso-8859-1"))})
    assert sil.fetch_roster(session) == "Añorve Baños"


def test_wikipedia_fetch_returns_the_text_and_which_revision_it_is(sources):
    wikitext, revision = wikipedia.fetch_page(sources)
    assert wikitext.startswith("[[Archivo:Gobernadores mexicanos")
    assert revision == {"id": 175719290, "timestamp": "2026-10-08T04:24:51Z"}


def test_wikipedia_fetch_fails_clearly_if_the_page_is_gone():
    session = Session({wikipedia.API_URL: Response(payload={"query": {"pages": [{"missing": True}]}})})
    with pytest.raises(ValueError):
        wikipedia.fetch_page(session)


def test_refresh_writes_governors_senators_and_deputies_with_the_time_of_retrieval(sources, tmp_path):
    out = tmp_path / "politicians.json"
    dataset = refresh_politicians(out, sources, now=lambda: NOW, cache_dir=tmp_path / "cache", pause_seconds=0)
    saved = json.loads(out.read_text(encoding="utf-8"))
    assert saved == dataset
    assert len(saved["people"]) == 32 + 128 + 6 + 9 + 6 + 5 + 1 + 22  # governors, senators, sample deputies, justices, electoral and discipline magistrates, president, cabinet
    assert sum(1 for p in saved["people"] if p["office"] == "magistrate_tepjf") == 6  # seven seats, one vacant
    assert saved["sources"]["wikipedia_tdj"]["url"].endswith("oldid=175170915")
    assert "electoral_term" in saved["rules"] and "discipline_term" in saved["rules"]
    assert saved["generated_at"] == NOW
    assert all(p["citation"]["retrieved_at"] == NOW for p in saved["people"])


def test_a_failed_refresh_leaves_the_previous_file_untouched(tmp_path):
    out = tmp_path / "politicians.json"
    out.write_text('{"people": ["previous"]}', encoding="utf-8")
    with pytest.raises(ConnectionError):
        refresh_politicians(out, DownSession(), now=lambda: NOW, cache_dir=tmp_path / "cache", pause_seconds=0)
    assert out.read_text(encoding="utf-8") == '{"people": ["previous"]}'
    assert [p.name for p in tmp_path.iterdir() if p.is_file()] == [out.name]


def inegi_session(sample):
    """INEGI's municipalities plus INE's district archive, as build_map asks for both."""
    return Session({f"{geo.SERVICE_URL}/geo/mgem/": Response(payload=sample), districts.ARCHIVE_URL: ArchiveResponse(content=ine_archive_bytes())})


def test_build_map_downloads_every_state_and_writes_map_plus_source_file(tmp_path, monkeypatch):
    sample = json.loads((FIXTURES / "inegi_mgem_01_sample.json").read_text(encoding="utf-8"))
    monkeypatch.setattr(geo, "STATES", {"01": "Aguascalientes"})
    session = inegi_session(sample)
    meta = build_map(tmp_path / "out", tmp_path / "cache", session, now=lambda: NOW, log=lambda _: None)

    assert session.requested == ["https://gaia.inegi.org.mx/wscatgeo/v2/geo/mgem/01", districts.ARCHIVE_URL]
    topology = json.loads((tmp_path / "out" / "municipios.topojson").read_text(encoding="utf-8"))
    assert len(topology["objects"]["municipios"]["geometries"]) == 3
    saved_meta = json.loads((tmp_path / "out" / "map_source.json").read_text(encoding="utf-8"))
    assert saved_meta == meta
    assert saved_meta["edition"] == "INEGI. Marco Geoestadístico, diciembre de 2025"
    assert saved_meta["retrieved_at"] == NOW
    assert saved_meta["municipality_count"] == 3


def test_build_map_reuses_downloads_and_keeps_their_original_date(tmp_path, monkeypatch):
    sample = json.loads((FIXTURES / "inegi_mgem_01_sample.json").read_text(encoding="utf-8"))
    monkeypatch.setattr(geo, "STATES", {"01": "Aguascalientes"})
    build_map(tmp_path / "out", tmp_path / "cache", inegi_session(sample), now=lambda: NOW, log=lambda _: None)

    later = "2026-12-01T08:00:00Z"
    meta = build_map(tmp_path / "out", tmp_path / "cache", DownSession(), now=lambda: later, log=lambda _: None)
    assert meta["retrieved_at"] == NOW  # the data is still what INEGI served on the first day


def test_build_map_with_refresh_downloads_again(tmp_path, monkeypatch):
    sample = json.loads((FIXTURES / "inegi_mgem_01_sample.json").read_text(encoding="utf-8"))
    monkeypatch.setattr(geo, "STATES", {"01": "Aguascalientes"})
    build_map(tmp_path / "out", tmp_path / "cache", inegi_session(sample), now=lambda: NOW, log=lambda _: None)

    later = "2026-12-01T08:00:00Z"
    session = inegi_session(sample)
    meta = build_map(tmp_path / "out", tmp_path / "cache", session, refresh=True, now=lambda: later, log=lambda _: None)
    assert len(session.requested) == 2  # the state, and INE's archive again
    assert meta["retrieved_at"] == later


def profile_requests(session):
    return [url for url in session.requested if url.startswith(sil.PROFILE_URL)]


def test_refresh_reads_each_legislators_profile_once_and_remembers_it(sources, tmp_path):
    out, cache = tmp_path / "politicians.json", tmp_path / "cache"
    first = refresh_politicians(out, sources, now=lambda: NOW, cache_dir=cache, pause_seconds=0, max_profiles=500)
    assert len(profile_requests(sources)) == 128 + 6  # every senator and deputy
    abramo = next(p for p in first["people"] if p["name"] == "Yerico Abramo Masso")
    assert abramo["district_number"] == 4
    assert abramo["contact"]["email"] == "yerico.abramo@diputados.gob.mx"

    sources.requested.clear()
    refresh_politicians(out, sources, now=lambda: NOW, cache_dir=cache, pause_seconds=0, max_profiles=500)
    assert profile_requests(sources) == []


def test_a_profile_that_cannot_be_read_costs_only_that_district_and_is_retried_next_time(sources, tmp_path):
    class FailingProfile(Response):
        def raise_for_status(self):
            raise ConnectionError("profile unavailable")

    working_profile = sources.routes[sil.PROFILE_URL]
    sources.routes[sil.PROFILE_URL] = FailingProfile()
    out, cache = tmp_path / "politicians.json", tmp_path / "cache"
    dataset = refresh_politicians(out, sources, now=lambda: NOW, cache_dir=cache, pause_seconds=0, max_profiles=500)
    assert len(dataset["people"]) == 32 + 128 + 6 + 9 + 6 + 5 + 1 + 22
    assert all(p["district_number"] is None for p in dataset["people"] if p["office"] == "deputy")
    assert any("fichas" in w and "134" in w for w in dataset["warnings"])
    assert len(profile_requests(sources)) == 3  # three refusals in a row: stop asking, don't hammer

    sources.routes[sil.PROFILE_URL] = working_profile
    sources.requested.clear()
    refresh_politicians(out, sources, now=lambda: NOW, cache_dir=cache, pause_seconds=0, max_profiles=500)
    assert len(profile_requests(sources)) == 134


def test_refresh_reads_only_a_small_batch_of_profiles_per_run(sources, tmp_path):
    out, cache = tmp_path / "politicians.json", tmp_path / "cache"
    first = refresh_politicians(out, sources, now=lambda: NOW, cache_dir=cache, pause_seconds=0, max_profiles=2)
    assert len(profile_requests(sources)) == 2
    assert any("fichas" in w and "132" in w for w in first["warnings"])  # 132 still to read

    sources.requested.clear()
    refresh_politicians(out, sources, now=lambda: NOW, cache_dir=cache, pause_seconds=0, max_profiles=2)
    assert len(profile_requests(sources)) == 2  # the next two


def test_a_refusal_page_served_as_a_profile_is_not_remembered_as_an_answer(sources, tmp_path):
    working_profile = sources.routes[sil.PROFILE_URL]
    sources.routes[sil.PROFILE_URL] = Response(content=b"<html>Error. This page can't be displayed.</html>")
    out, cache = tmp_path / "politicians.json", tmp_path / "cache"
    refresh_politicians(out, sources, now=lambda: NOW, cache_dir=cache, pause_seconds=0, max_profiles=500)

    sources.routes[sil.PROFILE_URL] = working_profile
    sources.requested.clear()
    dataset = refresh_politicians(out, sources, now=lambda: NOW, cache_dir=cache, pause_seconds=0, max_profiles=500)
    assert len(profile_requests(sources)) == 134
    assert next(p for p in dataset["people"] if p["name"] == "Yerico Abramo Masso")["district_number"] == 4


# ----- Municipal presidents: one Wikipedia page per state, re-read at most once a day -----

from informate import mayors as mayors_module  # noqa: E402

MAYORS_TITLE = "Anexo:Presidentes municipales de Aguascalientes (2024-2027)"


@pytest.fixture
def with_mayors(sources, tmp_path, monkeypatch):
    """The usual sources plus Aguascalientes' page of municipal presidents and a map of that state."""
    monkeypatch.setattr(mayors_module, "PAGES", {"01": MAYORS_TITLE})
    other_pages = sources.routes[wikipedia.API_URL]
    mayors_text = (FIXTURES / "wiki_pm_aguascalientes_rev172212877.wikitext").read_text(encoding="utf-8")
    mayors_payload = {"query": {"pages": [{"title": MAYORS_TITLE, "revisions": [
        {"revid": 172212877, "timestamp": "2026-02-24T03:18:36Z", "slots": {"main": {"content": mayors_text}}}]}]}}
    sources.routes[wikipedia.API_URL] = lambda params: (
        Response(payload=mayors_payload) if params["titles"] == MAYORS_TITLE else other_pages(params))

    names = ["Aguascalientes", "Asientos", "Calvillo", "Cosío", "Jesús María", "Pabellón de Arteaga",
             "Rincón de Romos", "San José de Gracia", "Tepezalá", "El Llano", "San Francisco de los Romo"]
    geometries = [{"properties": {"cvegeo": f"01{i + 1:03d}", "cve_ent": "01", "nomgeo": name}} for i, name in enumerate(names)]
    catalog = tmp_path / "municipios.topojson"
    catalog.write_text(json.dumps({"objects": {"municipios": {"geometries": geometries}}}), encoding="utf-8")
    return sources, catalog


def mayor_requests(session):
    return [params for url, params in session.asked if url == wikipedia.API_URL and params["titles"] == MAYORS_TITLE]


def test_refresh_adds_municipal_presidents_when_given_the_map(with_mayors, tmp_path):
    sources, catalog = with_mayors
    dataset = refresh_politicians(tmp_path / "p.json", sources, now=lambda: NOW, cache_dir=tmp_path / "cache",
                                  pause_seconds=0, catalog_path=catalog)
    presidents = [p for p in dataset["people"] if p["office"] == "mayor"]
    assert len(presidents) == 11
    assert presidents[0]["municipality_code"] == "01001"
    assert len(mayor_requests(sources)) == 1


def test_municipal_presidents_are_not_fetched_again_within_a_day(with_mayors, tmp_path):
    sources, catalog = with_mayors
    args = dict(cache_dir=tmp_path / "cache", pause_seconds=0, catalog_path=catalog)
    refresh_politicians(tmp_path / "p.json", sources, now=lambda: NOW, **args)
    sources.asked.clear()
    later = refresh_politicians(tmp_path / "p.json", sources, now=lambda: "2026-11-07T18:00:00Z", **args)
    assert mayor_requests(sources) == []
    president = next(p for p in later["people"] if p["office"] == "mayor")
    assert president["citation"]["retrieved_at"] == NOW  # when the page was really read
    assert later["sources"]["wikipedia_mayors"]["retrieved_at"] == NOW


def test_municipal_presidents_are_fetched_again_after_a_day(with_mayors, tmp_path):
    sources, catalog = with_mayors
    args = dict(cache_dir=tmp_path / "cache", pause_seconds=0, catalog_path=catalog)
    refresh_politicians(tmp_path / "p.json", sources, now=lambda: NOW, **args)
    sources.asked.clear()
    refresh_politicians(tmp_path / "p.json", sources, now=lambda: "2026-11-07T19:30:00Z", **args)
    assert len(mayor_requests(sources)) == 1


def test_without_the_map_there_are_no_municipal_presidents_and_no_extra_requests(sources, tmp_path):
    dataset = refresh_politicians(tmp_path / "p.json", sources, now=lambda: NOW, cache_dir=tmp_path / "cache", pause_seconds=0)
    assert not [p for p in dataset["people"] if p["office"] == "mayor"]


# ----- The district map comes from INE's 7z archive -----

def ine_archive_bytes():
    """A 7z archive laid out like INE's, holding the three-district fixture as the layer."""
    if not hasattr(ine_archive_bytes, "cached"):
        buffer = io.BytesIO()
        with py7zr.SevenZipFile(buffer, "w") as z:
            for suffix in (".shp", ".shx", ".dbf", ".prj"):
                z.write(FIXTURES / f"ine_distritos_aguascalientes{suffix}", f"{districts.LAYER}{suffix}")
        ine_archive_bytes.cached = buffer.getvalue()
    return ine_archive_bytes.cached


def test_build_map_also_builds_the_districts_from_ines_archive(tmp_path, monkeypatch):
    sample = json.loads((FIXTURES / "inegi_mgem_01_sample.json").read_text(encoding="utf-8"))
    monkeypatch.setattr(geo, "STATES", {"01": "Aguascalientes"})
    session = inegi_session(sample)
    meta = build_map(tmp_path / "out", tmp_path / "cache", session, now=lambda: NOW, log=lambda _: None)

    topology = json.loads((tmp_path / "out" / "distritos.topojson").read_text(encoding="utf-8"))
    assert len(topology["objects"]["distritos"]["geometries"]) == 3
    assert meta["districts"]["district_count"] == 3
    assert meta["districts"]["published_at"] == "2025-01-31"
    assert meta["districts"]["retrieved_at"] == NOW
    assert session.requested.count(districts.ARCHIVE_URL) == 1

    session.requested.clear()
    build_map(tmp_path / "out", tmp_path / "cache", session, now=lambda: "2026-12-01T08:00:00Z", log=lambda _: None)
    assert districts.ARCHIVE_URL not in session.requested  # the archive is kept, like the INEGI downloads
