"""The federal cabinet (gabinete legal), from the Spanish Wikipedia article "Gabinete de México".

Its table lists the dependencies in the order of article 26 of the Ley Orgánica
de la Administración Pública Federal, each with its current head. No official
page lists the cabinet in a form that can be read automatically. The source
gives names but not appointment dates.
"""
import re

from .mayors import _REF, _plain, _row_cells

PAGE_TITLE = "Gabinete de México"
SECTION_HEADING = "=== Gabinete legal ==="
_LINK = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]*))?\]\]")
_FILE = re.compile(r"\[\[(?:Archivo|File|Imagen|Image):[^\]]*\]\]", re.I)


def parse_cabinet(wikitext: str) -> list[dict]:
    """One dict per dependency: its name and article, and the head's name (None when vacant)."""
    start = wikitext.find(SECTION_HEADING)
    table_start = wikitext.find("{|", start)
    table_end = wikitext.find("\n|}", table_start)
    if start < 0 or table_start < 0 or table_end < 0:
        raise ValueError(f"Section {SECTION_HEADING!r} with a table not found on the Wikipedia page")
    table = _REF.sub("", wikitext[table_start:table_end])
    cabinet = []
    for row in re.split(r"\n\|-[^\n]*", table):
        cells = _row_cells(row)
        if not cells or len(cells) < 3:
            continue
        dependency_link = _LINK.search(_FILE.sub("", cells[0][2]))
        if not dependency_link:
            continue
        head = _plain(cells[2][2])
        vacant = head if head.lower().startswith("vacante") else None
        cabinet.append(
            {
                "dependency": (dependency_link.group(2) or dependency_link.group(1)).strip(),
                "article": dependency_link.group(1).strip(),
                "name": None if vacant or not head else head,
                "vacant": vacant,
            }
        )
    if not cabinet:
        raise ValueError("The cabinet table had no readable rows")
    return cabinet
