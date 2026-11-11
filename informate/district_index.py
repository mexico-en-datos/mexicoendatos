"""Which municipalities each federal district covers, from the map itself.

INE draws the 300 districts over electoral sections, not over municipalities, and publishes
the correspondence only inside its seccional tables. Here it is derived by overlaying INE's
district polygons on INEGI's municipal polygons: for every pair that overlaps, the share of
the municipality's area that lies inside the district. The two maps draw coasts and borders
slightly differently, so the share is taken over the part of the municipality that the
district map covers at all, not over its whole INEGI area. A municipality is "whole" in a
district when at least WHOLE of that area is there; slivers below MINIMUM (drawing noise
where the two maps disagree) are dropped. Areas are measured in an equal-area projection.
"""
import numpy as np
import shapely
from pyproj import Transformer
from shapely.geometry import shape
from shapely.strtree import STRtree

EQUAL_AREA = "EPSG:6372"  # Mexico ITRF2008 / LCC, in metres
WHOLE = 0.98
MINIMUM = 0.01
METHOD = (
    "Correspondencia calculada por superficie: se superponen los polígonos de los distritos del INE y de los municipios del "
    "INEGI y se mide qué parte de cada municipio cae en cada distrito, sobre la superficie que ambos mapas cubren. "
    "«Completo» es al menos el 98 %; se omiten los pedazos menores al 1 %, que son diferencias de trazo entre los dos mapas."
)

_project = Transformer.from_crs("EPSG:4326", EQUAL_AREA, always_xy=True).transform


def _to_metres(coords):
    xs, ys = _project(coords[:, 0], coords[:, 1])
    return np.column_stack([xs, ys])


def _planar(feature: dict):
    geometry = shape(feature["geometry"])
    if not geometry.is_valid:
        geometry = geometry.buffer(0)
    return shapely.transform(geometry, _to_metres)


def overlay(districts: list[dict], municipalities: list[dict], whole: float = WHOLE, minimum: float = MINIMUM) -> dict:
    """{"districts": {"20-1": [{"code", "name", "share", "whole"}, ...]}, "municipalities": {"20067": [{"district": "20-1", "share"}]}}.

    `districts` are GeoJSON features with properties ent/dist; `municipalities` with
    cvegeo/cve_ent/nomgeo (as geo.slim_features gives them). Lists are ordered by the area
    of the overlap, largest first. Only pairs within the same state are compared.
    """
    by_state: dict[str, list[tuple[dict, object]]] = {}
    for muni in municipalities:
        by_state.setdefault(muni["properties"]["cve_ent"], []).append((muni, _planar(muni)))
    planar_districts = [(district, _planar(district)) for district in sorted(districts, key=lambda d: (d["properties"]["ent"], d["properties"]["dist"]))]
    # The land the district map covers in each state: the base every share is measured against.
    covered_by_state = {}
    for district, geometry in planar_districts:
        covered_by_state.setdefault(district["properties"]["ent"], []).append(geometry)
    covered_by_state = {state: shapely.union_all(geometries) for state, geometries in covered_by_state.items()}
    base_area: dict[str, float] = {}
    out_districts: dict[str, list[dict]] = {}
    out_munis: dict[str, list[dict]] = {}
    for district, shape_d in planar_districts:
        state = district["properties"]["ent"]
        key = f"{state}-{district['properties']['dist']}"
        munis = by_state.get(state, [])
        tree = STRtree([geometry for _, geometry in munis])
        rows = []
        for index in tree.query(shape_d):
            muni, geometry = munis[index]
            code = muni["properties"]["cvegeo"]
            if code not in base_area:
                base_area[code] = geometry.intersection(covered_by_state[state]).area
            overlap = shape_d.intersection(geometry).area
            share = min(overlap / base_area[code], 1.0) if base_area[code] else 0.0
            if share < minimum:
                continue
            share = round(share, 4)
            rows.append((overlap, {"code": code, "name": muni["properties"]["nomgeo"], "share": share, "whole": round(share, 2) >= whole}))
        rows.sort(key=lambda item: -item[0])
        out_districts[key] = [row for _, row in rows]
        for _, row in rows:
            out_munis.setdefault(row["code"], []).append({"district": key, "share": row["share"]})
    for entries in out_munis.values():
        entries.sort(key=lambda item: -item["share"])
    return {"districts": out_districts, "municipalities": out_munis}
