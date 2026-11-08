#!/usr/bin/env python3
"""Tool 4: the GDP of each state, from INEGI's yearly PIBE press release.

Source: INEGI, Producto Interno Bruto por Entidad Federativa (PIBE), cifras
preliminares, comunicado de prensa 156/25 of 2025-12-05, cuadro 1. The figures
are yearly, so this runs when INEGI publishes the next release (each December),
not every day.

    python tools/fetch_gdp.py            # reuses the downloaded release if present
    python tools/fetch_gdp.py --refresh  # downloads it again

Writes web/data/gdp.json.
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from informate import gdp  # noqa: E402
from informate.refresh import new_session, utc_now, write_json  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--refresh", action="store_true", help="download the release again")
    args = parser.parse_args()

    cache = ROOT / ".cache" / f"inegi_pibe{gdp.RELEASE['year']}.pdf"
    if args.refresh or not cache.exists():
        print(f"Descargando {gdp.RELEASE['url']} …")
        response = new_session().get(gdp.RELEASE["url"], timeout=120)
        response.raise_for_status()
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_bytes(response.content)
    retrieved_at = utc_now()
    data = gdp.gdp_records(gdp.parse_pibe_table(gdp.extract_table_text(cache)), retrieved_at)
    out = ROOT / "web" / "data" / "gdp.json"
    write_json(out, data)
    total = data["national"]["gdp"]
    print(f"PIB {data['year']}: {total:,} {data['unit']} en total; {len(data['states'])} entidades.")
    print(f"Fuente: {data['citation']['url']} (publicado {data['citation']['published_at']}, consultado {retrieved_at})")
    print(f"Escrito: {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
