"""Read GeoJSON features back out of a TopoJSON file.

The published map (web/data/municipios.topojson) is the only copy of the
boundaries that travels with the repository; tools that need to place points in
municipalities (fuel stations) read it with this when INEGI's raw downloads are
not at hand. Simplified borders, so a point within a few hundred metres of a
boundary may land on the wrong side; stations that close to a border are rare.
"""


def _decode_arcs(topology: dict) -> list[list[list[float]]]:
    """Arcs as absolute coordinates: undo the delta encoding and the quantization transform."""
    transform = topology.get("transform")
    arcs = []
    for arc in topology["arcs"]:
        points, x, y = [], 0, 0
        for dx, dy in arc:
            if transform:
                x += dx
                y += dy
                points.append([x * transform["scale"][0] + transform["translate"][0], y * transform["scale"][1] + transform["translate"][1]])
            else:
                points.append([dx, dy])
        arcs.append(points)
    return arcs


def _ring(arcs: list, indices: list[int]) -> list[list[float]]:
    coordinates = []
    for index in indices:
        arc = arcs[index] if index >= 0 else list(reversed(arcs[~index]))
        if coordinates and coordinates[-1] == arc[0]:
            coordinates.extend(arc[1:])
        else:
            coordinates.extend(arc)
    return coordinates


def _geometry(arcs: list, geometry: dict) -> dict:
    kind = geometry["type"]
    if kind == "Polygon":
        return {"type": "Polygon", "coordinates": [_ring(arcs, ring) for ring in geometry["arcs"]]}
    if kind == "MultiPolygon":
        return {"type": "MultiPolygon", "coordinates": [[_ring(arcs, ring) for ring in polygon] for polygon in geometry["arcs"]]}
    raise ValueError(f"Unsupported TopoJSON geometry: {kind}")


def features(topology: dict, object_name: str) -> list[dict]:
    """The GeoJSON features of one object of a TopoJSON topology, properties included."""
    arcs = _decode_arcs(topology)
    return [
        {"type": "Feature", "properties": dict(geometry.get("properties", {})), "geometry": _geometry(arcs, geometry)}
        for geometry in topology["objects"][object_name]["geometries"]
    ]
