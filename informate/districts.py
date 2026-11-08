"""The 300 federal electoral districts, from INE's Marco Geográfico Seccional.

INE publishes its seccional geography as a 7z archive of shapefiles; the
`DISTRITO_FEDERAL` layer has one polygon per district with the state and
district numbers. The coordinates are in a Lambert Conformal Conic projection,
described by the layer's .prj file, and are turned into longitude and latitude
here so the page can draw them with the same projection as the municipalities.
"""
from email.utils import parsedate_to_datetime
from pathlib import Path

import shapefile
from pyproj import CRS, Transformer

ARCHIVE_URL = "https://cartografia.ine.mx/mapoteca/MGS_CCL/SHAPEFILE.7z"
LAYER = "DISTRITO_FEDERAL"
OBJECT_NAME = "distritos"
DISTRICTS = 300


def _to_lon_lat(geometry: dict, transformer: Transformer) -> dict:
    def ring(points):
        xs, ys = transformer.transform([p[0] for p in points], [p[1] for p in points])
        return [[round(x, 9), round(y, 9)] for x, y in zip(xs, ys)]

    if geometry["type"] == "Polygon":
        return {"type": "Polygon", "coordinates": [ring(r) for r in geometry["coordinates"]]}
    return {"type": "MultiPolygon", "coordinates": [[ring(r) for r in polygon] for polygon in geometry["coordinates"]]}


def read_districts(shp_path: Path) -> list[dict]:
    """GeoJSON features, one per district: properties {ent: "01", dist: 1}, coordinates in degrees."""
    shp_path = Path(shp_path)
    crs = CRS.from_wkt(shp_path.with_suffix(".prj").read_text())
    transformer = Transformer.from_crs(crs, "EPSG:4326", always_xy=True)
    reader = shapefile.Reader(str(shp_path))
    features = []
    for record, shape in zip(reader.records(), reader.shapes()):
        features.append(
            {
                "type": "Feature",
                "properties": {"ent": f"{int(record['ENTIDAD']):02d}", "dist": int(record["DISTRITO_F"])},
                "geometry": _to_lon_lat(shape.__geo_interface__, transformer),
            }
        )
    return features


def source_metadata(count: int, archive_modified: str | None, retrieved_at: str) -> dict:
    """Where the districts came from. `archive_modified` is the HTTP Last-Modified header."""
    published = parsedate_to_datetime(archive_modified).date().isoformat() if archive_modified else None
    return {
        "publisher": "INE",
        "publisher_name": "Instituto Nacional Electoral",
        "product": "Marco Geográfico Seccional, distritos electorales federales (distritación de 2023)",
        "layer": LAYER,
        "url": ARCHIVE_URL,
        "published_at": published,
        "retrieved_at": retrieved_at,
        "district_count": count,
        "attribution": "Fuente: INE, Marco Geográfico Seccional",
    }
