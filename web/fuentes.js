/* Infórmate, Fuentes: every source behind the site, with the date each was read. */
(() => {
  "use strict";

  const { el, link, integer, moment, day, EVERYDAY_NAME } = MXD;
  const $ = (selector) => document.querySelector(selector);
  const block = (title, kind, ...body) => el("div", { class: "source" }, el("div", {}, el("h3", {}, title), el("p", { class: "source__kind" }, kind)), el("div", { class: "source__body" }, body.flat(Infinity).filter(Boolean)));
  const read = (c) => `${c.published_at ? `, ${/^\d{4}-\d{2}-\d{2}$/.test(c.published_at) ? "publicado el" : "versión del"} ${day(c.published_at)}` : ""}; consultado el ${day(c.retrieved_at)}.`;

  async function start() {
    const getJSON = async (url, optional = false) => {
      const response = await fetch(url);
      if (!response.ok) {
        if (optional) return null;
        throw new Error(`${url}: ${response.status}`);
      }
      return response.json();
    };
    let data, map, gdp, crime, fuel, economy, capitals, cities, districtIndex, heritage;
    try {
      [data, map, gdp, crime, fuel, economy, capitals, cities, districtIndex, heritage] = await Promise.all([
        getJSON("data/politicians.json"),
        getJSON("data/map_source.json"),
        getJSON("data/gdp.json", true),
        getJSON("data/crime.json", true),
        getJSON("data/fuel.json", true),
        getJSON("data/economy.json", true),
        getJSON("data/capitals.json", true),
        getJSON("data/cities.json", true),
        getJSON("data/distritos_municipios.json", true),
        getJSON("data/patrimonio.json", true),
      ]);
    } catch (error) {
      const notice = $("#load-error");
      notice.hidden = false;
      notice.textContent = `No se pudieron cargar los datos (${error.message}).`;
      return;
    }
    const stateName = (code) => EVERYDAY_NAME[code] || (map.states.find((s) => s.cve_ent === code) || {}).name || code;
    const { sil, wikipedia, wikipedia_scjn: court, wikipedia_tepjf: electoral, wikipedia_tdj: discipline, wikipedia_president: presidency, wikipedia_cabinet: cabinet, wikipedia_mayors: mayorPages, wikipedia_congress: annex, wikipedia_autonomous: autonomousPages } = data.sources;
    const rules = data.rules;
    const ine = map.districts;
    const regions = data.circunscripciones;
    $("#data-date").textContent = `Cargos consultados el ${moment.format(new Date(data.generated_at))}.`;
    $("#sources").replaceChildren(
      ...[
        block(
          "Mapa de municipios y población",
          "Fuente oficial",
          el("p", {}, `${map.edition}. ${integer.format(map.municipality_count)} municipios en ${map.states.length} entidades.`),
          el("p", {}, `Los límites se descargaron del servicio web del INEGI, entidad por entidad, el ${day(map.retrieved_at)}. ${map.processing_note}`),
          el("p", {}, `Población, mujeres y hombres y viviendas habitadas: ${map.population_source}, del mismo servicio. ${map.municipalities_without_population.length} municipios creados después de ese censo no tienen cifra propia.`),
          el("details", {}, el("summary", {}, `Los ${map.states.length} enlaces de descarga, consultados el ${day(map.retrieved_at)}`), el("ul", {}, map.states.map((s) => el("li", {}, link(s.url, `${stateName(s.cve_ent)}: ${s.municipalities} municipios`))))),
          el("ul", { class: "cite" }, (map.reference_links || []).map((r) => el("li", {}, link(r.url, r.label), `, enlace revisado el ${day(r.checked_at)}.`)))
        ),
        ine
          ? block(
              "Mapa de distritos electorales federales",
              "Fuente oficial",
              el("p", {}, `${ine.attribution}: la capa ${ine.layer} del archivo publicado por el INE, con ${ine.district_count} distritos federales (distritación de 2023).`),
              el("p", { class: "cite" }, link(ine.url, "Archivo de shapefiles del Marco Geográfico Seccional"), `, con fecha del ${day(ine.published_at)}; descargado el ${day(ine.retrieved_at)}. Límites simplificados para visualización.`)
            )
          : null,
        districtIndex
          ? block(
              "Municipios de cada distrito",
              "Cálculo propio sobre dos fuentes oficiales",
              el("p", {}, districtIndex.method),
              el("p", { class: "cite" }, `Distritos: ${districtIndex.sources.districts.name}, archivo del ${day(districtIndex.sources.districts.published_at)}, descargado el ${day(districtIndex.sources.districts.retrieved_at)}. Municipios: ${districtIndex.sources.municipalities.name}. Calculado el ${day(districtIndex.generated_at)}.`)
            )
          : null,
        heritage
          ? block(
              "Pueblos Mágicos y Patrimonio Mundial",
              "Fuente secundaria y fuente oficial",
              el("p", {}, "Pueblos Mágicos: ", link(heritage.pueblos.citation.url, heritage.pueblos.citation.source_name), read(heritage.pueblos.citation), ` ${heritage.pueblos.count} localidades, con la fecha en que cada una entró al programa y sus coordenadas, tomadas de los mapas del anexo. El programa es de la `, link(heritage.pueblos.citation.programme_url, "Secretaría de Turismo"), ", que no publica la lista en una forma que pueda leerse automáticamente."),
              el("p", {}, "Patrimonio Mundial: ", link(heritage.unesco.citation.url, heritage.unesco.citation.source_name), `; consultada el ${day(heritage.unesco.citation.retrieved_at)}. ${heritage.unesco.count} sitios, con su categoría, año de inscripción y cada uno de los puntos que la UNESCO les asigna.`),
              heritage.warnings.length ? el("ul", {}, heritage.warnings.map((w) => el("li", {}, w))) : null
            )
          : null,
        capitals ? block("Capitales de las entidades", "Fuente secundaria", el("p", {}, link(capitals.citation.url, capitals.citation.source_name), read(capitals.citation)), el("p", {}, "Cada capital se ubica en su municipio según el catálogo del INEGI; las capitales cuyo municipio tiene otro nombre (Villahermosa en Centro, Chetumal en Othón P. Blanco…) están emparejadas una por una.")) : null,
        cities ? block("Ciudades de más de 100 mil habitantes", "Fuente secundaria", el("p", {}, link(cities.citation.url, cities.citation.source_name), read(cities.citation)), el("p", {}, `Población de cada ciudad según la ${cities.population_source}, como la da la página; es la ciudad, no el municipio. Cada ciudad se ubica en su municipio del INEGI.`)) : null,
        gdp ? block("PIB por entidad", "Fuente oficial", el("p", {}, link(gdp.citation.url, gdp.citation.source_name), read(gdp.citation)), el("p", {}, `Cifras en ${gdp.unit}; el PIB por habitante divide esa cifra entre la población del Censo 2020. El INEGI no publica PIB por municipio ni por distrito.`)) : null,
        economy
          ? block(
              "Salario mínimo, empleo, ingresos y pobreza",
              "Fuentes oficiales",
              el("p", {}, "Salario mínimo: ", link(economy.minimum_wage.citation.url, economy.minimum_wage.citation.source_name), read(economy.minimum_wage.citation), ` La Zona Libre de la Frontera Norte son los ${economy.minimum_wage.border_municipalities.length} municipios que la tabla enumera.`),
              el("p", {}, "Empleo (ocupación, desocupación, informalidad): ", link(economy.employment.citation.url, economy.employment.citation.source_name), read(economy.employment.citation), ` Próxima entrega: ${day(economy.employment.next_release)}.`),
              el("p", {}, "Ingresos de las personas ocupadas, en bandas de salario mínimo: ", link(economy.income.citation.url, economy.income.citation.source_name), read(economy.income.citation), " Un comunicado por entidad; cada entidad enlaza al suyo desde sus datos. El salario promedio por entidad lo publica el IMSS, cuyo sitio no admite lecturas automáticas, así que no se muestra."),
              el("p", {}, "Pobreza: ", link(economy.poverty.citation.url, economy.poverty.citation.source_name), read(economy.poverty.citation))
            )
          : null,
        crime
          ? block(
              "Homicidios dolosos y feminicidios",
              "Fuente oficial",
              el("p", {}, link(crime.citation.url, crime.citation.source_name), `, página del ${day(crime.citation.published_at)}; archivos descargados el ${day(crime.citation.retrieved_at)}.`),
              el("p", {}, `Víctimas registradas por las fiscalías de ${crime.period} y de todo ${crime.previous_year}, por entidad y por municipio. Las tasas por cada 100 mil habitantes usan la población del Censo 2020. Un municipio sin registros no aparece en los archivos.`),
              el("ul", {}, crime.citation.files.map((f) => el("li", {}, link(f.url, f.label))))
            )
          : null,
        fuel ? block("Precios de gasolina y diésel", "Fuente oficial", el("p", {}, link(fuel.citation.url, fuel.citation.source_name), `; consultado el ${day(fuel.citation.retrieved_at)}.`), el("p", {}, "Promedio simple de los precios reportados por las estaciones con precio, cada una ubicada en su municipio con los límites del INEGI; se actualiza a diario. La lista de estaciones está en ", link(fuel.citation.places_url, "el archivo de ubicaciones"), ".")) : null,
        block(
          "Senado y Cámara de Diputados",
          "Fuente oficial",
          el("p", {}, `${sil.name}; consultado el ${day(sil.retrieved_at)}.`),
          el("ul", {}, el("li", {}, link(sil.url, "Senado: integrantes de la LXVI Legislatura"), `, consultado el ${day(sil.retrieved_at)}.`), sil.deputies_url ? el("li", {}, link(sil.deputies_url, "Cámara de Diputados: integrantes de la LXVI Legislatura"), `, consultado el ${day(sil.retrieved_at)}.`) : null),
          el("p", {}, "Cada persona enlaza a su ficha en el SIL, que la Secretaría de Gobernación compila a partir de fuentes públicas. De esa ficha salen el distrito o la circunscripción, los estudios y el correo, teléfono y oficina oficiales.")
        ),
        block("Gobiernos de las entidades", "Fuente secundaria", el("p", {}, link(wikipedia.url, wikipedia.name), `, versión del ${day(wikipedia.published_at)}; consultada el ${day(wikipedia.retrieved_at)}.`), el("p", {}, "No hay una lista oficial, única y vigente de quienes encabezan los gobiernos estatales que pueda consultarse de forma automática; se cita la versión exacta de Wikipedia que se leyó.")),
        mayorPages
          ? block(
              "Presidencias municipales y alcaldías",
              "Fuente secundaria",
              el("p", {}, `${mayorPages.name}; consultados el ${day(mayorPages.retrieved_at)}.`),
              el("p", {}, "La lista del gobierno federal corresponde al periodo anterior, así que se cita la versión exacta de cada anexo de Wikipedia que se leyó."),
              el("details", {}, el("summary", {}, `Los ${mayorPages.pages.length} anexos`), el("ul", {}, mayorPages.pages.map((page) => el("li", {}, link(page.url, stateName(page.state_code)), `, versión del ${day(page.published_at)}.`))))
            )
          : null,
        presidency ? block("Presidencia de la República", "Fuente secundaria", el("p", {}, link(presidency.url, presidency.name), `, versión del ${day(presidency.published_at)}; consultada el ${day(presidency.retrieved_at)}.`), el("p", {}, "El artículo sobre el cargo dice quién lo ocupa y desde cuándo; el partido se toma del artículo de la persona titular.")) : null,
        cabinet ? block("Gabinete", "Fuente secundaria", el("p", {}, link(cabinet.url, cabinet.name), `, versión del ${day(cabinet.published_at)}; consultada el ${day(cabinet.retrieved_at)}.`), el("p", {}, "La tabla «Gabinete legal» del artículo lista las dependencias del Ejecutivo federal con sus titulares; no da fechas de nombramiento.")) : null,
        court || electoral || discipline
          ? block(
              "Poder Judicial",
              "Fuentes secundarias",
              court ? el("p", {}, "Suprema Corte: ", link(court.url, court.name), `, versión del ${day(court.published_at)}; consultada el ${day(court.retrieved_at)}.`) : null,
              electoral ? el("p", {}, "Tribunal Electoral, Sala Superior: ", link(electoral.url, electoral.name), `, versión del ${day(electoral.published_at)}; consultada el ${day(electoral.retrieved_at)}.`) : null,
              discipline ? el("p", {}, "Tribunal de Disciplina Judicial: ", link(discipline.url, discipline.name), `, versión del ${day(discipline.published_at)}; consultada el ${day(discipline.retrieved_at)}.`) : null,
              el("p", {}, "Los sitios de estos órganos no responden a consultas automáticas desde fuera de México; se usan los artículos de Wikipedia, citados en la versión exacta que se leyó.")
            )
          : null,
        annex
          ? block(
              "Mesa Directiva y coordinaciones de grupo en cada cámara",
              "Fuente secundaria",
              el("p", {}, link(annex.url, annex.name), `, versión del ${day(annex.published_at)}; consultada el ${day(annex.retrieved_at)}.`),
              el("p", {}, "Los sitios del Senado y de la Cámara rechazan las consultas automáticas, así que quién preside la Mesa Directiva y quién coordina cada grupo parlamentario se leen del anexo de Wikipedia sobre la legislatura, citado en su versión exacta. Quién preside la Junta de Coordinación Política no se copia de ahí: lo fija la Ley Orgánica del Congreso a partir de los escaños de cada grupo (regla más abajo).")
            )
          : null,
        autonomousPages
          ? block(
              "Órganos constitucionales autónomos",
              "Fuente secundaria",
              el("p", {}, `${autonomousPages.name}; consultados el ${day(autonomousPages.retrieved_at)}.`),
              el("ul", {}, autonomousPages.pages.map((page) => el("li", {}, link(page.url, page.body), `, versión del ${day(page.published_at)}; `, link(page.person_url, "artículo de la persona titular"), `, versión del ${day(page.person_published_at)}.`))),
              el("p", {}, "El artículo de cada órgano dice quién lo encabeza; el de la persona, desde cuándo. La duración de cada cargo sale de la Constitución y de las leyes, no de Wikipedia (reglas más abajo)."),
              data.autonomous && data.autonomous.length
                ? el("p", {}, "Logotipos, tomados de Wikimedia Commons: ", data.autonomous.map((b, i) => [i ? "; " : "", link(b.logo.url, b.short), ` (${b.logo.author}, ${b.logo.license_url ? "" : ""}`, b.logo.license_url ? link(b.logo.license_url, b.logo.license) : b.logo.license, `; descargado el ${day(b.logo.retrieved_at)})`]), ".")
                : null
            )
          : null,
        regions ? block("Circunscripciones de la Cámara de Diputados", "Fuente secundaria", el("p", {}, "Las 200 diputaciones de lista se eligen en cinco circunscripciones. La composición vigente se tomó de ", link(regions.source.url, regions.source.name), `, versión del ${day(regions.source.published_at)}; enlace revisado el ${day(regions.source.checked_at)}.`), el("ul", {}, regions.list.map((r) => el("li", {}, `${r.name} (cabecera ${r.seat}): ${r.states.map(stateName).join(", ")}.`)))) : null,
        block(
          "Fechas de inicio y de término de los cargos",
          "Fuentes citadas y reglas constitucionales",
          el("p", {}, "La fecha de inicio viene de la fuente de cada persona. Las fuentes del Congreso, de la Presidencia, de los órganos judiciales y de los órganos autónomos no dan el final del periodo, que se calcula con estas reglas:"),
          Object.values(rules).map((rule) => [el("p", {}, rule.text), el("p", { class: "cite" }, link(rule.url, rule.source_name), `, texto con última reforma del ${day(rule.published_at)}; enlace revisado el ${day(rule.checked_at)}.`)])
        ),
        data.warnings.length ? block("Avisos", "Diferencias entre lo que listan las fuentes y lo que marca la ley, y lo que falta por leer", el("ul", {}, data.warnings.map((w) => el("li", {}, w)))) : null,
      ].filter(Boolean)
    );
  }

  start();
})();
