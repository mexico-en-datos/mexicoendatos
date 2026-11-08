"""Senators and federal deputies, from the Sistema de Información Legislativa (SIL).

SIL is run by the Secretaría de Gobernación and compiles its data from public
sources such as the gazettes of Congress. Its roster gives every sitting
legislator a row and a profile page, which we use as that person's citation.
A deputy's district appears only on the profile page.
"""
import html
import re

BASE_URL = "http://sil.gobernacion.gob.mx"
LEGISLATURE = 66
SENATE, DEPUTIES = 2, 1  # SIL's codes for the two chambers


def roster_url(chamber: int) -> str:
    return (
        f"{BASE_URL}/Numeralia/Legisladores/resultadosNumeraliaLegisladores.php"
        f"?SID=&Legislatura={LEGISLATURE}&Camara={chamber}&Estatus=A"
    )


ROSTER_URL = roster_url(SENATE)
DEPUTIES_ROSTER_URL = roster_url(DEPUTIES)
PROFILE_URL = f"{BASE_URL}/Librerias/pp_PerfilLegislador.php"
ENCODING = "iso-8859-1"

_ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S | re.I)
_CELL = re.compile(r"<td[^>]*>(.*?)</td>", re.S | re.I)
_PROFILE = re.compile(r"pp_PerfilLegislador\.php\?SID=&Referencia=(\d+)")


def _cell_text(cell: str) -> str:
    no_tags = re.sub(r"<[^>]+>", " ", cell)
    return re.sub(r"\s+", " ", html.unescape(no_tags)).strip()


def _iso_date(ddmmyyyy: str) -> str:
    day, month, year = ddmmyyyy.split("/")
    return f"{year}-{month}-{day}"


def profile_url(sil_id: str) -> str:
    return f"{PROFILE_URL}?SID=&Referencia={sil_id}"


def parse_roster(page: str) -> list[dict]:
    """Rows of a SIL roster page, one dict per legislator. ValueError if none found."""
    senators = []
    for row in _ROW.findall(page):
        profile = _PROFILE.search(row)
        cells = _CELL.findall(row)
        if not profile or len(cells) < 10:
            continue
        # Columns: No., photo, name, role, party, election type, state,
        # sworn in, seat status, substitute.
        text = [_cell_text(c) for c in cells]
        senators.append(
            {
                "name": text[2],
                "role": text[3],
                "party_raw": text[4],
                "election_type": text[5],
                "state_raw": text[6],
                "sworn_in": _iso_date(text[7]),
                "seat_status": text[8],
                "substitute": text[9],
                "sil_id": profile.group(1),
                "profile_url": profile_url(profile.group(1)),
            }
        )
    if not senators:
        raise ValueError("No legislator rows found: SIL page layout changed or request was blocked")
    return senators


_DISTRICT = re.compile(r"Distrito:\s*(\d+)(?:\s*\(([^)]*)\))?")
_CIRCUNSCRIPTION = re.compile(r"Circunscripción:\s*(\w+)")
_PROFILE_FIELDS = {
    "Región de elección:": "region",
    "Correo electrónico:": "email",
    "Teléfono:": "phone",
    "Ubicación:": "office",
    "Último grado de estudios:": "degree",
    "Preparación académica:": "studies",
}


def _profile_fields(profile_page: str) -> dict:
    """The labelled rows of a profile page ("Correo electrónico:" -> value), by our field names."""
    fields = {}
    for row in _ROW.findall(profile_page):
        cells = [_cell_text(c) for c in _CELL.findall(row)]
        cells = [c for c in cells if c]
        if len(cells) == 2 and cells[0] in _PROFILE_FIELDS:
            fields[_PROFILE_FIELDS[cells[0]]] = cells[1]
    return fields


def parse_profile(profile_page: str) -> dict:
    """What a legislator's profile page says: where they were elected, and how to reach the office.

    District deputies: "Entidad: Coahuila Distrito: 4 (Saltillo)". List deputies: "Entidad:
    Campeche Circunscripción: Tercera". Senators and some list deputies: "Entidad: N/A".
    """
    fields = _profile_fields(profile_page)
    if "region" not in fields:  # not a profile at all: e.g. the error page SIL serves when it refuses a request
        raise ValueError("Not a SIL profile page: no 'Región de elección' field")
    district = _DISTRICT.search(fields["region"])
    circunscription = _CIRCUNSCRIPTION.search(fields["region"])
    schooling = ", ".join(part for part in (fields.get("degree"), fields.get("studies")) if part)
    return {
        "district": int(district.group(1)) if district else None,
        "district_seat": (district.group(2) or None) if district else None,
        "circunscription": circunscription.group(1) if circunscription else None,
        "email": fields.get("email"),
        "phone": fields.get("phone"),
        "office": fields.get("office"),
        "education": schooling or None,
    }


def parse_election_region(profile_page: str) -> dict:
    """Only the where-elected part of `parse_profile`."""
    profile = parse_profile(profile_page)
    return {key: profile[key] for key in ("district", "district_seat", "circunscription")}


def fetch_roster(session, url: str = ROSTER_URL) -> str:
    """Download a roster page. SIL serves ISO-8859-1."""
    response = session.get(url, timeout=90)
    response.raise_for_status()
    return response.content.decode(ENCODING)


def fetch_profile(session, sil_id: str) -> str:
    response = session.get(profile_url(sil_id), timeout=60)
    response.raise_for_status()
    return response.content.decode(ENCODING)
