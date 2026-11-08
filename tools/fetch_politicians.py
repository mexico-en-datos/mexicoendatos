#!/usr/bin/env python3
"""Tool 2: fetch, live, who holds office: the 32 governors and the 128 senators.

Sources:
  Senators   SIL, Secretaría de Gobernación (official): one profile link per person.
  Governors  Spanish Wikipedia list (secondary): cited to the exact revision read.

    python tools/fetch_politicians.py

Writes web/data/politicians.json. Every person has a citation with a link and dates.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from informate.refresh import new_session, refresh_politicians  # noqa: E402
from informate.report import summary_lines  # noqa: E402

OUT = ROOT / "web" / "data" / "politicians.json"


def main() -> None:
    catalog = ROOT / "web" / "data" / "municipios.topojson"
    if not catalog.exists():
        print("Sin mapa (ejecuta tools/build_map.py): se omiten las presidencias municipales.")
    dataset = refresh_politicians(
        OUT, new_session(), cache_dir=ROOT / ".cache", log=print,
        catalog_path=catalog if catalog.exists() else None,
    )
    print("\n".join(summary_lines(dataset)))
    print(f"\nEscrito: {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
