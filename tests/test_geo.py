"""Building the municipality map from INEGI's Marco Geoestadístico web service.

Fixture: three neighbouring municipalities of Aguascalientes exactly as served by
https://gaia.inegi.org.mx/wscatgeo/v2/geo/mgem/01 on 2026-11-06.
"""
import json
from pathlib import Path

import pytest

from informate.geo import build_topology, municipalities_url, slim_features, source_metadata

FIXTURE = Path(__file__).parent / "fixtures" / "inegi_mgem_01_sample.json"
RETRIEVED = "2026-11-06T19:00:00Z"


@pytest.fixture(scope="module")
def response():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def topology(response):
    return build_topology(slim_features([response]), tolerance=0.003)


def decode_arcs(topology):
    """Undo TopoJSON's delta + quantisation encoding: arcs as lists of [lon, lat]."""
    (kx, ky), (dx, dy) = topology["transform"]["scale"], topology["transform"]["translate"]
    arcs = []
    for arc in topology["arcs"]:
        x = y = 0
        points = []
        for step_x, step_y in arc:
            x, y = x + step_x, y + step_y
            points.append([x * kx + dx, y * ky + dy])
        arcs.append(points)
    return arcs


def rings_of(geometry, arcs):
    polygons = geometry["arcs"] if geometry["type"] == "MultiPolygon" else [geometry["arcs"]]
    for polygon in polygons:
        for ring in polygon:
            points = []
            for index in ring:
                arc = arcs[index] if index >= 0 else arcs[~index][::-1]
                points.extend(arc if not points else arc[1:])
            yield points


def signed_area(ring):
    """Shoelace formula; negative means clockwise (longitude right, latitude up)."""
    return sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(ring, ring[1:])) / 2


def test_url_points_at_inegis_municipal_layer_for_the_state():
    assert municipalities_url("01") == "https://gaia.inegi.org.mx/wscatgeo/v2/geo/mgem/01"


def test_features_keep_only_the_identifying_properties(response):
    features = slim_features([response])
    assert len(features) == 3
    by_code = {f["properties"]["cvegeo"]: f for f in features}
    assert by_code["01009"]["properties"] == {"cvegeo": "01009", "cve_ent": "01", "nomgeo": "Tepezalá", "pob": 22485, "cab": None}  # the sample carries no seat name
    assert "crs" not in by_code["01009"]["geometry"]


def test_topology_has_one_named_shape_per_municipality(topology):
    assert topology["type"] == "Topology"
    geometries = topology["objects"]["municipios"]["geometries"]
    assert sorted(g["properties"]["cvegeo"] for g in geometries) == ["01004", "01007", "01009"]
    assert all(g["properties"]["nomgeo"] for g in geometries)
    assert all(g["arcs"] for g in geometries)


def test_simplification_removes_most_points(response, topology):
    original = sum(
        len(ring) for f in response["features"] for polygon in f["geometry"]["coordinates"] for ring in polygon
    )
    simplified = sum(len(arc) for arc in topology["arcs"])
    assert simplified < original / 4


def test_shared_borders_are_stored_once_and_used_by_both_neighbours(topology):
    def arc_ids(geometry):
        polygons = geometry["arcs"] if geometry["type"] == "MultiPolygon" else [geometry["arcs"]]
        return {i if i >= 0 else ~i for polygon in polygons for ring in polygon for i in ring}

    tepezala, rincon = (
        next(g for g in topology["objects"]["municipios"]["geometries"] if g["properties"]["cvegeo"] == code)
        for code in ("01009", "01007")
    )
    assert arc_ids(tepezala) & arc_ids(rincon)


def test_outer_rings_run_clockwise_as_d3_needs(topology):
    # d3-geo treats a counter-clockwise outer ring as "the whole globe except this
    # shape", which would paint the entire map.
    arcs = decode_arcs(topology)
    for geometry in topology["objects"]["municipios"]["geometries"]:
        outer = max(rings_of(geometry, arcs), key=lambda ring: abs(signed_area(ring)))
        assert signed_area(outer) < 0


def test_shapes_stay_where_inegi_put_them(response, topology):
    arcs = decode_arcs(topology)
    lons = [p[0] for arc in arcs for p in arc]
    lats = [p[1] for arc in arcs for p in arc]
    raw = [p for f in response["features"] for polygon in f["geometry"]["coordinates"] for ring in polygon for p in ring]
    assert min(lons) == pytest.approx(min(p[0] for p in raw), abs=0.01)
    assert max(lats) == pytest.approx(max(p[1] for p in raw), abs=0.01)


def test_source_metadata_quotes_inegis_own_edition_and_counts_what_was_built(response):
    meta = source_metadata({"01": response}, retrieved_at=RETRIEVED, tolerance=0.003)
    assert meta["publisher"] == "INEGI"
    assert meta["edition"] == "INEGI. Marco Geoestadístico, diciembre de 2025"
    assert meta["retrieved_at"] == RETRIEVED
    assert meta["municipality_count"] == 3
    state = meta["states"][0]
    assert {k: state[k] for k in ("cve_ent", "name", "municipalities", "population", "url")} == {
        "cve_ent": "01", "name": "Aguascalientes", "municipalities": 3, "population": 96854,
        "url": "https://gaia.inegi.org.mx/wscatgeo/v2/geo/mgem/01"}
    assert meta["simplification_tolerance_degrees"] == 0.003


def test_source_metadata_refuses_to_mix_editions(response):
    other = json.loads(json.dumps(response))
    other["metadatos"]["Fuente_informacion_vectorial"] = "INEGI. Marco Geoestadístico, diciembre de 2024"
    with pytest.raises(ValueError):
        source_metadata({"01": response, "02": other}, retrieved_at=RETRIEVED, tolerance=0.003)


def test_every_reference_link_about_the_map_carries_the_date_it_was_checked(response):
    meta = source_metadata({"01": response}, retrieved_at=RETRIEVED, tolerance=0.003)
    assert len(meta["reference_links"]) >= 3
    for link in meta["reference_links"]:
        assert link["url"].startswith("https://www.inegi.org.mx/")
        assert link["label"]
        assert len(link["checked_at"]) == 10  # YYYY-MM-DD
    assert not any(key.endswith("_url") and key != "service_url" for key in meta)


def polygons_of(geometry):
    return geometry["arcs"] if geometry["type"] == "MultiPolygon" else [geometry["arcs"]]


def ring_points(ring, arcs):
    points = []
    for index in ring:
        arc = arcs[index] if index >= 0 else arcs[~index][::-1]
        points.extend(arc if not points else arc[1:])
    return points


def test_an_enclave_and_the_municipality_around_it_both_keep_correct_ring_directions():
    # San Francisco Ozolotepec (20148) lies wholly inside San Juan Ozolotepec (20211).
    # The enclave's outline is also the hole in its neighbour; the topojson library
    # left the enclave counter-clockwise, and d3 then drew it as "everything but this".
    response = json.loads((FIXTURE.parent / "inegi_mgem_20_enclave.json").read_text(encoding="utf-8"))
    topology = build_topology(slim_features([response]), tolerance=0.003)
    arcs = decode_arcs(topology)
    geometries = {g["properties"]["cvegeo"]: g for g in topology["objects"]["municipios"]["geometries"]}

    for geometry in geometries.values():
        for outer, *holes in polygons_of(geometry):
            assert signed_area(ring_points(outer, arcs)) < 0, "outer ring must be clockwise"
            for hole in holes:
                assert signed_area(ring_points(hole, arcs)) > 0, "hole must be counter-clockwise"

    surrounding = polygons_of(geometries["20211"])
    assert sum(len(polygon) - 1 for polygon in surrounding) == 1, "the surrounding municipality keeps its hole"


def test_population_is_summed_per_state_and_credited_to_the_census_inegi_names(response):
    meta = source_metadata({"01": response}, retrieved_at=RETRIEVED, tolerance=0.003)
    assert meta["population"] == 96854  # 22,485 + 57,369 + 17,000
    assert meta["population_source"] == "INEGI. Censo de Población y Vivienda, 2020"
    assert meta["municipalities_without_population"] == []


def test_a_municipality_created_after_the_census_has_no_figure_and_is_named(response):
    newer = json.loads(json.dumps(response))
    newer["features"][0]["properties"]["pob_total"] = None  # as INEGI serves municipalities created since 2020
    meta = source_metadata({"01": newer}, retrieved_at=RETRIEVED, tolerance=0.003)
    missing = newer["features"][0]["properties"]
    assert meta["states"][0]["population"] == 96854 - int(response["features"][0]["properties"]["pob_total"])
    assert meta["municipalities_without_population"] == [{"cvegeo": missing["cvegeo"], "name": missing["nomgeo"]}]


# ----- Facts per municipality and per state, from INEGI's own fields -----


def test_features_keep_population_and_seat_of_each_municipality():
    response = json.loads(FIXTURE.read_text(encoding="utf-8"))
    response["features"][0]["properties"]["nom_cab"] = "Tepezalá"  # as INEGI serves it live
    first = slim_features([response])[0]["properties"]
    assert first["cvegeo"] == "01009"
    assert first["pob"] == 22485  # Censo 2020, as an integer
    assert first["cab"] == "Tepezalá"  # the municipal seat


def test_state_facts_include_population_by_sex_and_dwellings():
    response = json.loads(FIXTURE.read_text(encoding="utf-8"))
    meta = source_metadata({"01": response}, retrieved_at="2026-11-07T00:00:00Z", tolerance=0.001)
    state = meta["states"][0]
    assert state["population"] == state["women"] + state["men"]
    assert state["women"] > state["men"] > 0
    assert state["dwellings"] > 0
    assert meta["women"] == state["women"] and meta["dwellings"] == state["dwellings"]
