"""Small text helpers shared by the parsers."""
import re
import unicodedata


def fold(text: str) -> str:
    """Lowercase, strip accents and collapse whitespace, for tolerant lookups."""
    decomposed = unicodedata.normalize("NFKD", text)
    no_accents = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", no_accents).strip().lower()


_MONTHS = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}
SPANISH_DATE = re.compile(r"(\d{1,2})\s*(?:\.?º|°)?\s+de\s+([a-záéíóú]+)\s+de\s+(\d{4})", re.I)


def spanish_date_to_iso(text: str) -> str | None:
    """'1 de octubre de 2022' anywhere in `text` -> '2022-10-01'; None if there is no date."""
    match = SPANISH_DATE.search(text)
    if not match or match.group(2).lower() not in _MONTHS:
        return None
    day, month, year = match.groups()
    return f"{year}-{_MONTHS[month.lower()]:02d}-{int(day):02d}"


_ROMAN = ((1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"), (50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I"))


def roman(number: int) -> str:
    """66 -> 'LXVI', as legislatures are numbered."""
    out = []
    for value, letters in _ROMAN:
        while number >= value:
            out.append(letters)
            number -= value
    return "".join(out)
