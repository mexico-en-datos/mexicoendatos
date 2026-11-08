"""Political parties, one short code each, and the labels each source uses for them."""
import re

from .text import fold

PARTIES = {
    "MORENA": {"name": "Morena"},
    "PAN": {"name": "Partido Acción Nacional"},
    "PRI": {"name": "Partido Revolucionario Institucional"},
    "PVEM": {"name": "Partido Verde Ecologista de México"},
    "PT": {"name": "Partido del Trabajo"},
    "MC": {"name": "Movimiento Ciudadano"},
    "SP": {"name": "Sin partido"},
    # Parties with no code of their own here: local parties, and national ones that hold
    # few posts. Records keep the party's own name alongside this code.
    "OTRO": {"name": "Otro partido"},
}

_ALIASES = {
    "sin partido": "SP",
    "sin grupo": "SP",
    "sg": "SP",
    "independiente": "SP",
    "ind.": "SP",
    "candidaturas independientes de mexico": "SP",
    "candidato independiente en mexico": "SP",
    "candidatos independientes": "SP",
    "interino": "SP",
    "interina": "SP",
    "movimiento regeneracion nacional": "MORENA",
}

_BY_LABEL = (
    {fold(code): code for code in PARTIES}
    | {fold(info["name"]): code for code, info in PARTIES.items()}
    | _ALIASES
)


def party_code(label: str) -> str:
    """Short code for a party label in any known spelling. KeyError if unknown."""
    without_qualifier = re.sub(r"\([^)]*\)", "", label)  # "Morena (partido político)"
    key = fold(without_qualifier)
    if key in _BY_LABEL:
        return _BY_LABEL[key]
    raise KeyError(f"Unknown party label: {label!r}")
