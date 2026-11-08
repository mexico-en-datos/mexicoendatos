"""Term dates that the sources do not list per person but that follow from a rule."""

# Article 56 of the Constitution, read in the federal legal archive (Orden Jurídico
# Nacional, Secretaría de Gobernación). `published_at` is the "última reforma" date
# printed on that copy; `checked_at` is the day a person last read it there.
SENATE_TERM_RULE = {
    "text": (
        "El Senado se renueva en su totalidad cada seis años (artículo 56 de la Constitución). "
        "Las senadoras y los senadores de la LXVI Legislatura concluyen el 31 de agosto de 2030."
    ),
    "source_name": (
        "Constitución Política de los Estados Unidos Mexicanos, artículo 56. "
        "Orden Jurídico Nacional, Secretaría de Gobernación"
    ),
    "url": "http://www.ordenjuridico.gob.mx/Constitucion/cn16.pdf",
    "published_at": "2024-11-15",
    "checked_at": "2026-11-06",
}

# Article 51, same copy of the Constitution.
DEPUTIES_TERM_RULE = {
    "text": (
        "La Cámara de Diputados se elige en su totalidad cada tres años (artículo 51 de la Constitución). "
        "Las diputadas y los diputados de la LXVI Legislatura concluyen el 31 de agosto de 2027."
    ),
    "source_name": (
        "Constitución Política de los Estados Unidos Mexicanos, artículo 51. "
        "Orden Jurídico Nacional, Secretaría de Gobernación"
    ),
    "url": SENATE_TERM_RULE["url"],
    "published_at": SENATE_TERM_RULE["published_at"],
    "checked_at": "2026-11-06",
}

# The LXVI Legislature opened a six-year Senate term on 1 September 2024.
_ANCHOR_LEGISLATURE = 66
_ANCHOR_YEAR = 2024
_YEARS_PER_LEGISLATURE = 3
_SENATE_TERM_YEARS = 6


def senate_term(legislature: int) -> tuple[str, str]:
    """First and last day of the six-year Senate term that includes `legislature`.

    A Senate term spans two legislatures and begins with the even-numbered one.
    """
    opening = legislature if legislature % 2 == 0 else legislature - 1
    start_year = _ANCHOR_YEAR + _YEARS_PER_LEGISLATURE * (opening - _ANCHOR_LEGISLATURE)
    return f"{start_year}-09-01", f"{start_year + _SENATE_TERM_YEARS}-08-31"


def deputies_term(legislature: int) -> tuple[str, str]:
    """First and last day of a legislature, which is a deputy's whole term."""
    start_year = _ANCHOR_YEAR + _YEARS_PER_LEGISLATURE * (legislature - _ANCHOR_LEGISLATURE)
    return f"{start_year}-09-01", f"{start_year + _YEARS_PER_LEGISLATURE}-08-31"
