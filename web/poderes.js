/* Infórmate, Poderes: the Senate, the Chamber of Deputies and the Supreme Court as
   hemicycles with their counts, and the Presidency with its cabinet. Clicking a seat or a
   name shows that person's data. */
(() => {
  "use strict";

  const { el, link, swatch, integer, moment, day, fact, facts, gloss, legislatureLabel, personLine, personCard, samePerson, seatingOrder, drawSeats, chamberCounts, seatTipLines, tooltip, regions, EVERYDAY_NAME, partyOf, sourceValue } = MXD;
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
    const leadership = S.data.congress && S.data.congress[office] ? leadershipRows(office, members) : null;
    figure.querySelector(".chamber__body").replaceChildren(
      ...[
        body.counts === false ? [] : chamberCounts(members, { majorities: body.majorities }),
        head ? facts(fact("Preside", el("button", { type: "button", class: "persona__link", onclick: () => showPerson(head) }, head.name))) : null,
        leadership,
        el("p", { class: "inset__note" }, body.note(listSeats)),
        el("p", { class: "inset__key" }, leadership ? "Pulsa un escaño para ver los datos de quien lo ocupa. Los escaños de borde grueso son de quienes presiden la Mesa Directiva o la Junta de Coordinación Política y de quienes coordinan cada grupo." : "Pulsa un escaño para ver los datos de quien lo ocupa."),
      ].flat(Infinity).filter(Boolean)
    );
    return figure;
  }

  /** Who presides the chamber and the Junta, and who coordinates each group: rows, with each name as the way to the person. */
  function leadershipRows(office, members) {
    const summary = S.data.congress[office];
    const holder = (entry) => members.find((p) => (p.roles || []).some((r) => r.kind === entry.kind && r.role === entry.role && (r.group || null) === (entry.group || null)));
    const nameOf = (entry) => {
      const person = holder(entry);
      return person ? el("button", { type: "button", class: "persona__link", onclick: () => showPerson(person) }, person.name) : el("span", {}, `${entry.name} (no aparece con ese nombre en el padrón del SIL)`);
    };
    const withParty = (entry) => el("span", {}, swatch(entry.party), " ", nameOf(entry));
    const president = summary.board.find((b) => /^president[ea]\b/i.test(b.role)) || null;
    const vices = summary.board.filter((b) => b !== president);
    const jucopo = summary.jucopo_president;
    return [
      el("h3", { class: "chamber__heading" }, gloss("Mesa Directiva"), ` · año legislativo ${summary.period}`),
      facts(
        fact("Preside", president ? withParty(president) : "La fuente no lo indica"),
        vices.length ? fact("Vicepresidencias", el("ul", { class: "plain" }, vices.map((v) => el("li", {}, withParty(v), ` (${v.role.toLowerCase()})`)))) : null,
        fact("Periodo", `${day(summary.start)} a ${day(summary.end)}`)
      ),
      el("h3", { class: "chamber__heading" }, gloss("Junta de Coordinación Política")),
      facts(
        fact("Preside", jucopo ? el("span", {}, withParty(jucopo), ` · su grupo tiene mayoría absoluta por sí solo: ${integer.format(jucopo.seats)} de ${integer.format(jucopo.total)} escaños`) : "Ningún grupo tiene mayoría absoluta por sí solo; la presidencia se turna cada año y la fuente no dice a quién toca"),
        fact("Grupos parlamentarios", el("ul", { class: "plain" }, summary.coordinators.map((c) => el("li", {}, swatch(c.group), ` ${partyOf(c.group).label}: `, nameOf(c)))))
      ),
      el("p", { class: "inset__note" }, "Estos cargos según ", sourceValue(summary.citation)),
    ];
  }

  /** One autonomous body: its head (the way to the person), the post, its dates, what the body does and its legal basis. */
  function autonomousBlock(body) {
    const person = peopleOf("autonomous_head").find((p) => p.body_key === body.key) || null;
    return el(
      "div",
      { class: "autonomous__body" },
      el("h3", {}, body.name === body.short ? body.name : `${body.name} (${body.short})`),
      facts(
        fact("Titular", person ? el("button", { type: "button", class: "persona__link", onclick: () => showPerson(person) }, person.name) : body.head),
        fact("Cargo", body.head_title),
        person && person.provisional ? fact("Designación", "Provisional, según la fuente") : null,
        fact("Desde", person && person.term_start ? day(person.term_start) : "Sin dato en la fuente"),
        person ? fact("Fin del periodo", person.term_end ? `${day(person.term_end)} (regla legal)` : person.term_end_note) : null,
        fact("Qué hace", body.mandate),
        fact("Fundamento", body.basis),
        fact("Nombramiento", body.appointment),
        fact("Duración del cargo", body.term),
        person ? fact("Fuente", sourceValue(person.citation)) : null
      )
    );
  }

  function renderChambers() {
    const grid = $("#grid");
    grid.replaceChildren(
      ...POWERS.map((power) =>
        el(
          "section",
          { class: "power" },
          el("h2", { class: "power__title" }, power.title, power.title === "Poder Legislativo" && legislatureLabel(S.data) ? el("span", { class: "power__when" }, " · ", gloss(legislatureLabel(S.data))) : null),
          power.intro ? el("p", { class: "ficha__intro" }, gloss(power.intro)) : null,
          power.title === "Poder Ejecutivo" ? executive() : el("div", { class: `overview__grid overview__grid--${power.bodies.length}` }, power.bodies.map(chamber))
        )
      ),
      S.data.autonomous && S.data.autonomous.length
        ? el(
            "section",
            { class: "power" },
            el("h2", { class: "power__title" }, gloss("Órganos constitucionales autónomos")),
            el("p", { class: "ficha__intro" }, gloss("Instituciones que la Constitución crea fuera de los tres poderes, con presupuesto y titulares propios. Hoy son cinco; aquí está quién encabeza cada una, hasta cuándo y con qué fundamento.")),
            el("div", { class: "autonomous" }, S.data.autonomous.map(autonomousBlock))
          )
        : null
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
    const presidesChamber = (office, label) => {
      const summary = S.data.congress && S.data.congress[office];
      const entry = summary && summary.board.find((b) => /^president[ea]\b/i.test(b.role));
      return entry ? fact(label, entry.name) : null;
    };
    const headOf = (key) => peopleOf("autonomous_head").find((p) => p.body_key === key) || null;
    box.replaceChildren(
      el("h2", { class: "ficha__place" }, "Poderes de la Nación"),
      el("h3", {}, "Poder Legislativo"),
      facts(
        legislatureLabel(S.data) ? fact("Legislatura", legislatureLabel(S.data)) : null,
        fact("Senado", `${count("senator")} escaños`),
        presidesChamber("senator", "Preside el Senado"),
        fact("Cámara de Diputados", `${count("deputy")} escaños`),
        presidesChamber("deputy", "Preside la Cámara de Diputados")
      ),
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
      ...(S.data.autonomous && S.data.autonomous.length ? [el("h3", {}, gloss("Órganos constitucionales autónomos")), facts(S.data.autonomous.map((b) => fact(b.short, name(headOf(b.key)))))] : []),
      el("p", { class: "ficha__intro" }, "Pulsa un escaño o un nombre para ver los datos de esa persona: cargo, partido, entidad, periodo, contacto oficial y fuente.")
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
    S.ctx = { stateName, legislature: S.data.legislature || null, ...regions(S.data, stateName) };
    tip = tooltip($("#tooltip"), $("#chambers"));
    $("#data-date").textContent = `Cargos consultados el ${moment.format(new Date(S.data.generated_at))}.`;
    renderChambers();
    renderFicha();
  }

  start();
})();
