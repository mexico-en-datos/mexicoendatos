#!/usr/bin/env python3
"""Tool 7: minimum wage, employment and poverty per state.

Sources: CONASAMI's table of minimum wages (yearly, PDF), INEGI's quarterly
ENOE bulletin (PDF, cuadro 5) and INEGI's multidimensional poverty tabulados
(yearly workbook). The addresses and dates live in `informate/economy.py`;
update them when a new edition is out (ENOE: every quarter; the others: yearly).

    python tools/fetch_economy.py            # reuses downloaded documents if present
    python tools/fetch_economy.py --refresh  # downloads them again

Writes web/data/economy.json.
"""
import argparse
import json
import sys
import time
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from informate import economy  # noqa: E402
from informate.refresh import load_catalog, new_session, utc_now, write_json  # noqa: E402


def fetch(session, url: str, path: Path, refresh: bool) -> Path:
    if refresh or not path.exists():
        print(f"Descargando {url} …")
        response = session.get(url, timeout=180)
        response.raise_for_status()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(response.content)
    return path


def pdf_text(path: Path) -> str:
    import pypdf

    return "\n".join(page.extract_text() for page in pypdf.PdfReader(str(path)).pages)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--refresh", action="store_true", help="download the documents again")
    args = parser.parse_args()
    warnings.filterwarnings("ignore", message="Conditional Formatting")

    session = new_session()
    cache = ROOT / ".cache" / "economy"
    wage_pdf = fetch(session, economy.MINIMUM_WAGE["url"], cache / f"conasami_{economy.MINIMUM_WAGE['year']}.pdf", args.refresh)
    enoe_pdf = fetch(session, economy.ENOE["url"], cache / Path(economy.ENOE["url"]).name, args.refresh)
    poverty_xlsx = fetch(session, economy.POVERTY["url"], cache / Path(economy.POVERTY["url"]).name, args.refresh)
    retrieved_at = utc_now()

    wage = economy.parse_minimum_wage(pdf_text(wage_pdf))
    border = economy.border_municipality_codes(wage, load_catalog(ROOT / "web" / "data" / "municipios.topojson"))
    enoe_pages = [page.extract_text() for page in __import__("pypdf").PdfReader(str(enoe_pdf)).pages]
    enoe_page = next((p for p in enoe_pages if "Cuadro 5" in p and "Aguascalientes" in p), None)
    if enoe_page is None:
        raise SystemExit("ENOE bulletin: cuadro 5 (entidades) not found; check the address in informate/economy.py")
    # One bulletin per state for the income bands; read gently and cached like the rest.
    income = {}
    for code, url in economy.STATE_BULLETIN.items():
        path = cache / Path(url).name
        if args.refresh or not path.exists():
            time.sleep(0.5)
        try:
            income[code] = economy.parse_income_bands(pdf_text(fetch(session, url, path, args.refresh)))
        except Exception as error:  # one state missing should not sink the rest
            print(f"Entidad {code}: sin bandas de ingreso ({error})")
    data = economy.economy_records(wage, border, economy.parse_enoe_table(enoe_page), economy.parse_poverty_workbook(poverty_xlsx), retrieved_at, income=income)
    out = ROOT / "web" / "data" / "economy.json"
    write_json(out, data)
    w, e, p = data["minimum_wage"], data["employment"], data["poverty"]
    print(f"Salario mínimo {w['year']}: {w['general']} general, {w['border']} frontera norte ({len(w['border_municipalities'])} municipios).")
    print(f"Desocupación nacional, {e['period']}: {e['national']['unemployment']} %; informalidad {e['national']['informality']} %.")
    print(f"Pobreza {p['year']}: {p['national']['poverty_pct']} % ({p['national']['poverty_people']:,} personas); extrema {p['national']['extreme_pct']} %.")
    print(f"Bandas de ingreso: {len(data['income']['states'])} entidades.")
    print(f"Escrito: {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
