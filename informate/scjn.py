"""The justices (ministras y ministros) of the Supreme Court, from Spanish Wikipedia.

The Court's own site refuses requests from outside Mexico, so the article on
Wikipedia is used: a secondary source, cited to the exact revision read. Its
"Composición actual" table lists the nine justices in order of the votes they
received in the 2025 judicial election, which is what decides their term length.
"""
import re

from .mayors import _REF, _plain, _row_cells
from .text import spanish_date_to_iso

PAGE_TITLE = "Suprema Corte de Justicia de la Nación"
SECTION_HEADING = "== Composición actual =="
JUSTICES = 9

# Third transitional article of the judicial reform decree (DOF 15 September 2024),
# as printed in the same copy of the Constitution used for the other rules.
JUSTICES_TERM_RULE = {
    "text": (
        "Las nueve ministras y ministros electos en 2025 duran, por excepción, once u ocho años: "
        "el periodo vence en 2036 para las cinco personas con más votos y en 2033 para las otras cuatro "
        "(artículo tercero transitorio de la reforma judicial publicada el 15 de septiembre de 2024). "
        "El orden por votos es el que da la fuente."
    ),
    "source_name": (
        "Constitución Política de los Estados Unidos Mexicanos, artículos transitorios del decreto "
        "del 15 de septiembre de 2024. Orden Jurídico Nacional, Secretaría de Gobernación"
    ),
    "url": "http://www.ordenjuridico.gob.mx/Constitucion/cn16.pdf",
    "published_at": "2024-11-15",
    "checked_at": "2026-11-07",
}


def term_end_by_rank(rank: int) -> str:
    """Year the term ends for the justice ranked `rank` (0 = most votes)."""
    return "2036" if rank < 5 else "2033"


def parse_justices(wikitext: str) -> list[dict]:
    """The justices in the order the page lists them (by votes received)."""
    start = wikitext.find(SECTION_HEADING)
    table_start = wikitext.find("{|", start)
    table_end = wikitext.find("\n|}", table_start)
    if start < 0 or table_start < 0 or table_end < 0:
        raise ValueError(f"Section {SECTION_HEADING!r} with a table not found on the Wikipedia page")
    table = _REF.sub("", wikitext[table_start:table_end])

    justices = []
    for row in re.split(r"\n\|-[^\n]*", table):
        cells = _row_cells(row)
        if not cells or len(cells) < 5:
            continue  # heading row, or nothing to read
        role, name, home_state, _, period = (_plain(content) for _, _, content in cells[:5])
        if not name:
            continue
        justices.append(
            {
                "role": role,
                "name": name,
                "home_state_raw": home_state,
                "term_start": spanish_date_to_iso(period),
            }
        )
    if not justices:
        raise ValueError("The Supreme Court table had no readable rows")
    return justices
