"""The governing bodies of each chamber of Congress, from the Spanish Wikipedia annex on
the current legislature ("Anexo:LXVI Legislatura del Congreso de la Unión de México").

The chambers' own pages refuse automated readers (the Senate answers 403, the Chamber's
site does not answer), so the annex is used: a secondary source, cited to the exact
revision read. For each chamber it gives the Mesa Directiva of the current legislative
year (who presides it and the vice-presidencies) and who coordinates each parliamentary
group. Who presides the Junta de Coordinación Política is not copied from it: the organic
law settles that from the seat counts, and the dataset applies the rule (JUCOPO_RULE).
"""
import re

from .parties import party_code
from .text import fold, roman

CHAMBER_HEADING = {"senator": "== Senado de la República ==", "deputy": "== Cámara de Diputados =="}
BOARD_HEADING = "=== Mesa directiva ==="
COORDINATORS_HEADING = "=== Coordinadores parlamentarios ==="

# Ley Orgánica del Congreso General, as published by Orden Jurídico Nacional (Secretaría de
# Gobernación). Articles 17 and 62: the Mesa Directiva of each chamber serves one legislative
# year. Articles 31 and 81: who presides the Junta de Coordinación Política.
_LAW = {
    "source_name": "Ley Orgánica del Congreso General de los Estados Unidos Mexicanos. Orden Jurídico Nacional, Secretaría de Gobernación",
    "url": "http://www.ordenjuridico.gob.mx/Documentos/Federal/html/wo16815.html",
    "published_at": "2022-12-19",
    "checked_at": "2026-11-11",
}
BOARD_RULE = _LAW | {
    "text": (
        "La Mesa Directiva de cada cámara se elige para un año legislativo, del 1 de septiembre al 31 de agosto, "
        "y sus integrantes pueden reelegirse (Ley Orgánica del Congreso General, artículos 17 y 62)."
    )
}
JUCOPO_RULE = _LAW | {
    "text": (
        "Preside la Junta de Coordinación Política durante toda la legislatura quien coordina al grupo parlamentario "
        "que por sí solo tiene la mayoría absoluta de la cámara (Ley Orgánica del Congreso General, artículos 31 y 81). "
        "Si ningún grupo la tiene, la presidencia se turna cada año legislativo."
    )
}

_YEAR_HEADING = re.compile(r"^==== *(\d{4})-(\d{2}) *====[ \t]*$", re.M)
_LINK = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]*))?\]\]")
_FILE = re.compile(r"\[\[(?:Archivo|File|Imagen|Image):[^\]]*\]\]", re.I)
_REF = re.compile(r"<ref[^>]*/>|<ref[^>]*>.*?</ref>", re.S)
_FLAG = re.compile(r"\{\{\s*Bandera2?\s*\|\s*([^}|]+)")
_COORDINATOR = re.compile(r"^\*.*?'''(?P<party>[^']+?):?'''\s*:?\s*(?P<link>\[\[[^\]]+\]\])", re.M)


def page_title(legislature: int) -> str:
    """The annex for a legislature: 66 -> 'Anexo:LXVI Legislatura del Congreso de la Unión de México'."""
    return f"Anexo:{roman(legislature)} Legislatura del Congreso de la Unión de México"


def _section(text: str, heading: str) -> str:
    """The wikitext under `heading`, up to the next heading of the same or a higher level."""
    level = len(heading) - len(heading.lstrip("="))
    match = re.search(r"^" + re.escape(heading) + r"[ \t]*$", text, re.M)
    if not match:
        raise ValueError(f"Heading {heading!r} not found on the Wikipedia page")
    rest = text[match.end():]
    following = re.search(r"^={1,%d}[^=]" % level, rest, re.M)
    return rest[: following.start()] if following else rest


def _plain(text: str) -> str:
    text = _FILE.sub("", text)
    text = re.sub(r"\{\{[^{}]*\}\}", "", text)
    text = _LINK.sub(lambda m: m.group(2) or m.group(1), text)
    text = re.sub(r"<br\s*/?>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>|'{2,}", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _person(cell: str) -> dict | None:
    """Name from the first article link in a cell: the article title, plus the shown text when it differs."""
    link = _LINK.search(_FILE.sub("", cell))
    if not link:
        return None
    name = re.sub(r"\s*\([^)]*\)$", "", link.group(1).strip())
    shown = _plain(link.group(2)) if link.group(2) else ""
    return {"name": name, "aliases": [shown] if shown and fold(shown) != fold(name) else []}


def _cells(row: str) -> list[str]:
    """The cells of a wikitext table row, without their formatting attributes."""
    cells = []
    for line in row.split("\n"):
        if not line.startswith("|") or line.startswith(("|}", "|+", "|-")):
            continue
        for part in line[1:].split("||"):
            part = part.strip()
            head, sep, tail = part.partition("|")
            if sep and "=" in head and not re.search(r"[\[{]", head):
                part = tail.strip()
            cells.append(part)
    return cells


def _board(section: str) -> tuple[str, list[dict]]:
    """('2026-27', members) from the first legislative-year table under the Mesa directiva heading."""
    year = _YEAR_HEADING.search(section)
    if not year:
        raise ValueError("No legislative-year table under the Mesa directiva heading")
    label = f"{year.group(1)}-{year.group(2)}"
    body = section[year.end():]
    table_start = body.find("{|")
    table_end = body.find("\n|}", table_start)
    if table_start < 0 or table_end < 0:
        raise ValueError(f"No table for the Mesa directiva of {label}")
    members = []
    for row in re.split(r"\n\|-[^\n]*", _REF.sub("", body[table_start:table_end])):
        cells = _cells(row)
        if len(cells) < 4:
            continue
        who = _person(cells[1])
        if not who:
            continue
        party_link = _LINK.search(_FILE.sub("", cells[3]))
        flag = _FLAG.search(cells[4]) if len(cells) > 4 else None
        members.append(
            who
            | {
                "role": _plain(cells[2]),
                "party": party_code(party_link.group(1)) if party_link else None,
                "party_name": (party_link.group(2) or party_link.group(1)).strip() if party_link else None,
                "state": flag.group(1).strip() if flag else None,
            }
        )
    if not members:
        raise ValueError(f"The Mesa directiva table of {label} had no readable rows")
    return label, members


def _coordinators(section: str) -> list[dict]:
    found = []
    for match in _COORDINATOR.finditer(_REF.sub("", section)):
        who = _person(match.group("link"))
        party_name = match.group("party").strip().rstrip(":").strip()
        if who:
            found.append({"party": party_code(party_name), "party_name": party_name} | who)
    if not found:
        raise ValueError("No parliamentary-group coordinators listed")
    return found


def parse_leadership(wikitext: str) -> dict:
    """Per chamber ('senator', 'deputy'): the legislative year of its Mesa Directiva, its members
    (name, role, party, state) and the coordinator of each parliamentary group."""
    out = {}
    for office, heading in CHAMBER_HEADING.items():
        chamber = _section(wikitext, heading)
        label, board = _board(_section(chamber, BOARD_HEADING))
        out[office] = {"period": label, "board": board, "coordinators": _coordinators(_section(chamber, COORDINATORS_HEADING))}
    return out


def legislative_year(label: str) -> tuple[str, str]:
    """'2026-27' -> ('2026-09-01', '2027-08-31'): the legislative year the Mesa Directiva serves."""
    match = re.fullmatch(r"(\d{4})-(\d{2})", label)
    if not match or int(match.group(2)) != (int(match.group(1)) + 1) % 100:
        raise ValueError(f"Not a legislative year: {label!r}")
    start = int(match.group(1))
    return f"{start}-09-01", f"{start + 1}-08-31"


def _tokens(name: str) -> set[str]:
    return set(fold(name).replace("-", " ").split())


def find_member(entry: dict, people: list[dict]) -> dict | None:
    """The roster record for a name from the annex: every word of the annex name (or of its
    shown form) is in the record's name. Several hits are narrowed by party, then by state;
    anything still ambiguous gives None, so the caller can say so instead of guessing."""
    wanted = [_tokens(name) for name in [entry["name"], *entry.get("aliases", [])]]
    hits = [person for person in people if any(words <= _tokens(person["name"]) for words in wanted)]
    if len(hits) > 1 and entry.get("party"):
        hits = [person for person in hits if person.get("party") == entry["party"]] or hits
    if len(hits) > 1 and entry.get("state"):
        hits = [person for person in hits if fold(person.get("state") or "") == fold(entry["state"])] or hits
    return hits[0] if len(hits) == 1 else None


def jucopo_president(coordinators: list[dict], seats_by_party: dict[str, int], total_seats: int) -> dict | None:
    """The coordinator who presides the Junta de Coordinación Política under JUCOPO_RULE:
    the one whose group alone holds more than half the seats. None when no group does."""
    for party, seats in seats_by_party.items():
        if seats * 2 > total_seats:
            for coordinator in coordinators:
                if coordinator["party"] == party:
                    return coordinator | {"seats": seats, "total": total_seats}
    return None
