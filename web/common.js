/* México en datos: what the three pages share. Party colours and labels, small DOM and
   formatting helpers, one person's entry (a line, or the full set of rows), the hemicycle
   drawing, and the hover box. Exposed as window.MXD; each page keeps its own state. */
window.MXD = (() => {
  "use strict";

  // Party colours are defined once, in style.css; here only the labels and order.
  const PARTIES = {
    MORENA: { label: "Morena", color: "var(--morena)" },
    PAN: { label: "PAN", color: "var(--pan)" },
    PRI: { label: "PRI", color: "var(--pri)" },
    PVEM: { label: "PVEM", color: "var(--pvem)" },
    PT: { label: "PT", color: "var(--pt)" },
    MC: { label: "MC", color: "var(--mc)" },
    OTRO: { label: "Otros partidos", color: "var(--otro)" },
    SP: { label: "Sin partido", color: "var(--sp)" },
  };
  const PARTY_ORDER = Object.keys(PARTIES);
  // Everyday names where INEGI's official name is long or ambiguous.
  const EVERYDAY_NAME = { "05": "Coahuila", "15": "Estado de México", "16": "Michoacán", "30": "Veracruz" };
  const SOURCE_SHORT = {
    sil: "SIL, Secretaría de Gobernación",
    wikipedia: "Wikipedia en español",
    wikipedia_mayors: "Wikipedia en español",
    wikipedia_scjn: "Wikipedia en español",
    wikipedia_president: "Wikipedia en español",
    wikipedia_cabinet: "Wikipedia en español",
    wikipedia_tepjf: "Wikipedia en español",
    wikipedia_tdj: "Wikipedia en español",
  };
  const OFFICE_BODY = {
    senator: "Poder Legislativo: Senado",
    deputy: "Poder Legislativo: Cámara de Diputados",
    justice: "Poder Judicial: Suprema Corte de Justicia de la Nación",
    magistrate_tepjf: "Poder Judicial: Tribunal Electoral, Sala Superior",
    magistrate_tdj: "Poder Judicial: Tribunal de Disciplina Judicial",
    governor: "Poder Ejecutivo del estado",
    mayor: "Ayuntamiento",
    president: "Poder Ejecutivo federal",
    secretary: "Poder Ejecutivo federal: gabinete",
  };

  // ---------- DOM and formatting ----------

  function el(tag, props = {}, ...children) {
    const node = document.createElement(tag);
    for (const [key, value] of Object.entries(props)) {
      if (value == null || value === false) continue;
      if (key === "class") node.className = value;
      else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
      else node.setAttribute(key, value === true ? "" : value);
    }
    for (const child of children.flat(Infinity)) if (child != null && child !== false) node.append(child);
    return node;
  }

  const link = (url, text) => el("a", { href: url, target: "_blank", rel: "noopener noreferrer" }, text);
  const partyOf = (code) => PARTIES[code] || PARTIES.SP;
  const partyRank = (code) => (PARTY_ORDER.includes(code) ? PARTY_ORDER.indexOf(code) : PARTY_ORDER.length);
  /** A party's name for a person: small parties keep their own name; offices without party say so. */
  const partyLabel = (person) => ((person.party === "OTRO" || person.party === "SP") && person.party_name ? person.party_name : partyOf(person.party).label);
  const swatch = (party) => el("span", { class: "swatch", style: `--c: ${partyOf(party).color}`, "aria-hidden": "true" });
  const fold = (text) => text.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  const capitalise = (text) => text.charAt(0).toUpperCase() + text.slice(1);

  const integer = new Intl.NumberFormat("es-MX");
  const signed = new Intl.NumberFormat("es-MX", { signDisplay: "exceptZero", minimumFractionDigits: 1, maximumFractionDigits: 1 });
  const oneDecimal = new Intl.NumberFormat("es-MX", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  const dayLocal = new Intl.DateTimeFormat("es-MX", { day: "numeric", month: "short", year: "numeric" });
  const dayUTC = new Intl.DateTimeFormat("es-MX", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });
  const moment = new Intl.DateTimeFormat("es-MX", { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit", hourCycle: "h23" });
  /** "2022-10-01" is a calendar date; "2026-11-06T20:07:19Z" is an instant shown in the reader's time zone. */
  const day = (iso) => (!iso ? "" : iso.length === 4 ? iso : iso.length === 10 ? dayUTC.format(new Date(`${iso}T00:00:00Z`)) : dayLocal.format(new Date(iso)));
  const motionOK = !window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /** One row of a facts list: label and value. Null when there is no value. */
  const fact = (label, value) => (value == null || value === "" ? null : [el("dt", {}, label), el("dd", {}, value)]);
  const facts = (...rows) => el("dl", { class: "facts" }, rows.flat(Infinity).filter(Boolean));

  /** The value of a "Fuente" row: the source, its version date and the day it was read. */
  function sourceValue(c) {
    const version = c.published_at ? `, versión del ${day(c.published_at)}` : "";
    const secondary = c.source.startsWith("wikipedia") ? " (fuente secundaria)" : "";
    return el("span", {}, link(c.url, SOURCE_SHORT[c.source] || c.source_name), `${version}; consultada el ${day(c.retrieved_at)}${secondary}`);
  }

  // ---------- One person ----------

  const NO_PARTY = new Set(["justice", "magistrate_tepjf", "magistrate_tdj", "secretary"]);
  const samePerson = (a, b) => Boolean(a && b) && a.office === b.office && a.name === b.name && a.district === b.district;
  /** "distrito 4 (Saltillo)" read off the end of the district label. */
  const districtOf = (person) => (person.district || "").slice(person.district.indexOf("distrito"));

  /** What a person's line says after the name: office and party, plus how they were elected. */
  function roleText(person) {
    const party = NO_PARTY.has(person.office) ? null : partyLabel(person);
    const how = person.office === "senator" || person.office === "deputy" ? person.election_type : null;
    return [person.title, party, how].filter(Boolean).join(" · ");
  }

  /** A compact entry: colour, name (a button that opens the details) and role. */
  function personLine(person, onOpen, extra = null) {
    return el(
      "li",
      { class: "person-line" },
      swatch(person.party),
      el("div", { class: "person-line__text" }, el("button", { type: "button", class: "persona__link person-line__name", onclick: () => onOpen(person) }, person.name), el("span", { class: "person-line__role" }, extra ? `${roleText(person)} · ${extra}` : roleText(person)))
    );
  }

  /** Every fact about a person as its own row. `ctx` names places: stateName(code), regionByNumber(n), regionStates(region). */
  function personRows(person, ctx) {
    const legislator = person.office === "senator" || person.office === "deputy";
    const region = person.office === "deputy" && person.region_number ? ctx.regionByNumber(person.region_number) : null;
    let where = person.state_code ? ctx.stateName(person.state_code) : null;
    if (!where && person.office === "senator") where = "Ninguna: lista nacional";
    if (!where && person.office === "deputy") where = region ? "Ninguna: lista regional" : "Lista regional; la circunscripción aún no se ha leído de la fuente";
    const seat = person.office === "deputy" && person.district_number ? districtOf(person).replace(/^distrito /, "") : null;
    const election = person.election_type ? person.election_type + (person.seat_status === "Suplente" ? ", suplente en funciones" : "") : null;
    const ruled = person.term_end_basis === "rule" ? " (regla constitucional)" : "";
    const contact = person.contact || null;
    const contactNote = legislator ? "Aún no leído de su ficha en el SIL; aparecerá en una próxima actualización" : "La fuente no lo publica para este cargo";
    const party = NO_PARTY.has(person.office) ? null : el("span", {}, swatch(person.party), ` ${partyLabel(person)}`);
    return [
      fact("Cargo", person.title),
      fact("Poder u órgano", OFFICE_BODY[person.office]),
      fact("Partido", party),
      fact("Entidad", where),
      fact("Distrito", seat),
      region ? fact("Circunscripción", `${region.name} (cabecera ${region.seat}): ${ctx.regionStates(region)}`) : null,
      fact("Municipio", person.municipality),
      fact("Elección", election),
      fact("Suplente", person.substitute),
      fact("Inicio del cargo", person.term_start ? day(person.term_start) : "Sin dato en la fuente"),
      fact("Fin del periodo", person.term_end ? `${day(person.term_end)}${ruled}` : person.term_end_note ? person.term_end_note : legislator || person.office === "president" ? null : "Sin dato en la fuente"),
      fact("Estudios", person.education),
      contact ? [fact("Correo oficial", contact.email ? el("a", { href: `mailto:${contact.email}` }, contact.email) : "Sin dato"), fact("Teléfono", contact.phone), fact("Oficina", contact.office)] : fact("Contacto oficial", contactNote),
      fact("Fuente", sourceValue(person.citation)),
      person.citation.party_url ? fact("Partido según", el("span", {}, link(person.citation.party_url, "el artículo de la persona"), `, versión del ${day(person.citation.party_published_at)}`)) : null,
    ];
  }

  /** The full card: name, role line and every row. */
  function personCard(person, ctx) {
    return [el("h2", { class: "ficha__place" }, person.name), el("p", { class: "ficha__sub" }, swatch(person.party), ` ${roleText(person)}`), facts(personRows(person, ctx))];
  }

  // ---------- Chambers: every seat drawn as a hemicycle ----------

  const INSET = { width: 320, height: 172, inner: 52, outer: 150 };

  /** Seat centres on concentric half-rings, ordered left to right so party blocks form wedges. */
  function hemicycle(count, inset = INSET) {
    const rows = Math.max(1, Math.round(Math.sqrt(count / 6)));
    const radii = rows === 1 ? [inset.outer * 0.8] : d3.range(rows).map((i) => inset.inner + ((inset.outer - inset.inner) * i) / (rows - 1));
    const total = d3.sum(radii);
    const perRow = radii.map((r) => Math.floor((count * r) / total));
    for (let i = rows - 1, left = count - d3.sum(perRow); left > 0; i = (i - 1 + rows) % rows, left--) perRow[i]++;
    const seats = [];
    radii.forEach((r, row) => {
      const n = perRow[row];
      for (let j = 0; j < n; j++) {
        const angle = n === 1 ? Math.PI / 2 : Math.PI - (Math.PI * j) / (n - 1);
        seats.push({ x: r * Math.cos(angle), y: -r * Math.sin(angle), angle, row });
      }
    });
    seats.sort((a, b) => b.angle - a.angle || a.row - b.row);
    const rowGap = rows === 1 ? 24 : (inset.outer - inset.inner) / (rows - 1);
    const arcGap = (Math.PI * inset.outer) / Math.max(1, perRow[rows - 1] - 1);
    return { seats, radius: 0.42 * Math.min(rowGap, arcGap) };
  }

  /** Members of a body in seating order: state seats first (by party, then state), then list seats (by region, then party). */
  function seatingOrder(people) {
    const rank = (p) => (p.party === null ? PARTY_ORDER.length : partyRank(p.party));
    const region = (p) => (p.state_code ? 0 : p.region_number || 9);
    return [...people].sort(
      (a, b) =>
        (b.state_code ? 1 : 0) - (a.state_code ? 1 : 0) || region(a) - region(b) || rank(a) - rank(b) || (a.state || "").localeCompare(b.state || "", "es") || a.name.localeCompare(b.name, "es")
    );
  }

  /** Shaded wedges behind groups of list seats, with a label each. */
  function shadeWedges(centre, groups, step, inset = INSET) {
    for (const group of groups) {
      const from = d3.max(group.seats, (d) => d.angle);
      const to = d3.min(group.seats, (d) => d.angle);
      const wedge = d3.arc().innerRadius(inset.inner - 10).outerRadius(inset.outer + 9).startAngle(Math.PI / 2 - from - step / 2).endAngle(Math.PI / 2 - to + step / 2);
      centre.append("path").attr("class", `inset__wedge${group.alternate ? " inset__wedge--alt" : ""}`).attr("d", wedge());
      const mid = Math.PI / 2 - (from + to) / 2;
      centre.append("text").attr("class", "inset__wedge-label").attr("x", (inset.outer + 20) * Math.sin(mid)).attr("y", -(inset.outer + 20) * Math.cos(mid) + 4).attr("text-anchor", "middle").text(group.label);
    }
  }

  /** Draw a body's seats into an <svg>. `members` are in seating order; a member may be a
   *  placeholder ({placeholder: true, party: null}). Returns the placed seats. */
  function drawSeats(svgNode, members, { office, onPick, onHover, onLeave, inset = INSET } = {}) {
    const { seats, radius } = hemicycle(members.length, inset);
    const placed = members.map((person, i) => ({ person, ...seats[i] }));
    const svg = d3.select(svgNode).attr("viewBox", `0 0 ${inset.width} ${inset.height}`);
    svg.selectAll("*").remove();
    const centre = svg.append("g").attr("transform", `translate(${inset.width / 2}, ${inset.outer + 8})`);
    const listSeats = placed.filter((d) => !d.person.state_code && !d.person.placeholder);
    const step = placed.length > 1 ? Math.abs(placed[1].angle - placed[0].angle) : 0;
    if ((office === "senator" || office === "deputy") && listSeats.length && listSeats.length < placed.length) {
      const groups = office === "deputy"
        ? d3.groups(listSeats, (d) => d.person.region_number || 0).map(([number, group], i) => ({ seats: group, label: number ? `${number}.ª` : "sin leer", alternate: i % 2 === 1 }))
        : [{ seats: listSeats, label: "sin entidad" }];
      shadeWedges(centre, groups, step, inset);
    }
    centre
      .selectAll("circle")
      .data(placed)
      .join("circle")
      .attr("class", "seat")
      .attr("cx", (d) => d.x)
      .attr("cy", (d) => d.y)
      .attr("r", radius)
      .style("fill", (d) => (d.person.party === null ? "var(--land)" : partyOf(d.person.party).color))
      .on("pointermove", (event, d) => onHover && onHover(event, d.person))
      .on("pointerleave", () => onLeave && onLeave())
      .on("click", (event, d) => onPick && onPick(d.person));
    return placed;
  }

  /** The counts under a chamber: one row per party, as rows, plus the two majority lines. */
  function chamberCounts(members, { majorities = true } = {}) {
    const counts = d3.rollup(members, (group) => group.length, (p) => p.party);
    const total = members.length;
    const row = (code, label, n) =>
      el("li", {}, code ? swatch(code) : el("span", { class: "swatch swatch--empty", "aria-hidden": "true" }), el("span", { class: "inset__party" }, label), el("span", { class: "inset__seats" }, integer.format(n)), el("span", { class: "inset__share" }, `${Math.round((1000 * n) / total) / 10}%`));
    const rows = PARTY_ORDER.filter((code) => counts.has(code)).map((code) => row(code, PARTIES[code].label, counts.get(code)));
    if (counts.has(null)) rows.push(row(null, "Sin dato", counts.get(null)));
    const simple = Math.floor(total / 2) + 1;
    const qualified = Math.ceil((2 * total) / 3);
    const holder = (threshold) => {
      const party = PARTY_ORDER.find((code) => (counts.get(code) || 0) >= threshold);
      return party ? `${PARTIES[party].label}, con ${counts.get(party)}` : "ningún partido por sí solo";
    };
    return [
      el("ul", { class: "inset__counts" }, rows),
      majorities ? facts(fact(`Mayoría simple (${simple} escaños)`, holder(simple)), fact(`Mayoría calificada, dos tercios (${qualified})`, holder(qualified))) : null,
    ];
  }

  /** What a seat says when pointed at. */
  function seatTipLines(person, ctx) {
    if (person.placeholder) return [el("p", {}, person.municipality || person.name), person.state_code ? el("p", { class: "tooltip__place" }, ctx.stateName(person.state_code)) : null, el("p", { class: "tooltip__sub" }, person.note || "Sin dato en la fuente")];
    const region = person.office === "deputy" && person.region_number ? ctx.regionByNumber(person.region_number) : null;
    const where = person.state_code ? ctx.stateName(person.state_code) : region ? `${region.name}: ${ctx.regionStates(region)}` : person.district;
    return [el("p", {}, swatch(person.party), ` ${person.name}, ${partyLabel(person)}`), el("p", { class: "tooltip__place" }, where), el("p", { class: "tooltip__sub" }, roleText(person)), el("p", { class: "tooltip__sub" }, "Pulsa para ver sus datos")];
  }

  // ---------- Hover box ----------

  /** A hover box inside `area`, positioned near the pointer; `show(event, key, build)` rebuilds only when the key changes. */
  function tooltip(tipEl, area) {
    let key = null;
    return {
      show(event, newKey, build) {
        if (event.pointerType === "touch") return;
        if (newKey !== key) {
          tipEl.replaceChildren(...build().filter(Boolean));
          key = newKey;
        }
        tipEl.hidden = false;
        const box = area.getBoundingClientRect();
        const x = event.clientX - box.left;
        const y = event.clientY - box.top;
        tipEl.style.left = `${Math.max(4, Math.min(box.width - tipEl.offsetWidth - 4, x + 14))}px`;
        tipEl.style.top = `${y + 18 + tipEl.offsetHeight > box.height ? Math.max(4, y - tipEl.offsetHeight - 12) : y + 18}px`;
      },
      hide() {
        tipEl.hidden = true;
      },
      reset() {
        key = null;
      },
    };
  }

  /** Region (circunscripción) lookups over a politicians.json dataset. */
  function regions(data, stateName) {
    const list = data.circunscripciones ? data.circunscripciones.list : [];
    return {
      list,
      regionOfState: (code) => list.find((r) => r.states.includes(code)) || null,
      regionByNumber: (number) => list.find((r) => r.number === number) || null,
      regionStates: (region) => region.states.map(stateName).join(", "),
    };
  }

  return {
    PARTIES, PARTY_ORDER, EVERYDAY_NAME, SOURCE_SHORT, INSET,
    el, link, partyOf, partyRank, partyLabel, swatch, fold, capitalise,
    integer, signed, oneDecimal, moment, day, motionOK,
    fact, facts, sourceValue,
    samePerson, districtOf, roleText, personLine, personRows, personCard,
    hemicycle, seatingOrder, drawSeats, chamberCounts, seatTipLines, tooltip, regions,
  };
})();
