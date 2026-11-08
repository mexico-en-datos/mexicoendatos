"""Homicide victims from the SESNSP's open data (Registro Nacional de Incidencia Delictiva)."""
import pytest

from informate.crime import victims_by_place, crime_records

HEAD = "Año,Clave_Ent,Entidad,Bien jurídico afectado,Tipo de delito,Subtipo de delito,Modalidad,Sexo,Rango de edad,Enero,Febrero,Marzo,Abril,Mayo,Junio,Julio,Agosto,Septiembre,Octubre,Noviembre,Diciembre\n"
STATE_2026 = HEAD + (
    "2026,01,Aguascalientes,La vida y la Integridad corporal,Homicidio,Homicidio doloso,Con arma de fuego,Hombre,18 a 29 años,2,1,0,3,0,0,1,0,2,0,0,0\n"
    "2026,01,Aguascalientes,La vida y la Integridad corporal,Homicidio,Homicidio doloso,Con arma blanca,Mujer,30 a 60 años,1,0,0,0,0,0,0,0,0,0,0,0\n"
    "2026,01,Aguascalientes,La vida y la Integridad corporal,Homicidio,Homicidio culposo,En accidente de tránsito,Hombre,18 a 29 años,9,9,9,9,9,9,9,9,9,0,0,0\n"
    "2026,01,Aguascalientes,La vida y la Integridad corporal,Feminicidio,Feminicidio,Con arma de fuego,Mujer,18 a 29 años,0,1,0,0,0,0,0,0,0,0,0,0\n"
    "2026,14,Jalisco,La vida y la Integridad corporal,Homicidio,Homicidio doloso,Con arma de fuego,Hombre,18 a 29 años,10,10,10,10,10,10,10,10,10,0,0,0\n"
)
HISTORY = HEAD + (
    "2024,1,Aguascalientes,La vida y la Integridad corporal,Homicidio,Homicidio doloso,Con arma de fuego,Hombre,Adultos (18 y más),5,5,5,5,5,5,5,5,5,5,5,5\n"
    "2025,1,Aguascalientes,La vida y la Integridad corporal,Homicidio,Homicidio doloso,Con arma de fuego,Hombre,Adultos (18 y más),1,1,1,1,1,1,1,1,1,1,1,1\n"
    "2025,1,Aguascalientes,La vida y la Integridad corporal,Homicidio,Homicidio doloso,No especificado,No identificado,No especificado,0,0,0,0,0,0,0,0,0,0,0,2\n"
)
MUNI_HEAD = "Año,Clave_Ent,Entidad,Cve. Municipio,Municipio,Bien jurídico afectado,Tipo de delito,Subtipo de delito,Modalidad,Sexo,Rango de edad,Enero,Febrero,Marzo,Abril,Mayo,Junio,Julio,Agosto,Septiembre,Octubre,Noviembre,Diciembre\n"
MUNI_2026 = MUNI_HEAD + (
    "2026,01,Aguascalientes,1001,Aguascalientes,La vida y la Integridad corporal,Homicidio,Homicidio doloso,Con arma de fuego,Hombre,18 a 29 años,2,1,0,3,0,0,1,0,2,0,0,0\n"
    "2026,01,Aguascalientes,1001,Aguascalientes,La vida y la Integridad corporal,Feminicidio,Feminicidio,Con arma de fuego,Mujer,18 a 29 años,0,1,0,0,0,0,0,0,0,0,0,0\n"
    "2026,14,Jalisco,14039,Guadalajara,La vida y la Integridad corporal,Homicidio,Homicidio doloso,Con arma blanca,Hombre,30 a 60 años,1,0,0,0,0,0,0,0,0,0,0,0\n"
)


def test_state_victims_are_summed_over_the_months_covered_and_keyed_by_padded_code():
    by_state = victims_by_place(STATE_2026, "state", year=2026, months=9)
    assert by_state["01"] == {"homicides": 10, "feminicides": 1}  # 9 + 1 homicides; manslaughter not counted
    assert by_state["14"] == {"homicides": 90, "feminicides": 0}


def test_history_file_with_unpadded_codes_gives_a_full_year():
    assert victims_by_place(HISTORY, "state", year=2025, months=12)["01"] == {"homicides": 14, "feminicides": 0}
    assert victims_by_place(HISTORY, "state", year=2024, months=12)["01"]["homicides"] == 60


def test_municipal_victims_are_keyed_by_five_digit_inegi_code():
    by_muni = victims_by_place(MUNI_2026, "municipality", year=2026, months=9)
    assert by_muni["01001"] == {"homicides": 9, "feminicides": 1}
    assert by_muni["14039"] == {"homicides": 1, "feminicides": 0}


def test_records_add_rates_per_100k_ranks_and_the_previous_year():
    population = {"01": 1425607, "14": 8348151}
    data = crime_records(
        victims_by_place(STATE_2026, "state", 2026, 9), victims_by_place(HISTORY, "state", 2025, 12), victims_by_place(MUNI_2026, "municipality", 2026, 9),
        population, year=2026, months=9, retrieved_at="2026-11-07T18:00:00Z"
    )
    assert data["year"] == 2026 and data["months"] == 9 and data["period"] == "enero a septiembre de 2026"
    ags = data["states"]["01"]
    assert ags["homicides"] == 10 and ags["feminicides"] == 1 and ags["previous_year_homicides"] == 14
    assert ags["homicide_rate"] == pytest.approx(100000 * 10 / 1425607, abs=0.01)
    assert data["states"]["14"]["rank_by_rate"] == 1 and ags["rank_by_rate"] == 2  # Jalisco's rate is higher
    assert data["national"]["homicides"] == 100 and data["national"]["feminicides"] == 1
    assert data["municipalities"]["14039"] == {"homicides": 1, "feminicides": 0}
    assert data["citation"]["source"] == "sesnsp" and data["citation"]["retrieved_at"] == "2026-11-07T18:00:00Z"
