"""Gross domestic product per state, from INEGI's yearly PIBE press release.

INEGI publishes the preliminary GDP of each state (PIBE, Producto Interno Bruto
por Entidad Federativa) every December for the year before. The release is a
PDF; its "Cuadro 1" lists, per state, GDP at market prices for the last two
years in thousands of millions of pesos at 2018 prices, with the annual change.
INEGI's indicator API would give the same numbers but needs a personal token,
which this project avoids.
"""
import re

from .states import STATES
from .text import fold

RELEASE = {
    "year": 2024,
    "url": "https://www.inegi.org.mx/contenidos/saladeprensa/boletines/2025/pibent/PIBE2024_CP.pdf",
    "published_at": "2025-12-05",  # comunicado de prensa 156/25
    "source_name": "INEGI. Producto Interno Bruto por Entidad Federativa 2024, cifras preliminares (comunicado 156/25, cuadro 1)",
    "unit": "miles de millones de pesos a precios de 2018",
}
NATIONAL = "Estados Unidos Mexicanos"

# A number as the table prints it: thousands split by one space ("3 886"), decimals with a point, maybe negative.
_NUMBER = re.compile(r"-?\d{1,3}(?: \d{3})*(?:\.\d+)?")
_BY_NAME = {fold(name): code for code, name in STATES.items()}


def _numbers(text: str) -> list[float]:
    return [float(n.replace(" ", "")) for n in _NUMBER.findall(text)]


def parse_pibe_table(page_text: str) -> dict:
    """Cuadro 1 of the release as {"national": row, "states": {code: row}}; a row is
    {"gdp_previous", "gdp", "growth"} (GDP at market prices, the growth in percent)."""
    states, national = {}, None
    for line in page_text.splitlines():
        match = re.match(r"^([A-Za-zÁÉÍÓÚÑáéíóúñ ]+?)\s+(-?\d.*)$", line.strip())
        if not match:
            continue
        name, numbers = match.group(1).strip(), _numbers(match.group(2))
        if len(numbers) != 9:  # GDP, taxes and gross value added: two years and a change each
            continue
        row = {"gdp_previous": int(numbers[0]), "gdp": int(numbers[1]), "growth": numbers[2]}
        if name == NATIONAL:
            national = row
        elif fold(name) in _BY_NAME:
            states[_BY_NAME[fold(name)]] = row
    if national is None or len(states) != 32:
        raise ValueError(f"Cuadro 1 not found: {len(states)} states and {'a' if national else 'no'} national total")
    return {"national": national, "states": states}


def gdp_records(table: dict, retrieved_at: str, release: dict = RELEASE) -> dict:
    """What the page shows: the year, the unit, every state's GDP, growth and share, and the citation."""
    total = table["national"]["gdp"]
    return {
        "year": release["year"],
        "unit": release["unit"],
        "national": dict(table["national"]),
        "states": {code: {**row, "share": round(100 * row["gdp"] / total, 2)} for code, row in table["states"].items()},
        "citation": {
            "source": "inegi_pibe",
            "source_name": release["source_name"],
            "url": release["url"],
            "published_at": release["published_at"],
            "retrieved_at": retrieved_at,
        },
    }


def extract_table_text(pdf_path) -> str:
    """The text of the release page that holds cuadro 1."""
    import pypdf  # imported here so the parser tests need no PDF library

    for page in pypdf.PdfReader(str(pdf_path)).pages:
        text = page.extract_text()
        if "Cuadro 1" in text and NATIONAL in text:
            return text
    raise ValueError(f"{pdf_path}: no page with cuadro 1")
