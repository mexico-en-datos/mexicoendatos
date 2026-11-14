"""Neighbouring countries cut to the map's frame."""
from shapely.geometry import shape

from informate.neighbors import NEIGHBOURS, select_neighbours


def country(code, west, south, east, north):
    return {"type": "Feature", "properties": {"ADM0_A3": code, "NAME": code}, "geometry": {"type": "Polygon", "coordinates": [[[west, south], [east, south], [east, north], [west, north], [west, south]]]}}


FEATURES = [
    country("USA", -170.0, 25.0, -66.0, 71.0),  # spills far beyond the frame on three sides
    country("GTM", -92.3, 13.7, -88.2, 17.8),  # inside
    country("MEX", -118.0, 14.5, -86.7, 32.7),  # Mexico itself is drawn from INEGI, not from here
    country("BRA", -74.0, -34.0, -34.0, 5.0),  # not a neighbour
    country("CUB", -85.0, 19.8, -74.1, 23.3),  # partly outside the frame's east edge
]


def test_only_neighbours_are_kept_each_cut_to_the_frame():
    kept = select_neighbours(FEATURES, frame=(-126.0, 8.0, -76.0, 42.0))
    assert [f["properties"]["code"] for f in kept] == ["CUB", "GTM", "USA"]
    usa = shape(next(f["geometry"] for f in kept if f["properties"]["code"] == "USA"))
    assert usa.bounds == (-126.0, 25.0, -76.0, 42.0)
    cuba = shape(next(f["geometry"] for f in kept if f["properties"]["code"] == "CUB"))
    assert cuba.bounds[2] == -76.0


def test_names_are_the_spanish_ones_shown_on_the_map():
    kept = select_neighbours(FEATURES)
    assert next(f["properties"]["name"] for f in kept if f["properties"]["code"] == "USA") == "Estados Unidos"
    assert NEIGHBOURS["BLZ"] == "Belice"


def test_a_neighbour_entirely_outside_the_frame_is_dropped():
    assert select_neighbours([country("NIC", -87.7, 10.7, -83.1, 15.0)], frame=(-126.0, 20.0, -76.0, 42.0)) == []
