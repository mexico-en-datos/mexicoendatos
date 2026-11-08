"""Each source labels parties its own way; the dataset uses one short code per party."""
import pytest

from informate.parties import PARTIES, party_code


@pytest.mark.parametrize(
    "label, code",
    [
        # SIL labels
        ("Morena", "MORENA"),
        ("PAN", "PAN"),
        ("PRI", "PRI"),
        ("PVEM", "PVEM"),
        ("PT", "PT"),
        ("MC", "MC"),
        ("Sin Partido", "SP"),
        # Wikipedia link targets
        ("Morena (partido político)", "MORENA"),
        ("Partido Acción Nacional", "PAN"),
        ("Partido Revolucionario Institucional", "PRI"),
        ("Movimiento Ciudadano (partido político de México)", "MC"),
        ("Partido Verde Ecologista de México", "PVEM"),
        ("Partido del Trabajo (México)", "PT"),
        ("Movimiento Regeneración Nacional", "MORENA"),
        ("Candidaturas independientes de México", "SP"),
        ("Candidato independiente en México", "SP"),
        ("Interino", "SP"),
    ],
)
def test_party_code_resolves_each_source_label(label, code):
    assert party_code(label) == code


def test_party_code_rejects_unknown_labels_instead_of_guessing():
    with pytest.raises(KeyError):
        party_code("Partido Inventado")


def test_every_party_code_has_a_display_name():
    for code in ("MORENA", "PAN", "PRI", "PVEM", "PT", "MC", "SP"):
        assert PARTIES[code]["name"]


def test_parties_without_a_code_of_their_own_fall_under_other():
    assert PARTIES["OTRO"]["name"] == "Otro partido"
