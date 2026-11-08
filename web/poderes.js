/* México en datos, Poderes: the Senate, the Chamber of Deputies and the Supreme Court as
   hemicycles with their counts, and the Presidency with its cabinet. Clicking a seat or a
   name shows that person's data. */
(() => {
  "use strict";

  const { el, link, swatch, integer, moment, day, fact, facts, personLine, personCard, samePerson, seatingOrder, drawSeats, chamberCounts, seatTipLines, tooltip, regions, EVERYDAY_NAME } = MXD;
  const $ = (selector) => document.querySelector(selector);
  const S = { data: null, mapSource: null, person: null, ctx: null };

  const BODIES = {
    senator: { title: (n) => `Senado: ${n} escaños`, majorities: true, note: (list) => `${list} de lista nacional, sin entidad.` },
    deputy: { title: (n) => `Cámara de Diputados: ${n} escaños`, majorities: true, note: (list) => `${list} de listas regionales, por circunscripción (sombreadas).` },
    justice: { title: (n) => `Suprema Corte de Justicia de la Nación: ${n} ministras y ministros`, counts: false, note: () => "Elegidos por voto popular en 2025." },
    magistrate_tepjf: { title: (n) => `Tribunal Electoral, Sala Superior: 7 magistraturas${n < 7 ? `, ${7 - n} vacante${7 - n > 1 ? "s" : ""}` : ""}`, counts: false, seats: 7, vacant: "Escaño vacante desde el 31 de octubre de 2025, según la fuente", note: () => "Cinco en funciones desde 2016 y dos elegidas por voto en 2025." },
    magistrate_tdj: { title: (n) => `Tribunal de Disciplina Judicial: ${n} magistraturas`, counts: false, note: () => "Elegidas por voto popular en 2025." },
  };
  const POWERS = [
    { title: "Poder Legislativo", bodies: ["senator", "deputy"], intro: "El Congreso de la Unión: dos cámaras." },
    { title: "Poder Ejecutivo", bodies: [], intro: null },
    { title: "Poder Judicial", bodies: ["justice", "magistrate_tepjf", "magistrate_tdj"], intro: "Lo integran la Suprema Corte, el Tribunal Electoral, el Tribunal de Disciplina Judicial y el Órgano de Administración Judicial; los tres primeros se eligen por voto." },
  ];
  const presides = (office) => peopleOf(office).find((p) => /presidenta|presidente/i.test(p.title)) || null;

  const peopleOf = (office) => S.data.people.filter((p) => p.office === office);
  const stateName = (code) => EVERYDAY_NAME[code] || (S.mapSource.states.find((s) => s.cve_ent === code) || {}).name || code;
  let tip;

  function markChosen() {
    d3.selectAll("#grid .seat")
      .classed("seat--chosen", (d) => samePerson(d.person, S.person))
      .filter((d) => samePerson(d.person, S.person))
      .raise();
  }

  function showPerson(person) {
    S.person = person;
    markChosen();
    renderFicha();
    $("#ficha").scrollIntoView({ block: "nearest", behavior: MXD.motionOK ? "smooth" : "auto" });
  }

  /** One body as a figure: caption, seats, counts and notes. */
  function chamber(office) {
    const body = BODIES[office];
    const members = seatingOrder(peopleOf(office));
    const seats = body.seats && members.length < body.seats
      ? members.concat(Array.from({ length: body.seats - members.length }, () => ({ office, party: null, name: "Vacante", placeholder: true, note: body.vacant })))
      : members;
    const figure = el("figure", { class: "chamber overview__panel" }, el("figcaption", {}, body.title(members.length)), document.createElementNS("http://www.w3.org/2000/svg", "svg"), el("div", { class: "chamber__body" }));
    const placed = drawSeats(figure.querySelector("svg"), seats, {
      office,
      onPick: (person) => !person.placeholder && showPerson(person),
      onHover: (event, person) => tip.show(event, `${person.office}${person.name}${person.placeholder ? "vacante" : ""}`, () => seatTipLines(person, S.ctx)),
      onLeave: () => tip.hide(),
    });
    const listSeats = placed.filter((d) => !d.person.state_code && !d.person.placeholder).length;
    const head = presides(office);
    figure.querySelector(".chamber__body").replaceChildren(
      ...[
        body.counts === false ? [] : chamberCounts(members, { majorities: body.majorities }),
        head ? facts(fact("Preside", el("button", { type: "button", class: "persona__link", onclick: () => showPerson(head) }, head.name))) : null,
        el("p", { class: "inset__note" }, body.note(listSeats)),
        el("p", { class: "inset__key" }, "Pulsa un escaño para ver los datos de quien lo ocupa."),
      ].flat(Infinity).filter(Boolean)
    );
    return figure;
  }

  function renderChambers() {
    const grid = $("#grid");
    grid.replaceChildren(
      ...POWERS.map((power) =>
        el(
          "section",
          { class: "power" },
          el("h2", { class: "power__title" }, power.title),
          power.intro ? el("p", { class: "ficha__intro" }, power.intro) : null,
          power.title === "Poder Ejecutivo" ? executive() : el("div", { class: `overview__grid overview__grid--${power.bodies.length}` }, power.bodies.map(chamber))
        )
      )
    );
    markChosen();
  }

  /** The Presidency and the cabinet. */
  function executive() {
    const president = peopleOf("president")[0];
    const cabinet = peopleOf("secretary");
    const vacancies = S.data.warnings.filter((w) => w.startsWith("Gabinete:"));
    return el(
      "div",
      { class: "chain" },
      president ? el("ul", { class: "people" }, personLine(president, showPerson)) : el("p", { class: "ficha__intro" }, "La fuente no indica quién ocupa la Presidencia."),
      el("h3", {}, `Dependencias del gabinete: ${cabinet.length} titulares`),
      el(
        "ol",
        { class: "chain__list" },
        cabinet.map((p) => el("li", {}, el("span", { class: "chain__office" }, p.title), el("button", { type: "button", class: "chain__name persona__link", onclick: () => showPerson(p) }, p.name)))
      ),
      vacancies.length ? facts(vacancies.map((w) => fact("Vacante", w.replace(/^Gabinete: la fuente muestra vacante /, "")))) : null,
      cabinet.length ? facts(fact("Fuente", MXD.sourceValue(cabinet[0].citation)), fact("Fecha de nombramiento", "La fuente no la da")) : null
    );
  }

  function renderFicha() {
    const box = $("#ficha");
    if (S.person) {
      box.replaceChildren(
        ...personCard(S.person, S.ctx).flat(Infinity),
        el("p", { class: "ficha__back" }, el("button", { type: "button", class: "link-button", onclick: () => { S.person = null; markChosen(); renderFicha(); } }, "Volver al resumen"))
      );
      return;
    }
    const count = (office) => peopleOf(office).length;
    const name = (person) => (person ? person.name : "Sin dato en la fuente");
    box.replaceChildren(
      el("h2", { class: "ficha__place" }, "Poderes de la Nación"),
      el("h3", {}, "Poder Legislativo"),
      facts(fact("Senado", `${count("senator")} escaños`), fact("Cámara de Diputados", `${count("deputy")} escaños`)),
      el("h3", {}, "Poder Ejecutivo"),
      facts(fact("Presidencia de la República", name(peopleOf("president")[0])), fact("Gabinete", `${count("secretary")} titulares`)),
      el("h3", {}, "Poder Judicial"),
      facts(
        fact("Suprema Corte", `${count("justice")} ministras y ministros`),
        fact("Preside la Corte", name(presides("justice"))),
        fact("Tribunal Electoral, Sala Superior", `${count("magistrate_tepjf")} de 7 magistraturas ocupadas`),
        fact("Preside el Tribunal Electoral", name(presides("magistrate_tepjf"))),
        fact("Tribunal de Disciplina Judicial", `${count("magistrate_tdj")} magistraturas`),
        fact("Preside el Tribunal de Disciplina", name(presides("magistrate_tdj")))
      ),
      el("p", { class: "ficha__intro" }, "Pulsa un escaño o un nombre para ver los datos de esa persona: cargo, partido, entidad, periodo, contacto oficial y fuente.")
    );
  }

  function renderSources() {
    const { sil, wikipedia_scjn: court, wikipedia_tepjf: electoral, wikipedia_tdj: discipline, wikipedia_president: presidency, wikipedia_cabinet: cabinet } = S.data.sources;
    const item = (what, source, extra = "") => el("li", {}, `${what}: `, link(source.url, source.name), source.published_at ? `, versión del ${day(source.published_at)}` : "", `; consultada el ${day(source.retrieved_at)}.${extra}`);
    $("#sources-body").replaceChildren(
      el("ul", { class: "sources__list" }, item("Senadurías y diputaciones, con sus datos de contacto", sil), court ? item("Suprema Corte", court, " Fuente secundaria.") : null, electoral ? item("Tribunal Electoral, Sala Superior", electoral, " Fuente secundaria.") : null, discipline ? item("Tribunal de Disciplina Judicial", discipline, " Fuente secundaria.") : null, presidency ? item("Presidencia", presidency, " Fuente secundaria.") : null, cabinet ? item("Gabinete", cabinet, " Fuente secundaria; sin fechas de nombramiento.") : null),
      el("p", { class: "ficha__intro" }, "Las fechas de término salen de la Constitución; ", el("a", { href: "mapas-politicos.html#fuentes" }, "el detalle está en Mapas políticos"), ".")
    );
  }

  async function start() {
    const getJSON = async (url) => {
      const response = await fetch(url);
      if (!response.ok) throw new Error(`${url}: ${response.status}`);
      return response.json();
    };
    try {
      [S.data, S.mapSource] = await Promise.all([getJSON("data/politicians.json"), getJSON("data/map_source.json")]);
    } catch (error) {
      const notice = $("#load-error");
      notice.hidden = false;
      notice.textContent = `No se pudieron cargar los datos (${error.message}). Genera los archivos con «python tools/fetch_politicians.py» y abre la página con «python tools/serve.py».`;
      return;
    }
    S.ctx = { stateName, ...regions(S.data, stateName) };
    tip = tooltip($("#tooltip"), $("#chambers"));
    $("#data-date").textContent = `Cargos consultados el ${moment.format(new Date(S.data.generated_at))}.`;
    renderChambers();
    renderFicha();
    renderSources();
  }

  start();
})();
