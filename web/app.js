/* Infórmate: map of Mexico's municipalities with who governs each state and who
   represents it in Congress, and who presides each municipality. Reads three files written by the Python tools:
   data/municipios.topojson, data/map_source.json and data/politicians.json. */
(() => {
  "use strict";

  const { PARTIES, PARTY_ORDER, EVERYDAY_NAME, INSET, el, link, swatch, partyOf, partyRank, partyLabel, fold, integer, moment, day, motionOK, fact, facts, sourceValue, samePerson, districtOf, personLine, personCard, seatingOrder, drawSeats, chamberCounts, seatTipLines } = MXD;
  const NATIONAL_LIST = "LN";

  const S = { view: "governor", showMunis: false, selected: null, person: null, topo: null, mapSource: null, data: null, states: [], munis: [], districts: [], byState: new Map(), national: [], mayorOf: new Map(), mayorShapes: new Map(), deputyOfDistrict: new Map() };

  // ---------- Small helpers ----------

  const $ = (selector) => document.querySelector(selector);

  const stateName = (code) => EVERYDAY_NAME[code] || S.states.find((s) => s.code === code)?.name || code;
  // ---------- Data ----------

  function indexPeople() {
    S.byState = new Map();
    S.national = [];
    S.mayorOf = new Map();
    for (const person of S.data.people) {
      if (!person.state_code) {
        if (person.office === "senator") S.national.push(person);
        continue;
      }
      if (!S.byState.has(person.state_code)) S.byState.set(person.state_code, { governor: null, senators: [], deputies: [], mayors: [] });
      const entry = S.byState.get(person.state_code);
      if (person.office === "governor") entry.governor = person;
      else if (person.office === "senator") entry.senators.push(person);
      else if (person.office === "deputy") entry.deputies.push(person);
      else {
        entry.mayors.push(person);
        if (person.municipality_code) S.mayorOf.set(person.municipality_code, person);
      }
    }
    S.deputyOfDistrict = new Map(S.data.people.filter((p) => p.office === "deputy" && p.district_number).map((p) => [`${p.state_code}-${p.district_number}`, p]));
    S.national.sort((a, b) => partyRank(a.party) - partyRank(b.party) || a.name.localeCompare(b.name, "es"));
    for (const entry of S.byState.values()) {
      entry.deputies.sort((a, b) => (a.district_number ?? 999) - (b.district_number ?? 999) || a.name.localeCompare(b.name, "es"));
      entry.mayors.sort((a, b) => a.municipality.localeCompare(b.municipality, "es"));
    }
    // One combined shape per party, so the municipal map is a handful of fills.
    S.mayorShapes = new Map();
    for (const muni of S.munis) {
      const mayor = S.mayorOf.get(muni.code);
      if (!mayor) continue;
      if (!S.mayorShapes.has(mayor.party)) S.mayorShapes.set(mayor.party, new Path2D());
      S.mayorShapes.get(mayor.party).addPath(muni.shape);
    }
  }

  const governorOf = (code) => S.byState.get(code)?.governor || null;
  /** A state's senators: the two majority seats first, the first-minority seat last. */
  const senatorsOf = (code) =>
    [...(S.byState.get(code)?.senators || [])].sort(
      (a, b) => (a.election_type === "Primera minoría") - (b.election_type === "Primera minoría") || a.name.localeCompare(b.name, "es")
    );
  const mayorsOf = (code) => S.byState.get(code)?.mayors || [];
  /** Whether pointing at the map should pick out single municipalities rather than whole states. */
  const municipalHover = () => S.showMunis || S.view === "mayor";
  /** A state's district deputies, by district number. */
  const deputiesOf = (code) => S.byState.get(code)?.deputies || [];
  /** Deputies elected from the regional party lists; they belong to no state. */
  const listDeputies = () =>
    S.data.people.filter((p) => p.office === "deputy" && !p.state_code).sort((a, b) => partyRank(a.party) - partyRank(b.party) || a.name.localeCompare(b.name, "es"));

  // ---------- People and citations ----------

  // ---------- One person ----------

  const people = (...persons) => el("ul", { class: "people" }, persons.flat().filter(Boolean).map((p) => personLine(p, showPerson)));
  /** The short "Fuente" cell of the roster. */
  const shortSource = (c) => el("span", {}, link(c.url, MXD.SOURCE_SHORT[c.source] || c.source_name), c.published_at ? `, ${day(c.published_at)}` : "", `; leída el ${day(c.retrieved_at)}`);
  const ctx = () => ({ stateName, regionByNumber, regionStates });

  /** Open a person's data where the place's data was; the map outlines their state, if they have one. */
  function showPerson(person) {
    S.person = person;
    if (person.state_code && S.selected !== person.state_code) {
      S.selected = person.state_code;
      const state = S.states.find((s) => s.code === person.state_code);
      selectedOutline.attr("d", state ? state.outline : null);
      zoomTo(state);
    }
    renderFicha();
    $("#ficha").scrollIntoView({ block: "nearest", behavior: motionOK ? "smooth" : "auto" });
  }

  // ---------- Map ----------

  const W = 960;
  const H = 640;
  const svg = d3.select("#map svg").attr("viewBox", `0 0 ${W} ${H}`).attr("preserveAspectRatio", "xMidYMid meet");
  const projection = d3.geoConicConformal().parallels([17.5, 29.5]).rotate([102, 0]);
  const path = d3.geoPath(projection);
  let zoomLayer, stateShapes, hoverState, selectedOutline, zoom, graticuleShape, districtLines;
  // On wide screens the country sits a little left of centre, so the floating inset covers only sea.
  const insetFloats = window.matchMedia("(min-width: 901px)");
  const home = () => (insetFloats.matches ? d3.zoomIdentity.translate(-120, 8) : d3.zoomIdentity);
  let transform = home();

  function buildMap() {
    const layer = S.topo.objects.municipios;
    const facts = new Map(S.mapSource.states.map((s) => [s.cve_ent, s]));
    const byState = d3.group(layer.geometries, (g) => g.properties.cve_ent);
    S.states = Array.from(byState, ([code, geometries]) => ({
      code,
      name: facts.get(code)?.name || code,
      population: facts.get(code)?.population ?? null,
      municipalities: geometries.length,
      feature: { type: "Feature", geometry: topojson.merge(S.topo, geometries) },
    })).sort((a, b) => a.code.localeCompare(b.code));

    projection.fitExtent([[24, 24], [W - 24, H - 24]], { type: "Feature", geometry: topojson.merge(S.topo, layer.geometries) });

    const sameState = (a, b) => a.properties.cve_ent === b.properties.cve_ent;
    zoomLayer = svg.append("g");
    graticuleShape = new Path2D(path(d3.geoGraticule().extent([[-150, 0], [-55, 45]]).step([5, 5])()));
    for (const state of S.states) {
      state.outline = path(state.feature);
      state.shape = new Path2D(state.outline);
      state.box = path.bounds(state.feature);
      measureShape(state);
    }
    const stateByCode = new Map(S.states.map((s) => [s.code, s]));
    const features = topojson.feature(S.topo, layer).features;
    S.munis = features.map((feature) => ({
      code: feature.properties.cvegeo,
      name: feature.properties.nomgeo,
      state_code: feature.properties.cve_ent,
      shape: new Path2D(path(feature)),
    }));
    stateShapes = zoomLayer.append("g").selectAll("path").data(S.states).join("path").attr("class", "state").attr("d", (d) => d.outline);
    hoverState = zoomLayer.append("path").attr("class", "hover-state");
    zoomLayer.append("path").attr("class", "muni-lines").attr("d", path(topojson.mesh(S.topo, layer, (a, b) => a !== b && sameState(a, b))));
    zoomLayer.append("path").attr("class", "state-lines").attr("d", path(topojson.mesh(S.topo, layer, (a, b) => a !== b && !sameState(a, b))));
    zoomLayer.append("path").attr("class", "coast").attr("d", path(topojson.mesh(S.topo, layer, (a, b) => a === b)));
    selectedOutline = zoomLayer.append("path").attr("class", "selected-outline");
    // The municipality shapes are what the pointer touches. With municipalities hidden,
    // they stand in for their state: the whole state lights up and the box names the state.
    zoomLayer
      .append("g")
      .on("pointerleave", () => {
        hideTip();
        hoverState.attr("d", null);
        litSeats(S.selected);
      })
      .selectAll("path")
      .data(features)
      .join("path")
      .attr("class", "muni")
      .attr("d", path)
      .on("pointermove", (event, d) => {
        const { cvegeo, cve_ent } = d.properties;
        hoverState.attr("d", municipalHover() ? null : stateByCode.get(cve_ent).outline);
        litSeats(cve_ent);
        showTip(event, municipalHover() ? `m${cvegeo}` : `e${cve_ent}`, () => placeTip(d.properties));
      })
      .on("click", (event, d) => {
        // In the municipal view a municipality is the unit: open its president's card when the source names one.
        const mayor = municipalHover() ? S.mayorOf.get(d.properties.cvegeo) : null;
        if (mayor) showPerson(mayor);
        else select(d.properties.cve_ent);
      });

    // The 300 federal districts: filled on the canvas in the Deputies view, pointed at here.
    const districtLayer = S.districtTopo.objects.distritos;
    S.districts = topojson.feature(S.districtTopo, districtLayer).features.map((feature) => ({
      state_code: feature.properties.ent,
      number: feature.properties.dist,
      outline: path(feature),
      shape: new Path2D(path(feature)),
    }));
    districtLines = new Path2D(path(topojson.mesh(S.districtTopo, districtLayer, (a, b) => a !== b)));
    zoomLayer
      .append("g")
      .on("pointerleave", () => {
        hideTip();
        hoverState.attr("d", null);
        litSeats(S.selected);
      })
      .selectAll("path")
      .data(S.districts)
      .join("path")
      .attr("class", "district")
      .attr("d", (d) => d.outline)
      .on("pointermove", (event, d) => {
        hoverState.attr("d", d.outline);
        litSeats(d.state_code);
        showTip(event, `d${d.state_code}-${d.number}`, () => districtTip(d));
      })
      .on("click", (event, d) => {
        const deputy = S.deputyOfDistrict.get(`${d.state_code}-${d.number}`);
        if (deputy) showPerson(deputy);
        else select(d.state_code);
      });

    zoom = d3
      .zoom()
      .scaleExtent([1, 30])
      .translateExtent([[-240, -60], [W + 240, H + 60]])
      .filter((event) => {
        if (event.type === "wheel") return event.ctrlKey || event.metaKey; // plain wheel scrolls the page
        if (event.type.startsWith("touch")) return event.touches.length > 1; // one finger scrolls the page
        return !event.button;
      })
      .on("zoom", (event) => {
        transform = event.transform;
        zoomLayer.attr("transform", transform).style("--k", transform.k);
        drawUnderlay();
      });
    svg.call(zoom).on("dblclick.zoom", null);
    svg.call(zoom.transform, home());
    insetFloats.addEventListener("change", () => {
      if (!S.selected) svg.call(zoom.transform, home());
    });

    $("#zoom-in").addEventListener("click", () => svg.transition().duration(motionOK ? 250 : 0).call(zoom.scaleBy, 1.8));
    $("#zoom-out").addEventListener("click", () => svg.transition().duration(motionOK ? 250 : 0).call(zoom.scaleBy, 1 / 1.8));
    $("#zoom-reset").addEventListener("click", () => select(null));
    new ResizeObserver(drawUnderlay).observe(underlay);
  }

  function paintMap() {
    $("#map").classList.toggle("view-seats", S.view !== "governor");
    $("#map").classList.toggle("view-mayor", S.view === "mayor");
    $("#map").classList.toggle("view-deputy", S.view === "deputy");
    stateShapes.style("fill", (d) => {
      if (S.view !== "governor") return "none"; // seats are painted on the canvas underneath
      const governor = governorOf(d.code);
      return governor ? partyOf(governor.party).color : "var(--land)";
    });
    drawUnderlay();
  }

  // ---------- Canvas underlay: graticule, and the seats of the Senate and Deputies views ----------
  //
  // In those two views each state is cut into equal-area blocks, one per seat, in the colour of
  // the party that holds it (the Senate can also be drawn as a majority colour plus three dots).
  // This is painted on a canvas under the SVG, which keeps the borders and everything you can
  // point at.

  const underlay = $("#map canvas");
  const pen = underlay.getContext("2d");
  const cssColor = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  const hexCache = new Map();
  function hexOf(variable) {
    if (!hexCache.has(variable)) hexCache.set(variable, cssColor(variable));
    return hexCache.get(variable);
  }
  const partyHex = (code) => hexOf(partyOf(code).color.slice(4, -1)); // "var(--pan)" -> "--pan"

  /** A point well inside a state's shape, to place its three Senate dots (its centroid can fall
   *  outside a crescent-shaped state). From one small raster of the shape, peeled inward. */
  function measureShape(state) {
    const [[x0, y0], [x1, y1]] = state.box;
    const n = 64;
    const raster = document.createElement("canvas");
    raster.width = raster.height = n;
    const ink = raster.getContext("2d", { willReadFrequently: true });
    ink.setTransform(n / (x1 - x0), 0, 0, n / (y1 - y0), (-x0 * n) / (x1 - x0), (-y0 * n) / (y1 - y0));
    ink.fill(state.shape);
    const alpha = ink.getImageData(0, 0, n, n).data;
    const inside = (i, j) => i >= 0 && j >= 0 && i < n && j < n && alpha[(j * n + i) * 4 + 3] > 127;
    const seen = new Uint8Array(n * n);
    let layer = [];
    for (let j = 0; j < n; j++) {
      for (let i = 0; i < n; i++) {
        const onEdge = inside(i, j) && !(inside(i - 1, j) && inside(i + 1, j) && inside(i, j - 1) && inside(i, j + 1));
        if (onEdge) {
          seen[j * n + i] = 1;
          layer.push([i, j]);
        }
      }
    }
    let deepest = layer[0] || [n / 2, n / 2];
    while (layer.length) {
      deepest = layer[Math.floor(layer.length / 2)];
      const next = [];
      for (const [i, j] of layer) {
        for (const [a, b] of [[i - 1, j], [i + 1, j], [i, j - 1], [i, j + 1]]) {
          if (inside(a, b) && !seen[b * n + a]) {
            seen[b * n + a] = 1;
            next.push([a, b]);
          }
        }
      }
      layer = next;
    }
    state.anchor = [x0 + ((deepest[0] + 0.5) / n) * (x1 - x0), y0 + ((deepest[1] + 0.5) / n) * (y1 - y0)];
  }

  /** The parties holding a state's three Senate seats. */
  const seatsOf = (code) => senatorsOf(code).map((person) => person.party);

  /** Fill the state with the party holding most of its seats (grey when no party has two). */
  function fillMajority(state, parties) {
    const counts = d3.rollup(parties, (group) => group.length, (code) => code);
    const leader = [...counts].find(([, seats]) => seats * 2 > parties.length);
    pen.fillStyle = leader ? partyHex(leader[0]) : hexOf("--land");
    pen.fill(state.shape);
  }

  /** Three dots at a point well inside the state, one per seat. Drawn in screen pixels. */
  function drawDots(state, parties, place, density) {
    const centre = place.transformPoint(new DOMPoint(state.anchor[0], state.anchor[1]));
    const r = 4.6 * density;
    const slots = [[-r * 1.12, r * 0.9], [r * 1.12, r * 0.9], [0, -r * 1.05]];
    parties.forEach((code, i) => {
      const [dx, dy] = slots[i] || [(i - 1) * r * 2.3, r * 3];
      pen.beginPath();
      pen.arc(centre.x + dx, centre.y + dy, r, 0, 2 * Math.PI);
      pen.fillStyle = partyHex(code);
      pen.fill();
      pen.lineWidth = 1.5 * density;
      pen.strokeStyle = "#ffffff";
      pen.stroke();
    });
  }

  function drawUnderlay() {
    if (!graticuleShape) return;
    const density = window.devicePixelRatio || 1;
    const width = Math.round(underlay.clientWidth * density);
    const height = Math.round(underlay.clientHeight * density);
    if (underlay.width !== width || underlay.height !== height) {
      underlay.width = width;
      underlay.height = height;
    }
    // Map units -> canvas pixels: the same "fit and centre" the SVG uses, then the zoom.
    const fit = Math.min(underlay.clientWidth / W, underlay.clientHeight / H);
    const left = (underlay.clientWidth - W * fit) / 2;
    const top = (underlay.clientHeight - H * fit) / 2;
    const scale = density * fit * transform.k;
    const place = new DOMMatrix([scale, 0, 0, scale, density * (left + fit * transform.x), density * (top + fit * transform.y)]);

    pen.setTransform(1, 0, 0, 1, 0, 0);
    pen.clearRect(0, 0, width, height);
    pen.setTransform(place);
    pen.strokeStyle = "#c3d0d9";
    pen.lineWidth = (0.6 * density) / scale;
    pen.stroke(graticuleShape);
    if (S.view === "governor") return;
    if (S.view === "deputy") {
      // Each federal district in the colour of its deputy's party; grey until that profile is read.
      pen.fillStyle = hexOf("--land");
      for (const state of S.states) pen.fill(state.shape);
      for (const district of S.districts) {
        const deputy = S.deputyOfDistrict.get(`${district.state_code}-${district.number}`);
        if (!deputy) continue;
        pen.fillStyle = partyHex(deputy.party);
        pen.fill(district.shape);
      }
      pen.strokeStyle = "#ffffff";
      pen.lineWidth = (0.8 * density) / scale;
      pen.stroke(districtLines);
      return;
    }
    if (S.view === "mayor") {
      pen.fillStyle = hexOf("--land");
      for (const state of S.states) pen.fill(state.shape);
      for (const [party, shape] of S.mayorShapes) {
        pen.fillStyle = partyHex(party);
        pen.fill(shape);
      }
      return;
    }

    // Senate: the party holding most of the state's three seats, and one dot per seat.
    for (const state of S.states) {
      const parties = seatsOf(state.code);
      if (parties.length) fillMajority(state, parties);
      else {
        pen.fillStyle = hexOf("--land");
        pen.fill(state.shape);
      }
    }
    pen.setTransform(1, 0, 0, 1, 0, 0);
    for (const state of S.states) drawDots(state, seatsOf(state.code), place, density);
  }

  function zoomTo(state) {
    let target = home();
    if (state) {
      const [[x0, y0], [x1, y1]] = state.box;
      const k = Math.max(1, Math.min(14, 0.75 / Math.max((x1 - x0) / W, (y1 - y0) / H)));
      target = d3.zoomIdentity.translate(W / 2, H / 2).scale(k).translate(-(x0 + x1) / 2, -(y0 + y1) / 2);
    }
    svg.transition().duration(motionOK ? 650 : 0).call(zoom.transform, target);
  }

  // ---------- Tooltip ----------

  const tip = $("#tooltip");
  let tipKey = null;

  function showTip(event, key, build) {
    if (event.pointerType === "touch") return; // on touch the ficha does this job
    if (key !== tipKey) {
      tip.replaceChildren(...build().filter(Boolean));
      tipKey = key;
    }
    tip.hidden = false;
    const box = $(".map-area").getBoundingClientRect();
    const x = event.clientX - box.left;
    const y = event.clientY - box.top;
    tip.style.left = `${Math.max(4, Math.min(box.width - tip.offsetWidth - 4, x + 14))}px`;
    tip.style.top = `${y + 18 + tip.offsetHeight > box.height ? Math.max(4, y - tip.offsetHeight - 12) : y + 18}px`;
  }

  function hideTip() {
    tip.hidden = true;
  }

  const tipPerson = (person) => el("span", {}, swatch(person.party), ` ${person.name}, ${partyLabel(person)}`);

  /** Hover box for a spot on the map: the state, plus the municipality when those are shown. */
  function placeTip(props) {
    const code = props.cve_ent;
    let sub;
    let lines;
    if (S.view === "governor") {
      const governor = governorOf(code);
      sub = governor ? governor.title : "Sin titular en la fuente";
      lines = governor ? [tipPerson(governor)] : [];
    } else if (S.view === "senator") {
      sub = "Senado";
      lines = senatorsOf(code).map(tipPerson);
    } else if (S.view === "mayor") {
      const mayor = S.mayorOf.get(props.cvegeo);
      sub = mayor ? mayor.title : "Presidencia municipal";
      lines = [mayor ? tipPerson(mayor) : el("span", {}, "Sin dato en la fuente")];
    } else {
      const deputies = deputiesOf(code);
      const counts = d3.rollup(deputies, (group) => group.length, (person) => person.party);
      sub = `Cámara de Diputados: ${deputies.length} distritos`;
      lines = PARTY_ORDER.filter((party) => counts.has(party)).map((party) => el("span", {}, swatch(party), ` ${PARTIES[party].label}: ${counts.get(party)}`));
    }
    return [
      municipalHover() ? el("p", {}, props.nomgeo) : null,
      el("p", { class: "tooltip__place" }, stateName(code)),
      el("p", { class: "tooltip__sub" }, sub),
      el("div", { class: "tooltip__people" }, lines),
    ];
  }

  function districtTip(district) {
    const deputy = S.deputyOfDistrict.get(`${district.state_code}-${district.number}`);
    const seat = deputy && deputy.district.includes("(") ? deputy.district.slice(deputy.district.lastIndexOf("(")) : "";
    return [
      el("p", {}, `Distrito ${district.number} ${seat}`.trim()),
      el("p", { class: "tooltip__place" }, stateName(district.state_code)),
      el("p", { class: "tooltip__sub" }, deputy ? `${deputy.title}, mayoría relativa` : "Diputación de mayoría relativa"),
      el("div", { class: "tooltip__people" }, [deputy ? tipPerson(deputy) : el("span", {}, "Ficha aún no leída en el SIL")]),
    ];
  }

  // ---------- Legend and national list ----------

  function countByParty(office) {
    return d3.rollup(S.data.people.filter((p) => p.office === office), (group) => group.length, (p) => p.party);
  }

  const LEGEND_TEXT = {
    governor: "El color de cada entidad es el partido de quien encabeza su gobierno.",
    senator: "El color de la entidad es el partido que tiene dos o tres de sus senadurías; en gris, las entidades con tres partidos distintos. Los puntos son sus tres senadoras y senadores.",
    mayor: "El color de cada municipio es el partido de quien encabeza su ayuntamiento. En gris claro, los municipios sin dato en la fuente.",
    deputy: "Cada distrito electoral federal (INE, distritación de 2023) lleva el color del partido de su diputada o diputado; en gris claro, los distritos cuya ficha aún no se ha leído. Las 200 diputaciones de lista se eligen por circunscripción: cinco regiones que agrupan a las entidades.",
  };

  // ---------- Chambers: every seat drawn as a hemicycle, with the counts ----------

  const CHAMBER = {
    governor: { title: (n) => `Gubernaturas: ${n}`, seats: false, majorities: false },
    senator: { title: (n) => `Senado: ${n} escaños`, seats: true, majorities: true, list: (n) => `${n} de lista nacional, sin entidad.` },
    deputy: { title: (n) => `Cámara de Diputados: ${n} escaños`, seats: true, majorities: true, list: (n) => `${n} de listas regionales, por circunscripción (sombreadas).` },
    mayor: { title: (n) => `Municipios: ${integer.format(n)}`, seats: false, majorities: false },
    justice: { title: (n) => `Suprema Corte: ${n} ministras y ministros`, seats: true, majorities: false },
  };
  const regionsList = () => (S.data.circunscripciones ? S.data.circunscripciones.list : []);
  const regionOfState = (code) => regionsList().find((r) => r.states.includes(code)) || null;
  const regionByNumber = (number) => regionsList().find((r) => r.number === number) || null;
  const regionStates = (region) => region.states.map(stateName).join(", ");

  /** Who holds the seats of an office, in seating order: state seats first (by party, then
   *  state), then the list seats (deputies: by region, then party). The municipal view adds
   *  a grey seat per municipality the source says nothing about. */
  function chamberMembers(office) {
    const people = S.data.people.filter((p) => p.office === office);
    const empty = office === "mayor"
      ? S.munis.filter((muni) => !S.mayorOf.has(muni.code)).map((muni) => ({ office: "mayor", party: null, name: muni.name, state_code: muni.state_code, municipality: muni.name, placeholder: true }))
      : [];
    return seatingOrder(people.concat(empty));
  }

  /** Light the seats that belong to a state: its own, and the list seats of its region. */
  function litSeats(code) {
    const region = code ? regionOfState(code) : null;
    d3.selectAll(".chamber svg circle")
      .classed("seat--lit", (d) =>
        Boolean(code) && (d.person.state_code === code || (d.person.office === "deputy" && !d.person.state_code && region && d.person.region_number === region.number))
      )
      .classed("seat--chosen", (d) => samePerson(d.person, S.person))
      .filter((d) => samePerson(d.person, S.person))
      .raise();
  }

  /** Fill a <figure class="chamber"> (caption, svg, body) with one office's seats and counts. */
  function fillChamber(figure, office) {
    const chamber = CHAMBER[office];
    const members = chamberMembers(office);
    figure.querySelector("figcaption").textContent = chamber.title(members.length);
    const svgNode = figure.querySelector("svg");
    svgNode.toggleAttribute("hidden", !chamber.seats); // SVG elements have no `hidden` property
    let listSeats = 0;
    if (chamber.seats) {
      const placed = drawSeats(svgNode, members, {
        office,
        onPick: (person) => (person.placeholder ? select(person.state_code) : showPerson(person)),
        onHover: (event, person) => showTip(event, `s${person.name}${person.municipality || ""}`, () => seatTipLines(person, ctx())),
        onLeave: hideTip,
      });
      listSeats = placed.filter((d) => !d.person.state_code && !d.person.placeholder).length;
    } else {
      d3.select(svgNode).selectAll("*").remove();
    }
    figure.querySelector(".chamber__body").replaceChildren(
      ...[office === "justice" ? null : chamberCounts(members, { majorities: chamber.majorities }), listSeats && chamber.list ? el("p", { class: "inset__note" }, chamber.list(listSeats)) : null].flat().filter(Boolean)
    );
    litSeats(S.selected);
  }

  /** The inset over the map: the current view's chamber, plus the map key. */
  function renderInset() {
    const inset = $("#inset");
    fillChamber(inset, S.view);
    inset.querySelector(".chamber__body").append(el("p", { class: "inset__key" }, `${LEGEND_TEXT[S.view]}${CHAMBER[S.view].seats ? " Pulsa un escaño para ver los datos de quien lo ocupa." : ""}`));
  }

  // ---------- Ficha ----------

  function select(code, { zoomMap = true } = {}) {
    S.person = null;
    S.selected = code;
    const state = S.states.find((s) => s.code === code) || null;
    selectedOutline.attr("d", state ? state.outline : null);
    if (zoomMap && code !== NATIONAL_LIST) zoomTo(state);
    renderFicha();
  }

  function renderFicha() {
    $("#state-picker").value = S.selected || "";
    litSeats(S.selected);
    const content = S.person
      ? [personCard(S.person, ctx()), el("p", { class: "ficha__back" }, el("button", { type: "button", class: "link-button", onclick: () => select(S.selected === NATIONAL_LIST ? NATIONAL_LIST : S.selected, { zoomMap: false }) }, S.selected === NATIONAL_LIST ? "Volver a la lista nacional" : S.selected ? `Volver a ${stateName(S.selected)}` : "Ver todo el país"))]
      : !S.selected
        ? countryFicha()
        : S.selected === NATIONAL_LIST
          ? nationalListFicha()
          : stateFicha(S.states.find((s) => s.code === S.selected));
    $("#ficha").replaceChildren(...content.flat(Infinity));
  }

  const populationNote = () => el("p", { class: "cite" }, `Población: ${S.mapSource.population_source}.`);

  function countryFicha() {
    const governors = countByParty("governor");
    const senators = countByParty("senator");
    const deputies = countByParty("deputy");
    const mayors = countByParty("mayor");
    const justices = S.data.people.filter((p) => p.office === "justice");
    const total = (counts) => d3.sum(counts.values());
    const cell = (counts, code) => el("td", {}, String(counts.get(code) || 0));
    return [
      el("h2", { class: "ficha__place" }, "México"),
      el(
        "dl",
        { class: "facts" },
        fact("Población", integer.format(S.mapSource.population)),
        fact("Entidades", String(S.states.length)),
        fact("Municipios", integer.format(S.mapSource.municipality_count))
      ),
      populationNote(),
      el(
        "table",
        { class: "tally" },
        el(
          "thead",
          {},
          el("tr", {}, el("th", { scope: "col" }, "Partido"), el("th", { scope: "col" }, "Gubernaturas"), el("th", { scope: "col" }, "Senado"), el("th", { scope: "col" }, "Diputados"), el("th", { scope: "col" }, "Municipios"))
        ),
        el(
          "tbody",
          {},
          PARTY_ORDER.filter((code) => governors.has(code) || senators.has(code) || deputies.has(code) || mayors.has(code)).map((code) =>
            el("tr", {}, el("td", {}, swatch(code), PARTIES[code].label), cell(governors, code), cell(senators, code), cell(deputies, code), cell(mayors, code))
          )
        ),
        el("tfoot", {}, el("tr", {}, el("td", {}, "Total"), el("td", {}, String(total(governors))), el("td", {}, String(total(senators))), el("td", {}, String(total(deputies))), el("td", {}, integer.format(total(mayors)))))
      ),
      el("p", { class: "ficha__intro" }, "Elige una entidad en el mapa o en la lista para ver quién la gobierna y quién la representa en el Congreso."),
      justices.length
        ? [
            el("h3", {}, "Suprema Corte de Justicia de la Nación"),
            el("p", { class: "ficha__intro" }, `${justices.length} ministras y ministros, elegidos por voto popular; no representan a ninguna entidad.`),
            el("details", { class: "ficha__more" }, el("summary", {}, "Ver quiénes son"), people(justices)),
          ]
        : null,
    ];
  }

  const backButton = () =>
    el("p", { class: "ficha__back" }, el("button", { type: "button", class: "link-button", onclick: () => select(null) }, "Ver todo el país"));

  function stateFicha(state) {
    const governor = governorOf(state.code);
    const senators = senatorsOf(state.code);
    const deputies = deputiesOf(state.code);
    const mayors = mayorsOf(state.code);
    const mayorParties = d3.rollup(mayors, (group) => group.length, (person) => person.party);
    return [
      el("h2", { class: "ficha__place" }, stateName(state.code)),
      el(
        "dl",
        { class: "facts" },
        stateName(state.code) !== state.name ? fact("Nombre oficial", state.name) : null,
        fact("Población", state.population == null ? "Sin dato" : integer.format(state.population)),
        fact("Municipios", integer.format(state.municipalities))
      ),
      populationNote(),
      el("h3", {}, "Gobierno del estado"),
      governor ? people(governor) : el("p", { class: "ficha__intro" }, "La fuente no lista a nadie en este cargo."),
      el("h3", {}, "Senado"),
      senators.length ? people(senators) : el("p", { class: "ficha__intro" }, "La fuente no lista senadurías para esta entidad."),
      el("h3", {}, "Cámara de Diputados"),
      deputies.length
        ? [
            el("p", { class: "ficha__intro" }, `${deputies.length} diputaciones de mayoría relativa, una por distrito federal.`),
            el("details", { class: "ficha__more" }, el("summary", {}, "Ver quiénes son"), people(deputies)),
          ]
        : el("p", { class: "ficha__intro" }, "La fuente no lista diputaciones de distrito para esta entidad."),
      regionDeputies(state.code),
      el("h3", {}, state.code === "09" ? "Alcaldías" : "Presidencias municipales"),
      mayors.length
        ? [
            el("p", { class: "ficha__intro" }, `La fuente da titular para ${mayors.length} de ${integer.format(state.municipalities)} municipios.`),
            el(
              "ul",
              { class: "legend__items ficha__parties" },
              PARTY_ORDER.filter((code) => mayorParties.has(code)).map((code) =>
                el("li", {}, swatch(code), PARTIES[code].label, el("span", { class: "legend__count" }, String(mayorParties.get(code))))
              )
            ),
            el(
              "details",
              { class: "ficha__more" },
              el("summary", {}, "Ver quiénes son"),
              facts(fact("Inicio del cargo", mayors[0].term_start ? day(mayors[0].term_start) : "Sin dato"), fact("Fin del periodo", mayors[0].term_end ? day(mayors[0].term_end) : "Sin dato"), fact("Fuente", sourceValue(mayors[0].citation))),
              el(
                "table",
                { class: "compact" },
                el("thead", {}, el("tr", {}, el("th", { scope: "col" }, "Municipio"), el("th", { scope: "col" }, "Titular"), el("th", { scope: "col" }, "Partido"))),
                el("tbody", {}, mayors.map((p) => el("tr", {}, el("td", {}, p.municipality), el("td", {}, el("button", { type: "button", class: "persona__link", onclick: () => showPerson(p) }, p.name)), el("td", {}, swatch(p.party), partyLabel(p)))))
              )
            ),
          ]
        : el("p", { class: "ficha__intro" }, "La fuente no lista presidencias municipales para esta entidad."),
      backButton(),
    ];
  }

  /** The list deputies elected in the region a state belongs to. */
  function regionDeputies(code) {
    const region = regionOfState(code);
    if (!region) return null;
    const listed = S.data.people.filter((p) => p.office === "deputy" && !p.state_code && p.region_number === region.number);
    return [
      el("p", { class: "ficha__intro" }, `${stateName(code)} forma parte de la ${region.name.toLowerCase()} (${regionStates(region)}), que elige ${listed.length ? listed.length : "40"} diputaciones de lista${listed.length ? "" : "; sus fichas aún no se han leído"}.`),
      listed.length ? el("details", { class: "ficha__more" }, el("summary", {}, "Ver las diputaciones de lista de la región"), people(listed)) : null,
    ];
  }

  function nationalListFicha() {
    return [
      el("h2", { class: "ficha__place" }, "Lista nacional"),
      el("p", { class: "ficha__sub" }, `${S.national.length} senadurías de representación proporcional. No corresponden a ninguna entidad.`),
      el("h3", {}, "Senado"),
      people(S.national),
      backButton(),
    ];
  }

  function fillPicker() {
    const states = [...S.states].sort((a, b) => stateName(a.code).localeCompare(stateName(b.code), "es"));
    $("#state-picker").replaceChildren(
      el("option", { value: "" }, "Todo el país"),
      ...states.map((s) => el("option", { value: s.code }, stateName(s.code))),
      el("option", { value: NATIONAL_LIST }, "Lista nacional del Senado")
    );
    $("#state-picker").addEventListener("change", (event) => select(event.target.value || null));
  }

  // ---------- Roster table ----------

  function fillFilters() {
    const states = [...S.states].sort((a, b) => stateName(a.code).localeCompare(stateName(b.code), "es"));
    $("#f-party").replaceChildren(el("option", { value: "" }, "Todos"), ...PARTY_ORDER.map((code) => el("option", { value: code }, PARTIES[code].label)));
    $("#f-state").replaceChildren(
      el("option", { value: "" }, "Todas"),
      ...states.map((s) => el("option", { value: s.code }, stateName(s.code))),
      el("option", { value: NATIONAL_LIST }, "Listas de representación proporcional")
    );
    for (const id of ["#f-name", "#f-office", "#f-party", "#f-state"]) $(id).addEventListener("input", renderRoster);
  }

  function placeCell(person) {
    if (person.office === "deputy" && !person.state_code && person.region_number) {
      const region = regionByNumber(person.region_number);
      return el("td", {}, `${region.name} (${regionStates(region)})`);
    }
    if (!person.state_code && person.office !== "senator") return el("td", {}, person.district);
    if (person.office === "mayor") {
      const pick = () => {
        select(person.state_code);
        $(".atlas").scrollIntoView({ behavior: motionOK ? "smooth" : "auto" });
      };
      return el("td", {}, `${person.municipality}, `, el("button", { type: "button", class: "link-button", onclick: pick }, stateName(person.state_code)));
    }
    const code = person.state_code || NATIONAL_LIST;
    const label = person.state_code ? stateName(person.state_code) : "Lista nacional";
    let rest = "";
    if (person.office === "senator") rest = ` (${person.election_type.toLowerCase()})`;
    if (person.office === "deputy") rest = person.district_number ? `, ${districtOf(person)}` : " (mayoría relativa)";
    const choose = () => {
      select(code);
      $(".atlas").scrollIntoView({ behavior: motionOK ? "smooth" : "auto" });
    };
    return el("td", {}, el("button", { type: "button", class: "link-button", onclick: choose }, label), rest);
  }

  const ROWS_SHOWN_AT_FIRST = 300;
  let showAllRows = false;

  function rosterRow(p) {
    return el(
      "tr",
      {},
      el("td", { class: "name" }, p.name),
      el("td", {}, p.title),
      el("td", { class: "party" }, swatch(p.party), partyLabel(p)),
      placeCell(p),
      el("td", { class: "dates" }, p.term_start ? day(p.term_start) : "Sin dato"),
      el("td", { class: "dates" }, p.term_end ? day(p.term_end) : "Sin dato"),
      el("td", { class: "cited" }, shortSource(p.citation))
    );
  }

  function renderRoster(event) {
    if (event) showAllRows = false; // a changed filter starts again from the short list
    const name = fold($("#f-name").value.trim());
    const office = $("#f-office").value;
    const party = $("#f-party").value;
    const place = $("#f-state").value;
    const rows = S.data.people.filter(
      (p) =>
        (!name || fold(p.name).includes(name)) &&
        (!office || p.office === office) &&
        (!party || p.party === party) &&
        (!place || (p.state_code || NATIONAL_LIST) === place)
    );
    const shown = showAllRows ? rows : rows.slice(0, ROWS_SHOWN_AT_FIRST);
    $("#f-count").textContent = `${integer.format(rows.length)} de ${integer.format(S.data.people.length)} personas`;
    $("#roster-body").replaceChildren(
      ...(rows.length
        ? shown.map(rosterRow)
        : [el("tr", {}, el("td", { class: "empty", colspan: "7" }, "Nadie coincide con esos filtros. Quita alguno para ver más personas."))])
    );
    const more = $("#roster-more");
    more.hidden = shown.length === rows.length;
    more.textContent = `Mostrar las ${integer.format(rows.length - shown.length)} personas restantes`;
  }

  // ---------- Sources ----------

  function sourceBlock(title, kind, ...body) {
    return el("div", { class: "source" }, el("div", {}, el("h3", {}, title), el("p", { class: "source__kind" }, kind)), el("div", { class: "source__body" }, body));
  }

  function renderSources() {
    const map = S.mapSource;
    const { sil, wikipedia } = S.data.sources;
    const rules = [S.data.rules.senate_term, S.data.rules.deputies_term, S.data.rules.justices_term, S.data.rules.president_term].filter(Boolean);
    const court = S.data.sources.wikipedia_scjn;
    const presidency = S.data.sources.wikipedia_president;
    const cabinetSource = S.data.sources.wikipedia_cabinet;
    const ine = map.districts;
    const regions = S.data.circunscripciones;
    const mayorPages = S.data.sources.wikipedia_mayors;
    const noFigure = map.municipalities_without_population.length;
    $("#map-credit").replaceChildren(`${map.attribution}, consultado el ${day(map.retrieved_at)}. `, el("a", { href: "#fuentes" }, "Fuentes"));
    const blocks = [
      sourceBlock(
        "Mapa de municipios",
        "Fuente oficial",
        el("p", {}, `${map.edition}. ${integer.format(map.municipality_count)} municipios en ${map.states.length} entidades.`),
        el("p", {}, `Los límites se descargaron del servicio web del INEGI, entidad por entidad, el ${day(map.retrieved_at)}. ${map.processing_note}`),
        el("p", {}, `Población: ${map.population_source}, del mismo servicio. ${noFigure} municipios creados después de ese censo no tienen cifra propia.`),
        el(
          "details",
          {},
          el("summary", {}, `Los ${map.states.length} enlaces de descarga, consultados el ${day(map.retrieved_at)}`),
          el("ul", {}, map.states.map((s) => el("li", {}, link(s.url, `${EVERYDAY_NAME[s.cve_ent] || s.name}: ${s.municipalities} municipios`))))
        ),
        el("ul", { class: "cite" }, map.reference_links.map((r) => el("li", {}, link(r.url, r.label), `, enlace revisado el ${day(r.checked_at)}.`)))
      ),
      sourceBlock(
        "Senado y Cámara de Diputados",
        "Fuente oficial",
        el("p", {}, `${sil.name}; consultado el ${day(sil.retrieved_at)}.`),
        el(
          "ul",
          {},
          el("li", {}, link(sil.url, "Senado: integrantes de la LXVI Legislatura"), `, consultado el ${day(sil.retrieved_at)}.`),
          sil.deputies_url
            ? el("li", {}, link(sil.deputies_url, "Cámara de Diputados: integrantes de la LXVI Legislatura"), `, consultado el ${day(sil.retrieved_at)}.`)
            : null
        ),
        el("p", {}, "Cada persona enlaza a su propia ficha en el SIL, que la Secretaría de Gobernación compila a partir de fuentes públicas como las gacetas del Congreso. El distrito de cada diputación se lee en esa ficha.")
      ),
      sourceBlock(
        "Gobernadoras, gobernadores y jefa de Gobierno",
        "Fuente secundaria",
        el("p", {}, link(wikipedia.url, wikipedia.name), `, versión del ${day(wikipedia.published_at)}; consultada el ${day(wikipedia.retrieved_at)}.`),
        el("p", {}, "No encontramos una lista oficial, única y vigente de quienes encabezan los gobiernos estatales que pueda consultarse de forma automática. Por eso se cita la versión exacta de Wikipedia que se leyó, para que cualquiera pueda comprobarla.")
      ),
      mayorPages
        ? sourceBlock(
            "Presidencias municipales y alcaldías",
            "Fuente secundaria",
            el("p", {}, `${mayorPages.name}; consultados el ${day(mayorPages.retrieved_at)}.`),
            el("p", {}, "No hay una lista oficial y vigente de presidentes municipales que pueda consultarse de forma automática; la del gobierno federal corresponde al periodo anterior. Se cita la versión exacta de cada anexo de Wikipedia que se leyó."),
            el(
              "details",
              {},
              el("summary", {}, `Los ${mayorPages.pages.length} anexos, consultados el ${day(mayorPages.retrieved_at)}`),
              el("ul", {}, mayorPages.pages.map((page) => el("li", {}, link(page.url, EVERYDAY_NAME[page.state_code] || page.state), `, versión del ${day(page.published_at)}.`)))
            )
          )
        : null,
      ine
        ? sourceBlock(
            "Mapa de distritos electorales",
            "Fuente oficial",
            el("p", {}, `${ine.attribution}: la capa ${ine.layer} del archivo publicado por el INE, con ${ine.district_count} distritos federales (distritación de 2023).`),
            el("p", { class: "cite" }, link(ine.url, "Archivo de shapefiles del Marco Geográfico Seccional"), `, con fecha del ${day(ine.published_at)}; descargado el ${day(ine.retrieved_at)}. Límites simplificados para visualización.`)
          )
        : null,
      cabinetSource
        ? sourceBlock(
            "Gabinete",
            "Fuente secundaria",
            el("p", {}, link(cabinetSource.url, cabinetSource.name), `, versión del ${day(cabinetSource.published_at)}; consultada el ${day(cabinetSource.retrieved_at)}.`),
            el("p", {}, "La tabla «Gabinete legal» del artículo lista las dependencias del Ejecutivo federal con sus titulares. No da fechas de nombramiento ni partido, y no encontramos una página oficial que pueda leerse de forma automática.")
          )
        : null,
      presidency
        ? sourceBlock(
            "Presidencia de la República",
            "Fuente secundaria",
            el("p", {}, link(presidency.url, presidency.name), `, versión del ${day(presidency.published_at)}; consultada el ${day(presidency.retrieved_at)}.`),
            el("p", {}, "El artículo sobre el cargo dice quién lo ocupa y desde cuándo; el partido se toma del artículo de la persona titular, enlazado en su ficha.")
          )
        : null,
      regions
        ? sourceBlock(
            "Circunscripciones de la Cámara de Diputados",
            "Fuente secundaria",
            el("p", {}, "Las 200 diputaciones de lista se eligen en cinco circunscripciones, cada una un grupo de entidades. La composición vigente desde el 29 de marzo de 2023 se tomó de ", link(regions.source.url, regions.source.name), `, versión del ${day(regions.source.published_at)}; enlace revisado el ${day(regions.source.checked_at)}.`),
            el("ul", {}, regions.list.map((r) => el("li", {}, `${r.name} (cabecera ${r.seat}): ${regionStates(r)}.`)))
          )
        : null,
      court
        ? sourceBlock(
            "Suprema Corte de Justicia de la Nación",
            "Fuente secundaria",
            el("p", {}, link(court.url, court.name), `, versión del ${day(court.published_at)}; consultada el ${day(court.retrieved_at)}.`),
            el("p", {}, "El sitio de la Corte no responde a consultas desde fuera de México, así que se usa el artículo de Wikipedia, citado en la versión exacta que se leyó.")
          )
        : null,
      sourceBlock(
        "Fechas de inicio y de término",
        "Fuentes citadas y dos reglas constitucionales",
        el("p", {}, "La fecha en que cada persona asumió el cargo viene de su fuente: el SIL para el Congreso (toma de protesta) y Wikipedia para los gobiernos estatales y municipales, que también da la fecha de término."),
        el("p", {}, "El SIL no publica cuándo termina cada senaduría o diputación, y las fuentes de la Corte y de la Presidencia tampoco dan el final del periodo, así que esas fechas se calculan con estas reglas:"),
        rules.map((rule) => [
          el("p", {}, rule.text),
          el("p", { class: "cite" }, link(rule.url, rule.source_name), `, texto con última reforma del ${day(rule.published_at)}; enlace revisado el ${day(rule.checked_at)}.`),
        ])
      ),
      S.data.warnings.length
        ? sourceBlock("Avisos", "Diferencias entre lo que listan las fuentes y lo que marca la ley", el("ul", {}, S.data.warnings.map((w) => el("li", {}, w))))
        : null,
    ];
    $("#sources").replaceChildren(...blocks.filter(Boolean));
  }

  // ---------- Header, refresh, view switch ----------

  function renderDataDate() {
    $("#data-date").textContent = `Cargos consultados el ${moment.format(new Date(S.data.generated_at))}.`;
  }

  function renderPeople() {
    indexPeople();
    paintMap();
    renderInset();
    renderFicha();
    renderRoster();
    renderSources();
    renderDataDate();
  }

  async function refreshData() {
    const button = $("#refresh");
    const message = $("#refresh-msg");
    button.disabled = true;
    message.textContent = "Consultando las fuentes…";
    try {
      const response = await fetch("api/refresh", { method: "POST" });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || `Error ${response.status}`);
      S.data = payload;
      renderPeople();
      message.textContent = "Datos actualizados.";
    } catch (error) {
      message.textContent = `No se pudo actualizar; se conservan los datos anteriores. (${error.message})`;
    } finally {
      button.disabled = false;
    }
  }

  function setView(view) {
    S.view = view;
    for (const button of document.querySelectorAll(".views button")) button.setAttribute("aria-pressed", String(button.dataset.view === view));
    hideTip();
    tipKey = null;
    paintMap();
    renderInset();
  }

  async function start() {
    const getJSON = async (url) => {
      const response = await fetch(url);
      if (!response.ok) throw new Error(`${url}: ${response.status}`);
      return response.json();
    };
    try {
      [S.topo, S.districtTopo, S.mapSource, S.data] = await Promise.all([getJSON("data/municipios.topojson"), getJSON("data/distritos.topojson"), getJSON("data/map_source.json"), getJSON("data/politicians.json")]);
    } catch (error) {
      const notice = $("#load-error");
      notice.hidden = false;
      notice.textContent = `No se pudieron cargar los datos (${error.message}). Genera los archivos con «python tools/build_map.py» y «python tools/fetch_politicians.py», y abre la página con «python tools/serve.py».`;
      return;
    }
    buildMap();
    fillPicker();
    fillFilters();
    renderPeople();
    for (const button of document.querySelectorAll(".views button")) button.addEventListener("click", () => setView(button.dataset.view));
    // Deep links: #vista=deputy&entidad=15
    const wanted = new URLSearchParams(location.hash.slice(1));
    if (wanted.get("vista") === "overview") location.replace("poderes.html"); // the old address of Poderes
    if (wanted.get("vista") && document.querySelector(`.views button[data-view="${wanted.get("vista")}"]`)) setView(wanted.get("vista"));
    if (wanted.get("entidad")) select(wanted.get("entidad"));
    $("#roster-more").addEventListener("click", () => {
      showAllRows = true;
      renderRoster();
    });
    $("#show-munis").addEventListener("change", (event) => {
      S.showMunis = event.target.checked;
      $("#map").classList.toggle("show-munis", S.showMunis);
      hoverState.attr("d", null);
      hideTip();
      tipKey = null;
    });

    // The refresh button only exists when the local server (tools/serve.py) is behind the page.
    fetch("api/status")
      .then((response) => (response.ok ? response.json() : null))
      .then((status) => {
        if (status && status.live) {
          $("#refresh").hidden = false;
          $("#refresh").addEventListener("click", refreshData);
        }
      })
      .catch(() => {});
  }

  start();
})();
