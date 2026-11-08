"""A plain-text summary of a dataset, for the command line."""
from collections import Counter

OFFICES = (
    ("governor", "Gubernaturas"),
    ("senator", "Senado"),
    ("deputy", "Cámara de Diputados"),
    ("mayor", "Presidencias municipales"),
    ("justice", "Suprema Corte"),
    ("president", "Presidencia"),
    ("secretary", "Gabinete"),
)


def summary_lines(dataset: dict) -> list[str]:
    lines = []
    for office, label in OFFICES:
        parties = Counter(person["party"] for person in dataset["people"] if person["office"] == office)
        if parties:
            breakdown = ", ".join(f"{party} {count}" for party, count in parties.most_common())
            lines.append(f"{label}: {sum(parties.values())}  ({breakdown})")
    lines.append("")
    for source in dataset["sources"].values():
        published = f"publicado: {source['published_at']}, " if source.get("published_at") else ""
        where = source["url"] if "url" in source else f"{len(source.get('pages', []))} páginas"
        lines.append(f"Fuente: {source['name']}")
        lines.append(f"        {where}  ({published}consultado: {source['retrieved_at']})")
    lines.extend(f"AVISO: {warning}" for warning in dataset["warnings"])
    return lines
