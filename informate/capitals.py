"""The capital city of each state, from Spanish Wikipedia, placed in its municipality.

Capitals are fixed by each state's constitution; the Wikipedia annex of federal
entities lists them in one table and is cited to the revision read. Each capital
is then matched to INEGI's municipality so the map can point at it. A few
capitals sit in a municipality with a different name; those pairs are spelled
out below rather than guessed.
"""
import re

from .mayors import _REF, _plain, _row_cells
from .states import STATES
from .text import fold
from . import wikipedia

PAGE_TITLE = "Anexo:Entidades federativas de México"
# Capital city -> municipality name in INEGI's catalogue, where the two differ.
MUNICIPALITY_OF = {
    "villahermosa": "centro",
    "ciudad victoria": "victoria",
    "chetumal": "othon p. blanco",
    "san francisco de campeche": "campeche",
    "chilpancingo de los bravo": "chilpancingo de los bravo",
    "oaxaca de juarez": "oaxaca de juarez",
    "tuxtla gutierrez": "tuxtla gutierrez",
    "pachuca de soto": "pachuca de soto",
    "toluca de lerdo": "toluca",
    "santiago de queretaro": "queretaro",
    "culiacan rosales": "culiacan",
    "tlaxcala de xicohtencatl": "tlaxcala",
    "xalapa-enriquez": "xalapa",
    "xalapa": "xalapa",
    "victoria de durango": "durango",
    "puebla de zaragoza": "puebla",
    "merida": "merida",
    "cuernavaca": "cuernavaca",
}
_BY_NAME = {fold(name): code for code, name in STATES.items()}
_ALSO = {"coahuila": "05", "michoacan": "16", "veracruz": "30", "estado de mexico": "15", "mexico": "15"}


def _state_code(name: str) -> str | None:
    key = fold(name)
    return _BY_NAME.get(key) or _ALSO.get(key)


def parse_capitals(wikitext: str) -> dict[str, str]:
    """{state code: capital name} from the annex's main table."""
    start = wikitext.find("{|")
    table = _REF.sub("", wikitext[start : wikitext.find("\n|}", start)])
    headers = [h.strip() for h in re.findall(r"^!\s*(?:[^|\n]*\|)?\s*(.+)$", table, re.M)]
    capital_column = next((i for i, h in enumerate(headers) if _plain(h).lower().startswith("capital")), 3)
    capitals = {}
    for row in re.split(r"\n\|-[^\n]*", table):
        cells = _row_cells(row)
        if not cells:
            continue
        texts = [_plain(content) for _, _, content in cells]
        if len(texts) <= capital_column or not texts[0]:
            continue
        code = _state_code(texts[0])
        if code and texts[capital_column]:
            # Ciudad de México has no capital of its own: the page prints a dash; it is its own seat.
            capitals[code] = texts[capital_column] if texts[capital_column] not in ("—", "-", "–") else STATES[code]
    if len(capitals) != 32:
        raise ValueError(f"Expected 32 capitals, found {len(capitals)}")
    return capitals


def capital_records(capitals: dict[str, str], catalog: dict[str, dict[str, str]], revision: dict, retrieved_at: str) -> dict:
    """Each capital with the code and name of its municipality; the citation covers all."""
    states = {}
    for code, capital in capitals.items():
        wanted = MUNICIPALITY_OF.get(fold(capital), fold(capital))
        by_name = {fold(name): (muni_code, name) for muni_code, name in catalog.get(code, {}).items()}
        match = by_name.get(wanted)
        if match is None and code != "09":  # try the first word(s) before "de": "Oaxaca de Juárez" -> "Oaxaca"
            short = wanted.split(" de ")[0]
            match = by_name.get(short)
        states[code] = {"capital": capital, "municipality_code": match[0] if match else None, "municipality": match[1] if match else None}
    return {
        "states": states,
        "citation": {
            "source": "wikipedia_capitals",
            "source_name": f"Wikipedia en español, «{PAGE_TITLE}»",
            "url": wikipedia.page_permalink(revision["id"], title=PAGE_TITLE),
            "published_at": revision["timestamp"],
            "retrieved_at": retrieved_at,
        },
    }
