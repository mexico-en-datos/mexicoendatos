"""Mexico's 32 federal entities, keyed by INEGI's 2-digit code (cve_ent).

Names are INEGI's own, as returned by
https://gaia.inegi.org.mx/wscatgeo/v2/mgee/ (checked 2026-11-06).
"""
from .text import fold

STATES = {
    "01": "Aguascalientes",
    "02": "Baja California",
    "03": "Baja California Sur",
    "04": "Campeche",
    "05": "Coahuila de Zaragoza",
    "06": "Colima",
    "07": "Chiapas",
    "08": "Chihuahua",
    "09": "Ciudad de México",
    "10": "Durango",
    "11": "Guanajuato",
    "12": "Guerrero",
    "13": "Hidalgo",
    "14": "Jalisco",
    "15": "México",
    "16": "Michoacán de Ocampo",
    "17": "Morelos",
    "18": "Nayarit",
    "19": "Nuevo León",
    "20": "Oaxaca",
    "21": "Puebla",
    "22": "Querétaro",
    "23": "Quintana Roo",
    "24": "San Luis Potosí",
    "25": "Sinaloa",
    "26": "Sonora",
    "27": "Tabasco",
    "28": "Tamaulipas",
    "29": "Tlaxcala",
    "30": "Veracruz de Ignacio de la Llave",
    "31": "Yucatán",
    "32": "Zacatecas",
}

# Spellings other sources use for the same entity.
_ALIASES = {
    "coahuila": "05",
    "michoacan": "16",
    "veracruz": "30",
    "distrito federal": "09",
}

_BY_NAME = {fold(name): code for code, name in STATES.items()} | _ALIASES


def state_code(name: str) -> str:
    """INEGI code for a state name in any known spelling. KeyError if unknown."""
    key = fold(name)
    if key in _BY_NAME:
        return _BY_NAME[key]
    if key.startswith("estado de "):  # Wikipedia titles: "Estado de Guerrero"
        rest = key.removeprefix("estado de ")
        if rest in _BY_NAME:
            return _BY_NAME[rest]
    raise KeyError(f"Unknown state name: {name!r}")
