"""Overlaying districts on municipalities: whole, partial and negligible overlaps, on small
squares of ground near the centre of the country."""
from informate.district_index import METHOD, overlay


def square(west, south, size):
    east, north = west + size, south + size
    return {"type": "Polygon", "coordinates": [[[west, south], [east, south], [east, north], [west, north], [west, south]]]}


def muni(code, name, west, south, size, state="20"):
    return {"type": "Feature", "properties": {"cvegeo": code, "cve_ent": state, "nomgeo": name}, "geometry": square(west, south, size)}


def district(state, number, west, south, size):
    return {"type": "Feature", "properties": {"ent": state, "dist": number}, "geometry": square(west, south, size)}


MUNICIPALITIES = [
    muni("20001", "Entero", -100.0, 20.0, 0.1),  # fully inside district 1
    muni("20002", "Partido", -99.9, 20.0, 0.1),  # its western half in district 1, eastern half in district 2
    muni("20003", "Rozado", -100.0, 20.1495, 0.1),  # only a 0.5 % sliver touches district 1
    muni("20004", "Ajeno", -100.0, 19.5, 0.1),  # nowhere near
    muni("21001", "Otro estado", -100.0, 20.0, 0.1, state="21"),  # same ground, other state: never compared
]
# Three districts cover all the ground that the municipalities of state 20 occupy, except "Ajeno";
# shares are measured over the ground the district map covers, as on the real maps.
DISTRICTS = [district("20", 1, -100.0, 20.0, 0.15), district("20", 2, -99.85, 20.0, 0.15), district("20", 3, -100.0, 20.15, 0.15)]


def test_each_district_lists_its_municipalities_largest_overlap_first():
    result = overlay(DISTRICTS, MUNICIPALITIES)
    first = result["districts"]["20-1"]
    assert [m["code"] for m in first] == ["20001", "20002"]
    assert first[0]["code"] == "20001" and first[0]["name"] == "Entero" and first[0]["share"] >= 0.999 and first[0]["whole"]
    assert 0.48 < first[1]["share"] < 0.52 and first[1]["whole"] is False
    assert [m["code"] for m in result["districts"]["20-2"]] == ["20002"]
    assert [(m["code"], m["whole"]) for m in result["districts"]["20-3"]] == [("20003", True)]


def test_slivers_and_other_states_are_left_out():
    result = overlay(DISTRICTS, MUNICIPALITIES)
    codes = {m["code"] for rows in result["districts"].values() for m in rows}
    assert "20003" not in {m["code"] for m in result["districts"]["20-1"]}  # the sliver in district 1
    assert "20004" not in codes and "21001" not in codes
    # The sliver is kept when the threshold allows it, so the cut is the threshold and not the geometry.
    loose = overlay(DISTRICTS, MUNICIPALITIES, minimum=0.001)
    assert any(m["code"] == "20003" for m in loose["districts"]["20-1"])


def test_municipalities_know_their_districts_biggest_share_first():
    result = overlay(DISTRICTS, MUNICIPALITIES)
    assert [d["district"] for d in result["municipalities"]["20001"]] == ["20-1"] and result["municipalities"]["20001"][0]["share"] >= 0.999
    shared = result["municipalities"]["20002"]
    assert [d["district"] for d in shared] == ["20-1", "20-2"] or [d["district"] for d in shared] == ["20-2", "20-1"]
    assert abs(sum(d["share"] for d in shared) - 1.0) < 0.01


def test_the_method_is_described_for_the_page():
    assert "98 %" in METHOD and "1 %" in METHOD
