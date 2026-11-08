#!/usr/bin/env python3
"""Tool 5: homicide victims per state and municipality, from the SESNSP's open data.

Source: Secretariado Ejecutivo del Sistema Nacional de Seguridad Pública, Registro
Nacional de Incidencia Delictiva, víctimas del fuero común (page dated 2026-10-16).
The SESNSP publishes a new cut every month; the share ids and the months covered
live in `informate/crime.py` and are updated by hand when a new cut is out.

    python tools/fetch_crime.py            # reuses the downloaded zips if present
    python tools/fetch_crime.py --refresh  # downloads them again

Writes web/data/crime.json.
"""
import argparse
import io
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from informate import crime  # noqa: E402
from informate.refresh import new_session, utc_now, write_json  # noqa: E402


def download(session, key: str, cache: Path, refresh: bool) -> str:
    """The CSV inside the zip the SESNSP serves for `key`, cached on disk."""
    path = cache / f"{key}.zip"
    if refresh or not path.exists():
        url = crime.DOWNLOAD.format(share=crime.FILES[key]["share"])
        print(f"Descargando {crime.FILES[key]['label']} …")
        response = session.get(url, timeout=300)
        response.raise_for_status()
        if not response.content.startswith(b"PK"):
            raise RuntimeError(f"{url} did not return a zip file (got {response.headers.get('content-type')})")
        cache.mkdir(parents=True, exist_ok=True)
        path.write_bytes(response.content)
    with zipfile.ZipFile(io.BytesIO(path.read_bytes())) as archive:
        names = [n for n in archive.namelist() if n.lower().endswith(".csv")]
        if not names:
            raise RuntimeError(f"{path}: no CSV inside")
        return crime.decode(archive.read(names[0]))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--refresh", action="store_true", help="download the files again")
    args = parser.parse_args()

    session = new_session()
    cache = ROOT / ".cache" / "sesnsp"
    texts = {key: download(session, key, cache, args.refresh) for key in crime.FILES}
    retrieved_at = utc_now()
    map_source = json.loads((ROOT / "web" / "data" / "map_source.json").read_text(encoding="utf-8"))
    population = {s["cve_ent"]: s["population"] for s in map_source["states"]}
    data = crime.crime_records(
        crime.victims_by_place(texts["state_current"], "state", crime.YEAR, crime.MONTHS),
        crime.victims_by_place(texts["state_history"], "state", crime.YEAR - 1, 12),
        crime.victims_by_place(texts["municipal_current"], "municipality", crime.YEAR, crime.MONTHS),
        population,
        year=crime.YEAR,
        months=crime.MONTHS,
        retrieved_at=retrieved_at,
    )
    out = ROOT / "web" / "data" / "crime.json"
    write_json(out, data)
    n = data["national"]
    print(f"Homicidios dolosos (víctimas), {data['period']}: {n['homicides']:,}; feminicidios: {n['feminicides']:,}; en {data['previous_year']}: {n['previous_year_homicides']:,}.")
    print(f"{len(data['states'])} entidades y {len(data['municipalities'])} municipios con dato. Fuente: {crime.PAGE_URL} (página del {crime.PAGE_DATE}, consultada {retrieved_at})")
    print(f"Escrito: {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
