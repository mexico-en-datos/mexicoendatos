"""Mexico's main cities, from Spanish Wikipedia, placed in their municipalities.

The annex of the most populous cities lists every city of 100,000 people or
more with its state and population (Encuesta Intercensal 2025 in the revision
read). It is a secondary source, cited to the revision. Each city is matched
to INEGI's municipality by name within its state, with a short table for the
cities whose municipality is called something else (Cancún is in Benito
Juárez), so the map can place it at the municipality.
"""
import re

from .mayors import _REF, _plain, _row_cells
from .text import fold
from . import wikipedia

PAGE_TITLE = "Anexo:Ciudades más pobladas de México"
# ISO 3166-2:MX codes used by the page's flag templates -> INEGI state codes.
ISO = {
    "AGU": "01", "BCN": "02", "BCS": "03", "CAM": "04", "COA": "05", "COL": "06", "CHP": "07", "CHH": "08", "CMX": "09", "DIF": "09",
    "DUR": "10", "GUA": "11", "GRO": "12", "HID": "13", "JAL": "14", "MEX": "15", "MIC": "16", "MOR": "17", "NAY": "18", "NLE": "19",
    "OAX": "20", "PUE": "21", "QUE": "22", "ROO": "23", "SLP": "24", "SIN": "25", "SON": "26", "TAB": "27", "TAM": "28", "TLA": "29",
    "VER": "30", "YUC": "31", "ZAC": "32",
}
# City -> municipality, where the names differ beyond the usual prefixes and suffixes.
MUNICIPALITY_OF = {
    "cancun": "benito juarez", "villahermosa": "centro", "playa del carmen": "solidaridad", "los mochis": "ahome",
    "ciudad obregon": "cajeme", "ciudad del carmen": "carmen", "chetumal": "othon p. blanco", "ciudad victoria": "victoria",
    "san jose del cabo": "los cabos", "cabo san lucas": "los cabos", "ciudad lopez mateos": "atizapan de zaragoza",
    "los reyes acaquilpan": "la paz", "tlaquepaque": "san pedro tlaquepaque", "san francisco de campeche": "campeche",
    "victoria de durango": "durango", "culiacan rosales": "culiacan", "xalapa-enriquez": "xalapa", "puebla de zaragoza": "puebla",
    "santiago de queretaro": "queretaro", "toluca de lerdo": "toluca", "ciudad nezahualcoyotl": "nezahualcoyotl",
    "heroica matamoros": "matamoros", "ciudad acuna": "acuna", "tapachula de cordova y ordonez": "tapachula",
    "zamora de hidalgo": "zamora", "san cristobal de las casas": "san cristobal de las casas", "tlaxcala de xicohtencatl": "tlaxcala",
    "chalco de diaz covarrubias": "chalco", "texcoco de mora": "texcoco", "ojo de agua": "tecamac", "san pablo de las salinas": "tultitlan",
    "buenavista": "tultitlan", "ciudad santa catarina": "santa catarina", "ciudad benito juarez": "juarez", "ciudad general escobedo": "general escobedo",
    "ciudad apodaca": "apodaca", "san nicolas de los garza": "san nicolas de los garza", "ciudad guadalupe": "guadalupe",
    "ciudad madero": "ciudad madero", "fraccionamiento real palmas": "general zuazua", "tulancingo": "tulancingo de bravo",
    "poza rica de hidalgo": "poza rica de hidalgo", "jiutepec": "jiutepec", "temixco": "temixco",
    "xico": "valle de chalco solidaridad", "san francisco coacalco": "coacalco de berriozabal", "hacienda santa fe": "tlajomulco de zuniga",
    "miramar": "altamira", "el pueblito": "corregidora", "san bernardino tlaxcalancingo": "san andres cholula", "tepexpan": "acolman",
    "ciudad guzman": "zapotlan el grande", "cholula de rivadavia": "san pedro cholula", "ciudad de villa de alvarez": "villa de alvarez",
}
_STRIP = (r"^ciudad ", r"^heroica ", r"^villa de ", r"^san francisco de ")


def _state_of(cell: str) -> str | None:
    iso = re.search(r"\{\{MEX\|([A-Z]{3})\}\}", cell)
    if iso:
        return ISO.get(iso.group(1))
    if re.search(r"Ciudad de México", cell):
        return "09"
    return None


def parse_cities(wikitext: str) -> list[dict]:
    """Cities in the page's order (by population): name as shown, state code, population, rank."""
    start = wikitext.find("{|")
    table = _REF.sub("", wikitext[start : wikitext.find("\n|}", start)])
    cities = []
    for row in re.split(r"\n\|-[^\n]*", table):
        cells = _row_cells(row)
        if not cells:
            continue
        raw = [content for _, _, content in cells]
        if len(raw) < 5:
            continue
        name = _plain(raw[2])  # columns: rank, code, city, population, state, metropolitan area, region
        population = next((int(m.group(1)) for c in raw[3:5] for m in [re.search(r"formatnum:(\d+)", c)] if m), None)
        state = next((s for s in (_state_of(c) for c in raw[3:6]) if s), None)
        metro = _plain(raw[5]) if len(raw) > 5 else ""
        if name and population and state:
            cities.append({"name": name, "state_code": state, "population": population, "rank": len(cities) + 1, "metro": metro or None})
    if len(cities) < 50:
        raise ValueError(f"Expected the table of cities over 100,000 people; found {len(cities)} rows")
    return cities


def _split_hint(name: str) -> tuple[str, str | None]:
    """'Veracruz (Municipio de Boca del Río)' -> ('Veracruz', 'Boca del Río')."""
    match = re.match(r"^(.*?)\s*\((?:[Mm]unicipio de )?([^)]+)\)$", name)
    return (match.group(1).strip(), match.group(2).strip()) if match else (name, None)


def _candidates(name: str) -> list[str]:
    name, hint = _split_hint(name)
    key = fold(name)
    out = [fold(hint)] if hint else []
    out.append(MUNICIPALITY_OF.get(key, key))
    stripped = key
    for pattern in _STRIP:
        stripped = re.sub(pattern, "", stripped)
    out.append(stripped)
    for base in (key, stripped):  # "León de los Aldama" -> "León"; "Tulancingo de Bravo" stays a candidate too
        if " de " in base:
            out.append(base.split(" de ")[0])
    return list(dict.fromkeys(out))


def city_records(cities: list[dict], catalog: dict[str, dict[str, str]], revision: dict, retrieved_at: str) -> dict:
    placed = []
    for city in cities:
        by_name = {fold(name): (code, name) for code, name in catalog.get(city["state_code"], {}).items()}
        match = None
        if city["state_code"] != "09":
            for candidate in _candidates(city["name"]):
                match = by_name.get(candidate)
                if not match:  # "Tlalnepantla" -> the one municipality called "Tlalnepantla de …"
                    starts = [v for k, v in by_name.items() if k.startswith(candidate + " de ")]
                    match = starts[0] if len(starts) == 1 else None
                if match:
                    break
        shown, _ = _split_hint(city["name"])
        placed.append({**city, "name": shown, "municipality_code": match[0] if match else None, "municipality": match[1] if match else None})
    return {
        "population_source": "Encuesta Intercensal 2025 (INEGI), según la página",
        "cities": placed,
        "citation": {
            "source": "wikipedia_cities",
            "source_name": f"Wikipedia en español, «{PAGE_TITLE}»",
            "url": wikipedia.page_permalink(revision["id"], title=PAGE_TITLE),
            "published_at": revision["timestamp"],
            "retrieved_at": retrieved_at,
        },
    }
