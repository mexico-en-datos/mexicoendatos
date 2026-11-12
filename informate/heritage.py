"""Pueblos Mágicos and World Heritage sites in Mexico, as points on the map.

Pueblos Mágicos are the localities that the Secretaría de Turismo (SECTUR) recognises under
its programme of that name. SECTUR publishes them only as one web article per town, so the
list is read from the Spanish Wikipedia annex "Anexo:Pueblos mágicos": one table per state
with each locality and the day it was named, and a map with its coordinates. Secondary
source, cited to the revision read.

World Heritage sites come from the UNESCO World Heritage Centre's own list, in its Spanish
edition, as the XML it publishes for the whole list: name, category (cultural, natural,
mixed), year of inscription, criteria, the places it covers and their coordinates.
"""
import re
import xml.etree.ElementTree as ET

from .states import state_code
from .text import fold, spanish_date_to_iso

PUEBLOS_TITLE = "Anexo:Pueblos mágicos"
SECTUR_URL = "https://www.gob.mx/sectur/articulos/pueblos-magicos-206528"
UNESCO_XML_URL = "https://whc.unesco.org/es/list/xml/"
UNESCO_LIST_URL = "https://whc.unesco.org/es/list/"
UNESCO_NAME = "UNESCO, Centro del Patrimonio Mundial: Lista del Patrimonio Mundial"
CATEGORY = {"Cultural": "cultural", "Natural": "natural", "Mixed": "mixto", "Mixto": "mixto"}

_SECTION = re.compile(r"^=== *(.+?) *===\s*$", re.M)
# The locality cell, bold, in the forms the page uses: '''[[Name]]''', [[Target|'''Name''']] and '''Name'''.
_ROW_NAMES = (
    re.compile(r"'''\s*\[\[([^\]|]+)(?:\|([^\]]+))?\]\]\s*'''"),
    re.compile(r"\[\[([^\]|]+)\|\s*'''([^'\]]+)'''\s*\]\]"),
    re.compile(r"'''([^'\[\]{}<>]+)'''"),
)
_PLAIN_LINK = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")
_ORDER_DATE = re.compile(r"\{\{\s*orden\s*\|\s*(\d{4}-\d{2}-\d{2})")
_POINT = re.compile(r"\{\{\s*Mapa de localización~\s*\|(.*?)\}\}", re.S)
_TAG = re.compile(r"<[^>]+>")


def _clean_name(text: str) -> str:
    text = _PLAIN_LINK.sub(lambda m: m.group(2) or m.group(1), text)
    text = re.sub(r"'{2,}", "", text)
    text = re.sub(r"\s*\([^)]*\)\s*$", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _key(text: str) -> str:
    """Letters and digits only, folded: 'Cuatro Ciénegas' and 'Cuatrociénegas de Carranza' share a prefix."""
    return re.sub(r"[^a-z0-9]", "", fold(text))


def _lookup(name: str, *maps: dict) -> tuple[float, float] | None:
    """The point for `name`: the same key, else the map label that begins the name (or that
    the name begins), longest match first. Each map in turn, so a state's own map wins."""
    key = _key(name)
    for points in maps:
        if key in points:
            return points[key]
    for points in maps:
        candidates = [k for k in points if len(k) >= 4 and (k in key or key in k)]
        if candidates:
            return points[max(candidates, key=len)]
    # Last resort, within the state's own map only: the label sharing the longest stretch of
    # letters with the name ("Real del Monte" on the table, "Mineral del Monte" on the map).
    if maps:
        scored = sorted(((_common(key, k), k) for k in maps[0]), reverse=True)
        if scored and scored[0][0] >= 6 and (len(scored) == 1 or scored[0][0] > scored[1][0]):
            return maps[0][scored[0][1]]
    return None


def _common(a: str, b: str) -> int:
    """Length of the longest run of characters that `a` and `b` share."""
    best = 0
    for i in range(len(a)):
        for j in range(len(b)):
            n = 0
            while i + n < len(a) and j + n < len(b) and a[i + n] == b[j + n]:
                n += 1
            best = max(best, n)
    return best


def _points(wikitext: str) -> dict[str, tuple[float, float]]:
    """Name key -> (lat, lon) from every map point template in `wikitext`."""
    found = {}
    for match in _POINT.finditer(wikitext):
        parts = [p.strip() for p in match.group(1).split("|")]
        keyed = {k.strip().lower(): v.strip() for k, v in (p.split("=", 1) for p in parts if "=" in p)}
        positional = [p for p in parts[1:] if "=" not in p and p]
        name = _clean_name(keyed.get("label") or (positional[0] if positional else ""))
        try:
            lat, lon = float(keyed["lat"]), float(keyed["long"])
        except (KeyError, ValueError):
            continue
        if name:
            found[_key(name)] = (lat, lon)
    return found


def _row_name(row: str) -> str | None:
    for pattern in _ROW_NAMES:
        match = pattern.search(row)
        if match:
            groups = match.groups()
            return _clean_name(groups[-1] or groups[0])
    return None


def parse_pueblos(wikitext: str) -> tuple[list[dict], list[str]]:
    """One dict per Pueblo Mágico: name, state (code and name), the day it was named (ISO
    date, or just the year when the page gives no day) and coordinates. Also warnings for
    the towns whose coordinates the page's maps do not give."""
    national = _points(wikitext)
    headings = list(_SECTION.finditer(wikitext))
    pueblos, warnings = [], []
    for index, heading in enumerate(headings):
        state_name = _clean_name(heading.group(1))
        try:
            code = state_code(state_name)
        except KeyError:
            continue  # not a state section
        end = headings[index + 1].start() if index + 1 < len(headings) else len(wikitext)
        section = wikitext[heading.end():end]
        local = _points(section)
        for row in re.split(r"\n\|-", section):
            row = row.split("{{Mapa de localización")[0]  # the state's map follows its last row
            if row.lstrip().startswith("!"):
                continue
            name = _row_name(row)
            if not name:
                continue
            dated = _ORDER_DATE.search(row)
            when = dated.group(1) if dated else spanish_date_to_iso(_TAG.sub("", row)) or (re.search(r"\b(19|20)\d{2}\b", _TAG.sub("", row)) or [None])[0]
            point = _lookup(name, local, national)
            if not point:
                warnings.append(f"Pueblos Mágicos: {name} ({state_name}) no tiene coordenadas en la fuente.")
            pueblos.append({"name": name, "state_code": code, "state": state_name, "named_on": when, "lat": point[0] if point else None, "lon": point[1] if point else None})
    if not pueblos:
        raise ValueError("No Pueblos Mágicos tables found on the Wikipedia page")
    pueblos.sort(key=lambda p: (p["state_code"], fold(p["name"])))
    return pueblos, warnings


def parse_unesco(xml_text: str, country: str = "mx") -> list[dict]:
    """The World Heritage sites of one country from the Centre's XML list: id, name,
    category, year inscribed, criteria, the places covered, every point, link and summary."""
    root = ET.fromstring(xml_text)
    sites = []
    for row in root:
        if (row.findtext("iso_code") or "").strip().lower() != country:
            continue
        points = []
        geolocations = row.find("geolocations")
        for poi in (list(geolocations) if geolocations is not None else []):
            try:
                points.append([float(poi.findtext("latitude")), float(poi.findtext("longitude"))])
            except (TypeError, ValueError):
                continue
        category = (row.findtext("category") or "").strip()
        sites.append(
            {
                "id": int(row.findtext("id_number")),
                "name": (row.findtext("site") or "").strip(),
                "category": CATEGORY.get(category, category.lower()),
                "inscribed": int(row.findtext("date_inscribed")) if (row.findtext("date_inscribed") or "").isdigit() else None,
                "criteria": (row.findtext("criteria_txt") or "").strip() or None,
                "location": (row.findtext("location") or "").strip() or None,
                "danger": (row.findtext("danger") or "0").strip() not in ("", "0"),
                "url": (row.findtext("http_url") or "").strip().replace("/en/list/", "/es/list/"),
                "summary": re.sub(r"\s+", " ", _TAG.sub("", row.findtext("short_description") or "")).strip(),
                "points": points,
            }
        )
    if not sites:
        raise ValueError(f"No World Heritage sites with country code {country!r} in the list")
    sites.sort(key=lambda s: (s["inscribed"] or 0, fold(s["name"])))
    return sites
