"""Governors, from the Spanish Wikipedia list of sitting heads of state governments.

Wikipedia is a secondary source. Every record we derive from it is cited to the
exact revision that was read, so a reader can see what the page said that day.
"""
import re
from urllib.parse import quote

from .text import spanish_date_to_iso

PAGE_TITLE = "Anexo:Gobernantes de las entidades federativas de México"
API_URL = "https://es.wikipedia.org/w/api.php"
SECTION_HEADING = "== Gobernantes en funciones =="

_OFFICE = re.compile(
    r"\[\[(?:[^\]|]*\|)?([^\]|]+)\]\]\s+(?:de la|del|de)\s+\[\[(?:[^\]|]*\|)?([^\]|]+)\]\]"
)
_PERSON = re.compile(r"^\[\[(?!Archivo:|File:|Imagen:|Image:)([^\]|]+)(?:\|([^\]]+))?\]\]")
_PARTY = re.compile(r"link=([^\]|]+)")
_NOISE = re.compile(r"<ref[^>]*/>|<ref[^>]*>.*?</ref>|\{\{[^{}]*\}\}", re.S)


def _cells(row: str) -> list[str]:
    """Wikitext table cells: each starts on a line beginning with '|'."""
    cells: list[str] = []
    for line in row.split("\n"):
        if line.startswith("|") and not line.startswith(("|-", "|}")):
            cells.append(line[1:].strip())
        elif cells:
            cells[-1] += "\n" + line
    return cells


def page_permalink(revision_id: int, title: str = PAGE_TITLE) -> str:
    """A link to exactly the revision that was read."""
    return f"https://es.wikipedia.org/w/index.php?title={quote(title.replace(' ', '_'), safe=':_')}&oldid={revision_id}"


def parse_governors(wikitext: str) -> list[dict]:
    """Rows of the 'Gobernantes en funciones' table. ValueError if it can't be read."""
    start = wikitext.find(SECTION_HEADING)
    table_start = wikitext.find("{|", start)
    table_end = wikitext.find("\n|}", table_start)
    if start < 0 or table_start < 0 or table_end < 0:
        raise ValueError(f"Section {SECTION_HEADING!r} with a table not found on the Wikipedia page")

    governors = []
    rows = re.split(r"\n\|-[^\n]*", wikitext[table_start:table_end])
    for row in rows:
        row = _NOISE.sub("", row)
        cells = _cells(row)
        office = _OFFICE.search(cells[0]) if cells else None
        if not office:
            continue  # header row
        person = next((m for m in (_PERSON.match(c) for c in cells[1:]) if m), None)
        party = _PARTY.search(row)
        dates = [d for d in (spanish_date_to_iso(c) for c in cells[-2:]) if d]
        if not (person and party and len(dates) == 2):
            raise ValueError(f"Could not read governor row: {row[:200]!r}")
        article = person.group(1).strip()
        governors.append(
            {
                "title": office.group(1).strip(),
                "state_raw": office.group(2).strip(),
                "name": (person.group(2) or article).strip(),
                "article": article,
                "party_raw": party.group(1).strip(),
                "term_start": dates[0],
                "term_end": dates[1],
            }
        )
    if not governors:
        raise ValueError("Governors table had no readable rows")
    return governors


def fetch_page(session, title: str = PAGE_TITLE) -> tuple[str, dict]:
    """Current wikitext of a page, plus the id and timestamp of that revision."""
    params = {
        "action": "query",
        "prop": "revisions",
        "rvprop": "ids|timestamp|content",
        "rvslots": "main",
        "titles": title,
        "format": "json",
        "formatversion": "2",
    }
    response = session.get(API_URL, params=params, timeout=60)
    response.raise_for_status()
    page = response.json()["query"]["pages"][0]
    if "revisions" not in page:
        raise ValueError(f"Wikipedia page not found: {title}")
    revision = page["revisions"][0]
    return revision["slots"]["main"]["content"], {"id": revision["revid"], "timestamp": revision["timestamp"]}
