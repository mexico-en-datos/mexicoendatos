"""The two other elected bodies of the federal judiciary, from Spanish Wikipedia.

Since the judicial reform of 2024 the Poder Judicial de la Federación has three
bodies whose members are elected by popular vote: the Supreme Court (see
`scjn.py`), the Sala Superior of the Tribunal Electoral (seven seats) and the
Tribunal de Disciplina Judicial (five seats). Their own sites are not read
automatically; the Wikipedia articles are used as a secondary source, cited to
the exact revision read.
"""
import re

from .mayors import _REF, _plain, _row_cells

TEPJF_PAGE_TITLE = "Tribunal Electoral del Poder Judicial de la Federación"
TDJ_PAGE_TITLE = "Tribunal de Disciplina Judicial (México)"
TEPJF_SEATS = 7
TDJ_SEATS = 5
SWORN_IN_2025 = "2025-09-01"  # second transitional article: those elected in 2025 took the oath on 1 September 2025

_FECHA = re.compile(r"\{\{\s*fecha\s*\|\s*(\d{1,2})\s*\|\s*(\d{1,2})\s*\|\s*(\d{4})", re.I)

# Fourth and fifth transitional articles of the judicial reform decree (DOF 15 September 2024),
# as printed in the same copy of the Constitution used for the other rules.
_SOURCE = {
    "source_name": (
        "Constitución Política de los Estados Unidos Mexicanos, artículos transitorios del decreto "
        "del 15 de septiembre de 2024. Orden Jurídico Nacional, Secretaría de Gobernación"
    ),
    "url": "http://www.ordenjuridico.gob.mx/Constitucion/cn16.pdf",
    "published_at": "2024-11-15",
    "checked_at": "2026-11-07",
}
TEPJF_TERM_RULE = {
    "text": (
        "Las magistraturas de la Sala Superior del Tribunal Electoral en funciones al entrar en vigor la reforma "
        "judicial permanecen hasta 2027; las electas en 2025 duran ocho años, hasta 2033 "
        "(artículo cuarto transitorio de la reforma publicada el 15 de septiembre de 2024). "
        "Quienes resultaron electos en 2025 tomaron protesta el 1 de septiembre de 2025 (artículo segundo transitorio)."
    ),
    **_SOURCE,
}
TDJ_TERM_NOTE = "Vence en 2033 para las dos personas con más votos y en 2030 para las otras tres; la fuente no da el orden de votación"
TDJ_TERM_RULE = {
    "text": (
        "Las cinco magistraturas del Tribunal de Disciplina Judicial electas en 2025 tomaron protesta el 1 de "
        "septiembre de 2025 (artículo segundo transitorio). Su periodo vence en 2030 para tres de ellas y en 2033 "
        "para las dos con más votos (artículo quinto transitorio de la reforma publicada el 15 de septiembre de 2024); "
        "la fuente no da el orden de votación, así que la página no asigna el año a cada persona."
    ),
    **_SOURCE,
}


def _table_after(wikitext: str, heading: str) -> str:
    start = wikitext.find(heading)
    table_start = wikitext.find("{|", start)
    table_end = wikitext.find("\n|}", table_start)
    if start < 0 or table_start < 0 or table_end < 0:
        raise ValueError(f"Section {heading!r} with a table not found on the Wikipedia page")
    return _REF.sub("", wikitext[table_start:table_end])


def _iso(fecha_template: str) -> str | None:
    match = _FECHA.search(fecha_template)
    return f"{match.group(3)}-{int(match.group(2)):02d}-{int(match.group(1)):02d}" if match else None


def parse_electoral_tribunal(wikitext: str) -> list[dict]:
    """The seven seats of the Sala Superior, in the page's order; a vacant seat is a row too."""
    table = _table_after(wikitext, "Integración de la Sala superior")
    seats = []
    for row in re.split(r"\n\|-[^\n]*", table):
        cells = _row_cells(row)
        if not cells:
            continue
        texts = [_plain(content) for _, _, content in cells]
        if len(cells) == 1 and "vacante" in texts[0].lower():
            seats.append({"role": None, "name": None, "elected": None, "vacant": True})
        elif len(cells) >= 3 and texts[1]:
            seats.append({"role": texts[0] or None, "name": texts[1], "elected": _iso(cells[2][2]), "vacant": False})
    if len(seats) != TEPJF_SEATS:
        raise ValueError(f"Expected {TEPJF_SEATS} seats in the Sala Superior table, found {len(seats)}")
    return seats


def electoral_term_end(elected: str | None) -> str | None:
    """Year the term ends: 2027 for those in office at the reform, 2033 for those elected in 2025."""
    if not elected:
        return None
    return "2033" if elected >= "2025" else "2027"


def parse_discipline_tribunal(wikitext: str) -> list[dict]:
    """The five magistrates, in the page's order; the president is marked in the name cell."""
    table = _table_after(wikitext, "== Composición ==")
    rows = []
    start = None
    for row in re.split(r"\n\|-[^\n]*", table):
        cells = _row_cells(row)
        if not cells:
            continue
        texts = [_plain(content) for _, _, content in cells]
        if len(texts) >= 2 and texts[1]:  # the first row carries the shared period cell, e.g. "1 de septiembre de 2025-"
            start = _spanish_start(texts[1])
        name = texts[0]
        if not name:
            continue
        role = None
        marked = re.search(r"\(([^)]*)\)", name)
        if marked:
            role = marked.group(1).strip()
            name = name[: marked.start()].strip()
        rows.append({"name": name, "role": role, "term_start": start})
    if len(rows) != TDJ_SEATS:
        raise ValueError(f"Expected {TDJ_SEATS} magistrates in the Tribunal de Disciplina table, found {len(rows)}")
    return rows


_MONTHS = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12}


def _spanish_start(period: str) -> str | None:
    """'1 de septiembre de 2025-' -> '2025-09-01'."""
    match = re.search(r"(\d{1,2}) de (\w+) de (\d{4})", period)
    if not match or match.group(2).lower() not in _MONTHS:
        return None
    return f"{match.group(3)}-{_MONTHS[match.group(2).lower()]:02d}-{int(match.group(1)):02d}"
