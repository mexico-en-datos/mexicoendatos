# México en datos

A map of Mexico with all its municipalities, showing what each place is and who
runs it: population and dwellings, each state's GDP and its rank, homicide
victims this year and last, today's gasoline and diesel prices, and who governs
and represents it (governor, senators, deputy, municipal president), the
Presidency and its cabinet, and the three elected bodies of the federal
judiciary (Supreme Court, Tribunal Electoral, Tribunal de Disciplina Judicial).

The main page (`web/index.html`, "Explorar México") is one map you go into
level by level. At the country level each state carries a mark: a square for
its governor and three circles for its senators, in party colours, and under
them three grey bars (unemployment, homicide rate, gasoline price) whose height
is the state's place among the 32. Inside a state the map stays neutral and
shows municipality lines and dashed federal-district lines together; pointing
at a municipality names its president and the deputy of the district under the
pointer. Each level's data is grouped as Población, Economía, Seguridad,
Combustibles and Gobierno y representación, with ranks. The second page (`web/mapas-politicos.html`, "Mapas políticos")
is one map per office, coloured by party, with every seat of the body shown
drawn as a hemicycle with party counts and majorities. "Mapas económicos" (`web/mapas-economicos.html`) and "Mapas de seguridad"
(`web/mapas-seguridad.html`) colour the map by one figure at a time (GDP,
unemployment, poverty, income bands, gasoline price, homicides…) with a
five-step scale and every state ranked. The last page
(`web/poderes.html`, "Poderes de la Nación") shows the three powers: Legislativo (Senate and
Chamber as hemicycles with counts and majorities), Ejecutivo (Presidency and
cabinet) and Judicial (Supreme Court, Tribunal Electoral's Sala Superior and
Tribunal de Disciplina Judicial, each with who presides it). Every page lists people by name
only; clicking a seat or a name shows that person's data as one row per fact:
office, party, where they were elected, term, schooling, source and, for
legislators, the official email, phone and office of their seat as SIL lists
them. `web/common.js` holds what the three pages share.

The site is meant to live at mexicoendatos.net; `DEPLOY.md` explains how to
publish it without it pointing back at its author. Every person and every
figure carries a citation: a link plus the date it was read.

The page itself is in Spanish; the code and this file are in English.

## Run it

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

.venv/bin/python tools/build_map.py          # tool 1: the map (once; ~100 MB download, a few minutes)
.venv/bin/python tools/fetch_politicians.py  # tool 2: governors, senators, deputies and
                                             #         municipal presidents, live (a few minutes)
.venv/bin/python tools/serve.py              # tool 3: the page, at http://127.0.0.1:8000
.venv/bin/python tools/fetch_gdp.py          # tool 4: GDP per state (yearly; INEGI publishes in December)
.venv/bin/python tools/fetch_crime.py        # tool 5: homicide victims per state and municipality (monthly cut)
.venv/bin/python tools/fetch_fuel.py         # tool 6: gasoline and diesel prices per municipality (daily)
.venv/bin/python tools/fetch_economy.py      # tool 7: minimum wage, employment, income bands and poverty per state
.venv/bin/python tools/fetch_capitals.py     # tool 8: the capital of each state (on demand)
```

Run the tests with `.venv/bin/python -m pytest`.

## The three tools

| Tool | What it does | Writes |
|---|---|---|
| `tools/build_map.py` | Downloads the municipal boundaries of the 32 states from INEGI and the 300 federal districts from INE (an 86 MB archive), simplifies them and writes one file each. `--refresh` downloads again; otherwise it reuses the copies in `.cache/inegi/`. | `web/data/municipios.topojson`, `web/data/distritos.topojson`, `web/data/map_source.json` |
| `tools/fetch_politicians.py` | Fetches the 32 heads of state governments, the 128 senators, the 500 federal deputies and about 2,050 municipal presidents as the sources list them at that moment. The municipal pages are re-read at most once a day. Each legislator's SIL profile (district or region, official email, phone, office, schooling) is read once, 100 per run, and remembered in `.cache/sil_fichas.json`. | `web/data/politicians.json` |
| `tools/fetch_crime.py` | Downloads the SESNSP's victims files (state and municipal, current year; state, 2015-2025) and sums intentional homicide and feminicide victims per place for the months covered, with rates per 100,000 inhabitants (census 2020) and ranks. The share ids and months covered are in `informate/crime.py`; update them when the SESNSP publishes a new monthly cut. | `web/data/crime.json` |
| `tools/fetch_fuel.py` | Reads the CRE's two XML feeds (stations and prices), places each station in its municipality (INEGI boundaries from the map cache, or the published map when the cache is absent, as in the daily workflow) and averages regular, premium and diesel per municipality, state and country. | `web/data/fuel.json` |
| `tools/fetch_economy.py` | Reads CONASAMI's minimum-wage table (general and northern-border wage, and the border municipalities, matched to INEGI codes), INEGI's quarterly ENOE bulletin (cuadro 5: employed, unemployed, participation, unemployment and informality per state) and INEGI's poverty workbook (poverty and extreme poverty per state, 2024), and ranks the states. Addresses and dates are in `informate/economy.py`; update them for each new edition. | `web/data/economy.json` |
| `tools/fetch_capitals.py` | Reads each state's capital from the Wikipedia annex of federal entities and places it in its INEGI municipality (a short table in `informate/capitals.py` covers the capitals whose municipality has another name, such as Villahermosa in Centro). | `web/data/capitals.json` |
| `tools/fetch_gdp.py` | Reads each state's GDP from INEGI's yearly PIBE press release (a PDF; its cuadro 1). INEGI's indicator API has the same numbers but needs a personal token, which this project avoids. | `web/data/gdp.json` |
| `tools/serve.py` | Serves `web/` on this computer. The page's "Actualizar datos" button re-runs tool 2 (at most once a minute). | (updates `politicians.json`) |

## Where the data comes from

All links below were opened on 2026-11-06.

| Data | Source | Kind | Link (date) |
|---|---|---|---|
| Municipal boundaries (2,478 municipalities) | INEGI, *Marco Geoestadístico, diciembre de 2025*, through INEGI's web service, one request per state | Official | `https://gaia.inegi.org.mx/wscatgeo/v2/geo/mgem/01` … `/32` (downloaded 2026-11-06) |
| Federal district boundaries (300) | INE, Marco Geográfico Seccional, layer `DISTRITO_FEDERAL` (districting of 2023), reprojected from Lambert Conformal Conic | Official | [SHAPEFILE.7z](https://cartografia.ine.mx/mapoteca/MGS_CCL/SHAPEFILE.7z) (archive dated 2025-01-31, downloaded 2026-11-07) |
| Federal cabinet: dependency and head | Spanish Wikipedia article *Gabinete de México*, its "Gabinete legal" table. No appointment dates or parties there, and no official page that can be read automatically. | Secondary | [revision 175533934](https://es.wikipedia.org/w/index.php?title=Gabinete_de_M%C3%A9xico&oldid=175533934) (published 2026-09-26, read 2026-11-07) |
| GDP per state, 2024, at 2018 prices, with annual growth | INEGI, PIB por Entidad Federativa 2024, cifras preliminares, comunicado 156/25, cuadro 1. Yearly; no official GDP exists per district or municipality, and the page says so. | Official | [PIBE2024_CP.pdf](https://www.inegi.org.mx/contenidos/saladeprensa/boletines/2025/pibent/PIBE2024_CP.pdf) (published 2025-12-05, read 2026-11-07) |
| Homicide and feminicide victims, per state and municipality, monthly | SESNSP, Registro Nacional de Incidencia Delictiva, víctimas del fuero común (page dated 2026-10-16; files cover January to September 2026 and 2015-2025). Rates use the 2020 census population. | Official | [datos abiertos de incidencia delictiva](https://www.gob.mx/sesnsp/acciones-y-programas/datos-abiertos-de-incidencia-delictiva) (files downloaded 2026-11-07) |
| Gasoline and diesel prices per station | Comisión Reguladora de Energía, prices reported by permit holders, XML feeds `places` and `prices`. No publication date in the feed; the day read is the date. | Official | [prices](https://publicacionexterna.azurewebsites.net/publicaciones/prices), [places](https://publicacionexterna.azurewebsites.net/publicaciones/places) (read 2026-11-07) |
| Tribunal Electoral, Sala Superior: seven seats, who holds them and when elected | Spanish Wikipedia article, "Integración de la Sala superior" table. Terms: fourth transitional article of the 2024 judicial reform (2027 for those in office then, 2033 for those elected in 2025). | Secondary | [revision 175170851](https://es.wikipedia.org/w/index.php?title=Tribunal_Electoral_del_Poder_Judicial_de_la_Federaci%C3%B3n&oldid=175170851) (published 2026-09-03, read 2026-11-07) |
| Tribunal de Disciplina Judicial: five magistrates | Spanish Wikipedia article, "Composición" table. Terms: fifth transitional article (two until 2033, three until 2030, by votes; the source gives no vote order, so the page says so). | Secondary | [revision 175170915](https://es.wikipedia.org/w/index.php?title=Tribunal_de_Disciplina_Judicial_%28M%C3%A9xico%29&oldid=175170915) (published 2026-09-03, read 2026-11-07) |
| Minimum wage 2026: general and northern-border zone, and the border municipalities | CONASAMI, Tabla de salarios mínimos generales y profesionales vigentes a partir del 1 de enero de 2026 (PDF). | Official | [Tabla_de_Salarios_M_nimos_2026.pdf](https://www.gob.mx/cms/uploads/attachment/file/1041076/Tabla_de_Salarios_M_nimos_2026.pdf) (read 2026-11-07) |
| Income bands of the employed per state (share earning up to 1, 1-2, 2-3, 3-5, over 5 minimum wages; none) | INEGI, ENOE, second quarter of 2026, one press release per state (32 PDFs, "Nivel de ingresos"). Used because the average wage per state is IMSS's figure and IMSS's servers refuse automated readers. | Official | e.g. [enoe2026_08_Jal.pdf](https://www.inegi.org.mx/contenidos/saladeprensa/boletines/2026/enoe/enoe2026_08_Jal.pdf) (published 2026-08-25, read 2026-11-07) |
| Employment per state: employed, unemployed, participation, unemployment, informality | INEGI, ENOE, second quarter of 2026, press release cuadro 5. Next release 2026-11-25. | Official | [enoe2026_08.pdf](https://www.inegi.org.mx/contenidos/saladeprensa/boletines/2026/enoe/enoe2026_08.pdf) (published 2026-08-25, read 2026-11-07) |
| Poverty per state, 2024: population in poverty and in extreme poverty, people and percent | INEGI, Pobreza Multidimensional 2024, tabulados por entidad federativa (Coneval methodology, ENIGH 2024). | Official | [pm_ef_2024.xlsx](https://www.inegi.org.mx/contenidos/desarrollosocial/pm/tabulados/pm_ef_2024.xlsx) (published 2025-08-13, read 2026-11-07) |
| State capitals | Spanish Wikipedia, «Anexo:Entidades federativas de México», capital column. | Secondary | [revision 175410084](https://es.wikipedia.org/w/index.php?title=Anexo:Entidades_federativas_de_M%C3%A9xico&oldid=175410084) (published 2026-09-18, read 2026-11-08) |
| Population per state | INEGI, *Censo de Población y Vivienda, 2020*, from the same web service (summed from its municipalities; 9 municipalities created after the census have no figure of their own) | Official | same downloads (2026-11-06) |
| Federal deputies: name, party, state and district, or regional list | SIL. One profile page per deputy, which is also where the district is read. | Official | [roster of the LXVI Legislature](http://sil.gobernacion.gob.mx/Numeralia/Legisladores/resultadosNumeraliaLegisladores.php?SID=&Legislatura=66&Camara=1&Estatus=A) (read 2026-11-06) |
| Senators: name, party, state, how the seat was won | SIL, Sistema de Información Legislativa, Secretaría de Gobernación. One profile page per senator. | Official | [roster of the LXVI Legislature](http://sil.gobernacion.gob.mx/Numeralia/Legisladores/resultadosNumeraliaLegisladores.php?SID=&Legislatura=66&Camara=2&Estatus=A) (read 2026-11-06) |
| Municipal presidents: name, party, term | Spanish Wikipedia, one list per state (*Anexo:Presidentes municipales de …*) plus Mexico City's alcaldías. Each record is cited to the exact revision of its state's page; the page shows all 32 links with their dates. | Secondary | e.g. [Aguascalientes, revision 172212877](https://es.wikipedia.org/w/index.php?title=Anexo:Presidentes_municipales_de_Aguascalientes_(2024-2027)&oldid=172212877) (published 2026-02-24, read 2026-11-06) |
| President: name, party, term | Spanish Wikipedia article on the office (*Presidente de México*) for the holder and start date, and the holder's own article for the party. Six-year term per Article 83 of the Constitution. | Secondary | [office article, revision 176178323](https://es.wikipedia.org/w/index.php?title=Presidente_de_M%C3%A9xico&oldid=176178323) (published 2026-11-06, read 2026-11-07) |
| The five regions (circunscripciones) that elect the 200 list deputies | Spanish Wikipedia, *Anexo:Circunscripciones electorales de México*; make-up in force since 29 March 2023. Checked against a built-in table by a test. | Secondary | [revision 172276913](https://es.wikipedia.org/w/index.php?title=Anexo:Circunscripciones_electorales_de_M%C3%A9xico&oldid=172276913) (published 2026-02-28, read 2026-11-07) |
| Supreme Court justices: name, role, term | Spanish Wikipedia article *Suprema Corte de Justicia de la Nación* (its "Composición actual" table, in order of votes received). The Court's site refuses requests from outside Mexico. | Secondary | [revision 176164501](https://es.wikipedia.org/w/index.php?title=Suprema_Corte_de_Justicia_de_la_Naci%C3%B3n&oldid=176164501) (published 2026-11-05, read 2026-11-07) |
| Governors: name, party, term | Spanish Wikipedia, *Anexo:Gobernantes de las entidades federativas de México*. Each record is cited to the exact revision that was read. | Secondary | [revision 175719290](https://es.wikipedia.org/w/index.php?title=Anexo:Gobernantes_de_las_entidades_federativas_de_M%C3%A9xico&oldid=175719290) (published 2026-10-08, read 2026-11-06) |

Background pages: [INEGI web service documentation](https://www.inegi.org.mx/servicios/catalogounico.html) (checked 2026-11-06),
[Marco Geoestadístico](https://www.inegi.org.mx/temas/mg/) (checked 2026-11-06),
[INEGI terms of free use](https://www.inegi.org.mx/inegi/terminos.html) (checked 2026-11-06).

Why these sources, as found on 2026-11-06:

- The Senate's own site (`senado.gob.mx`) refuses automated requests, so senators come from SIL, which is also official.
- There is no current official list of municipal presidents: the federal one
  ([INAFED on datos.gob.mx](https://www.datos.gob.mx/dataset/a67f0a5b-5933-4d7f-8d51-53cb874ffd29/resource/22dec87e-ec40-45e6-9bf7-3065ad1ad7b5/download/presidentes_municipales.csv),
  file dated 2025-07-12, checked 2026-11-06) covers the previous term. Wikipedia's
  lists cover about 2,050 of the 2,478 municipalities; most of the rest are
  in Oaxaca, whose page lists only 152 of 570. The page says how many are missing.
- No single official, current list of governors could be read automatically. The governors' conference domain (`conago.org.mx`) no longer belongs to the conference, and Wikidata's entries were out of date. Wikipedia's list is maintained, so it is used and labelled as a secondary source.

## Every person has a citation

Each record in `web/data/politicians.json` looks like this:

```json
{
  "office": "senator",
  "title": "Senador",
  "name": "Heriberto Marcelo Aguilar Castillo",
  "party": "MORENA",
  "state_code": "26",
  "state": "Sonora",
  "district": "Sonora (mayoría relativa)",
  "term_start": "2024-08-29",
  "term_end": "2030-08-31",
  "term_end_basis": "rule",
  "citation": {
    "source": "sil",
    "url": "http://sil.gobernacion.gob.mx/Librerias/pp_PerfilLegislador.php?SID=&Referencia=9229132",
    "published_at": null,
    "retrieved_at": "2026-11-06T20:07:19Z"
  }
}
```

`retrieved_at` is when the tool read the source. `published_at` is the source's
own date when it states one (Wikipedia revisions do; SIL pages do not).

`term_start` is the day the person took office, as the source lists it (for
legislators, the day they were sworn in). `term_end` comes from the source for
governors (`"term_end_basis": "source"`). SIL does not list it for legislators,
so it is calculated (`"term_end_basis": "rule"`): the whole Senate is renewed
every six years (Article 56 of the Constitution), so the senators of the LXVI
Legislature end on 31 August 2030; the Chamber of Deputies is elected every
three years (Article 51), so its deputies end on 31 August 2027. The justices
elected in 2025 serve, by exception, until 2036 (the five with most votes) or
2033 (the other four), per the third transitional article of the judicial
reform decree of 15 September 2024; the source gives only the year, so
`term_end` is `"2036"` or `"2033"` for them. The articles were read in the
federal legal archive:
[Orden Jurídico Nacional, cn16.pdf](http://www.ordenjuridico.gob.mx/Constitucion/cn16.pdf)
(text with last reform of 2024-11-15, read 2026-11-06).

"District" for a senator is the state plus how the seat was won. The 32
senators elected from the national list have no state. For a deputy it is the
state and district number (300 district seats), or the regional list they were
elected from (200 list seats, which belong to no state).

If a source lists fewer or more people than the law provides for (3 senators
per state, 32 from the national list, one head of government per state), the
tool keeps what the source says and adds a warning, which the page shows under
"Fuentes".

## Notes on the page

- Fonts and libraries are stored in `web/vendor/`, so the page works without
  internet: [D3 7.9.0](https://cdn.jsdelivr.net/npm/d3@7.9.0/dist/d3.min.js),
  [topojson-client 3.1.0](https://cdn.jsdelivr.net/npm/topojson-client@3.1.0/dist/topojson-client.min.js)
  and the [Archivo](https://fonts.google.com/specimen/Archivo) typeface (all downloaded 2026-11-06).
- Party colours follow each party's own colour and were checked together for
  colour-blind readers. The closest pair (MC orange and PVEM green) is only
  moderately separated for red-green colour blindness, so the page never relies
  on colour alone: the legend, the hover box, the side panel and the table all
  name the party.
- The borders are simplified to about 300 m for display. They are not a
  substitute for INEGI's official cartography.

## Being gentle with SIL

SIL is an old server and refuses clients that ask too fast. On 2026-11-06,
reading 500 profile pages 0.3 seconds apart made it answer every request from
this address with an error page. The tool now reads at most 100 profiles per
run, 2 seconds apart, and stops after three refusals in a row. Legislators
whose profile has not been read yet are listed without a district number or
contact details, and the page says how many are pending. Each later run fills
in more; on 2026-11-07 SIL started refusing after about 100 profiles per run,
so the daily workflow needs several days to read all 628.

## Not done yet

- Local deputies.
- Appointment dates for cabinet members (the source has none).
- Inflation per city (INEGI's INPC), once a tokenless table is found.
- Average wage per state (IMSS): its site answers 403 to automated readers, so it is not read.
- If one source is down, the whole refresh fails and the previous data stays;
  the sources are not yet refreshed independently of each other.
- The Wikipedia page titles carry the municipal term's years (`informate/mayors.py`),
  so they must be updated when a state renews its municipalities.
- Publishing the page on the internet. The data files are static, so any static
  host works if the two tools run on a schedule; the "Actualizar datos" button
  needs `tools/serve.py` or an equivalent.
