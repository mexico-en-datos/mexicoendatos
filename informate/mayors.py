"""Municipal presidents, from the Spanish Wikipedia list kept for each state.

There is no current official list of Mexico's municipal presidents that can be read
automatically (the federal one, INAFED's, is a full term out of date), so this uses
the per-state lists on Wikipedia. It is a secondary source: each record is cited to
the exact revision of its state's page.

Every page has the same table: municipality, president, party. A municipality takes
more than one row when its president was replaced or changed party; the last row is
the current situation.
"""
import re
import time
from difflib import SequenceMatcher
from urllib.parse import quote

from . import wikipedia
from .text import SPANISH_DATE, fold, spanish_date_to_iso

# One page per state, keyed by INEGI state code. The years in each title are the
# municipal term, so these titles change when a state renews its municipalities.
PAGES = {
    "01": "Anexo:Presidentes municipales de Aguascalientes (2024-2027)",
    "02": "Anexo:Presidentes municipales de Baja California (2024-2027)",
    "03": "Anexo:Presidentes municipales de Baja California Sur (2024-2027)",
    "04": "Anexo:Presidentes municipales de Campeche (2024-2027)",
    "05": "Anexo:Presidentes municipales de Coahuila (2024-2027)",
    "06": "Anexo:Presidentes municipales de Colima (2024-2027)",
    "07": "Anexo:Presidentes municipales de Chiapas (2024-2027)",
    "08": "Anexo:Presidentes municipales de Chihuahua (2024-2027)",
    "09": "Anexo:Alcaldes de la Ciudad de México (2024-2027)",
    "10": "Anexo:Presidentes municipales de Durango (2025-2028)",
    "11": "Anexo:Presidentes municipales de Guanajuato (2024-2027)",
    "12": "Anexo:Presidentes municipales de Guerrero (2024-2027)",
    "13": "Anexo:Presidentes municipales de Hidalgo (2024-2027)",
    "14": "Anexo:Presidentes municipales de Jalisco (2024-2027)",
    "15": "Anexo:Presidentes municipales del Estado de México (2024-2027)",
    "16": "Anexo:Presidentes municipales de Michoacán (2024-2027)",
    "17": "Anexo:Presidentes municipales de Morelos (2024-2027)",
    "18": "Anexo:Presidentes municipales de Nayarit (2024-2027)",
    "19": "Anexo:Presidentes municipales de Nuevo León (2024-2027)",
    "20": "Anexo:Presidentes municipales de Oaxaca (2025-2027)",
    "21": "Anexo:Presidentes municipales de Puebla (2024-2027)",
    "22": "Anexo:Presidentes municipales de Querétaro (2024-2027)",
    "23": "Anexo:Presidentes municipales de Quintana Roo (2024-2027)",
    "24": "Anexo:Presidentes municipales de San Luis Potosí (2024-2027)",
    "25": "Anexo:Presidentes municipales de Sinaloa (2024-2027)",
    "26": "Anexo:Presidentes municipales de Sonora (2024-2027)",
    "27": "Anexo:Presidentes municipales de Tabasco (2024-2027)",
    "28": "Anexo:Presidentes municipales de Tamaulipas (2024-2027)",
    "29": "Anexo:Presidentes municipales de Tlaxcala (2024-2027)",
    "30": "Anexo:Presidentes municipales de Veracruz (2026-2029)",
    "31": "Anexo:Presidentes municipales de Yucatán (2024-2027)",
    "32": "Anexo:Presidentes municipales de Zacatecas (2024-2027)",
}

COLUMNS = 4  # municipality, president, party colour, party
NAME = 1
# Municipalities INEGI now lists under a new name, by state: {Wikipedia's name: INEGI's name}.
RENAMED = {"23": {"solidaridad": "playa del carmen"}}
_FIRST_HEADINGS = {"municipio", "alcaldia", "ayuntamiento", "demarcacion"}
_NO_HOLDER = ("vacante", "concejo municipal", "consejo municipal")

_REF = re.compile(r"<ref[^>]*/>|<ref[^>]*>.*?</ref>", re.S)
_TEMPLATE = re.compile(r"\{\{[^{}]*\}\}")
_FILE_LINK = re.compile(r"\[\[(?:Archivo|File|Imagen|Image):[^\]]*\]\]", re.I)
_LINK = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]*))?\]\]")
_ATTRIBUTES = re.compile(r"^\s*((?:[\w-]+\s*=\s*(?:\"[^\"]*\"|[^\s|]+)\s*)+)\|(?!\|)(.*)$", re.S)
_SPAN = r"{kind}span\s*=\s*\"?(\d+)"


def _plain(cell: str) -> str:
    """Cell text without markup: no templates, no file links, links as their shown text."""
    text = _FILE_LINK.sub("", cell)
    while _TEMPLATE.search(text):
        text = _TEMPLATE.sub("", text)
    text = _LINK.sub(lambda m: m.group(2) or m.group(1), text)
    text = re.sub(r"<[^>]+>|'{2,}", "", text)
    return re.sub(r"\s+", " ", text.replace("&nbsp;", " ")).strip()


def _split_cell(cell: str) -> tuple[int, int, str]:
    """(rowspan, colspan, content) of a wikitext table cell."""
    match = _ATTRIBUTES.match(cell)
    attributes, content = (match.group(1), match.group(2)) if match else ("", cell)
    span = {kind: re.search(_SPAN.format(kind=kind), attributes, re.I) for kind in ("row", "col")}
    return (
        int(span["row"].group(1)) if span["row"] else 1,
        int(span["col"].group(1)) if span["col"] else 1,
        content.strip(),
    )


def _row_cells(row: str) -> list[tuple[int, int, str]] | None:
    """Cells of one table row, or None for a heading row."""
    cells: list[str] = []
    for line in row.split("\n"):
        if line.startswith("!"):
            return None
        if line.startswith("|") and not line.startswith(("|-", "|}", "|+")):
            cells.extend(line[1:].split("||"))
        elif cells:
            cells[-1] += "\n" + line
    return [_split_cell(cell) for cell in cells]


def _municipal_table(wikitext: str) -> str:
    """The table whose first heading is 'Municipio' (or 'Alcaldía'), not the party summary."""
    for chunk in wikitext.split("{|")[1:]:
        table = chunk.split("\n|}")[0]
        heading = re.search(r"^!(.*)$", table, re.M)
        if heading:
            first = heading.group(1).split("!!")[0].split("|")[-1]
            if fold(_plain(first)) in _FIRST_HEADINGS:
                return table
    raise ValueError("No table of municipalities and their presidents found on the Wikipedia page")


def parse_mayors(wikitext: str) -> list[dict]:
    """One dict per municipality: its name and article on Wikipedia, and who presides it now.

    `name` is None when the page says the post is vacant or held by a council; `vacant`
    then carries the page's wording.
    """
    table = _REF.sub("", _municipal_table(wikitext))
    remaining = [0] * COLUMNS  # rows each column is still covered by an earlier rowspan
    current: list[str | None] = [None] * COLUMNS
    municipalities: list[list[str | None]] = []
    for row in re.split(r"\n\|-[^\n]*", table):
        cells = _row_cells(row)
        if not cells:
            continue
        free = [column for column in range(COLUMNS) if remaining[column] == 0]
        starts_municipality = 0 in free
        for rowspan, colspan, content in cells:
            covered = free[:colspan]
            for column in covered:
                # A cell that starts in the president column and runs on across the party
                # columns names a person (or a vacancy) and gives no party.
                current[column] = "" if covered[0] == NAME and column != NAME else content
                remaining[column] = rowspan
            free = free[colspan:]
        remaining = [max(0, rows - 1) for rows in remaining]
        if starts_municipality:
            municipalities.append(list(current))
        elif municipalities:
            municipalities[-1] = list(current)  # a later row replaces the earlier situation

    mayors = []
    for municipality_cell, name_cell, _, party_cell in municipalities:
        link = _LINK.search(_FILE_LINK.sub("", municipality_cell or ""))
        name = _plain(name_cell or "")
        vacant = name if fold(name).startswith(_NO_HOLDER) else None
        party_link = _LINK.search(_FILE_LINK.sub("", party_cell or ""))
        mayors.append(
            {
                "municipality": _plain(municipality_cell or ""),
                "article": link.group(1).strip() if link else "",
                "name": None if vacant or not name else name,
                "vacant": vacant,
                "party_raw": None if vacant else (party_link.group(1).strip() if party_link else _plain(party_cell or "")),
            }
        )
    return mayors


def parse_term(wikitext: str) -> tuple[str | None, str | None]:
    """(start, end) of the municipal term as stated in the page's opening paragraph."""
    opening = _REF.sub("", wikitext.split("\n==")[0])
    start = re.search(r"inici\w*[^.]*?(" + SPANISH_DATE.pattern + ")", opening, re.I)
    end = re.search(r"(?:conclu|termin|finaliz)\w*[^.]*?(" + SPANISH_DATE.pattern + ")", opening, re.I)
    return (
        spanish_date_to_iso(start.group(1)) if start else None,
        spanish_date_to_iso(end.group(1)) if end else None,
    )


def match_municipality(shown: str, article: str, official: dict[str, str], state_code: str | None = None) -> str | None:
    """INEGI code of the municipality Wikipedia calls `shown` (linking to `article`).

    `official` maps the INEGI codes of one state's municipalities to their names. Tried
    in order, each only if it singles out one municipality: the same name; a known
    rename; the official name that contains Wikipedia's ('Cintalapa' in 'Cintalapa de
    Figueroa'); the official name contained in Wikipedia's ('Zaragoza' in 'Villa de
    Zaragoza'); a near-identical spelling ('Tixpéhual' / 'Tixpéual'). Anything ambiguous,
    including two municipalities that share a name, gives None.
    """
    names = [(fold(name), code) for code, name in official.items()]
    bare_article = re.sub(r"\s*\([^)]*\)", "", re.sub(r"^Municipio de ", "", article))
    candidates = [fold(text) for text in (shown, bare_article, article) if text.strip()]
    renamed = RENAMED.get(state_code, {})
    candidates += [renamed[candidate] for candidate in candidates if candidate in renamed]

    tests = (
        lambda candidate, name: candidate == name,
        lambda candidate, name: re.search(rf"\b{re.escape(candidate)}\b", name),
        lambda candidate, name: len(name) >= 4 and re.search(rf"\b{re.escape(name)}\b", candidate),
        lambda candidate, name: SequenceMatcher(None, candidate, name).ratio() >= 0.9,
    )
    for test in tests:
        for candidate in candidates:
            found = {code for name, code in names if test(candidate, name)}
            if len(found) == 1:
                return found.pop()
            if found and test is tests[0]:
                return None  # several municipalities carry exactly this name
    return None


def fetch_pages(session, titles: list[str], pause_seconds: float = 6.0, batch_size: int = 7) -> dict[str, dict]:
    """Current wikitext and revision of each page: {title: {"wikitext", "revision"}}.

    Wikipedia answers bursts with "too many requests", so pages are asked for a few
    per request with a pause in between.
    """
    pages = {}
    for start in range(0, len(titles), batch_size):
        if start:
            time.sleep(pause_seconds)
        params = {
            "action": "query",
            "prop": "revisions",
            "rvprop": "ids|timestamp|content",
            "rvslots": "main",
            "titles": "|".join(titles[start:start + batch_size]),
            "format": "json",
            "formatversion": "2",
        }
        response = session.get(wikipedia.API_URL, params=params, timeout=90)
        response.raise_for_status()
        for page in response.json()["query"]["pages"]:
            if "revisions" not in page:
                raise ValueError(f"Wikipedia page not found: {page.get('title')}")
            revision = page["revisions"][0]
            pages[page["title"]] = {
                "wikitext": revision["slots"]["main"]["content"],
                "revision": {"id": revision["revid"], "timestamp": revision["timestamp"]},
            }
    missing = [title for title in titles if title not in pages]
    if missing:
        raise ValueError(f"Wikipedia did not return: {missing}")
    return pages


def page_permalink(title: str, revision_id: int) -> str:
    return f"https://es.wikipedia.org/w/index.php?title={quote(title.replace(' ', '_'), safe=':_()')}&oldid={revision_id}"
