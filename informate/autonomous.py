"""The constitutionally autonomous bodies (órganos constitucionales autónomos) and who heads
each one, from Spanish Wikipedia: the body's article names its head in the infobox, and the
head's own article gives the day the term began. Both are secondary sources, cited to the
exact revisions read; none of the five bodies publishes this in a form that can be read
automatically from outside Mexico without being blocked.

How long each head serves is not taken from Wikipedia but from the Constitution and the
laws, quoted in BODIES; the end of each term is computed from the start under that rule.
"""
import re
from datetime import date, timedelta

from .text import fold, spanish_date_to_iso

_CONSTITUTION = {
    "source_name": "Constitución Política de los Estados Unidos Mexicanos. Orden Jurídico Nacional, Secretaría de Gobernación",
    "url": "http://www.ordenjuridico.gob.mx/Constitucion/cn16.pdf",
    "published_at": "2024-11-15",
    "checked_at": "2026-11-11",
}

# In the order of the constitutional articles that create them.
BODIES = [
    {
        "key": "inegi",
        "logo": {"file": "img/inegi.png", "title": "File:INEGI.png", "author": "Instituto Nacional de Estadística y Geografía", "license": "Dominio público", "license_url": None, "retrieved_at": "2026-11-12"},
        "post_pattern": r"instituto nacional de estadistica",
        "page": "Instituto Nacional de Estadística y Geografía",
        "name": "Instituto Nacional de Estadística y Geografía",
        "short": "INEGI",
        "head_field": "titular_nom",
        "title_field": "titular_tipo",
        "mandate": (
            "«El Estado contará con un Sistema Nacional de Información Estadística y Geográfica cuyos datos serán "
            "considerados oficiales» (artículo 26, apartado B, de la Constitución). El INEGI norma y coordina ese sistema: "
            "censos, encuestas, cuentas nacionales y cartografía."
        ),
        "basis": "Artículo 26, apartado B, de la Constitución",
        "appointment": "Lo designa la Presidencia de la República con aprobación del Senado.",
        "term": {
            "years": 6,
            "text": (
                "Seis años, contados desde el 1 de enero del cuarto año del sexenio presidencial (Ley del Sistema Nacional de "
                "Información Estadística y Geográfica, artículo 68)."
            ),
            "source_name": "Ley del Sistema Nacional de Información Estadística y Geográfica. Orden Jurídico Nacional, Secretaría de Gobernación",
            "url": "https://www.ordenjuridico.gob.mx/Documentos/Federal/html/wo29.html",
            "published_at": "2023-12-01",
            "checked_at": "2026-11-11",
        },
    },
    {
        "key": "banxico",
        "logo": {"file": "img/banxico.png", "title": "File:Logobm.svg", "author": "Banco de México", "license": "Dominio público", "license_url": None, "retrieved_at": "2026-11-12"},
        "post_pattern": r"banco de mexico",
        "page": "Banco de México",
        "name": "Banco de México",
        "short": "Banxico",
        "head_field": "gobernador",
        "title_field": None,
        "mandate": (
            "«El Estado tendrá un banco central que será autónomo en el ejercicio de sus funciones y en su administración. "
            "Su objetivo prioritario será procurar la estabilidad del poder adquisitivo de la moneda nacional» (artículo 28 de "
            "la Constitución). Emite los billetes y monedas, fija la tasa de interés de referencia y administra las reservas."
        ),
        "basis": "Artículo 28, párrafo séptimo, de la Constitución",
        "appointment": "A quien lo gobierna lo designa la Presidencia de la República con aprobación del Senado.",
        "term": {
            "years": 6,
            "text": "Seis años, contados desde el 1 de enero del cuarto año del sexenio presidencial (Ley del Banco de México, artículo 40).",
            "source_name": "Ley del Banco de México, texto vigente publicado por la Cámara de Diputados (copia en gob.mx)",
            "url": "https://www.gob.mx/cms/uploads/attachment/file/168167/LBM.pdf",
            "published_at": "2014-01-10",
            "checked_at": "2026-11-11",
        },
    },
    {
        "key": "ine",
        "logo": {"file": "img/ine.png", "title": "File:Logo ine 2026.svg", "author": "Instituto Nacional Electoral", "license": "Dominio público", "license_url": None, "retrieved_at": "2026-11-12"},
        "post_pattern": r"instituto nacional electoral",
        "page": "Instituto Nacional Electoral",
        "name": "Instituto Nacional Electoral",
        "short": "INE",
        "head_field": "titular_nom",
        "title_field": "titular_tipo",
        "mandate": (
            "«La organización de las elecciones es una función estatal que se realiza a través del Instituto Nacional "
            "Electoral y de los organismos públicos locales» (artículo 41, base V, de la Constitución). Organiza las "
            "elecciones federales, lleva el padrón y expide la credencial para votar."
        ),
        "basis": "Artículo 41, base V, de la Constitución",
        "appointment": "A quien preside su Consejo General lo elige la Cámara de Diputados por dos tercios de los presentes.",
        "term": {
            "years": 9,
            "text": (
                "Nueve años, sin reelección. Si la falta ocurre en los primeros seis años, la Cámara de Diputados elige a quien "
                "concluya el periodo; si ocurre en los últimos tres, a alguien para un periodo nuevo (artículo 41, base V, "
                "apartado A, de la Constitución)."
            ),
            "provisional_note": (
                "corresponde a la Cámara de Diputados elegir a quien concluya el periodo de nueve años de la vacante "
                "(artículo 41, base V, apartado A, de la Constitución)"
            ),
        }
        | _CONSTITUTION,
    },
    {
        "key": "fgr",
        "logo": {"file": "img/fgr.png", "title": "File:Logo de la FGR México.png", "author": "Gabomiranda (Wikimedia Commons)", "license": "CC BY-SA 4.0", "license_url": "https://creativecommons.org/licenses/by-sa/4.0", "retrieved_at": "2026-11-12"},
        "post_pattern": r"fiscal(?:ia)? general de la republica",
        "page": "Fiscalía General de la República (México)",
        "name": "Fiscalía General de la República",
        "short": "FGR",
        "head_field": "titular_nom",
        "title_field": "titular_tipo",
        "mandate": (
            "«El Ministerio Público de la Federación se organizará en una Fiscalía General de la República como órgano "
            "público autónomo» (artículo 102, apartado A, de la Constitución). Investiga y persigue los delitos federales."
        ),
        "basis": "Artículo 102, apartado A, de la Constitución",
        "appointment": "El Senado forma una lista de diez, la Presidencia escoge una terna y el Senado elige por dos tercios.",
        "term": {"years": 9, "text": "Nueve años (artículo 102, apartado A, de la Constitución)."} | _CONSTITUTION,
    },
    {
        "key": "cndh",
        "logo": {"file": "img/cndh.png", "title": "File:Logo Horizontal Color.png", "author": "Logo_CNDH (Wikimedia Commons)", "license": "CC BY-SA 4.0", "license_url": "https://creativecommons.org/licenses/by-sa/4.0", "retrieved_at": "2026-11-12"},
        "post_pattern": r"comision nacional de los derechos humanos",
        "page": "Comisión Nacional de los Derechos Humanos (México)",
        "name": "Comisión Nacional de los Derechos Humanos",
        "short": "CNDH",
        "head_field": "titular_nom",
        "title_field": "titular_tipo",
        "mandate": (
            "Organismo de protección de los derechos humanos que conoce «de quejas en contra de actos u omisiones de "
            "naturaleza administrativa provenientes de cualquier autoridad o servidor público» que los violen, salvo los del "
            "Poder Judicial (artículo 102, apartado B, de la Constitución). Emite recomendaciones, no sentencias."
        ),
        "basis": "Artículo 102, apartado B, de la Constitución",
        "appointment": "A quien la preside lo elige el Senado por dos tercios de los presentes, tras consulta pública.",
        "term": {
            "years": 5,
            "reelectable_once": True,
            "text": "Cinco años, con una sola reelección posible (artículo 102, apartado B, de la Constitución).",
        }
        | _CONSTITUTION,
    },
]
BODY = {spec["key"]: spec for spec in BODIES}
COMMONS_FILE = "https://commons.wikimedia.org/wiki/{title}"


def logo_source(spec: dict) -> dict:
    """The logo's file on the site plus its page on Wikimedia Commons, author and licence."""
    logo = spec["logo"]
    return logo | {"url": COMMONS_FILE.format(title=logo["title"].replace(" ", "_"))}

_LINK = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]*))?\]\]")
_FILE = re.compile(r"\[\[(?:Archivo|File|Imagen|Image):[^\]]*\]\]", re.I)
_REF = re.compile(r"<ref[^>]*/>|<ref[^>]*>.*?</ref>", re.S)
_FECHA = re.compile(r"\{\{\s*fecha\s*\|\s*(\d{1,2})\s*\|\s*(\d{1,2})\s*\|\s*(\d{4})", re.I)
_REELECTED = re.compile(r"reelegid[ao] para el periodo (\d{4})\s*[-–]\s*(\d{4})", re.I)


def _field(wikitext: str, name: str) -> str | None:
    """An infobox field's raw value, without references; None when absent or empty."""
    match = re.search(r"^\|\s*" + re.escape(name) + r"\s*=\s*(.*)$", wikitext, re.M)
    if not match:
        return None
    value = _REF.sub("", match.group(1)).strip()
    return value or None


def _plain(text: str) -> str:
    text = _FILE.sub("", text)
    text = _LINK.sub(lambda m: m.group(2) or m.group(1), text)
    text = re.sub(r"<[^>]+>|'{2,}", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _date(text: str | None) -> str | None:
    if not text:
        return None
    stamped = _FECHA.search(text)
    if stamped:
        return f"{stamped.group(3)}-{int(stamped.group(2)):02d}-{int(stamped.group(1)):02d}"
    return spanish_date_to_iso(text)


def parse_head(wikitext: str, spec: dict) -> dict:
    """Who heads the body, from its article's infobox: {"name", "article", "title"} (title None
    when the infobox does not name the post)."""
    value = _field(wikitext, spec["head_field"])
    link = _LINK.search(_FILE.sub("", value or ""))
    if not link:
        raise ValueError(f"The infobox of «{spec['page']}» names nobody in {spec['head_field']!r}")
    title = _plain(_field(wikitext, spec["title_field"]) or "") if spec["title_field"] else ""
    return {"name": (link.group(2) or link.group(1)).strip(), "article": link.group(1).strip(), "title": title or None}


def parse_tenure(wikitext: str, spec: dict) -> dict:
    """From the head's own article: the post as the infobox words it, when it began and (if
    given) ended, whether the infobox marks it provisional, and a re-election the lead records."""
    for suffix in ["", *map(str, range(2, 10))]:
        cargo = _field(wikitext, f"cargo{suffix}")
        if not cargo:
            continue
        links = [m.group(1).strip() for m in _LINK.finditer(cargo)]
        if spec["page"] not in links and not re.search(spec["post_pattern"], fold(_plain(cargo))):
            continue
        reelected = _REELECTED.search(wikitext)
        return {
            "title": _plain(cargo),
            "start": _date(_field(wikitext, f"inicio{suffix}")),
            "end": _date(_field(wikitext, f"final{suffix}")),
            "provisional": fold(_field(wikitext, f"subtítulo{suffix}") or "") == "provisional",
            "reelected": (int(reelected.group(1)), int(reelected.group(2))) if reelected else None,
        }
    raise ValueError(f"No post at «{spec['page']}» in the infobox of the head's article")


def _plus_years(day: str, years: int) -> date:
    start = date.fromisoformat(day)
    return date(start.year + years, start.month, start.day)


def term_end(spec: dict, tenure: dict) -> tuple[str | None, str | None, str | None]:
    """(end date, basis, note) for a head under the body's rule. The basis is 'rule' when the
    end is computed; a note explains a provisional post, a re-election or a missing start."""
    rule = spec["term"]
    if not tenure["start"]:
        return None, None, "La fuente no da la fecha de inicio"
    if tenure["provisional"]:
        return None, None, f"Designación provisional, según la fuente; {rule['provisional_note']}" if rule.get("provisional_note") else "Designación provisional, según la fuente"
    periods, note = 1, None
    if tenure["reelected"] and rule.get("reelectable_once"):
        periods, note = 2, f"Reelección para {tenure['reelected'][0]}-{tenure['reelected'][1]} registrada por la fuente"
    end = _plus_years(tenure["start"], rule["years"] * periods) - timedelta(days=1)
    return end.isoformat(), "rule", note
