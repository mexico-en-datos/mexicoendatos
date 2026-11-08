"""Download from the sources and write the files the web page reads."""
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

import py7zr

from . import cabinet, districts, geo, judiciary, mayors, president, scjn, sil, wikipedia
from .dataset import (
    build_dataset,
    cabinet_records,
    deputy_records,
    governor_records,
    justice_records,
    magistrate_records,
    mayor_records,
    president_records,
    senator_records,
)

USER_AGENT = "Informate/0.1 (civic data project; python-requests)"


def new_session() -> requests.Session:
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    return session


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_json(path: Path, data, pretty: bool = True) -> None:
    """Write via a temporary file so readers never see a half-written file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = (
        json.dumps(data, ensure_ascii=False, indent=2)
        if pretty
        else json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    )
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


REFUSALS_BEFORE_GIVING_UP = 3


def _legislator_profiles(session, legislators: list[dict], cache_dir: Path | None, pause_seconds: float, max_profiles: int, log) -> dict:
    """What each legislator's SIL profile says (district, contact details), by SIL id.

    SIL is an old server and refuses clients that ask too fast, so this reads only a
    batch per run, pauses between requests, and stops after a few failures in a row.
    Profiles already read are remembered in `cache_dir`; the rest are picked up on
    later runs. Entries from before contact details were read are read again.
    """
    cache_file = Path(cache_dir) / "sil_fichas.json" if cache_dir else None
    profiles = json.loads(cache_file.read_text(encoding="utf-8")) if cache_file and cache_file.exists() else {}
    missing = [row["sil_id"] for row in legislators if "email" not in profiles.get(row["sil_id"], {})]
    batch = missing[:max_profiles]
    if batch:
        log(f"Leyendo {len(batch)} de {len(missing)} fichas de legisladores pendientes en el SIL…")
    failures_in_a_row = 0
    for position, sil_id in enumerate(batch):
        if position:
            time.sleep(pause_seconds)
        try:
            profiles[sil_id] = sil.parse_profile(sil.fetch_profile(session, sil_id))
            failures_in_a_row = 0
        except Exception:  # unreadable or refused: skip it now, try again on a later run
            failures_in_a_row += 1
            if failures_in_a_row >= REFUSALS_BEFORE_GIVING_UP:
                log("El SIL no está entregando fichas; se reintenta en la próxima actualización.")
                break
    if cache_file and batch:
        write_json(cache_file, profiles, pretty=False)
    return profiles


def load_catalog(topojson_path: Path) -> dict[str, dict[str, str]]:
    """INEGI's municipalities from the map file: {state code: {municipality code: name}}."""
    topology = json.loads(Path(topojson_path).read_text(encoding="utf-8"))
    catalog: dict[str, dict[str, str]] = {}
    for geometry in topology["objects"][geo.OBJECT_NAME]["geometries"]:
        props = geometry["properties"]
        catalog.setdefault(props["cve_ent"], {})[props["cvegeo"]] = props["nomgeo"]
    return catalog


def _hours_between(earlier: str, later: str) -> float:
    def parse(stamp: str) -> datetime:
        return datetime.fromisoformat(stamp.replace("Z", "+00:00"))

    return (parse(later) - parse(earlier)).total_seconds() / 3600


def _mayor_pages(session, cache_dir: Path | None, now_stamp: str, max_age_hours: float, pause_seconds: float, log) -> tuple[dict, str]:
    """Each state's Wikipedia page of municipal presidents, and when they were read.

    The 32 pages are re-read at most once every `max_age_hours`, so pressing the page's
    refresh button repeatedly does not keep asking Wikipedia for them.
    """
    cache_file = Path(cache_dir) / "wikipedia_presidencias.json" if cache_dir else None  # not kept in git: large, re-read daily
    if cache_file and cache_file.exists():
        cached = json.loads(cache_file.read_text(encoding="utf-8"))
        same_pages = {code: page["title"] for code, page in cached["pages"].items()} == mayors.PAGES
        if same_pages and _hours_between(cached["fetched_at"], now_stamp) < max_age_hours:
            return cached["pages"], cached["fetched_at"]
    log(f"Leyendo {len(mayors.PAGES)} anexos de presidentes municipales en Wikipedia…")
    fetched = mayors.fetch_pages(session, list(mayors.PAGES.values()), pause_seconds=pause_seconds)
    pages = {code: {"title": title, **fetched[title]} for code, title in mayors.PAGES.items()}
    if cache_file:
        write_json(cache_file, {"fetched_at": now_stamp, "pages": pages}, pretty=False)
    return pages, now_stamp


def refresh_politicians(
    out_path: Path,
    session,
    now=utc_now,
    cache_dir: Path | None = None,
    pause_seconds: float = 2.0,
    max_profiles: int = 100,
    log=lambda message: None,
    catalog_path: Path | None = None,
    mayors_max_age_hours: float = 24,
    mayors_pause_seconds: float = 6.0,
) -> dict:
    """Fetch senators and deputies (SIL), governors and municipal presidents (Wikipedia),
    and write the dataset. Municipal presidents need `catalog_path`, the map file, to be
    placed in INEGI's municipalities; without it they are left out.

    If a roster or the governors' list cannot be fetched, the exception propagates and
    the existing file stays as it was.
    """
    retrieved_at = now()
    senator_rows = sil.parse_roster(sil.fetch_roster(session))
    deputy_rows = sil.parse_roster(sil.fetch_roster(session, sil.DEPUTIES_ROSTER_URL))
    wikitext, revision = wikipedia.fetch_page(session)
    governors = governor_records(wikipedia.parse_governors(wikitext), revision, retrieved_at)
    court_text, court_revision = wikipedia.fetch_page(session, scjn.PAGE_TITLE)
    justices = justice_records(scjn.parse_justices(court_text), court_revision, retrieved_at)
    electoral_text, electoral_revision = wikipedia.fetch_page(session, judiciary.TEPJF_PAGE_TITLE)
    electoral_seats = judiciary.parse_electoral_tribunal(electoral_text)
    discipline_text, discipline_revision = wikipedia.fetch_page(session, judiciary.TDJ_PAGE_TITLE)
    magistrates = magistrate_records(electoral_seats, "tepjf", electoral_revision, retrieved_at) + magistrate_records(
        judiciary.parse_discipline_tribunal(discipline_text), "tdj", discipline_revision, retrieved_at
    )
    judicial_notes = [f"Tribunal Electoral: {n} de las {judiciary.TEPJF_SEATS} magistraturas de la Sala Superior están vacantes según la fuente." for n in [sum(1 for seat in electoral_seats if seat["vacant"])] if n]
    office_text, office_revision = wikipedia.fetch_page(session, president.OFFICE_TITLE)
    office = president.parse_office(office_text)
    person_text, person_revision = wikipedia.fetch_page(session, office["article"])
    head_of_state = president_records(
        office, president.parse_party(person_text), {"office": office_revision, "person": person_revision}, retrieved_at
    )
    cabinet_text, cabinet_revision = wikipedia.fetch_page(session, cabinet.PAGE_TITLE)
    secretaries, cabinet_notes = cabinet_records(cabinet.parse_cabinet(cabinet_text), cabinet_revision, retrieved_at)

    profiles = _legislator_profiles(session, senator_rows + deputy_rows, cache_dir, pause_seconds, max_profiles, log)
    senators = senator_records(senator_rows, retrieved_at, profiles=profiles)
    deputies = deputy_records(deputy_rows, profiles, retrieved_at)
    unread = sum(1 for row in senator_rows + deputy_rows if "email" not in profiles.get(row["sil_id"], {}))
    notes = cabinet_notes + judicial_notes + (
        [f"Faltan por leer las fichas de {unread} legisladores en el SIL: aparecen sin distrito o sin datos de contacto hasta una próxima actualización."]
        if unread
        else []
    )
    presidents, pages, pages_read_at = [], None, None
    if catalog_path:
        pages, pages_read_at = _mayor_pages(session, cache_dir, retrieved_at, mayors_max_age_hours, mayors_pause_seconds, log)
        presidents, mayor_notes = mayor_records(pages, load_catalog(catalog_path), pages_read_at)
        notes += mayor_notes
    dataset = build_dataset(
        senators, governors, revision, retrieved_at, deputies=deputies, extra_warnings=notes,
        mayors=presidents, mayor_pages=pages, mayors_retrieved_at=pages_read_at,
        justices=justices, scjn_revision=court_revision,
        president=head_of_state, president_revisions={"office": office_revision, "person": person_revision},
        cabinet=secretaries, cabinet_revision=cabinet_revision,
        magistrates=magistrates, judiciary_revisions={"tepjf": electoral_revision, "tdj": discipline_revision},
    )
    write_json(Path(out_path), dataset)
    return dataset


def _load_state(session, cve_ent: str, cache_dir: Path, refresh: bool, now) -> dict:
    """One state's INEGI response with the date it was downloaded, from cache if present."""
    cached = cache_dir / f"mgem_{cve_ent}.json"
    if cached.exists() and not refresh:
        return json.loads(cached.read_text(encoding="utf-8"))
    response = session.get(geo.municipalities_url(cve_ent), timeout=180)
    response.raise_for_status()
    entry = {"retrieved_at": now(), "response": response.json()}
    write_json(cached, entry, pretty=False)
    return entry


def build_map(
    out_dir: Path,
    cache_dir: Path,
    session,
    refresh: bool = False,
    tolerance: float = geo.DEFAULT_TOLERANCE,
    now=utc_now,
    log=print,
    pause_seconds: float = 0.5,
) -> dict:
    """Download every state's municipalities from INEGI and write
    `municipios.topojson` plus `map_source.json` (where the map came from)."""
    out_dir, cache_dir = Path(out_dir), Path(cache_dir)
    entries = {}
    for position, (cve_ent, name) in enumerate(geo.STATES.items()):
        was_cached = (cache_dir / f"mgem_{cve_ent}.json").exists() and not refresh
        if position and not was_cached:
            time.sleep(pause_seconds)  # be gentle with INEGI's server
        entries[cve_ent] = _load_state(session, cve_ent, cache_dir, refresh, now)
        count = len(entries[cve_ent]["response"]["features"])
        log(f"{cve_ent} {name}: {count} municipios ({'copia local' if was_cached else 'descargado'})")

    responses = {cve_ent: entry["response"] for cve_ent, entry in entries.items()}
    oldest_download = min(entry["retrieved_at"] for entry in entries.values())
    meta = geo.source_metadata(responses, retrieved_at=oldest_download, tolerance=tolerance)

    log("Simplificando límites…")
    topology = geo.build_topology(geo.slim_features(list(responses.values())), tolerance)
    write_json(out_dir / "municipios.topojson", topology, pretty=False)

    meta["districts"] = _build_districts(session, out_dir, cache_dir, refresh, tolerance, now, log)
    write_json(out_dir / "map_source.json", meta)
    return meta


def _build_districts(session, out_dir: Path, cache_dir: Path, refresh: bool, tolerance: float, now, log) -> dict:
    """INE's 300 federal districts, from its archive (kept in the cache once downloaded)."""
    archive = cache_dir / "ine_mgs_seccional.7z"
    stamp = cache_dir / "ine_mgs_seccional.json"
    if not archive.exists() or refresh:
        log("Descargando los distritos electorales del INE (unos 86 MB)…")
        response = session.get(districts.ARCHIVE_URL, timeout=900)
        response.raise_for_status()
        archive.parent.mkdir(parents=True, exist_ok=True)
        archive.write_bytes(response.content)
        write_json(stamp, {"retrieved_at": now(), "last_modified": response.headers.get("Last-Modified")})
    record = json.loads(stamp.read_text(encoding="utf-8"))

    folder = cache_dir / "ine_mgs_seccional"
    with py7zr.SevenZipFile(archive, "r") as z:
        layer_files = [name for name in z.getnames() if Path(name).stem == districts.LAYER]
        z.extract(path=folder, targets=layer_files)
    shp = next(folder.rglob(f"{districts.LAYER}.shp"))
    features = districts.read_districts(shp)
    log(f"Distritos electorales federales: {len(features)}. Simplificando límites…")
    topology = geo.build_topology(features, tolerance, object_name=districts.OBJECT_NAME)
    write_json(out_dir / "distritos.topojson", topology, pretty=False)
    return districts.source_metadata(len(features), record["last_modified"], record["retrieved_at"])
