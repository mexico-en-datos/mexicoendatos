"""The municipality map, built from INEGI's Marco Geoestadístico.

INEGI serves the municipal boundaries of each state as GeoJSON through its
"Catálogo Único de Claves Geoestadísticas" web service. We download the 32
states, keep each municipality's identifying fields, and simplify the borders
(shared borders stay shared, so no gaps open between neighbours) into one
TopoJSON file small enough for a web page.
"""
import topojson

from .states import STATES

SERVICE_URL = "https://gaia.inegi.org.mx/wscatgeo/v2"
# Background pages about the data. `checked_at` is the date a person last opened
# the link and confirmed it still shows what the label says; update it by hand.
REFERENCE_LINKS = [
    {
        "label": "Documentación del servicio web del Catálogo Único de Claves Geoestadísticas",
        "url": "https://www.inegi.org.mx/servicios/catalogounico.html",
        "checked_at": "2026-11-06",
    },
    {
        "label": "Marco Geoestadístico, página del producto",
        "url": "https://www.inegi.org.mx/temas/mg/",
        "checked_at": "2026-11-06",
    },
    {
        "label": "Términos de libre uso de la información del INEGI",
        "url": "https://www.inegi.org.mx/inegi/terminos.html",
        "checked_at": "2026-11-06",
    },
]
OBJECT_NAME = "municipios"
DEFAULT_TOLERANCE = 0.003  # degrees; roughly 300 m on the ground


def municipalities_url(cve_ent: str) -> str:
    return f"{SERVICE_URL}/geo/mgem/{cve_ent}"


def _count(value) -> int | None:
    """INEGI serves counts as strings; None when the census has none (municipalities created later)."""
    return None if value in (None, "") else int(value)


def slim_features(responses: list[dict]) -> list[dict]:
    """GeoJSON features from INEGI responses, keeping code, state, name, census population and seat."""
    features = []
    for response in responses:
        for feature in response["features"]:
            props = feature["properties"]
            features.append(
                {
                    "type": "Feature",
                    "properties": {
                        "cvegeo": props["cvegeo"],
                        "cve_ent": props["cve_ent"],
                        "nomgeo": props["nomgeo"],
                        "pob": _count(props.get("pob_total")),
                        "cab": props.get("nom_cab") or None,
                    },
                    "geometry": {
                        "type": feature["geometry"]["type"],
                        "coordinates": feature["geometry"]["coordinates"],
                    },
                }
            )
    return features


def build_topology(features: list[dict], tolerance: float = DEFAULT_TOLERANCE, object_name: str = OBJECT_NAME) -> dict:
    """TopoJSON (as a dict) with one object, simplified to `tolerance` degrees."""
    topology = topojson.Topology(
        {"type": "FeatureCollection", "features": features},
        prequantize=1e6,
        toposimplify=tolerance,
        winding_order="CW_CCW",  # clockwise outer rings, as d3-geo expects
        object_name=object_name,
    ).to_dict()
    _enforce_ring_directions(topology, object_name)
    return topology


def _signed_area(ring: list[int], arcs: list[list[tuple[float, float]]]) -> float:
    """Shoelace area of a ring given as arc references; negative means clockwise."""
    points: list[tuple[float, float]] = []
    for index in ring:
        arc = arcs[index] if index >= 0 else arcs[~index][::-1]
        points.extend(arc if not points else arc[1:])
    return sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(points, points[1:])) / 2


def _enforce_ring_directions(topology: dict, object_name: str = OBJECT_NAME) -> None:
    """Make every outer ring clockwise and every hole counter-clockwise, in place.

    The topojson library gets this wrong for enclaves (a municipality wholly inside
    another): the enclave shares its outline with the hole around it and comes out
    counter-clockwise, which d3-geo draws as "the whole globe except this shape".
    A ring is turned around by reversing its arc list and flipping each reference.
    """
    arcs = []
    for arc in topology["arcs"]:  # quantised arcs are delta-encoded; the sign of an area survives the scaling
        x = y = 0
        points = []
        for step_x, step_y in arc:
            x, y = x + step_x, y + step_y
            points.append((x, y))
        arcs.append(points)

    for geometry in topology["objects"][object_name]["geometries"]:
        polygons = geometry["arcs"] if geometry["type"] == "MultiPolygon" else [geometry["arcs"]]
        for polygon in polygons:
            for position, ring in enumerate(polygon):
                area = _signed_area(ring, arcs)
                is_outer = position == 0
                if (is_outer and area > 0) or (not is_outer and area < 0):
                    polygon[position] = [~index for index in reversed(ring)]


def source_metadata(responses_by_state: dict[str, dict], retrieved_at: str, tolerance: float) -> dict:
    """Where the map came from, in INEGI's own words, plus what we did to it."""
    editions = {r["metadatos"]["Fuente_informacion_vectorial"] for r in responses_by_state.values()}
    if len(editions) != 1:
        raise ValueError(f"INEGI served different editions for different states: {sorted(editions)}")
    edition = editions.pop()
    census = {r["metadatos"]["Fuente_informacion_estadistica"] for r in responses_by_state.values()}
    if len(census) != 1:
        raise ValueError(f"INEGI cited different population sources for different states: {sorted(census)}")

    states, without_population = [], []
    for cve_ent, response in sorted(responses_by_state.items()):
        totals = {"population": 0, "women": 0, "men": 0, "dwellings": 0}
        for feature in response["features"]:
            props = feature["properties"]
            if props.get("pob_total") in (None, ""):  # municipality created after the census
                without_population.append({"cvegeo": props["cvegeo"], "name": props["nomgeo"]})
                continue
            totals["population"] += int(props["pob_total"])
            totals["women"] += _count(props.get("pob_femenina")) or 0
            totals["men"] += _count(props.get("pob_masculina")) or 0
            totals["dwellings"] += _count(props.get("total_viviendas_habitadas")) or 0
        states.append(
            {
                "cve_ent": cve_ent,
                "name": STATES[cve_ent],
                "municipalities": len(response["features"]),
                **totals,
                "url": municipalities_url(cve_ent),
            }
        )
    return {
        "publisher": "INEGI",
        "publisher_name": "Instituto Nacional de Estadística y Geografía",
        "product": "Marco Geoestadístico, áreas geoestadísticas municipales",
        "edition": edition,
        "attribution": f"Fuente: {edition}",
        "service_name": "Servicio web del Catálogo Único de Claves de Áreas Geoestadísticas",
        "service_url": SERVICE_URL,
        "reference_links": REFERENCE_LINKS,
        "retrieved_at": retrieved_at,
        "municipality_count": sum(s["municipalities"] for s in states),
        "population": sum(s["population"] for s in states),
        "women": sum(s["women"] for s in states),
        "men": sum(s["men"] for s in states),
        "dwellings": sum(s["dwellings"] for s in states),
        "population_source": census.pop(),
        "municipalities_without_population": without_population,
        "states": states,
        "simplification_tolerance_degrees": tolerance,
        "processing_note": (
            "Límites simplificados para visualización a partir de los datos del INEGI; "
            "no sustituyen a la cartografía oficial."
        ),
    }
