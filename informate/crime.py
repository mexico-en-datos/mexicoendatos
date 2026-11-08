"""Homicide victims, from the SESNSP's open data.

The Secretariado Ejecutivo del Sistema Nacional de Seguridad Pública publishes
every month the crimes reported to the state prosecutors (Registro Nacional de
Incidencia Delictiva). The "víctimas" files count victims rather than case
files; the page lists one per level (state, municipality) and methodology. The
files sit on the SESNSP's SharePoint; the share links download without a login
through SharePoint's download endpoint.
"""
import csv
import io

PAGE_URL = "https://www.gob.mx/sesnsp/acciones-y-programas/datos-abiertos-de-incidencia-delictiva"
PAGE_DATE = "2026-10-16"  # the date printed on the page when these links were taken
SOURCE_NAME = "SESNSP, Registro Nacional de Incidencia Delictiva: víctimas del fuero común"
DOWNLOAD = "https://sspcgob-my.sharepoint.com/personal/cni_sspc_gob_mx/_layouts/15/download.aspx?share={share}"
# The share ids behind the page's links (taken 2026-11-07) and the months each file covers.
FILES = {
    "state_current": {"share": "IQB62zi8YeCOR5sJgXLRXNoTAc0815g0LPL0OhuUPy9Z_ec", "label": "Víctimas, estatal, 2026 (metodología 2026)"},
    "municipal_current": {"share": "IQBckYHO8d6WTZ0ZaSCYDjLIAY8dl7y6o2XJc6mhl27rGiU", "label": "Víctimas, municipal, 2026 (metodología 2026)"},
    "state_history": {"share": "IQC7gjMDceDhTovbaLjJhCsPATp0-Oa3jyDBxpZ8qZm7Nkw", "label": "Víctimas, estatal, 2015-2025"},
}
YEAR = 2026
MONTHS = 9  # January to September 2026 in the files published in October 2026

MONTH_COLUMNS = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
MONTH_NAMES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
COUNTED = {"Homicidio doloso": "homicides", "Feminicidio": "feminicides"}


def read_rows(text: str) -> list[dict]:
    return list(csv.DictReader(io.StringIO(text)))


def decode(raw: bytes) -> str:
    """The files come as UTF-8 with a BOM or as Latin-1, depending on the year."""
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return raw.decode("latin-1")


def victims_by_place(text: str, level: str, year: int, months: int) -> dict[str, dict]:
    """Homicide and feminicide victims per place over the first `months` of `year`.

    `level` is "state" (keyed by the 2-digit INEGI code) or "municipality" (5-digit
    code). Codes in the files sometimes lack their leading zero.
    """
    width = 2 if level == "state" else 5
    key = "Clave_Ent" if level == "state" else "Cve. Municipio"
    totals: dict[str, dict] = {}
    for row in read_rows(text):
        if int(row["Año"]) != year or row["Subtipo de delito"] not in COUNTED:
            continue
        code = row[key].strip().zfill(width)
        place = totals.setdefault(code, {"homicides": 0, "feminicides": 0})
        place[COUNTED[row["Subtipo de delito"]]] += sum(int(row[column] or 0) for column in MONTH_COLUMNS[:months])
    return totals


def period_label(year: int, months: int) -> str:
    return f"{MONTH_NAMES[0]} a {MONTH_NAMES[months - 1]} de {year}" if months < 12 else f"todo {year}"


def crime_records(current: dict, previous: dict, municipal: dict, population: dict[str, int], year: int, months: int, retrieved_at: str) -> dict:
    """What the page shows: per state, victims this year so far, the rate per 100,000
    inhabitants (census 2020), the rank among states by that rate, and last year's total;
    per municipality, the counts; and the national totals."""
    states = {}
    for code, counts in current.items():
        people = population.get(code)
        states[code] = {
            **counts,
            "homicide_rate": round(100000 * counts["homicides"] / people, 2) if people else None,
            "previous_year_homicides": previous.get(code, {}).get("homicides"),
        }
    ranked = sorted((c for c in states if states[c]["homicide_rate"] is not None), key=lambda c: -states[c]["homicide_rate"])
    for rank, code in enumerate(ranked, start=1):
        states[code]["rank_by_rate"] = rank
    return {
        "year": year,
        "months": months,
        "period": period_label(year, months),
        "previous_year": year - 1,
        "national": {
            "homicides": sum(c["homicides"] for c in current.values()),
            "feminicides": sum(c["feminicides"] for c in current.values()),
            "previous_year_homicides": sum(c["homicides"] for c in previous.values()) if previous else None,
        },
        "states": states,
        "municipalities": municipal,
        "citation": {
            "source": "sesnsp",
            "source_name": SOURCE_NAME,
            "url": PAGE_URL,
            "published_at": PAGE_DATE,
            "retrieved_at": retrieved_at,
            "files": [dict(spec, url=DOWNLOAD.format(share=spec["share"])) for spec in FILES.values()],
        },
    }
