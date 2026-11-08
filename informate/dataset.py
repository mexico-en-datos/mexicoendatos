"""The published dataset: one record per office holder, each with its citation.

Every citation carries a link and two dates: `retrieved_at` (when we read the
source) and `published_at` (the source's own date, when it states one).
"""
import re
from collections import Counter

from . import cabinet as cabinet_source
from . import judiciary
from . import circunscripciones
from . import mayors as mayor_pages_source
from . import president as president_source
from . import scjn, sil, wikipedia
from .parties import PARTIES, party_code
from .states import STATES, state_code
from .president import PRESIDENT_TERM_RULE, presidential_term
from .scjn import JUSTICES_TERM_RULE
from .terms import DEPUTIES_TERM_RULE, SENATE_TERM_RULE, deputies_term, senate_term

SOURCES = {
    "sil": {
        "name": "Sistema de Información Legislativa (SIL), Secretaría de Gobernación",
        "official": True,
    },
    "wikipedia": {
        "name": f"Wikipedia en español, «{wikipedia.PAGE_TITLE}»",
        "official": False,
    },
    "wikipedia_mayors": {
        "name": "Wikipedia en español, anexos de presidentes municipales de cada entidad",
        "official": False,
    },
    "wikipedia_scjn": {
        "name": f"Wikipedia en español, «{scjn.PAGE_TITLE}»",
        "official": False,
    },
    "wikipedia_tepjf": {
        "name": f"Wikipedia en español, «{judiciary.TEPJF_PAGE_TITLE}»",
        "official": False,
    },
    "wikipedia_tdj": {
        "name": "Wikipedia en español, «Tribunal de Disciplina Judicial»",
        "official": False,
    },
    "wikipedia_cabinet": {
        "name": f"Wikipedia en español, «{cabinet_source.PAGE_TITLE}»",
        "official": False,
    },
    "wikipedia_president": {
        "name": f"Wikipedia en español, «{president_source.OFFICE_TITLE}» y el artículo de la persona titular",
        "official": False,
    },
}

SENATORS_PER_STATE = 3
NATIONAL_LIST_SEATS = 32
DEPUTIES = 500


def _citation(source: str, url: str, retrieved_at: str, published_at: str | None, source_name: str | None = None) -> dict:
    return {
        "source": source,
        "source_name": source_name or SOURCES[source]["name"],
        "url": url,
        "published_at": published_at,
        "retrieved_at": retrieved_at,
    }


def _contact(profile: dict | None) -> dict | None:
    """The office's contact details from a SIL profile, or None when the profile hasn't been read."""
    if not profile or "email" not in profile:
        return None
    return {"email": profile.get("email"), "phone": profile.get("phone"), "office": profile.get("office")}


def senator_records(parsed: list[dict], retrieved_at: str, profiles: dict[str, dict] | None = None) -> list[dict]:
    """Senators. `profiles` maps a SIL id to what that person's profile page says (contact details)."""
    _, senate_term_end = senate_term(sil.LEGISLATURE)
    profiles = profiles or {}
    records = []
    for row in parsed:
        profile = profiles.get(row["sil_id"])
        code = state_code(row["state_raw"]) if row["state_raw"] else None
        party = party_code(row["party_raw"])
        how_elected = row["election_type"].capitalize()
        place = STATES[code] if code else "Lista nacional"
        records.append(
            {
                "office": "senator",
                "title": row["role"].split()[0],  # "Senador" / "Senadora"
                "name": row["name"],
                "party": party,
                "party_name": PARTIES[party]["name"],
                "state_code": code,
                "state": STATES[code] if code else None,
                "district": f"{place} ({how_elected.lower()})",
                "election_type": how_elected,
                "seat_status": row["seat_status"],
                "term_start": row["sworn_in"],  # the day this person was sworn in
                "term_end": senate_term_end,
                "term_end_basis": "rule",  # SIL does not list it; see SENATE_TERM_RULE
                "substitute": row["substitute"] or None,
                "contact": _contact(profile),
                "education": profile.get("education") if profile else None,
                "citation": _citation("sil", row["profile_url"], retrieved_at, published_at=None),
            }
        )
    return records


def _deputy_district(row: dict, state: str | None, region: dict) -> str:
    """Where a deputy was elected, saying only what the source says."""
    if row["election_type"].startswith("Mayor"):
        if region.get("district") is None:
            return f"{state} (mayoría relativa)"
        seat = f" ({region['district_seat']})" if region.get("district_seat") else ""
        return f"{state}, distrito {region['district']}{seat}"
    if region.get("circunscription"):
        return f"{region['circunscription']} circunscripción (representación proporcional)"
    return "Lista plurinominal (representación proporcional)"


def deputy_records(parsed: list[dict], regions: dict[str, dict], retrieved_at: str) -> list[dict]:
    """Federal deputies. `regions` maps a SIL id to what that person's profile says
    about their district; deputies missing from it are listed without a district number.

    Only district (majority) deputies belong to a state. List deputies are elected
    from five regional lists, so they get no state even though SIL names one for them.
    """
    _, term_end = deputies_term(sil.LEGISLATURE)
    records = []
    for row in parsed:
        by_district = row["election_type"].startswith("Mayor")
        code = state_code(row["state_raw"]) if by_district and row["state_raw"] else None
        state = STATES[code] if code else None
        party = party_code(row["party_raw"])
        region = regions.get(row["sil_id"], {})
        records.append(
            {
                "office": "deputy",
                "title": row["role"].split()[0],  # "Diputado" / "Diputada"
                "name": row["name"],
                "party": party,
                "party_name": PARTIES[party]["name"],
                "state_code": code,
                "state": state,
                "district": _deputy_district(row, state, region),
                "district_number": region.get("district") if by_district else None,
                "region_number": None if by_district else circunscripciones.number_of(region.get("circunscription") or ""),
                "election_type": row["election_type"].capitalize(),
                "seat_status": row["seat_status"],
                "term_start": row["sworn_in"],
                "term_end": term_end,
                "term_end_basis": "rule",  # see DEPUTIES_TERM_RULE
                "substitute": row["substitute"] or None,
                "contact": _contact(region),
                "education": region.get("education"),
                "citation": _citation("sil", row["profile_url"], retrieved_at, published_at=None),
            }
        )
    return records


def governor_records(parsed: list[dict], revision: dict, retrieved_at: str) -> list[dict]:
    permalink = wikipedia.page_permalink(revision["id"])
    records = []
    for row in parsed:
        code = state_code(row["state_raw"])
        party = party_code(row["party_raw"])
        records.append(
            {
                "office": "governor",
                "title": row["title"],
                "name": row["name"],
                "party": party,
                "party_name": PARTIES[party]["name"],
                "state_code": code,
                "state": STATES[code],
                "district": STATES[code],
                "election_type": None,
                "seat_status": None,
                "term_start": row["term_start"],
                "term_end": row["term_end"],
                "term_end_basis": "source",
                "citation": _citation("wikipedia", permalink, retrieved_at, revision["timestamp"]),
            }
        )
    return records


def mayor_records(pages: dict[str, dict], catalog: dict[str, dict[str, str]], retrieved_at: str) -> tuple[list[dict], list[str]]:
    """Municipal presidents, and plain-language notes about what the source lacks.

    `pages` maps a state code to that state's Wikipedia page ({"title", "wikitext",
    "revision"}); `catalog` maps a state code to its municipalities ({INEGI code: name}).
    A president whose municipality cannot be matched to INEGI's is kept, without a code.
    """
    records, vacant, unplaced = [], [], []
    for code, page in sorted(pages.items()):
        official = catalog.get(code, {})
        term_start, term_end = mayor_pages_source.parse_term(page["wikitext"])
        citation = _citation(
            "wikipedia",
            mayor_pages_source.page_permalink(page["title"], page["revision"]["id"]),
            retrieved_at,
            page["revision"]["timestamp"],
            source_name=f"Wikipedia en español, «{page['title']}»",
        )
        seen = set()
        for row in mayor_pages_source.parse_mayors(page["wikitext"]):
            if row["name"] is None:
                vacant.append(f"{row['municipality']} ({STATES[code]})")
                continue
            cvegeo = mayor_pages_source.match_municipality(row["municipality"], row["article"], official, state_code=code)
            if cvegeo in seen:
                continue  # the source lists this municipality twice
            if cvegeo:
                seen.add(cvegeo)
            else:
                unplaced.append(f"{row['municipality']} ({STATES[code]})")
            label = row["party_raw"] or ""
            try:
                party = party_code(label) if label else "SP"
            except KeyError:
                party = "OTRO"
            if party == "OTRO":
                party_name = re.sub(r"\s*\([^)]*\)", "", label).strip()
            else:
                party_name = PARTIES[party]["name"] if label else "Sin partido indicado en la fuente"
            municipality = official.get(cvegeo, row["municipality"])
            records.append(
                {
                    "office": "mayor",
                    "title": "Alcaldía" if code == "09" else "Presidencia municipal",
                    "name": row["name"],
                    "party": party,
                    "party_name": party_name,
                    "state_code": code,
                    "state": STATES[code],
                    "municipality_code": cvegeo,
                    "municipality": municipality,
                    "district": municipality,
                    "election_type": None,
                    "seat_status": None,
                    "term_start": term_start,
                    "term_end": term_end,
                    "term_end_basis": "source",
                    "citation": citation,
                }
            )

    notes = []
    total = sum(len(municipalities) for municipalities in catalog.values())
    covered = {record["municipality_code"] for record in records if record["municipality_code"]}
    if total - len(covered):
        in_oaxaca = sum(1 for cvegeo in catalog.get("20", {}) if cvegeo not in covered)
        notes.append(
            f"Presidencias municipales: la fuente da titular para {len(covered)} de {total} municipios; "
            f"faltan {total - len(covered)}" + (f", {in_oaxaca} de ellos en Oaxaca" if in_oaxaca else "") + "."
        )
    if vacant:
        notes.append(
            f"{len(vacant)} municipios aparecen sin titular en la fuente (vacante o concejo municipal): {', '.join(vacant)}."
        )
    if unplaced:
        notes.append(
            f"{len(unplaced)} presidencias municipales no se pudieron ubicar en el mapa: {', '.join(unplaced[:12])}"
            + ("…" if len(unplaced) > 12 else ".")
        )
    return records, notes


def justice_records(parsed: list[dict], revision: dict, retrieved_at: str) -> list[dict]:
    """The Supreme Court's justices, with the end of each term from the 2024 rule."""
    permalink = wikipedia.page_permalink(revision["id"], title=scjn.PAGE_TITLE)
    records = []
    for rank, row in enumerate(parsed):
        records.append(
            {
                "office": "justice",
                "title": row["role"],
                "name": row["name"],
                "party": "SP",
                "party_name": "Cargo sin partido",
                "state_code": None,
                "state": None,
                "district": scjn.PAGE_TITLE,
                "election_type": None,
                "seat_status": None,
                "term_start": row["term_start"],
                "term_end": scjn.term_end_by_rank(rank),
                "term_end_basis": "rule",  # see JUSTICES_TERM_RULE
                "citation": _citation("wikipedia_scjn", permalink, retrieved_at, revision["timestamp"]),
            }
        )
    return records


BODIES = {
    "tepjf": {"office": "magistrate_tepjf", "body": "Tribunal Electoral del Poder Judicial de la Federación", "short": "Tribunal Electoral", "source": "wikipedia_tepjf", "title": judiciary.TEPJF_PAGE_TITLE},
    "tdj": {"office": "magistrate_tdj", "body": "Tribunal de Disciplina Judicial", "short": "Tribunal de Disciplina Judicial", "source": "wikipedia_tdj", "title": judiciary.TDJ_PAGE_TITLE},
}


def magistrate_records(parsed: list[dict], body: str, revision: dict, retrieved_at: str) -> list[dict]:
    """The magistrates of the Tribunal Electoral's Sala Superior (`body` "tepjf") or of the
    Tribunal de Disciplina Judicial ("tdj"). Vacant seats are not people and are left out."""
    spec = BODIES[body]
    permalink = wikipedia.page_permalink(revision["id"], title=spec["title"])
    records = []
    for row in parsed:
        if row.get("vacant"):
            continue
        role = row.get("role") or "Magistratura"
        if body == "tepjf":
            term_start = judiciary.SWORN_IN_2025 if row["elected"] and row["elected"] >= "2025" else row["elected"]
            term_end, note = judiciary.electoral_term_end(row["elected"]), None
        else:
            term_start, term_end, note = row["term_start"], None, judiciary.TDJ_TERM_NOTE
        records.append(
            {
                "office": spec["office"],
                "title": f"{role} del {spec['short']}",
                "name": row["name"],
                "party": "SP",
                "party_name": "Cargo sin partido",
                "state_code": None,
                "state": None,
                "district": spec["body"],
                "election_type": None,
                "seat_status": None,
                "term_start": term_start,
                "term_end": term_end,
                "term_end_basis": "rule",  # see TEPJF_TERM_RULE and TDJ_TERM_RULE
                "term_end_note": note,
                "citation": _citation(spec["source"], permalink, retrieved_at, revision["timestamp"]),
            }
        )
    return records


def president_records(office: dict, party_label: str, revisions: dict, retrieved_at: str) -> list[dict]:
    """The President, as a one-item list, cited to the office's article (and the person's for the party)."""
    party = party_code(party_label)
    term_start, term_end = presidential_term(office["term_start"])
    citation = _citation(
        "wikipedia_president",
        wikipedia.page_permalink(revisions["office"]["id"], title=president_source.OFFICE_TITLE),
        retrieved_at,
        revisions["office"]["timestamp"],
    )
    citation["party_url"] = wikipedia.page_permalink(revisions["person"]["id"], title=office["article"])
    citation["party_published_at"] = revisions["person"]["timestamp"]
    return [
        {
            "office": "president",
            "title": "Presidencia de la República",
            "name": office["name"],
            "party": party,
            "party_name": PARTIES[party]["name"],
            "state_code": None,
            "state": None,
            "district": "Presidencia de la República",
            "election_type": None,
            "seat_status": None,
            "term_start": term_start,
            "term_end": term_end,
            "term_end_basis": "rule",
            "citation": citation,
        }
    ]


def cabinet_records(parsed: list[dict], revision: dict, retrieved_at: str) -> tuple[list[dict], list[str]]:
    """The heads of the federal dependencies, plus notes on the posts the source shows vacant."""
    citation = _citation(
        "wikipedia_cabinet", wikipedia.page_permalink(revision["id"], title=cabinet_source.PAGE_TITLE), retrieved_at, revision["timestamp"]
    )
    records, vacant = [], []
    for row in parsed:
        if row["name"] is None:
            vacant.append(row["dependency"])
            continue
        records.append(
            {
                "office": "secretary",
                "title": row["dependency"],
                "name": row["name"],
                "party": "SP",
                "party_name": "Partido no indicado en la fuente",
                "state_code": None,
                "state": None,
                "district": row["dependency"],
                "election_type": None,
                "seat_status": None,
                "term_start": None,
                "term_end": None,
                "term_end_basis": None,
                "citation": citation,
            }
        )
    notes = [f"Gabinete: la fuente muestra vacante {', '.join(vacant)}."] if vacant else []
    return records, notes


def check_dataset(people: list[dict]) -> list[str]:
    """Plain-language warnings (in Spanish, shown on the page) where the sources
    list fewer or more office holders than the law provides for."""
    warnings = []
    senators = [p for p in people if p["office"] == "senator"]
    governors = Counter(p["state_code"] for p in people if p["office"] == "governor")
    by_state = Counter(p["state_code"] for p in senators)

    for code, name in STATES.items():
        if by_state[code] != SENATORS_PER_STATE:
            warnings.append(
                f"{name}: la fuente lista {by_state[code]} senadores por la entidad "
                f"(se esperaban {SENATORS_PER_STATE})."
            )
        if governors[code] != 1:
            warnings.append(
                f"{name}: la fuente lista {governors[code]} titulares del ejecutivo estatal "
                "(se esperaba 1)."
            )
    if by_state[None] != NATIONAL_LIST_SEATS:
        warnings.append(
            f"Lista nacional: la fuente lista {by_state[None]} senadores "
            f"(se esperaban {NATIONAL_LIST_SEATS})."
        )
    deputies = sum(1 for p in people if p["office"] == "deputy")
    if deputies and deputies != DEPUTIES:
        warnings.append(
            f"Cámara de Diputados: la fuente lista {deputies} diputaciones (se esperaban {DEPUTIES})."
        )
    justices = sum(1 for p in people if p["office"] == "justice")
    if justices and justices != scjn.JUSTICES:
        warnings.append(f"Suprema Corte: la fuente lista {justices} ministras y ministros (se esperaban {scjn.JUSTICES}).")
    electoral = sum(1 for p in people if p["office"] == "magistrate_tepjf")
    if electoral and electoral > judiciary.TEPJF_SEATS:
        warnings.append(f"Tribunal Electoral: la fuente lista {electoral} magistraturas en la Sala Superior (son {judiciary.TEPJF_SEATS} escaños).")
    discipline = sum(1 for p in people if p["office"] == "magistrate_tdj")
    if discipline and discipline != judiciary.TDJ_SEATS:
        warnings.append(f"Tribunal de Disciplina Judicial: la fuente lista {discipline} magistraturas (se esperaban {judiciary.TDJ_SEATS}).")
    presidents = sum(1 for p in people if p["office"] == "president")
    if presidents > 1:
        warnings.append(f"Presidencia de la República: la fuente lista {presidents} titulares (se esperaba 1).")
    return warnings


def build_dataset(
    senators: list[dict],
    governors: list[dict],
    revision: dict,
    retrieved_at: str,
    deputies: list[dict] = (),
    extra_warnings: list[str] = (),
    mayors: list[dict] = (),
    mayor_pages: dict[str, dict] | None = None,
    mayors_retrieved_at: str | None = None,
    justices: list[dict] = (),
    scjn_revision: dict | None = None,
    president: list[dict] = (),
    president_revisions: dict | None = None,
    cabinet: list[dict] = (),
    cabinet_revision: dict | None = None,
    magistrates: list[dict] = (),
    judiciary_revisions: dict | None = None,
    judiciary_vacancies: dict | None = None,
) -> dict:
    people = governors + senators + list(deputies) + list(mayors) + list(justices) + list(magistrates) + list(president) + list(cabinet)
    mayor_source = {}
    for body, revision in (judiciary_revisions or {}).items():
        spec = BODIES[body]
        mayor_source[spec["source"]] = SOURCES[spec["source"]] | {
            "url": wikipedia.page_permalink(revision["id"], title=spec["title"]),
            "published_at": revision["timestamp"],
            "retrieved_at": retrieved_at,
        }
    if cabinet_revision:
        mayor_source["wikipedia_cabinet"] = SOURCES["wikipedia_cabinet"] | {
            "url": wikipedia.page_permalink(cabinet_revision["id"], title=cabinet_source.PAGE_TITLE),
            "published_at": cabinet_revision["timestamp"],
            "retrieved_at": retrieved_at,
        }
    if president_revisions:
        mayor_source["wikipedia_president"] = SOURCES["wikipedia_president"] | {
            "url": wikipedia.page_permalink(president_revisions["office"]["id"], title=president_source.OFFICE_TITLE),
            "published_at": president_revisions["office"]["timestamp"],
            "retrieved_at": retrieved_at,
        }
    if scjn_revision:
        mayor_source["wikipedia_scjn"] = SOURCES["wikipedia_scjn"] | {
            "url": wikipedia.page_permalink(scjn_revision["id"], title=scjn.PAGE_TITLE),
            "published_at": scjn_revision["timestamp"],
            "retrieved_at": retrieved_at,
        }
    if mayor_pages:
        mayor_source["wikipedia_mayors"] = SOURCES["wikipedia_mayors"] | {
            "retrieved_at": mayors_retrieved_at,
            "pages": [
                {
                    "state_code": code,
                    "state": STATES[code],
                    "url": mayor_pages_source.page_permalink(page["title"], page["revision"]["id"]),
                    "published_at": page["revision"]["timestamp"],
                }
                for code, page in sorted(mayor_pages.items())
            ],
        }
    return {
        "generated_at": retrieved_at,
        "sources": mayor_source | {
            "sil": SOURCES["sil"]
            | {
                "url": sil.ROSTER_URL,
                "deputies_url": sil.DEPUTIES_ROSTER_URL,
                "published_at": None,
                "retrieved_at": retrieved_at,
            },
            "wikipedia": SOURCES["wikipedia"]
            | {
                "url": wikipedia.page_permalink(revision["id"]),
                "published_at": revision["timestamp"],
                "retrieved_at": retrieved_at,
            },
        },
        "rules": {
            "senate_term": SENATE_TERM_RULE,
            "deputies_term": DEPUTIES_TERM_RULE,
            "justices_term": JUSTICES_TERM_RULE,
            "electoral_term": judiciary.TEPJF_TERM_RULE,
            "discipline_term": judiciary.TDJ_TERM_RULE,
            "president_term": PRESIDENT_TERM_RULE,
        },
        "circunscripciones": {"list": circunscripciones.CIRCUNSCRIPCIONES, "source": circunscripciones.SOURCE},
        "warnings": check_dataset(people) + list(extra_warnings),
        "people": people,
    }
