#!/usr/bin/env python3
"""Tool 11: Pueblos Mágicos and World Heritage sites, as points for the map.

Sources:
  Pueblos Mágicos   Spanish Wikipedia annex "Anexo:Pueblos mágicos" (secondary; SECTUR has no list
                    that can be read automatically): each town, the day it was named, coordinates.
  World Heritage    UNESCO World Heritage Centre, Spanish list as XML (official).

    python tools/fetch_heritage.py

Writes web/data/patrimonio.json.
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from informate import heritage, wikipedia  # noqa: E402
from informate.refresh import new_session, utc_now, write_json  # noqa: E402

OUT = ROOT / "web" / "data" / "patrimonio.json"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--unesco-file", type=Path, help="a copy of UNESCO's XML list already downloaded (the site refuses repeated downloads); its retrieval date goes in --unesco-date")
    parser.add_argument("--unesco-date", help="when that copy was downloaded, as YYYY-MM-DD")
    args = parser.parse_args()
    session = new_session()
    retrieved_at = utc_now()
    wikitext, revision = wikipedia.fetch_page(session, heritage.PUEBLOS_TITLE)
    pueblos, warnings = heritage.parse_pueblos(wikitext)
    if args.unesco_file:
        unesco_text, unesco_read_at = args.unesco_file.read_text(encoding="utf-8"), args.unesco_date or retrieved_at
    else:
        response = session.get(heritage.UNESCO_XML_URL, timeout=120)
        response.raise_for_status()
        unesco_text, unesco_read_at = response.content.decode("utf-8"), retrieved_at
    sites = heritage.parse_unesco(unesco_text)
    payload = {
        "generated_at": retrieved_at,
        "pueblos": {
            "citation": {
                "source": "wikipedia_pueblos",
                "source_name": f"Wikipedia en español, «{heritage.PUEBLOS_TITLE}»",
                "url": wikipedia.page_permalink(revision["id"], title=heritage.PUEBLOS_TITLE),
                "published_at": revision["timestamp"],
                "retrieved_at": retrieved_at,
                "programme_url": heritage.SECTUR_URL,
                "programme_name": "Secretaría de Turismo, programa Pueblos Mágicos",
            },
            "count": len(pueblos),
            "items": pueblos,
        },
        "unesco": {
            "citation": {"source": "unesco", "source_name": heritage.UNESCO_NAME, "url": heritage.UNESCO_LIST_URL, "xml_url": heritage.UNESCO_XML_URL, "published_at": None, "retrieved_at": unesco_read_at},
            "count": len(sites),
            "items": sites,
        },
        "warnings": warnings,
    }
    write_json(OUT, payload)
    print(f"Pueblos Mágicos: {len(pueblos)} (versión del {revision['timestamp']}); Patrimonio Mundial: {len(sites)} sitios")
    for warning in warnings:
        print(f"AVISO: {warning}")
    print(f"Escrito: {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
