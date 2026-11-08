"""State names arrive spelled differently by each source; all must resolve to INEGI's 2-digit code."""
import pytest

from informate.states import STATES, state_code


def test_there_are_32_states_keyed_by_inegi_code():
    assert len(STATES) == 32
    assert STATES["01"] == "Aguascalientes"
    assert STATES["09"] == "Ciudad de México"
    assert STATES["32"] == "Zacatecas"


@pytest.mark.parametrize(
    "name, code",
    [
        # INEGI official names
        ("Coahuila de Zaragoza", "05"),
        ("Michoacán de Ocampo", "16"),
        ("Veracruz de Ignacio de la Llave", "30"),
        ("México", "15"),
        # SIL short names
        ("Coahuila", "05"),
        ("Michoacán", "16"),
        ("Veracruz", "30"),
        ("Ciudad de México", "09"),
        # Wikipedia link targets
        ("Estado de México", "15"),
        ("Estado de Guerrero", "12"),
        ("Estado de Hidalgo", "13"),
        ("Estado de Veracruz", "30"),
        # sloppy spacing, case and missing accents
        ("  nuevo leon ", "19"),
        ("QUERETARO", "22"),
    ],
)
def test_state_code_resolves_each_source_spelling(name, code):
    assert state_code(name) == code


def test_state_code_rejects_unknown_names_instead_of_guessing():
    with pytest.raises(KeyError):
        state_code("Atlántida")
