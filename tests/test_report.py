"""The short summary the fetch tool prints when it finishes."""
from informate.report import summary_lines

DATASET = {
    "people": [
        {"office": "governor", "party": "PAN"},
        {"office": "senator", "party": "MORENA"},
        {"office": "senator", "party": "PAN"},
        {"office": "mayor", "party": "OTRO"},
    ],
    "sources": {
        # one source with its own date, one without, and one that is a set of pages
        "wikipedia": {"name": "Wikipedia, gobernantes", "url": "https://example.org/g", "published_at": "2026-10-08T04:24:51Z", "retrieved_at": "2026-11-06T19:00:00Z"},
        "sil": {"name": "SIL", "url": "http://example.org/sil", "published_at": None, "retrieved_at": "2026-11-06T19:00:00Z"},
        "wikipedia_mayors": {"name": "Wikipedia, anexos", "retrieved_at": "2026-11-06T18:00:00Z", "pages": [{"url": "https://example.org/a"}, {"url": "https://example.org/b"}]},
    },
    "warnings": ["Faltan 2 municipios."],
}


def test_counts_each_office_with_its_parties():
    lines = summary_lines(DATASET)
    assert "Gubernaturas: 1  (PAN 1)" in lines
    assert "Senado: 2  (MORENA 1, PAN 1)" in lines
    assert "Presidencias municipales: 1  (OTRO 1)" in lines
    assert not any(line.startswith("Cámara de Diputados") for line in lines)  # none in this data


def test_every_source_is_listed_with_its_link_and_dates_whatever_its_shape():
    text = "\n".join(summary_lines(DATASET))
    assert "https://example.org/g  (publicado: 2026-10-08T04:24:51Z, consultado: 2026-11-06T19:00:00Z)" in text
    assert "http://example.org/sil  (consultado: 2026-11-06T19:00:00Z)" in text
    assert "2 páginas  (consultado: 2026-11-06T18:00:00Z)" in text


def test_warnings_are_repeated_at_the_end():
    assert summary_lines(DATASET)[-1] == "AVISO: Faltan 2 municipios."
