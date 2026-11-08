"""The President, from Spanish Wikipedia: the article on the office says who holds
it and since when; the person's own article gives their party."""
import re
from datetime import date, timedelta

from .text import spanish_date_to_iso

OFFICE_TITLE = "Presidente de México"

# Article 83 of the Constitution, same copy as the other rules.
PRESIDENT_TERM_RULE = {
    "text": (
        "La Presidencia de la República dura seis años a partir del 1 de octubre del año de la elección "
        "(artículo 83 de la Constitución)."
    ),
    "source_name": (
        "Constitución Política de los Estados Unidos Mexicanos, artículo 83. "
        "Orden Jurídico Nacional, Secretaría de Gobernación"
    ),
    "url": "http://www.ordenjuridico.gob.mx/Constitucion/cn16.pdf",
    "published_at": "2024-11-15",
    "checked_at": "2026-11-07",
}

_FIELD = r"^\|\s*{name}\s*=\s*(.*)$"
_LINK = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]*))?\]\]")
_FECHA = re.compile(r"\{\{\s*fecha\s*\|\s*(\d{1,2})\s*\|\s*(\d{1,2})\s*\|\s*(\d{4})", re.I)


def _field(wikitext: str, name: str) -> str:
    match = re.search(_FIELD.format(name=name), wikitext, re.M | re.I)
    if not match:
        raise ValueError(f"Infobox field {name!r} not found on the Wikipedia page")
    return re.sub(r"<ref[^>]*/>|<ref[^>]*>.*?</ref>", "", match.group(1), flags=re.S).strip()


def parse_office(wikitext: str) -> dict:
    """Who holds the office ({"name", "article", "term_start"}) from the office's infobox."""
    holder = _LINK.search(_field(wikitext, "titular"))
    if not holder:
        raise ValueError("The 'titular' field names nobody")
    start = _field(wikitext, "inicio")
    stamped = _FECHA.search(start)
    term_start = f"{stamped.group(3)}-{int(stamped.group(2)):02d}-{int(stamped.group(1)):02d}" if stamped else spanish_date_to_iso(start)
    return {"name": (holder.group(2) or holder.group(1)).strip(), "article": holder.group(1).strip(), "term_start": term_start}


def parse_party(wikitext: str) -> str:
    """The first party in the person's infobox, which Wikipedia lists as the current one."""
    links = [m.group(1).strip() for m in _LINK.finditer(_field(wikitext, "partido")) if not re.match(r"(Archivo|File|Imagen|Image):", m.group(1))]
    if not links:
        raise ValueError("The 'partido' field names no party")
    return links[0]


def presidential_term(term_start: str) -> tuple[str, str]:
    """Six years from taking office: 2024-10-01 -> ends 2030-09-30."""
    start = date.fromisoformat(term_start)
    end = date(start.year + 6, start.month, start.day) - timedelta(days=1)
    return term_start, end.isoformat()
