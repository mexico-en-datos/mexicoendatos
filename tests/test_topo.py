"""Reading the map back from its TopoJSON, so tools can place points without INEGI's raw files."""
import json
from pathlib import Path

from shapely.geometry import Point, shape

from informate.topo import features

TOPO = json.loads((Path(__file__).parent.parent / "web" / "data" / "municipios.topojson").read_text(encoding="utf-8"))


def test_every_municipality_comes_back_as_a_feature_with_its_codes():
    feats = features(TOPO, "municipios")
    assert len(feats) == 2478
    first = feats[0]
    assert first["type"] == "Feature" and first["properties"]["cvegeo"] == "01001" and first["properties"]["cve_ent"] == "01"
    assert first["geometry"]["type"] in ("Polygon", "MultiPolygon")


def test_decoded_shapes_contain_their_own_capital_cities():
    by_code = {f["properties"]["cvegeo"]: shape(f["geometry"]) for f in features(TOPO, "municipios")}
    assert by_code["14039"].contains(Point(-103.3496, 20.6767))  # Guadalajara
    assert by_code["09015"].contains(Point(-99.1332, 19.4326))  # Cuauhtémoc, Ciudad de México
    assert not by_code["14039"].contains(Point(-99.1332, 19.4326))
