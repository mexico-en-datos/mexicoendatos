"""The five regions (circunscripciones plurinominales) that elect the 200 list deputies.

Each region is a group of states. The make-up below is the one in force since
29 March 2023 (used in the 2024 election), as listed on Spanish Wikipedia; the
`parse_circunscripciones` reader exists so a test can check this table against
that page, and so it can be re-read when the regions are redrawn.
"""
import re

from .states import state_code

SOURCE = {
    "name": "Wikipedia en español, «Anexo:Circunscripciones electorales de México»",
    "url": "https://es.wikipedia.org/w/index.php?title=Anexo:Circunscripciones_electorales_de_M%C3%A9xico&oldid=172276913",
    "published_at": "2026-02-28T11:37:19Z",
    "checked_at": "2026-11-07",
}

CIRCUNSCRIPCIONES = [
    {"number": 1, "name": "Primera circunscripción", "seat": "Guadalajara", "states": ["02", "03", "08", "10", "14", "18", "25", "26"]},
    {"number": 2, "name": "Segunda circunscripción", "seat": "Monterrey", "states": ["01", "05", "11", "19", "24", "28", "32"]},
    {"number": 3, "name": "Tercera circunscripción", "seat": "Xalapa", "states": ["04", "07", "20", "23", "27", "30", "31"]},
    {"number": 4, "name": "Cuarta circunscripción", "seat": "Ciudad de México", "states": ["09", "12", "13", "17", "21", "29"]},
    {"number": 5, "name": "Quinta circunscripción", "seat": "Toluca", "states": ["06", "15", "16", "22"]},
]

_ORDINALS = {"primera": 1, "segunda": 2, "tercera": 3, "cuarta": 4, "quinta": 5}
_STATE_LINK = re.compile(r"\*\s*\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")


def circunscripcion_of(code: str) -> dict:
    return next(c for c in CIRCUNSCRIPCIONES if code in c["states"])


def number_of(ordinal: str) -> int | None:
    """'Tercera' or '3.ª' -> 3; None for anything else."""
    digits = re.match(r"\s*([1-5])\b", ordinal)
    if digits:
        return int(digits.group(1))
    return _ORDINALS.get(ordinal.strip().lower())


def parse_circunscripciones(wikitext: str) -> list[list[str]]:
    """The states of each region, as INEGI codes, in the order the page's table gives them."""
    start = wikitext.find("== Organización de las circunscripciones")
    table = wikitext[wikitext.find("{|", start):wikitext.find("\n|}", start)]
    regions = []
    for row in re.split(r"\n\|-[^\n]*", table):
        if not re.search(r"'''\d\.ª'''", row):
            continue
        shown = [(m.group(2) or m.group(1)).strip() for m in _STATE_LINK.finditer(row)]
        regions.append(sorted(state_code(name) for name in shown))
    if len(regions) != 5:
        raise ValueError(f"Expected 5 regions on the page, found {len(regions)}")
    return regions
