"""The countries around Mexico, drawn as context so the map does not float in empty sea.

Source: Natural Earth, "Admin 0 – Countries" at 1:50m, a public-domain dataset. Only the
neighbours that fall inside the map's frame are kept, and each is cut to that frame, so
the file stays small (the United States alone would otherwise bring Alaska and Hawaii).
"""
from shapely.geometry import box, mapping, shape

ARCHIVE_URL = "https://naciscdn.org/naturalearth/50m/cultural/ne_50m_admin_0_countries.zip"
PAGE_URL = "https://www.naturalearthdata.com/downloads/50m-cultural-vectors/"
SOURCE_NAME = "Natural Earth, Admin 0 – Countries, escala 1:50 000 000 (dominio público)"
LAYER = "ne_50m_admin_0_countries"
OBJECT_NAME = "vecinos"
# Country codes (ADM0_A3) and the Spanish names shown on the map.
NEIGHBOURS = {"USA": "Estados Unidos", "GTM": "Guatemala", "BLZ": "Belice", "HND": "Honduras", "SLV": "El Salvador", "CUB": "Cuba", "NIC": "Nicaragua"}
# West, south, east, north: a little more than the map shows, so cut edges stay off screen.
FRAME = (-126.0, 8.0, -76.0, 42.0)


def select_neighbours(features: list[dict], frame: tuple = FRAME, codes: dict = NEIGHBOURS) -> list[dict]:
    """GeoJSON features of the neighbouring countries, each cut to `frame`, with properties
    {code, name}. `features` carry a 'ADM0_A3' property as Natural Earth does."""
    window = box(*frame)
    kept = []
    for feature in features:
        code = feature["properties"].get("ADM0_A3")
        if code not in codes:
            continue
        geometry = shape(feature["geometry"])
        if not geometry.is_valid:
            geometry = geometry.buffer(0)
        clipped = geometry.intersection(window)
        if clipped.is_empty:
            continue
        kept.append({"type": "Feature", "properties": {"code": code, "name": codes[code]}, "geometry": mapping(clipped)})
    kept.sort(key=lambda f: f["properties"]["code"])
    return kept
