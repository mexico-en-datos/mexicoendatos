"""The 300 federal electoral districts, from INE's Marco Geográfico Seccional.

Fixture: Aguascalientes' three districts cut from the real DISTRITO_FEDERAL layer
(INE, archive dated 2025-01-31), with its projection file.
"""
from pathlib import Path

import pytest

from informate.districts import ARCHIVE_URL, read_districts, source_metadata
from informate.geo import build_topology

FIXTURE = Path(__file__).parent / "fixtures" / "ine_distritos_aguascalientes.shp"


@pytest.fixture(scope="module")
def districts():
    return read_districts(FIXTURE)


def test_each_district_is_a_feature_with_state_and_number(districts):
    assert sorted((f["properties"]["ent"], f["properties"]["dist"]) for f in districts) == [("01", 1), ("01", 2), ("01", 3)]
    assert all(f["geometry"]["type"] in ("Polygon", "MultiPolygon") for f in districts)


def test_coordinates_are_turned_into_longitude_and_latitude(districts):
    def points(geometry):
        polygons = geometry["coordinates"] if geometry["type"] == "MultiPolygon" else [geometry["coordinates"]]
        return [p for polygon in polygons for ring in polygon for p in ring]

    lons = [p[0] for f in districts for p in points(f["geometry"])]
    lats = [p[1] for f in districts for p in points(f["geometry"])]
    assert -102.9 < min(lons) and max(lons) < -101.8  # Aguascalientes
    assert 21.6 < min(lats) and max(lats) < 22.5


def test_districts_build_into_their_own_topology(districts):
    topology = build_topology(districts, tolerance=0.003, object_name="distritos")
    geometries = topology["objects"]["distritos"]["geometries"]
    assert sorted(g["properties"]["dist"] for g in geometries) == [1, 2, 3]
    assert all(g["arcs"] for g in geometries)


def test_source_metadata_names_ine_and_dates_the_archive():
    meta = source_metadata(count=300, archive_modified="Fri, 31 Jan 2025 23:24:32 GMT", retrieved_at="2026-11-07T01:30:00Z")
    assert meta["publisher"] == "INE"
    assert meta["url"] == ARCHIVE_URL
    assert meta["published_at"] == "2025-01-31"
    assert meta["retrieved_at"] == "2026-11-07T01:30:00Z"
    assert meta["district_count"] == 300
