"""Minimum wage, employment and poverty, per state, from official publications.

Three sources, none needing a token or an account:

- CONASAMI's yearly table of minimum wages (a PDF): the general wage, the
  northern border zone wage, and the list of border municipalities.
- INEGI's quarterly ENOE bulletin (a PDF): cuadro 5 has, per state, employed
  and unemployed people and the participation, unemployment and informality
  rates.
- INEGI's multidimensional poverty tabulados (a workbook, one sheet per
  state): population in poverty and in extreme poverty, people and percent,
  2016 to 2024.
"""
import re

from .states import STATES
from .text import fold

MINIMUM_WAGE = {
    "year": 2026,
    "url": "https://www.gob.mx/cms/uploads/attachment/file/1041076/Tabla_de_Salarios_M_nimos_2026.pdf",
    "source_name": "CONASAMI, Tabla de salarios mínimos generales y profesionales vigentes a partir del 1 de enero de 2026",
    "published_at": None,  # the table itself carries no date; the resolution behind it appeared in the DOF in December 2025
}
ENOE = {
    "url": "https://www.inegi.org.mx/contenidos/saladeprensa/boletines/2026/enoe/enoe2026_08.pdf",
    "source_name": "INEGI, Encuesta Nacional de Ocupación y Empleo, segundo trimestre de 2026 (comunicado de prensa, cuadro 5)",
    "published_at": "2026-08-25",
    "period": "segundo trimestre de 2026",
    "next_release": "2026-11-25",
}
# One bulletin per state, with the same quarter's figures; cuadro "Nivel de ingresos" gives the
# employed by income band, in minimum wages. The file names use INEGI's state abbreviations.
_ABBREVIATIONS = {
    "01": "Ags", "02": "BC", "03": "BCS", "04": "Camp", "05": "Coah", "06": "Col", "07": "Chis", "08": "Chih", "09": "CdMx", "10": "Dgo",
    "11": "Gto", "12": "Gro", "13": "Hgo", "14": "Jal", "15": "Mex", "16": "Mich", "17": "Mor", "18": "Nay", "19": "NL", "20": "Oax",
    "21": "Pue", "22": "Qro", "23": "QRoo", "24": "SLP", "25": "Sin", "26": "Son", "27": "Tab", "28": "Tamps", "29": "Tlax", "30": "Ver", "31": "Yuc", "32": "Zac",
}
STATE_BULLETIN = {code: ENOE["url"].replace(".pdf", f"_{abbr}.pdf") for code, abbr in _ABBREVIATIONS.items()}
INCOME_BANDS = {
    "Hasta un salario mínimo": "up_to_1",
    "Más de 1 hasta 2 salarios mínimos": "from_1_to_2",
    "Más de 2 hasta 3 salarios mínimos": "from_2_to_3",
    "Más de 3 hasta 5 salarios mínimos": "from_3_to_5",
    "Más de 5 salarios mínimos": "over_5",
    "No recibe ingresos": "none",
    "No especificado": "unspecified",
}
_TOKEN = re.compile(r"-?\d{1,3}(?:[ ,]\d{3})+(?:\.\d+)?|-?\d+(?:\.\d+)?")

POVERTY = {
    "year": 2024,
    "url": "https://www.inegi.org.mx/contenidos/desarrollosocial/pm/tabulados/pm_ef_2024.xlsx",
    "source_name": "INEGI, Pobreza Multidimensional 2024, tabulados por entidad federativa (metodología del Coneval, ENIGH 2024)",
    "published_at": "2025-08-13",
}

_BY_NAME = {fold(name): code for code, name in STATES.items()}
_NUMBER = re.compile(r"-?\d{1,3}(?: \d{3})*(?:\.\d+)?|\d+(?:\.\d+)?")


# ---------- Minimum wage ----------

def parse_minimum_wage(text: str) -> dict:
    """Amounts in pesos per day and the border-zone municipalities, by state name."""
    general = re.search(r"Zona del Salario Mínimo General.*?\$([\d.,]+)\s+\$[\d.,]+\s+[\d.]+%\s+\$([\d.,]+)", text, re.S)
    border = re.search(r"Zona Libre de la Frontera Norte\s+\$([\d.,]+)\s+\$[\d.,]+\s+[\d.]+%\s+\$([\d.,]+)", text)
    start = re.search(r"Vigentes a partir del 1º? de enero de (\d{4})", text)
    if not (general and border and start):
        raise ValueError("Minimum wage table not found in the CONASAMI document")
    zone = re.search(r"ÁREA GEOGRÁFICA de la Zona Libre de la Frontera Norte.*?Estados Unidos de Norteamérica:\s*(.*?)\.\s*\*\*", text, re.S)
    if not zone:
        raise ValueError("Border-zone municipality list not found in the CONASAMI document")
    municipalities = {}
    for part in re.split(r";\s*", re.sub(r"\s+", " ", zone.group(1))):
        match = re.match(r"\s*(?:y\s+)?(.*?),?\s+en el Estado de (.+)$", part.strip())
        if not match:
            continue
        names = [n.strip() for n in re.split(r",\s*|\s+y\s+|\s+e\s+(?=[A-ZÁÉÍÓÚ])", match.group(1)) if n.strip()]
        municipalities[match.group(2).strip()] = names
    return {
        "general": float(general.group(2).replace(",", "")),
        "border": float(border.group(2).replace(",", "")),
        "effective_from": f"{start.group(1)}-01-01",
        "border_municipalities": municipalities,
    }


def _squash(name: str) -> str:
    return fold(name).replace(" ", "").replace(".", "")


def border_municipality_codes(wage: dict, catalog: dict[str, dict[str, str]]) -> set[str]:
    """INEGI codes of the border-zone municipalities; names are matched within their state."""
    codes = set()
    for state_name, names in wage["border_municipalities"].items():
        state_code = _BY_NAME.get(fold(state_name))
        if not state_code:
            continue
        by_name = {_squash(name): code for code, name in catalog.get(state_code, {}).items()}
        for name in names:
            code = by_name.get(_squash(name))
            if code:
                codes.add(code)
    return codes


# ---------- Employment ----------

def parse_enoe_table(page_text: str) -> dict:
    """Cuadro 5 of the ENOE bulletin: per state, people and rates."""
    states, national, pending = {}, None, ""
    for raw in page_text.splitlines():
        line = raw.strip()
        numbers = [n for n in _NUMBER.findall(line) if n]
        if len(numbers) < 11:
            # A state name split over two lines ("Veracruz de Ignacio de la" / "Llave 3 310 652 …").
            pending = line if line and any(fold(name).startswith(fold(line)) for name in STATES.values()) else ""
            continue
        name_part = line[: line.find(numbers[0])].strip()
        name = f"{pending} {name_part}".strip() if pending else name_part
        pending = ""
        values = [float(n.replace(" ", "")) for n in numbers[:11]]
        row = {"employed": int(values[0]), "unemployed": int(values[1]), "participation": values[2], "unemployment": values[3], "informality": values[9]}
        if name == "Estados Unidos Mexicanos":
            national = row
        elif fold(name) in _BY_NAME:
            states[_BY_NAME[fold(name)]] = row
    if national is None or len(states) != 32:
        raise ValueError(f"ENOE cuadro 5 not found: {len(states)} states and {'a' if national else 'no'} national row")
    return {"national": national, "states": states}


def parse_income_bands(text: str) -> dict:
    """Share of the employed in each income band (percent, current quarter) from a state bulletin.

    Each row ends with three decimals: previous share, current share, change in points; the
    current share is the second to last. Counts are left alone: their thousands separators are
    ambiguous in the extracted text, and cuadro 5 of the national bulletin has them anyway.
    """
    heading = re.search(r"Nivel de ingresos", text, re.I)  # some bulletins write "Ingresos"
    if not heading:
        raise ValueError("'Nivel de ingresos' table not found in the state bulletin")
    block = text[heading.start():]
    end = block.find("Nota:")
    block = block[: end if end > 0 else None]
    bands = {}
    for line in block.splitlines()[1:]:
        for label, key in INCOME_BANDS.items():
            if line.startswith(label):
                decimals = re.findall(r"-?\d+\.\d+", line[len(label):])
                if len(decimals) >= 2:
                    bands[key] = float(decimals[-2])
                break
    if len(bands) != len(INCOME_BANDS):
        raise ValueError(f"Income bands incomplete: {sorted(bands)}")
    return bands


# ---------- Poverty ----------

def parse_poverty_workbook(path) -> dict:
    """Population in poverty and in extreme poverty in 2024, per state, from INEGI's workbook."""
    import openpyxl  # imported here so the other parsers need no spreadsheet library

    workbook = openpyxl.load_workbook(str(path), read_only=True, data_only=True)
    states, national = {}, None
    for sheet_name in workbook.sheetnames:
        if sheet_name == "Índice" or sheet_name.startswith(("IP ", "Gráfica")):  # precision intervals and charts
            continue
        rows = [[c for c in row if c is not None] for row in workbook[sheet_name].iter_rows(values_only=True)]
        place = next((r[0] for r in rows[2:8] if r and isinstance(r[0], str) and (r[0] == "Estados Unidos Mexicanos" or fold(r[0]) in _BY_NAME)), None)
        unit = next((r[0] for r in rows if r and isinstance(r[0], str) and r[0].startswith("(")), "")
        factor = 1_000_000 if "millones" in unit else 1_000
        figures = {}
        for row in rows:
            if row and row[0] in ("Población en situación de pobreza", "Población en situación de pobreza extrema") and len(row) >= 10:
                key = "poverty" if row[0].endswith("pobreza") else "extreme"
                figures[f"{key}_people"] = round(row[5] * factor)  # 2024 people: the 5th value after the label
                figures[f"{key}_pct"] = round(row[10], 2)  # 2024 percent: the 5th percentage
        if not place or len(figures) != 4:
            continue
        if place == "Estados Unidos Mexicanos":
            national = figures
        else:
            states[_BY_NAME[fold(place)]] = figures
    if national is None or len(states) != 32:
        raise ValueError(f"Poverty workbook not understood: {len(states)} states and {'a' if national else 'no'} national sheet")
    return {"national": national, "states": states}


# ---------- Together ----------

def _ranked(states: dict, key: str, out: str) -> None:
    order = sorted(states, key=lambda c: -states[c][key])
    for rank, code in enumerate(order, start=1):
        states[code][out] = rank


def economy_records(wage: dict, border_codes: set[str], enoe: dict, poverty: dict, retrieved_at: str, income: dict | None = None) -> dict:
    employment_states = {code: dict(row) for code, row in enoe["states"].items()}
    income_states = {code: dict(row) for code, row in (income or {}).items()}
    if income_states:
        _ranked(income_states, "up_to_1", "rank_by_up_to_1")
    _ranked(employment_states, "unemployment", "rank_by_unemployment")
    _ranked(employment_states, "informality", "rank_by_informality")
    poverty_states = {code: dict(row) for code, row in poverty["states"].items()}
    _ranked(poverty_states, "poverty_pct", "rank_by_poverty")
    cite = lambda spec: {"source": spec.get("source", "official"), "source_name": spec["source_name"], "url": spec["url"], "published_at": spec["published_at"], "retrieved_at": retrieved_at}
    return {
        "minimum_wage": {
            "year": MINIMUM_WAGE["year"],
            "general": wage["general"],
            "border": wage["border"],
            "effective_from": wage["effective_from"],
            "unit": "pesos diarios",
            "border_municipalities": sorted(border_codes),
            "citation": cite(MINIMUM_WAGE | {"source": "conasami"}),
        },
        "employment": {"period": ENOE["period"], "next_release": ENOE["next_release"], "national": enoe["national"], "states": employment_states, "citation": cite(ENOE | {"source": "inegi_enoe"})},
        "poverty": {"year": POVERTY["year"], "national": poverty["national"], "states": poverty_states, "citation": cite(POVERTY | {"source": "inegi_pm"})},
        "income": {
            "period": ENOE["period"],
            "states": income_states,
            "citation": cite({"source": "inegi_enoe", "source_name": "INEGI, ENOE, segundo trimestre de 2026, comunicados por entidad federativa (cuadro de nivel de ingresos)", "url": STATE_BULLETIN["01"], "published_at": ENOE["published_at"]}),
            "bulletins": STATE_BULLETIN,
        },
    }
