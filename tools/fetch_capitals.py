#!/usr/bin/env python3
"""Tool 8: the capital of each state, placed in its municipality.

Source: Spanish Wikipedia, «Anexo:Entidades federativas de México» (secondary; cited
to the revision read). Capitals change almost never, so this runs on demand.

    python tools/fetch_capitals.py

Writes web/data/capitals.json.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from informate import capitals, wikipedia  # noqa: E402
from informate.refresh import load_catalog, new_session, utc_now, write_json  # noqa: E402


def main() -> None:
    text, revision = wikipedia.fetch_page(new_session(), capitals.PAGE_TITLE)
    data = capitals.capital_records(capitals.parse_capitals(text), load_catalog(ROOT / "web" / "data" / "municipios.topojson"), revision, utc_now())
    out = ROOT / "web" / "data" / "capitals.json"
    write_json(out, data)
    missing = [code for code, row in data["states"].items() if not row["municipality_code"] and code != "09"]
    print(f"{len(data['states'])} capitales; sin municipio: {missing or 'ninguna'}. Fuente: {data['citation']['url']} (consultada {data['citation']['retrieved_at']})")
    print(f"Escrito: {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
