/* Infórmate: one map you go into level by level.
   Country (with the Presidency) -> state (government, Senate seats, economy) -> federal
   district (its deputy) -> municipality (its president). Names are shown at each level;
   a person's data appears when their name is pressed. */
(() => {
  "use strict";

  const { el, link, swatch, partyOf, partyRank, partyLabel, fold, integer, signed, oneDecimal, moment, day, motionOK, fact, facts, personLine, personCard, regions, EVERYDAY_NAME } = MXD;
  // Where a state's mark sits when its centre is too crowded: a nudge in map units, or, for the three
  // smallest central states, a fixed spot in a labelled column over the Pacific, joined by a thin line.
  const MARK_NUDGE = { "22": [-4, -16], "13": [18, -4], "15": [-12, 16], "21": [-4, 14], "06": [-30, 22], "12": [25, 14], "11": [-24, 10] };
  const MARK_AT = { "09": [468, 546], "17": [468, 580], "29": [468, 614] };
  // The three bars under each mark, in this order; each is the state's place among the 32 (tallest = highest value).
  const BARS = [
    { key: "unemployment", label: "Desocupación", value: (code) => (S.economy && S.economy.employment.states[code] ? S.economy.employment.states[code].unemployment : null) },
    { key: "homicides", label: "Homicidios por 100 mil", value: (code) => (S.crime && S.crime.states[code] ? S.crime.states[code].homicide_rate : null) },
    { key: "fuel", label: "Gasolina regular", value: (code) => (S.fuel && S.fuel.states[code] ? S.fuel.states[code].regular : null) },
  ];

  // Where the reader is: a level, what was chosen to get there, and the person whose data is open.
  const S = { data: null, gdp: null, crime: null, fuel: null, economy: null, capitals: null, cities: null, topo: null, districtTopo: null, mapSource: null, states: [], districts: [], munis: [], level: "country", state: null, district: null, muni: null, person: null, ctx: null, heritage: null, layers: { pueblos: false, unesco: false }, points: [] };
  const $ = (selector) => document.querySelector(selector);
  const stateName = (code) => EVERYDAY_NAME[code] || (S.states.find((s) => s.code === code) || {}).name || code;

  const peopleOf = (office, test = () => true) => S.data.people.filter((p) => p.office === office && test(p));
  const governorOf = (code) => peopleOf("governor", (p) => p.state_code === code)[0] || null;
  const senatorsOf = (code) =>
    peopleOf("senator", (p) => p.state_code === code).sort(
      (a, b) => (a.election_type === "Primera minoría") - (b.election_type === "Primera minoría") || a.name.localeCompare(b.name, "es")
    );
  const deputyOf = (district) => peopleOf("deputy", (p) => p.state_code === district.state_code && p.district_number === district.number)[0] || null;
  const mayorOf = (code) => peopleOf("mayor", (p) => p.municipality_code === code)[0] || null;
  const stateOf = (code) => S.states.find((s) => s.code === code);

  /** "Morena 12 · PAN 5 · …" for a group of people, biggest party first. */
  function partySplit(people) {
    const counts = d3.rollup(people, (group) => group.length, (p) => p.party);
    const codes = [...counts.keys()].sort((a, b) => counts.get(b) - counts.get(a) || partyRank(a) - partyRank(b));
    return el("ul", { class: "legend__items ficha__parties" }, codes.map((code) => el("li", {}, swatch(code), partyOf(code).label, el("span", { class: "legend__count" }, String(counts.get(code))))));
  }

  // ---------- Map ----------

  const W = 960;
  const H = 640;
  const svg = d3.select("#map svg").attr("viewBox", `0 0 ${W} ${H}`).attr("preserveAspectRatio", "xMidYMid meet");
  const projection = d3.geoConicConformal().parallels([17.5, 29.5]).rotate([102, 0]);
  const path = d3.geoPath(projection);
  const underlay = $("#map canvas");
  const pen = underlay.getContext("2d");
  const cssColor = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  const hexCache = new Map();
  const hexOf = (variable) => (hexCache.has(variable) ? hexCache : hexCache.set(variable, cssColor(variable))).get(variable);
  let zoomLayer, hoverShape, chosenOutline, marks, capitalMark, capitalStars, cityMarks, heritageMarks, zoom, graticule, stateLines, districtLines, muniLines, tip;
  let abroadShapes = [], abroadLines = null, abroadLabels = null;
  const STAR = "M0,-6.5 L1.9,-2 L6.5,-2 L2.8,0.9 L4,5.5 L0,2.6 L-4,5.5 L-2.8,0.9 L-6.5,-2 L-1.9,-2 Z";
  let transform = d3.zoomIdentity;

  function buildMap() {
    const layer = S.topo.objects.municipios;
    const factsByState = new Map(S.mapSource.states.map((s) => [s.cve_ent, s]));
    S.states = Array.from(d3.group(layer.geometries, (g) => g.properties.cve_ent), ([code, geometries]) => ({
      code,
      ...(factsByState.get(code) || { name: code }),
      municipalities: geometries.length,
      feature: { type: "Feature", geometry: topojson.merge(S.topo, geometries) },
    })).sort((a, b) => a.code.localeCompare(b.code));
    const country = { type: "Feature", geometry: topojson.merge(S.topo, layer.geometries) };
    projection.fitExtent([[24, 24], [W - 24, H - 24]], country);
    S.countryBox = path.bounds(country);
    for (const state of S.states) {
      state.outline = path(state.feature);
      state.shape = new Path2D(state.outline);
      state.box = path.bounds(state.feature);
      const [cx, cy] = path.centroid(state.feature);
      const [dx, dy] = MARK_NUDGE[state.code] || [0, 0];
      state.centre = [cx, cy];
      state.mark = MARK_AT[state.code] || [cx + dx, cy + dy];
    }
    S.munis = topojson.feature(S.topo, layer).features.map((feature) => ({
      code: feature.properties.cvegeo,
      name: feature.properties.nomgeo,
      state_code: feature.properties.cve_ent,
      population: feature.properties.pob,
      seat: feature.properties.cab,
      outline: path(feature),
      shape: new Path2D(path(feature)),
      box: path.bounds(feature),
      centre: path.centroid(feature),
    }));
    S.muniByCode = new Map(S.munis.map((m) => [m.code, m]));
    const districtLayer = S.districtTopo.objects.distritos;
    S.districts = topojson.feature(S.districtTopo, districtLayer).features.map((feature) => ({
      state_code: feature.properties.ent,
      number: feature.properties.dist,
      outline: path(feature),
      shape: new Path2D(path(feature)),
      box: path.bounds(feature),
    }));
    const sameState = (a, b) => a.properties.cve_ent === b.properties.cve_ent;
    graticule = new Path2D(path(d3.geoGraticule().extent([[-150, 0], [-55, 45]]).step([5, 5])()));
    stateLines = new Path2D(path(topojson.mesh(S.topo, layer, (a, b) => a !== b && !sameState(a, b))));
    muniLines = new Path2D(path(topojson.mesh(S.topo, layer, (a, b) => a !== b && sameState(a, b))));
    districtLines = new Path2D(path(topojson.mesh(S.districtTopo, districtLayer, (a, b) => a !== b)));
    if (S.abroad) {
      // The countries around Mexico, cut to the frame: drawn under everything, named at the country level.
      const countries = topojson.feature(S.abroad, S.abroad.objects.vecinos).features;
      // Names sit at each country's centre, except the United States, whose centre is far above the frame.
      abroadShapes = countries.map((f) => ({ code: f.properties.code, name: f.properties.name, shape: new Path2D(path(f)), centre: f.properties.code === "USA" ? projection([-104.5, 31.6]) : path.centroid(f) }));
      abroadLines = new Path2D(path(topojson.mesh(S.abroad, S.abroad.objects.vecinos)));
    }

    zoomLayer = svg.append("g");
    zoomLayer.append("path").attr("class", "coast").attr("d", path(topojson.mesh(S.topo, layer, (a, b) => a === b)));
    hoverShape = zoomLayer.append("path").attr("class", "hover-state");
    chosenOutline = zoomLayer.append("path").attr("class", "selected-outline");

    const hits = (items, kind, tipFor, onPick) =>
      zoomLayer
        .append("g")
        .attr("class", `hits hits--${kind}`)
        .on("pointerleave", () => {
          tip.hide();
          hoverShape.attr("d", null);
        })
        .selectAll("path")
        .data(items)
        .join("path")
        .attr("class", "hit")
        .attr("d", (d) => d.outline)
        .on("pointermove", (event, d) => {
          hoverShape.attr("d", d.outline);
          const district = kind === "muni" ? districtAt(event, d.state_code) : null;
          tip.show(event, kind + (d.code || `${d.state_code}-${d.number}`) + (district ? `-${district.number}` : ""), () => tipFor(d, event));
        })
        .on("click", (event, d) => onPick(d, event));
    hits(S.munis, "muni", (muni, event) => muniTip(muni, districtAt(event, muni.state_code)), (muni, event) => go("municipality", { state: stateOf(muni.state_code), district: districtAt(event, muni.state_code), muni }));
    hits(S.districts, "district", districtTip, (district) => go("district", { state: stateOf(district.state_code), district }));
    // Drawn last, so inside a state the other states still answer as whole states.
    hits(S.states, "state", stateTip, (state) => go("state", { state }));
    buildMarks();
    buildCities();
    capitalMark = zoomLayer.append("g").attr("class", "capital").style("display", "none");
    capitalMark.append("circle").attr("class", "capital__dot").attr("r", 4);
    capitalMark.append("text").attr("class", "capital__label").attr("x", 7).attr("y", 4);

    zoom = d3
      .zoom()
      .scaleExtent([1, 60])
      .translateExtent([[-120, -60], [W + 120, H + 60]])
      .filter((event) => {
        if (event.type === "wheel") return true; // the wheel zooms the map
        if (event.type.startsWith("touch")) return event.touches.length > 1;
        return !event.button;
      })
      .on("zoom", (event) => {
        transform = event.transform;
        zoomLayer.attr("transform", transform).style("--k", transform.k);
        placeMarks();
        placeCapital();
        placeCities();
        placeHeritage();
        placeAbroad();
        draw();
      });
    svg.call(zoom).on("dblclick.zoom", null);
    $("#zoom-in").addEventListener("click", () => svg.transition().duration(motionOK ? 250 : 0).call(zoom.scaleBy, 1.8));
    $("#zoom-out").addEventListener("click", () => svg.transition().duration(motionOK ? 250 : 0).call(zoom.scaleBy, 1 / 1.8));
    $("#zoom-reset").addEventListener("click", () => go("country", {}));
    new ResizeObserver(draw).observe(underlay);
  }

  /** Height of each bar for a state: its place among the states that have the figure, as a fraction of `max`. */
  function barHeights(code, max) {
    return BARS.map((bar) => {
      const values = S.states.map((s) => [s.code, bar.value(s.code)]).filter(([, v]) => v != null).sort((a, b) => a[1] - b[1]);
      const i = values.findIndex(([c]) => c === code);
      return i < 0 ? 0 : Math.max(1.2, (max * (i + 1)) / values.length);
    });
  }

  /** Stars on every state capital at the country level; dots with names for the main cities inside a state. */
  const citiesOf = (code) => (S.cities ? S.cities.cities.filter((c) => c.state_code === code && c.municipality_code && S.muniByCode.get(c.municipality_code)) : []);
  function buildCities() {
    const capitals = S.capitals ? Object.entries(S.capitals.states).map(([code, c]) => ({ code, ...c, muni: c.municipality_code ? S.muniByCode.get(c.municipality_code) : null })).filter((c) => c.muni) : [];
    capitalStars = zoomLayer
      .insert("g", ".marks")
      .attr("class", "stars")
      .selectAll("g")
      .data(capitals)
      .join("g")
      .attr("class", "star")
      .attr("transform", (d) => `translate(${d.muni.centre[0]}, ${d.muni.centre[1]})`)
      .on("pointermove", (event, d) => tip.show(event, `cap${d.code}`, () => [el("p", {}, d.capital), el("p", { class: "tooltip__place" }, `Capital de ${stateName(d.code)}`), el("p", { class: "tooltip__sub" }, "Pulsa para entrar")]))
      .on("pointerleave", () => tip.hide())
      .on("click", (event, d) => go("state", { state: stateOf(d.code) }));
    capitalStars.append("path").attr("class", "star__shape").attr("d", STAR);
    const cities = S.cities ? S.cities.cities.filter((c) => c.municipality_code && S.muniByCode.get(c.municipality_code)) : [];
    cityMarks = zoomLayer
      .append("g")
      .attr("class", "cities")
      .selectAll("g")
      .data(cities)
      .join("g")
      .attr("class", "city")
      .style("display", "none");
    cityMarks.append("circle").attr("class", "city__dot").attr("r", 3);
    cityMarks.append("text").attr("class", "city__label").attr("x", 6).attr("y", 3.5).text((d) => d.name);
  }
  /** Cities as dots with names: the big ones at the country level, all of a state's inside it; capitals keep their star. */
  function placeCities() {
    if (!cityMarks) return;
    const code = S.state && S.level !== "country" ? S.state.code : null;
    const isCapital = (d) => {
      const capital = capitalOf(d.state_code);
      return Boolean(capital && capital.municipality_code === d.municipality_code);
    };
    // At the country level one name per metropolitan area, its largest city; a metro that holds a capital shows only the star.
    const all = S.cities ? S.cities.cities : [];
    const metroKey = (c) => c.metro || c.name;
    const largestOfMetro = new Map();
    const metroHasCapital = new Set();
    for (const c of all) {
      if (c.state_code === "09" || isCapital(c)) metroHasCapital.add(metroKey(c));
      if (c.municipality_code && (!largestOfMetro.has(metroKey(c)) || largestOfMetro.get(metroKey(c)).population < c.population)) largestOfMetro.set(metroKey(c), c);
    }
    const shown = (d) => !isCapital(d) && Boolean(code) && d.state_code === code;
    cityMarks
      .style("display", (d) => (shown(d) ? null : "none"))
      .attr("transform", (d) => {
        const muni = S.muniByCode.get(d.municipality_code);
        return `translate(${muni.centre[0]}, ${muni.centre[1]}) scale(${1 / transform.k})`;
      });
    declutterLabels();
    if (capitalStars) capitalStars.attr("transform", (d) => `translate(${d.muni.centre[0]}, ${d.muni.centre[1]}) scale(${1 / transform.k})`).style("display", S.level === "country" ? null : "none");
  }

  /** Names that would sit on top of each other are dropped, biggest city first; the capital's name always stays. */
  function declutterLabels() {
    const kept = [];
    const overlaps = (a, b) => a.left < b.right + 2 && b.left < a.right + 2 && a.top < b.bottom + 1 && b.top < a.bottom + 1;
    if (capitalMark && capitalMark.style("display") !== "none") kept.push(capitalMark.select("text").node().getBoundingClientRect());
    const visible = cityMarks.filter(function () { return this.style.display !== "none"; }).nodes().sort((a, b) => b.__data__.population - a.__data__.population);
    for (const node of visible) {
      const text = node.querySelector("text");
      text.style.display = null;
      const box = text.getBoundingClientRect();
      if (kept.some((k) => overlaps(box, k))) text.style.display = "none";
      else kept.push(box);
    }
  }

  /** The capital of the chosen state: where it is, and the marker on the map (inside the state only). */
  const capitalOf = (code) => (S.capitals && S.capitals.states[code]) || null;
  function placeCapital() {
    if (!capitalMark) return;
    const capital = S.state && S.level !== "country" ? capitalOf(S.state.code) : null;
    const muni = capital && capital.municipality_code ? S.muniByCode.get(capital.municipality_code) : null;
    if (!muni) {
      capitalMark.style("display", "none");
      return;
    }
    capitalMark.style("display", null).attr("transform", `translate(${muni.centre[0]}, ${muni.centre[1]}) scale(${1 / transform.k})`).raise();
    capitalMark.select("text").text(capital.capital);
    capitalMark.select("circle").attr("display", "none");
    if (capitalMark.select("path").empty()) capitalMark.insert("path", "text").attr("class", "star__shape").attr("d", STAR);
  }

  /** The federal district under the pointer, within a state; null over no district. */
  function districtAt(event, stateCode) {
    if (!event || !zoomLayer) return null;
    const [x, y] = d3.pointer(event, zoomLayer.node());
    pen.save();
    pen.setTransform(1, 0, 0, 1, 0, 0);
    const found = S.districts.find((d) => d.state_code === stateCode && pen.isPointInPath(d.shape, x, y)) || null;
    pen.restore();
    return found;
  }

  /** Where a state's mark sits at this zoom: its designed spot at the country view (some sit in the
   *  sea, with a leader line), sliding towards the state's centre as you zoom in, since the state
   *  then has room for it. The leader line follows. */
  const markAt = (d) => {
    const k2 = transform.k * transform.k;
    return [d.centre[0] + (d.mark[0] - d.centre[0]) / k2, d.centre[1] + (d.mark[1] - d.centre[1]) / k2];
  };
  function placeMarks() {
    if (!marks) return;
    marks.attr("transform", (d) => {
      const [x, y] = markAt(d);
      return `translate(${x}, ${y}) scale(${1 / transform.k})`;
    });
    marks
      .select(".mark__leader")
      .attr("x1", (d) => (d.centre[0] - markAt(d)[0]) * transform.k)
      .attr("y1", (d) => (d.centre[1] - markAt(d)[1]) * transform.k);
  }

  /** On every state, a square for its governor and three circles for its senators, in party colours,
   *  and under them three bars: unemployment, homicide rate and gasoline price, as places among the 32. */
  function buildMarks() {
    const size = 10;
    const r = 4.3;
    const slots = [-21, -9, 2, 13]; // left edges: the square, then the three circles
    const barTop = size / 2 + 3; // the bars hang from here
    const barMax = 10;
    const barWidth = 11;
    marks = zoomLayer
      .append("g")
      .attr("class", "marks")
      .selectAll("g")
      .data(S.states)
      .join("g")
      .attr("class", "mark")
      .attr("transform", (d) => `translate(${d.mark[0]}, ${d.mark[1]})`)
      .on("pointermove", (event, d) => {
        hoverShape.attr("d", d.outline);
        tip.show(event, `state${d.code}`, () => stateTip(d));
      })
      .on("pointerleave", () => {
        tip.hide();
        hoverShape.attr("d", null);
      })
      .on("click", (event, d) => go("state", { state: d }));
    marks
      .filter((d) => MARK_AT[d.code])
      .append("line")
      .attr("class", "mark__leader")
      .attr("x1", (d) => d.centre[0] - d.mark[0])
      .attr("y1", (d) => d.centre[1] - d.mark[1])
      .attr("x2", 0)
      .attr("y2", 0);
    marks.append("rect").attr("class", "mark__halo").attr("x", slots[0] - 3).attr("y", -size / 2 - 3).attr("width", slots[3] + 2 * r + 3 - slots[0] + 3).attr("height", size + 6 + 3 + barMax + 2).attr("rx", 3);
    // The bars: a faint baseline, then one bar per figure, growing downwards from the top of the row.
    marks.append("line").attr("class", "mark__base").attr("x1", slots[0]).attr("x2", slots[0] + 3 * barWidth + 4).attr("y1", barTop).attr("y2", barTop);
    BARS.forEach((bar, i) => {
      marks
        .append("rect")
        .attr("class", `mark__bar mark__bar--${bar.key}`)
        .attr("x", slots[0] + i * (barWidth + 2))
        .attr("y", barTop)
        .attr("width", barWidth)
        .attr("height", (d) => barHeights(d.code, barMax)[i]);
    });
    marks
      .append("rect")
      .attr("class", "mark__gov")
      .attr("x", slots[0])
      .attr("y", -size / 2)
      .attr("width", size)
      .attr("height", size)
      .style("fill", (d) => {
        const governor = governorOf(d.code);
        return governor ? partyOf(governor.party).color : "var(--sheet)";
      });
    marks
      .filter((d) => MARK_AT[d.code])
      .append("text")
      .attr("class", "mark__label")
      .attr("x", slots[3] + 2 * r + 7)
      .attr("y", 8)
      .text((d) => stateName(d.code));
    for (const i of [0, 1, 2]) {
      marks
        .append("circle")
        .attr("class", "mark__sen")
        .attr("cx", slots[i + 1] + r)
        .attr("cy", 0)
        .attr("r", r)
        .style("fill", (d) => {
          const senator = senatorsOf(d.code)[i];
          return senator ? partyOf(senator.party).color : "var(--sheet)";
        });
    }
  }

  function zoomToBox(box) {
    let target = d3.zoomIdentity;
    if (box) {
      const [[x0, y0], [x1, y1]] = box;
      const k = Math.max(1, Math.min(60, 0.7 / Math.max((x1 - x0) / W, (y1 - y0) / H)));
      target = d3.zoomIdentity.translate(W / 2, H / 2).scale(k).translate(-(x0 + x1) / 2, -(y0 + y1) / 2);
    }
    svg.transition().duration(motionOK ? 700 : 0).call(zoom.transform, target);
  }

  /** What the canvas shows depends on the level: states, then the state's districts, then its municipalities. */
  function draw() {
    if (!graticule) return;
    const density = window.devicePixelRatio || 1;
    const width = Math.round(underlay.clientWidth * density);
    const height = Math.round(underlay.clientHeight * density);
    if (underlay.width !== width || underlay.height !== height) {
      underlay.width = width;
      underlay.height = height;
    }
    const fit = Math.min(underlay.clientWidth / W, underlay.clientHeight / H);
    const left = (underlay.clientWidth - W * fit) / 2;
    const top = (underlay.clientHeight - H * fit) / 2;
    const scale = density * fit * transform.k;
    const place = new DOMMatrix([scale, 0, 0, scale, density * (left + fit * transform.x), density * (top + fit * transform.y)]);
    const px = (n) => (n * density) / scale;

    pen.setTransform(1, 0, 0, 1, 0, 0);
    pen.clearRect(0, 0, width, height);
    pen.setTransform(place);
    pen.strokeStyle = hexOf("--map-grat");
    pen.lineWidth = px(0.6);
    pen.stroke(graticule);

    if (abroadLines) {
      pen.fillStyle = hexOf("--map-abroad");
      for (const country of abroadShapes) pen.fill(country.shape);
      pen.strokeStyle = hexOf("--map-border");
      pen.lineWidth = px(0.9);
      pen.stroke(abroadLines);
    }

    pen.fillStyle = hexOf("--land");
    for (const state of S.states) pen.fill(state.shape);

    if (S.state && S.level !== "country") {
      // Inside the chosen state: a lighter ground, thin municipality lines and dashed district lines, no party colours.
      pen.save();
      pen.clip(S.state.shape);
      pen.fillStyle = hexOf("--map-ground");
      pen.fill(S.state.shape);
      pen.strokeStyle = hexOf("--map-line");
      pen.lineWidth = px(0.7);
      pen.stroke(muniLines);
      pen.strokeStyle = hexOf("--map-district");
      pen.lineWidth = px(1.5);
      pen.setLineDash([px(5), px(3)]);
      pen.stroke(districtLines);
      pen.setLineDash([]);
      pen.restore();
      if (S.district) {
        pen.strokeStyle = hexOf("--map-district");
        pen.lineWidth = px(2.6);
        pen.setLineDash([px(6), px(4)]);
        pen.stroke(S.district.shape);
        pen.setLineDash([]);
      }
    }
    pen.strokeStyle = S.level === "country" ? hexOf("--map-state-line") : hexOf("--map-state-line-inner");
    pen.lineWidth = px(S.level === "country" ? 1.5 : 1);
    pen.stroke(stateLines);
  }

  // ---------- Hover boxes ----------

  const tipPerson = (person, role) => el("span", {}, swatch(person.party), ` ${person.name}, ${partyLabel(person)}${role ? ` (${role})` : ""}`);

  function stateTip(state) {
    const governor = governorOf(state.code);
    const senators = senatorsOf(state.code);
    const gdp = S.gdp && S.gdp.states[state.code];
    const job = S.economy && S.economy.employment.states[state.code];
    const crime = S.crime && S.crime.states[state.code];
    const fuel = S.fuel && S.fuel.states[state.code];
    const place = (rank, of) => (rank ? ` (${ordinal(rank, of)})` : "");
    return [
      el("p", { class: "tooltip__place" }, stateName(state.code)),
      el("p", { class: "tooltip__sub" }, `${integer.format(state.population)} habitantes${gdp ? ` · ${oneDecimal.format(gdp.share)} % del PIB` : ""}`),
      el("div", { class: "tooltip__people" }, governor ? tipPerson(governor, governor.title) : el("span", {}, "Gobierno: sin dato"), ...senators.map((p) => tipPerson(p, p.title))),
      el(
        "div",
        { class: "tooltip__people" },
        job ? el("span", {}, `Desocupación: ${oneDecimal.format(job.unemployment)} %${place(job.rank_by_unemployment, 32)}`) : null,
        crime ? el("span", {}, `Homicidios dolosos: ${oneDecimal.format(crime.homicide_rate)} por 100 mil${place(crime.rank_by_rate, 32)}`) : null,
        fuel && fuel.regular != null ? el("span", {}, `Gasolina regular: ${fuel.regular.toFixed(2)} pesos/litro${place(Number(rankOf(state.code, (c) => (S.fuel.states[c] || {}).regular).split(".")[0]), 32)}`) : null
      ),
      el("p", { class: "tooltip__sub" }, "Pulsa para entrar"),
    ];
  }

  function districtTip(district) {
    const deputy = deputyOf(district);
    return [el("p", {}, `Distrito ${district.number}`), el("p", { class: "tooltip__place" }, stateName(district.state_code)), el("div", { class: "tooltip__people" }, [deputy ? tipPerson(deputy) : el("span", {}, "Diputación aún no leída de la fuente")]), el("p", { class: "tooltip__sub" }, "Pulsa para entrar")];
  }

  function muniTip(muni, district) {
    const mayor = mayorOf(muni.code);
    const deputy = district ? deputyOf(district) : null;
    return [
      el("p", {}, muni.name),
      el("p", { class: "tooltip__place" }, `${stateName(muni.state_code)}${muni.population ? ` · ${integer.format(muni.population)} habitantes` : ""}`),
      el("div", { class: "tooltip__people" }, [mayor ? tipPerson(mayor, mayor.title) : el("span", {}, "Ayuntamiento: sin dato en la fuente")]),
      district ? el("div", { class: "tooltip__people" }, el("span", {}, `Distrito federal ${district.number}`), deputy ? tipPerson(deputy, deputy.title) : el("span", {}, "Diputación aún no leída de la fuente")) : null,
      el("p", { class: "tooltip__sub" }, "Pulsa para entrar"),
    ];
  }

  // ---------- Levels ----------

  const HINTS = {
    country: "Estrella: la capital. Cuadrado: partido de quien gobierna; círculos: los de sus tres senadurías. Barras: desocupación, homicidios por 100 mil habitantes y precio de la gasolina, por altura según el lugar entre las 32. Pulsa una entidad para entrar.",
    state: "Las líneas finas son los municipios; las punteadas, los distritos electorales federales. Pulsa un municipio para ver su ayuntamiento y la diputación de su distrito, u otra entidad para cambiar.",
    district: "El distrito elegido va punteado más grueso. Pulsa un municipio para ver su ayuntamiento, u otra entidad para cambiar.",
    municipality: "Pulsa otro municipio, u otra entidad; arriba puedes volver a un nivel anterior.",
  };

  /** The key drawn on the map: what the marks, stars, dots and lines mean at this level. */
  const svgEl = (tag, attrs = {}) => {
    const node = document.createElementNS("http://www.w3.org/2000/svg", tag);
    for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
    return node;
  };
  const symbol = (...parts) => {
    const svg = svgEl("svg", { viewBox: "0 0 34 20", "aria-hidden": "true" });
    for (const part of parts) svg.append(part);
    return svg;
  };
  const SYMBOL = {
    governor: () => symbol(svgEl("rect", { x: 12, y: 5, width: 10, height: 10, class: "key-square" })),
    senators: () => symbol(...[7, 17, 27].map((cx) => svgEl("circle", { cx, cy: 10, r: 4, class: "key-circle" }))),
    bars: () => symbol(...[[9, 6], [15, 10], [21, 14]].map(([x, h]) => svgEl("rect", { x, y: 17 - h, width: 4, height: h, class: "key-bar" }))),
    star: () => symbol(svgEl("path", { d: STAR, transform: "translate(17 10) scale(1.1)", class: "key-star" })),
    city: () => symbol(svgEl("circle", { cx: 17, cy: 10, r: 3, class: "key-city" })),
    stateLine: () => symbol(svgEl("path", { d: "M2 14 C 10 4, 22 16, 32 6", class: "key-line key-line--state" })),
    muniLine: () => symbol(svgEl("path", { d: "M2 14 C 10 4, 22 16, 32 6", class: "key-line key-line--muni" })),
    districtLine: () => symbol(svgEl("path", { d: "M2 14 C 10 4, 22 16, 32 6", class: "key-line key-line--district" })),
    chosenDistrict: () => symbol(svgEl("path", { d: "M2 14 C 10 4, 22 16, 32 6", class: "key-line key-line--chosen" })),
    pueblo: () => symbol(svgEl("path", { d: "M17,4 L23,10 L17,16 L11,10 Z", class: "heritage__pueblo" })),
    unesco: () => symbol(svgEl("circle", { cx: 17, cy: 10, r: 4.5, class: "heritage__unesco heritage__unesco--cultural" })),
  };
  const LEGEND = {
    country: [["governor", "Partido de quien gobierna la entidad"], ["senators", "Partidos de sus tres senadurías"], ["bars", "Desocupación, homicidios y gasolina: la barra sube con el lugar entre las 32 (más alta, peor)"], ["star", "Capital de la entidad"], ["stateLine", "Límite entre entidades"]],
    state: [["star", "Capital de la entidad"], ["city", "Ciudad de más de 100 mil habitantes"], ["muniLine", "Límite municipal"], ["districtLine", "Distrito electoral federal"], ["stateLine", "Límite entre entidades"]],
    district: [["chosenDistrict", "El distrito elegido"], ["districtLine", "Otros distritos electorales federales"], ["muniLine", "Límite municipal"], ["star", "Capital de la entidad"], ["city", "Ciudad de más de 100 mil habitantes"]],
    municipality: [["star", "Capital de la entidad"], ["city", "Ciudad de más de 100 mil habitantes"], ["muniLine", "Límite municipal"], ["districtLine", "Distrito electoral federal"]],
  };
  function renderLegend(level) {
    const rows = [...LEGEND[level]];
    if (S.layers.pueblos) rows.push(["pueblo", "Pueblo Mágico, programa de la Secretaría de Turismo"]);
    if (S.layers.unesco) rows.push(["unesco", "Patrimonio Mundial de la UNESCO: azul cultural, verde natural, ocre mixto"]);
    $("#legend").replaceChildren(...rows.map(([kind, text]) => el("div", { class: "map-legend__row" }, SYMBOL[kind](), el("span", {}, text))));
  }

  /** Pueblos Mágicos and World Heritage points: projected once and placed in their state and municipality. */
  function buildHeritage() {
    if (!S.heritage || !zoomLayer) return;
    const place = (lat, lon) => {
      const xy = projection([lon, lat]);
      if (!xy) return { xy: null, state: null, muni: null };
      pen.save();
      pen.setTransform(1, 0, 0, 1, 0, 0);
      const state = S.states.find((s) => pen.isPointInPath(s.shape, xy[0], xy[1])) || null;
      const muni = state ? S.munis.find((m) => m.state_code === state.code && pen.isPointInPath(m.shape, xy[0], xy[1])) || null : null;
      pen.restore();
      return { xy, state, muni };
    };
    S.points = [];
    for (const p of S.heritage.pueblos.items) if (p.lat != null) S.points.push({ kind: "pueblos", name: p.name, when: p.named_on, state_code: p.state_code, ...place(p.lat, p.lon) });
    for (const site of S.heritage.unesco.items) for (const [lat, lon] of site.points) S.points.push({ kind: "unesco", name: site.name, category: site.category, inscribed: site.inscribed, url: site.url, danger: site.danger, ...place(lat, lon) });
    S.points = S.points.filter((p) => p.xy);
    heritageMarks = zoomLayer.append("g").attr("class", "heritage");
    heritageMarks
      .selectAll("g")
      .data(S.points)
      .join("g")
      .attr("class", (d) => `heritage__mark heritage__mark--${d.kind}`)
      .style("display", "none")
      .each(function (d) {
        const g = d3.select(this);
        if (d.kind === "pueblos") g.append("path").attr("d", "M0,-5.5 L5.5,0 L0,5.5 L-5.5,0 Z").attr("class", "heritage__pueblo");
        else g.append("circle").attr("r", 4.5).attr("class", `heritage__unesco heritage__unesco--${d.category}`);
      })
      .on("pointermove", (event, d) => tip.show(event, `h${d.kind}${d.name}${d.xy[0]}`, () => heritageTip(d)))
      .on("pointerleave", () => tip.hide())
      .on("click", (event, d) => {
        event.stopPropagation();
        if (d.muni) go("municipality", { state: d.state, district: null, muni: d.muni });
        else if (d.state) go("state", { state: d.state });
      });
    const keyToggle = $("#key-toggle");
    if (keyToggle) keyToggle.addEventListener("click", () => keyToggle.setAttribute("aria-pressed", String(document.body.classList.toggle("show-key"))));
    for (const key of ["pueblos", "unesco"]) {
      const box = $(`#layer-${key}`);
      if (!box) continue;
      box.addEventListener("change", () => {
        S.layers[key] = box.checked;
        placeHeritage();
        renderLegend(S.level);
      });
    }
    placeHeritage();
  }

  /** The neighbours' names, kept the same size at any zoom; only the four that fit the frame well. */
  function placeAbroad() {
    if (!abroadShapes.length || !zoomLayer) return;
    if (!abroadLabels) {
      abroadLabels = zoomLayer
        .insert("g", ":first-child")
        .attr("class", "abroad")
        .selectAll("text")
        .data(abroadShapes.filter((c) => ["USA", "GTM", "BLZ", "CUB"].includes(c.code)))
        .join("text")
        .attr("class", "abroad__label")
        .text((d) => d.name);
    }
    abroadLabels.attr("transform", (d) => `translate(${d.centre[0]}, ${d.centre[1]}) scale(${1 / transform.k})`).style("display", S.level === "country" || transform.k < 2.5 ? null : "none");
  }

  function placeHeritage() {
    if (!heritageMarks) return;
    heritageMarks
      .selectAll(".heritage__mark")
      .style("display", (d) => (S.layers[d.kind] ? null : "none"))
      .attr("transform", (d) => `translate(${d.xy[0]}, ${d.xy[1]}) scale(${1 / transform.k})`);
  }

  function heritageTip(d) {
    const where = `${d.state ? stateName(d.state.code) : d.state_code ? stateName(d.state_code) : ""}${d.muni ? ` · ${d.muni.name}` : ""}`;
    const what = d.kind === "pueblos" ? `Pueblo Mágico desde ${day(d.when)}` : `Patrimonio Mundial (${d.category}), inscrito en ${d.inscribed}${d.danger ? "; en la lista del patrimonio en peligro" : ""}`;
    return [el("p", {}, d.name), el("p", { class: "tooltip__place" }, where), el("p", { class: "tooltip__sub" }, what), el("p", { class: "tooltip__sub" }, d.muni ? "Pulsa para ver el municipio" : "")];
  }

  /** Pueblos Mágicos and World Heritage sites of a place, as rows: names first, each a way to its municipality. */
  function heritageRows(stateCode, muniCode) {
    if (!S.heritage) return [fact("Pueblos Mágicos y Patrimonio Mundial", "Sin dato: falta el archivo de patrimonio")];
    const here = S.points.filter((p) => (muniCode ? p.muni && p.muni.code === muniCode : stateCode ? p.state && p.state.code === stateCode : true));
    const pueblos = here.filter((p) => p.kind === "pueblos");
    const sites = [...new Map(here.filter((p) => p.kind === "unesco").map((p) => [p.name, p])).values()];
    const toMuni = (p) => (p.muni && p.muni.code !== muniCode ? el("button", { type: "button", class: "persona__link", onclick: () => go("municipality", { state: p.state, district: null, muni: p.muni }) }, p.name) : p.name);
    const list = (items, render) => el("ul", { class: "plain" }, items.map((p) => el("li", {}, render(p))));
    const cite = S.heritage.pueblos.citation;
    const unesco = S.heritage.unesco.citation;
    const national = !stateCode && !muniCode;
    return [
      fact(
        national ? `Pueblos Mágicos (${S.heritage.pueblos.count})` : "Pueblos Mágicos",
        national ? "Localidades reconocidas por la Secretaría de Turismo; actívalos arriba para verlos en el mapa" : pueblos.length ? list(pueblos, (p) => [toMuni(p), el("span", { class: "muted" }, ` · desde ${day(p.when)}`)]) : "Ninguno"
      ),
      fact(
        national ? `Patrimonio Mundial (${S.heritage.unesco.count} sitios)` : "Patrimonio Mundial",
        national ? "Sitios inscritos por la UNESCO; actívalos arriba para verlos en el mapa" : sites.length ? list(sites, (p) => [toMuni(p), el("span", { class: "muted" }, ` · ${p.category}, ${p.inscribed}`), " ", link(p.url, "UNESCO")]) : "Ninguno"
      ),
      fact("Fuente del patrimonio", el("span", {}, link(cite.url, "Wikipedia, anexo de Pueblos Mágicos"), `, versión del ${day(cite.published_at)}, consultada el ${day(cite.retrieved_at)}; `, link(unesco.url, "UNESCO, Lista del Patrimonio Mundial"), `, consultada el ${day(unesco.retrieved_at)}`)),
    ];
  }

  const phone = window.matchMedia("(max-width: 700px)");
  const openSheet = (open) => document.body.classList.toggle("sheet-open", open && phone.matches);

  function go(level, { state = null, district = null, muni = null }) {
    openSheet(level !== "country");
    S.level = level;
    S.state = state;
    S.district = level === "state" || level === "country" ? null : district;
    S.muni = level === "municipality" ? muni : null;
    S.person = null;
    for (const name of ["country", "state", "district", "municipality"]) $("#map").classList.toggle(`level-${name}`, name === level);
    // Inside a state, that state's own hit shape steps aside so its districts and municipalities can be pointed at.
    zoomLayer.selectAll(".hits--state .hit").classed("hit--current", (d) => Boolean(state) && d.code === state.code);
    const focus = level === "municipality" ? muni : level === "district" ? district : state;
    chosenOutline.attr("d", focus && level !== "country" ? focus.outline : null);
    tip.hide();
    tip.reset();
    zoomToBox(focus ? focus.box : phone.matches ? S.countryBox : null); // a phone fills its narrow screen with the country
    placeCapital();
    placeCities();
    placeHeritage();
    placeAbroad();
    draw();
    $("#hint").textContent = HINTS[level];
    renderLegend(level);
    renderCrumbs();
    renderFicha();
  }

  /** Open one person's data where the level's data was; the level stays where it is. */
  function showPerson(person) {
    S.person = person;
    openSheet(true);
    renderFicha();
    $("#ficha").scrollIntoView({ block: "nearest", behavior: motionOK ? "smooth" : "auto" });
  }

  function renderCrumbs() {
    const crumb = (label, onclick) => (onclick ? el("button", { type: "button", class: "link-button", onclick }, label) : el("span", { "aria-current": "page" }, label));
    const parts = [crumb("México", S.level === "country" ? null : () => go("country", {}))];
    if (S.state) parts.push(crumb(stateName(S.state.code), S.level === "state" ? null : () => go("state", { state: S.state })));
    if (S.district) parts.push(crumb(`Distrito ${S.district.number}`, S.level === "district" ? null : () => go("district", { state: S.state, district: S.district })));
    if (S.muni) parts.push(crumb(S.muni.name, null));
    $("#crumbs").replaceChildren(...parts.flatMap((part, i) => (i ? [el("span", { class: "crumbs__sep", "aria-hidden": "true" }, "›"), part] : [part])));
  }

  /** The state's main cities, biggest first, each a jump to its municipality. */
  function cityRows(code) {
    const list = citiesOf(code).sort((a, b) => b.population - a.population);
    if (!list.length) return null;
    const row = (c) => {
      const muni = S.muniByCode.get(c.municipality_code);
      const label = c.municipality && fold(c.municipality) !== fold(c.name) ? `${c.name} (municipio de ${c.municipality})` : c.name;
      return fact(el("button", { type: "button", class: "persona__link", onclick: () => go("municipality", { state: stateOf(code), district: null, muni }) }, label), `${integer.format(c.population)} habitantes`);
    };
    return [
      el("h3", {}, `Ciudades de más de 100 mil habitantes: ${list.length}`),
      facts(list.map(row), sourceRow("Fuente", S.cities.citation.url, "Wikipedia, ciudades más pobladas", S.cities.citation.published_at, S.cities.citation.retrieved_at)),
      el("p", { class: "ficha__intro" }, `Población de las ciudades según la ${S.cities.population_source.split(" (")[0]}, como la da la fuente; es la ciudad, no el municipio.`),
    ];
  }

  /** "Capital: Villahermosa (municipio Centro)" with a jump to that municipality. */
  function capitalRow(code) {
    const capital = capitalOf(code);
    if (!capital) return null;
    const muni = capital.municipality_code ? S.muniByCode.get(capital.municipality_code) : null;
    if (!muni) return fact("Capital", capital.capital);
    const label = capital.municipality && capital.municipality !== capital.capital ? `${capital.capital} (municipio de ${capital.municipality})` : capital.capital;
    return fact("Capital", el("button", { type: "button", class: "persona__link", onclick: () => go("municipality", { state: stateOf(code), district: null, muni }) }, label));
  }
  const back = (label, onclick) => el("p", { class: "ficha__back" }, el("button", { type: "button", class: "link-button", onclick }, label));
  const people = (...persons) => el("ul", { class: "people" }, persons.flat().filter(Boolean).map((p) => personLine(p, showPerson)));
  const populationRows = (place) => [fact("Población (2020)", integer.format(place.population)), fact("Mujeres / hombres", `${integer.format(place.women)} / ${integer.format(place.men)}`), fact("Viviendas habitadas", integer.format(place.dwellings))];

  /** GDP rows for the country or a state, with the year and the unit spelled out. */
  function gdpRows(code) {
    if (!S.gdp) return [fact("PIB", "Sin dato: falta el archivo de PIB")];
    const row = code ? S.gdp.states[code] : S.gdp.national;
    if (!row) return [fact("PIB", "Sin dato en la fuente")];
    return [
      fact(`PIB ${S.gdp.year}`, `${integer.format(row.gdp)} mil millones de pesos (precios de 2018)`),
      code ? fact("Parte del PIB nacional", `${oneDecimal.format(row.share)} %`) : null,
      fact(`Crecimiento ${S.gdp.year}`, `${signed.format(row.growth)} %`),
    ];
  }
  const sourceRow = (label, url, text, published, retrieved) => fact(label, el("span", {}, link(url, text), published ? ` del ${day(published)}` : "", `; leído el ${day(retrieved)}`));
  const populationSource = () => sourceRow("Fuente", S.mapSource.service_url, "INEGI, Censo 2020", null, S.mapSource.retrieved_at);
  const ordinal = (n, of) => `${n}.º de ${of}`;
  /** Rank of a state among the 32 by a number, 1 = the highest. */
  const rankOf = (code, valueOf) => {
    const sorted = S.states.map((s) => [s.code, valueOf(s.code)]).filter(([, v]) => v != null).sort((a, b) => b[1] - a[1]);
    const i = sorted.findIndex(([c]) => c === code);
    return i < 0 ? null : ordinal(i + 1, sorted.length);
  };

  /** Rank of a municipality among a set of municipalities by a number, 1 = the highest; "3.º de 98". */
  function muniRank(code, codes, valueOf) {
    const sorted = codes.map((c) => [c, valueOf(c)]).filter(([, v]) => v != null).sort((a, b) => b[1] - a[1]);
    const i = sorted.findIndex(([c]) => c === code);
    return i < 0 ? null : ordinal(i + 1, sorted.length);
  }
  const munisOfState = (stateCode) => S.munis.filter((m) => m.state_code === stateCode).map((m) => m.code);
  const highest = " (1 = la más alta)";

  /** Economy rows: GDP, wages, employment and poverty, each with its rank and source. */
  function economyRows(code) {
    const rows = [];
    if (!S.gdp) rows.push(fact("PIB", "Sin dato: falta el archivo de PIB"));
    else {
      const row = code ? S.gdp.states[code] : S.gdp.national;
      const people = code ? stateOf(code).population : S.mapSource.population;
      const perHead = (c) => (S.gdp.states[c] ? (1e9 * S.gdp.states[c].gdp) / stateOf(c).population : null);
      if (!row) rows.push(fact("PIB", "Sin dato en la fuente"));
      else
        rows.push(
          fact(`PIB ${S.gdp.year}`, `${integer.format(row.gdp)} mil millones de pesos (precios de 2018)`),
          code ? fact("Lugar por PIB", rankOf(code, (c) => (S.gdp.states[c] || {}).gdp)) : null,
          fact("PIB por habitante", `${integer.format(Math.round((1e9 * row.gdp) / people))} pesos (precios de 2018, población de 2020)`),
          code ? fact("Lugar por PIB por habitante", rankOf(code, perHead)) : null,
          code ? fact("Parte del PIB nacional", `${oneDecimal.format(row.share)} %`) : null,
          fact(`Crecimiento ${S.gdp.year}`, `${signed.format(row.growth)} %`),
          code ? fact("Lugar por crecimiento", rankOf(code, (c) => (S.gdp.states[c] || {}).growth)) : null,
          sourceRow("Fuente del PIB", S.gdp.citation.url, `INEGI, PIBE ${S.gdp.year}`, S.gdp.citation.published_at, S.gdp.citation.retrieved_at)
        );
    }
    if (S.economy) {
      const e = S.economy.employment;
      const job = code ? e.states[code] : e.national;
      if (job)
        rows.push(
          fact(`Desocupación, ${e.period}`, `${oneDecimal.format(job.unemployment)} % de la población activa`),
          code ? fact(`Lugar por desocupación${highest}`, ordinal(job.rank_by_unemployment, Object.keys(e.states).length)) : null,
          fact("Informalidad laboral", `${oneDecimal.format(job.informality)} % de las personas ocupadas`),
          code ? fact(`Lugar por informalidad${highest}`, ordinal(job.rank_by_informality, Object.keys(e.states).length)) : null,
          fact("Personas ocupadas", integer.format(job.employed)),
          sourceRow("Fuente del empleo", e.citation.url, "INEGI, ENOE", e.citation.published_at, e.citation.retrieved_at)
        );
      const inc = S.economy.income;
      const bands = code ? inc.states[code] : nationalBands();
      if (bands)
        rows.push(
          fact(`Ocupados con hasta un salario mínimo, ${inc.period}`, `${oneDecimal.format(bands.up_to_1)} %`),
          code ? fact(`Lugar por esa parte${highest}`, ordinal(bands.rank_by_up_to_1, Object.keys(inc.states).length)) : null,
          fact("Ocupados con más de 2 salarios mínimos", `${oneDecimal.format(bands.from_2_to_3 + bands.from_3_to_5 + bands.over_5)} %`),
          fact("Ocupados sin ingresos", `${oneDecimal.format(bands.none)} %`),
          sourceRow("Fuente de ingresos", code ? inc.bulletins[code] : inc.citation.url, "INEGI, ENOE por entidad", inc.citation.published_at, inc.citation.retrieved_at)
        );
      const pv = S.economy.poverty;
      const poor = code ? pv.states[code] : pv.national;
      if (poor)
        rows.push(
          fact(`Pobreza ${pv.year}`, `${oneDecimal.format(poor.poverty_pct)} % de la población (${integer.format(poor.poverty_people)} personas)`),
          code ? fact(`Lugar por pobreza${highest}`, ordinal(poor.rank_by_poverty, Object.keys(pv.states).length)) : null,
          fact(`Pobreza extrema ${pv.year}`, `${oneDecimal.format(poor.extreme_pct)} % (${integer.format(poor.extreme_people)} personas)`),
          sourceRow("Fuente de pobreza", pv.citation.url, "INEGI, Pobreza Multidimensional 2024", pv.citation.published_at, pv.citation.retrieved_at)
        );
      rows.push(...wageRows(code, null));
    }
    return rows;
  }

  /** The income bands for the whole country: each state's shares weighted by its employed people. */
  function nationalBands() {
    if (!S.economy) return null;
    const { income, employment } = S.economy;
    const codes = Object.keys(income.states).filter((c) => employment.states[c]);
    if (!codes.length) return null;
    const total = d3.sum(codes, (c) => employment.states[c].employed);
    const weighted = (key) => d3.sum(codes, (c) => income.states[c][key] * employment.states[c].employed) / total;
    return { up_to_1: weighted("up_to_1"), from_2_to_3: weighted("from_2_to_3"), from_3_to_5: weighted("from_3_to_5"), over_5: weighted("over_5"), none: weighted("none") };
  }

  /** Minimum wage rows: the general wage, and the border wage where it applies. */
  function wageRows(code, muniCode) {
    if (!S.economy) return [];
    const w = S.economy.minimum_wage;
    const border = new Set(w.border_municipalities);
    const inBorder = (c) => border.has(c);
    const rows = [];
    if (muniCode) rows.push(fact(`Salario mínimo ${w.year}`, `${w[inBorder(muniCode) ? "border" : "general"].toFixed(2)} ${w.unit} (${inBorder(muniCode) ? "Zona Libre de la Frontera Norte" : "zona general"})`));
    else {
      const count = code ? munisOfState(code).filter(inBorder).length : border.size;
      rows.push(fact(`Salario mínimo ${w.year}, zona general`, `${w.general.toFixed(2)} ${w.unit}`));
      if (count) rows.push(fact("Salario mínimo, frontera norte", `${w.border.toFixed(2)} ${w.unit} en ${count} municipios`));
    }
    rows.push(sourceRow("Fuente del salario mínimo", w.citation.url, "CONASAMI, tabla 2026", null, w.citation.retrieved_at));
    return rows;
  }

  /** Security rows: homicide victims so far this year, rate and rank, feminicides, last year. */
  function securityRows(code, muniCode) {
    if (!S.crime) return [fact("Homicidios dolosos", "Sin dato: falta el archivo de incidencia delictiva")];
    const c = S.crime;
    const row = muniCode ? c.municipalities[muniCode] : code ? c.states[code] : c.national;
    const abbr = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];
    const period = c.months < 12 ? `${abbr[0]}–${abbr[c.months - 1]} ${c.year}` : String(c.year);
    const source = sourceRow("Fuente", c.citation.url, "SESNSP, víctimas registradas", c.citation.published_at, c.citation.retrieved_at);
    if (!row) return [fact(`Homicidios dolosos, ${period}`, "Sin registros en la fuente"), source];
    const muniCount = (m) => (c.municipalities[m] || {}).homicides;
    const withRecords = Object.keys(c.municipalities);
    return [
      fact(`Homicidios dolosos, ${period}`, integer.format(row.homicides)),
      code && !muniCode ? fact("Lugar por número de homicidios (1 = el más alto)", rankOf(code, (s) => (c.states[s] || {}).homicides)) : null,
      row.homicide_rate != null ? fact("Por cada 100 mil habitantes", oneDecimal.format(row.homicide_rate)) : null,
      row.rank_by_rate ? fact(`Lugar por tasa${highest}`, ordinal(row.rank_by_rate, Object.keys(c.states).length)) : null,
      muniCode ? fact("Lugar en la entidad por homicidios", `${muniRank(muniCode, munisOfState(code).filter((m) => c.municipalities[m]), muniCount)} municipios con registros`) : null,
      muniCode ? fact("Lugar nacional por homicidios", `${muniRank(muniCode, withRecords, muniCount)} municipios con registros`) : null,
      fact(`Feminicidios, ${period}`, integer.format(row.feminicides)),
      row.previous_year_homicides != null ? fact(`Homicidios dolosos, ${c.previous_year}`, integer.format(row.previous_year_homicides)) : null,
      source,
    ];
  }

  /** Fuel rows: average prices and the stations behind them. */
  function fuelRows(code, muniCode) {
    if (!S.fuel) return [fact("Gasolina", "Sin dato: falta el archivo de precios")];
    const f = S.fuel;
    const row = muniCode ? f.municipalities[muniCode] : code ? f.states[code] : f.national;
    const price = (v) => (v == null ? "Sin estaciones con ese combustible" : `${v.toFixed(2)} pesos/litro (promedio)`);
    if (!row) return [fact("Gasolina", "Sin estaciones con precio en la fuente"), sourceRow("Fuente", f.citation.url, "CRE, precios reportados", null, f.citation.retrieved_at)];
    const regularOf = (m) => (f.municipalities[m] || {}).regular;
    return [
      fact("Gasolina regular", price(row.regular)),
      code && !muniCode ? fact("Lugar por precio de la regular (1 = la más cara)", rankOf(code, (s) => (f.states[s] || {}).regular)) : null,
      muniCode ? fact("Lugar en la entidad por precio de la regular", `${muniRank(muniCode, munisOfState(code).filter((m) => f.municipalities[m]), regularOf)} municipios con estaciones`) : null,
      fact("Gasolina premium", price(row.premium)),
      fact("Diésel", price(row.diesel)),
      fact("Estaciones con precio", integer.format(row.stations)),
      sourceRow("Fuente", f.citation.url, "CRE, precios reportados", null, f.citation.retrieved_at),
    ];
  }
  /** The municipalities a district covers, whole or in part, each a way into that municipality. */
  function districtMunicipalities(district) {
    const covered = S.districtIndex ? S.districtIndex.districts[`${district.state_code}-${district.number}`] || [] : null;
    if (!covered) return el("p", { class: "ficha__intro" }, "La correspondencia entre distritos y municipios aún no se ha calculado.");
    const rows = covered.map((m) => {
      const muni = S.munis.find((x) => x.code === m.code) || null;
      const name = muni ? el("button", { type: "button", class: "persona__link", onclick: () => go("municipality", { state: S.state, district, muni }) }, m.name) : m.name;
      return fact(name, m.whole ? "Completo" : `En parte: ${Math.round(m.share * 100)} % de su superficie`);
    });
    return [facts(rows), el("p", { class: "cite" }, S.districtIndex.method)];
  }

  const levelName = () => (S.level === "municipality" ? S.muni.name : S.level === "district" ? `Distrito ${S.district.number}` : S.level === "state" ? stateName(S.state.code) : "México");

  const closeControl = () => {
    const full = () => document.body.classList.contains("sheet-full");
    const grow = el("button", { type: "button", class: "link-button", onclick: () => { document.body.classList.toggle("sheet-full"); grow.textContent = full() ? "Reducir" : "Ampliar"; } }, full() ? "Reducir" : "Ampliar");
    return el("p", { class: "ficha__close" }, grow, el("button", { type: "button", class: "link-button", onclick: () => openSheet(false) }, "Cerrar"));
  };

  function renderFicha() {
    const box = $("#ficha");
    if (S.person) {
      box.replaceChildren(closeControl(), ...personCard(S.person, S.ctx).flat(Infinity), back(`Volver a ${levelName()}`, () => { S.person = null; renderFicha(); }));
      return;
    }
    let content;
    if (S.level === "country") {
      const president = peopleOf("president")[0];
      const cabinet = peopleOf("secretary");
      const justices = peopleOf("justice");
      const electoral = peopleOf("magistrate_tepjf");
      const discipline = peopleOf("magistrate_tdj");
      content = [
        el("h2", { class: "ficha__place" }, "México"),
        el("h3", {}, "Población"),
        facts(fact("Capital", "Ciudad de México"), populationRows(S.mapSource), fact("Entidades", String(S.states.length)), fact("Municipios", integer.format(S.mapSource.municipality_count)), populationSource()),
        el("h3", {}, "Patrimonio"),
        facts(heritageRows(null, null)),
        el("h3", {}, "Economía"),
        facts(economyRows(null)),
        el("h3", {}, "Seguridad"),
        facts(securityRows(null)),
        el("h3", {}, "Combustibles"),
        facts(fuelRows(null)),
        el("h3", {}, "Gobierno y representación"),
        facts(fact("Gubernaturas", partySplit(peopleOf("governor"))), fact("Senado", partySplit(peopleOf("senator"))), fact("Cámara de Diputados", partySplit(peopleOf("deputy")))),
        president ? people(president) : el("p", { class: "ficha__intro" }, "La fuente no indica quién ocupa la Presidencia."),
        cabinet.length ? el("details", { class: "ficha__more" }, el("summary", {}, `Gabinete: ${cabinet.length} titulares`), el("ul", { class: "people" }, cabinet.map((p) => personLine(p, showPerson)))) : null,
        justices.length ? el("details", { class: "ficha__more" }, el("summary", {}, `Suprema Corte: ${justices.length} integrantes`), people(justices)) : null,
        electoral.length ? el("details", { class: "ficha__more" }, el("summary", {}, `Tribunal Electoral: ${electoral.length} magistraturas`), people(electoral)) : null,
        discipline.length ? el("details", { class: "ficha__more" }, el("summary", {}, `Tribunal de Disciplina Judicial: ${discipline.length} magistraturas`), people(discipline)) : null,
        el("p", { class: "ficha__intro" }, "Cada escaño y las mayorías están en ", el("a", { href: "poderes.html" }, "Poderes de la Nación"), "."),
      ];
    } else if (S.level === "state") {
      const governor = governorOf(S.state.code);
      const senators = senatorsOf(S.state.code);
      const districts = S.districts.filter((d) => d.state_code === S.state.code);
      const deputies = districts.map(deputyOf).filter(Boolean);
      const mayors = peopleOf("mayor", (p) => p.state_code === S.state.code);
      content = [
        el("h2", { class: "ficha__place" }, stateName(S.state.code)),
        stateName(S.state.code) !== S.state.name ? facts(fact("Nombre oficial", S.state.name)) : null,
        el("h3", {}, "Población"),
        facts(
          capitalRow(S.state.code),
          populationRows(S.state),
          fact("Lugar por población", rankOf(S.state.code, (c) => stateOf(c).population)),
          fact("Parte de la población nacional", `${oneDecimal.format((100 * S.state.population) / S.mapSource.population)} %`),
          fact("Municipios", integer.format(S.state.municipalities)),
          fact("Distritos federales", String(districts.length)),
          populationSource()
        ),
        el("h3", {}, "Patrimonio"),
        facts(heritageRows(S.state.code, null)),
        el("h3", {}, "Economía"),
        facts(economyRows(S.state.code)),
        el("h3", {}, "Seguridad"),
        facts(securityRows(S.state.code)),
        el("h3", {}, "Combustibles"),
        facts(fuelRows(S.state.code)),
        el("h3", {}, "Gobierno y representación"),
        governor ? people(governor) : el("p", { class: "ficha__intro" }, "La fuente no lista a nadie en el gobierno del estado."),
        senators.length ? people(senators) : el("p", { class: "ficha__intro" }, "La fuente no lista senadurías para esta entidad."),
        facts(
          fact(`Diputaciones de distrito (${districts.length})`, deputies.length ? partySplit(deputies) : "Aún no leídas de la fuente"),
          deputies.length && deputies.length < districts.length ? fact("Diputaciones aún no leídas", String(districts.length - deputies.length)) : null,
          fact(`${S.state.code === "09" ? "Alcaldías" : "Presidencias municipales"} (${integer.format(S.state.municipalities)})`, mayors.length ? partySplit(mayors) : "Sin dato en la fuente"),
          mayors.length < S.state.municipalities ? fact("Municipios sin titular en la fuente", integer.format(S.state.municipalities - mayors.length)) : null
        ),
        cityRows(S.state.code),
        el("p", { class: "ficha__intro" }, "Pulsa un municipio para ver su ayuntamiento y la diputación de su distrito."),
        back("Volver al país", () => go("country", {})),
      ];
    } else if (S.level === "district") {
      const deputy = deputyOf(S.district);
      const seat = deputy && deputy.district.includes("(") ? deputy.district.slice(deputy.district.lastIndexOf("(") + 1, -1) : null;
      content = [
        el("h2", { class: "ficha__place" }, `Distrito ${S.district.number}`),
        facts(fact("Entidad", stateName(S.state.code)), fact("Cabecera", seat), fact("Población, PIB, homicidios y precios", "No se publican por distrito electoral; los municipios de abajo sí los tienen")),
        el("h3", {}, "Cámara de Diputados"),
        deputy ? people(deputy) : el("p", { class: "ficha__intro" }, "La ficha de esta diputación en el SIL aún no se ha leído; aparecerá en una próxima actualización."),
        el("h3", {}, "Municipios que abarca"),
        districtMunicipalities(S.district),
        el("p", { class: "ficha__intro" }, "Pulsa un municipio, aquí o en el mapa, para ver sus datos y quién preside su ayuntamiento."),
        back(`Volver a ${stateName(S.state.code)}`, () => go("state", { state: S.state })),
      ];
    } else {
      const mayor = mayorOf(S.muni.code);
      content = [
        el("h2", { class: "ficha__place" }, S.muni.name),
        el("h3", {}, "Población"),
        facts(
          fact("Entidad", stateName(S.state.code)),
          capitalOf(S.state.code) && capitalOf(S.state.code).municipality_code === S.muni.code ? fact("Capital de la entidad", capitalOf(S.state.code).capital) : null,
          ...citiesOf(S.state.code).filter((c) => c.municipality_code === S.muni.code).map((c) => fact("Ciudad", `${c.name}: ${integer.format(c.population)} habitantes`)),
          fact("Cabecera", S.muni.seat),
          fact("Población (2020)", S.muni.population == null ? "Sin dato: municipio creado después del censo" : integer.format(S.muni.population)),
          fact("Lugar en la entidad por población", `${muniRank(S.muni.code, munisOfState(S.state.code), (m) => (S.munis.find((x) => x.code === m) || {}).population)} municipios con cifra del censo`),
          fact("Clave INEGI", S.muni.code),
          S.district ? fact("Distrito federal", String(S.district.number)) : null,
          populationSource()
        ),
        el("h3", {}, "Patrimonio"),
        facts(heritageRows(S.state.code, S.muni.code)),
        el("h3", {}, "Economía"),
        facts(wageRows(S.state.code, S.muni.code), fact("PIB, empleo y pobreza", "Se publican por entidad, no por municipio")),
        el("h3", {}, "Seguridad"),
        facts(securityRows(S.state.code, S.muni.code)),
        el("h3", {}, "Combustibles"),
        facts(fuelRows(S.state.code, S.muni.code)),
        el("h3", {}, S.state.code === "09" ? "Alcaldía" : "Presidencia municipal"),
        mayor ? people(mayor) : el("p", { class: "ficha__intro" }, "La fuente no da titular para este municipio."),
        S.district ? [el("h3", {}, `Distrito federal ${S.district.number}`), deputyOf(S.district) ? people(deputyOf(S.district)) : el("p", { class: "ficha__intro" }, "La ficha de esta diputación en el SIL aún no se ha leído."), el("p", { class: "ficha__intro" }, "Es el distrito del punto donde pulsaste; un municipio puede repartirse entre varios."), el("p", { class: "ficha__back" }, el("button", { type: "button", class: "link-button", onclick: () => go("district", { state: S.state, district: S.district }) }, `Ver el distrito ${S.district.number} en el mapa`))] : null,
        back(`Volver a ${stateName(S.state.code)}`, () => go("state", { state: S.state })),
      ];
    }
    box.replaceChildren(closeControl(), ...content.flat(Infinity).filter(Boolean));
  }

  /** The sources section: every source with its date, in one place. */

  // ---------- Search: states, municipalities and cities by name ----------

  function buildSearch() {
    const box = $("#search-box");
    const list = $("#search-results");
    if (!box || !list) return;
    const entries = [];
    for (const state of S.states) entries.push({ label: stateName(state.code), detail: "Entidad", key: fold(stateName(state.code)) + " " + fold(state.name), weight: 3, go: () => go("state", { state }) });
    for (const muni of S.munis) entries.push({ label: muni.name, detail: `Municipio · ${stateName(muni.state_code)}`, key: fold(muni.name), weight: muni.population || 0, go: () => go("municipality", { state: stateOf(muni.state_code), district: null, muni }) });
    for (const city of S.cities ? S.cities.cities : []) {
      const muni = city.municipality_code ? S.muniByCode.get(city.municipality_code) : null;
      if (!muni || fold(city.name) === fold(muni.name)) continue; // the municipality entry already covers it
      entries.push({ label: city.name, detail: `Ciudad · ${muni.name}, ${stateName(city.state_code)}`, key: fold(city.name), weight: city.population, go: () => go("municipality", { state: stateOf(city.state_code), district: null, muni }) });
    }
    let shown = [];
    const close = () => {
      list.hidden = true;
      list.replaceChildren();
      box.setAttribute("aria-expanded", "false");
      shown = [];
    };
    const pick = (entry) => {
      box.value = "";
      close();
      entry.go();
    };
    box.addEventListener("input", () => {
      const q = fold(box.value.trim());
      if (q.length < 2) return close();
      const starts = entries.filter((e) => e.key.startsWith(q) || e.key.split(" ").some((w) => w.startsWith(q)));
      const contains = entries.filter((e) => !starts.includes(e) && e.key.includes(q));
      const rank = (a, b) => (b.detail === "Entidad") - (a.detail === "Entidad") || b.weight - a.weight;
      shown = [...starts.sort(rank), ...contains.sort(rank)].slice(0, 8);
      list.replaceChildren(...shown.map((entry) => el("li", { role: "option" }, el("button", { type: "button", onclick: () => pick(entry) }, el("span", { class: "search__label" }, entry.label), el("span", { class: "search__detail" }, entry.detail)))));
      if (!shown.length) list.replaceChildren(el("li", { class: "search__none" }, "Sin coincidencias"));
      list.hidden = false;
      box.setAttribute("aria-expanded", "true");
    });
    box.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && shown.length) {
        event.preventDefault();
        pick(shown[0]);
      } else if (event.key === "Escape") close();
    });
    document.addEventListener("pointerdown", (event) => {
      if (!$("#search").contains(event.target)) close();
    });
  }

  // ---------- Start ----------

  async function start() {
    const getJSON = async (url, optional = false) => {
      const response = await fetch(url);
      if (!response.ok) {
        if (optional) return null;
        throw new Error(`${url}: ${response.status}`);
      }
      return response.json();
    };
    try {
      [S.topo, S.districtTopo, S.mapSource, S.data, S.gdp, S.crime, S.fuel, S.economy, S.capitals, S.cities, S.abroad] = await Promise.all([
        getJSON("data/municipios.topojson"),
        getJSON("data/distritos.topojson"),
        getJSON("data/map_source.json"),
        getJSON("data/politicians.json"),
        getJSON("data/gdp.json", true),
        getJSON("data/crime.json", true),
        getJSON("data/fuel.json", true),
        getJSON("data/economy.json", true),
        getJSON("data/capitals.json", true),
        getJSON("data/cities.json", true),
        getJSON("data/vecinos.topojson", true),
      ]);
    } catch (error) {
      const notice = $("#load-error");
      notice.hidden = false;
      notice.textContent = `No se pudieron cargar los datos (${error.message}). Genera los archivos con «python tools/build_map.py», «python tools/fetch_politicians.py» y «python tools/fetch_gdp.py», y abre la página con «python tools/serve.py».`;
      return;
    }
    tip = MXD.tooltip($("#tooltip"), $(".map-area"));
    buildMap();
    S.districtIndex = await fetch("data/distritos_municipios.json").then((response) => (response.ok ? response.json() : null)).catch(() => null);
    S.heritage = await fetch("data/patrimonio.json").then((response) => (response.ok ? response.json() : null)).catch(() => null);
    buildHeritage();
    S.ctx = { stateName, legislature: S.data.legislature || null, ...regions(S.data, stateName) };
    $("#data-date").textContent = `Cargos consultados el ${moment.format(new Date(S.data.generated_at))}.`;
    $("#map-credit").replaceChildren(`${S.mapSource.attribution} (${day(S.mapSource.retrieved_at)}); distritos: INE (${day(S.mapSource.districts.retrieved_at)}).`);
    buildSearch();
    // Deep links: #entidad=14, #entidad=14&distrito=5, #entidad=14&municipio=14039
    const wanted = new URLSearchParams(location.hash.slice(1));
    const state = S.states.find((s) => s.code === wanted.get("entidad"));
    const district = state && S.districts.find((d) => d.state_code === state.code && d.number === Number(wanted.get("distrito")));
    const muni = state && S.munis.find((m) => m.code === wanted.get("municipio"));
    if (muni) go("municipality", { state, district: district || null, muni });
    else if (district) go("district", { state, district });
    else if (state) go("state", { state });
    else go("country", {});
  }

  start();
})();
