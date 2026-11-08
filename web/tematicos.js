/* México en datos, Mapas económicos and Mapas de seguridad: one map per figure, coloured by
   value, by state or by municipality as the source allows, with every state ranked. The page's
   theme comes from <body data-tema="economia|seguridad">. */
(() => {
  "use strict";

  const { el, link, integer, oneDecimal, signed, moment, day, motionOK, fact, facts, tooltip, EVERYDAY_NAME } = MXD;
  const $ = (selector) => document.querySelector(selector);
  const THEME = document.body.dataset.tema;
  const S = { topo: null, mapSource: null, gdp: null, crime: null, fuel: null, economy: null, states: [], munis: [], indicator: null, selected: null };
  const stateName = (code) => EVERYDAY_NAME[code] || (S.states.find((s) => s.code === code) || {}).name || code;
  const stateOf = (code) => S.states.find((s) => s.code === code);
  const ordinal = (n, of) => `${n}.º de ${of}`;

  // Five steps of one hue, light to dark, for each theme; a brown-to-teal pair for growth, which can be negative.
  const RAMP = {
    economia: ["#e4f1f3", "#b9dde2", "#82bfc9", "#4293a3", "#155f6e"],
    seguridad: ["#f4e5ef", "#e3bdd7", "#ca8bb9", "#a4578f", "#6e2a5f"],
  };
  const DIVERGING = { negative: ["#8a4a1f", "#c48a5a", "#e8c9ad"], positive: ["#b9dde2", "#6fb1bd", "#155f6e"] };
  const NO_DATA = "#e9e9e6";

  const pct = (v) => `${oneDecimal.format(v)} %`;
  const money = (v) => `${v.toFixed(2)} pesos/litro`;
  const count = (v) => integer.format(v);
  const per100k = (v) => oneDecimal.format(v);

  /** What each page can show. `level` says what gets coloured; `value(code)` reads the figure for a place. */
  const INDICATORS = {
    economia: [
      { key: "pib", label: "PIB 2024", unit: "mil millones de pesos de 2018", level: "state", value: (c) => (S.gdp && S.gdp.states[c] ? S.gdp.states[c].gdp : null), format: count, source: () => S.gdp && S.gdp.citation },
      { key: "pib-habitante", label: "PIB por habitante", unit: "pesos de 2018 por persona (población de 2020)", level: "state", value: (c) => (S.gdp && S.gdp.states[c] ? Math.round((1e9 * S.gdp.states[c].gdp) / stateOf(c).population) : null), format: count, source: () => S.gdp && S.gdp.citation },
      { key: "crecimiento", label: "Crecimiento 2024", unit: "cambio anual del PIB", level: "state", diverging: true, value: (c) => (S.gdp && S.gdp.states[c] ? S.gdp.states[c].growth : null), format: (v) => `${signed.format(v)} %`, source: () => S.gdp && S.gdp.citation },
      { key: "desocupacion", label: "Desocupación", unit: "porcentaje de la población activa, segundo trimestre de 2026", level: "state", value: (c) => (S.economy && S.economy.employment.states[c] ? S.economy.employment.states[c].unemployment : null), format: pct, source: () => S.economy && S.economy.employment.citation },
      { key: "informalidad", label: "Informalidad", unit: "porcentaje de las personas ocupadas, segundo trimestre de 2026", level: "state", value: (c) => (S.economy && S.economy.employment.states[c] ? S.economy.employment.states[c].informality : null), format: pct, source: () => S.economy && S.economy.employment.citation },
      { key: "hasta-un-salario", label: "Hasta un salario mínimo", unit: "porcentaje de las personas ocupadas que ganan hasta un salario mínimo, segundo trimestre de 2026", level: "state", value: (c) => (S.economy && S.economy.income.states[c] ? S.economy.income.states[c].up_to_1 : null), format: pct, source: () => S.economy && S.economy.income.citation },
      { key: "mas-de-dos-salarios", label: "Más de 2 salarios mínimos", unit: "porcentaje de las personas ocupadas que ganan más de dos salarios mínimos, segundo trimestre de 2026", level: "state", value: (c) => { const b = S.economy && S.economy.income.states[c]; return b ? Math.round(10 * (b.from_2_to_3 + b.from_3_to_5 + b.over_5)) / 10 : null; }, format: pct, source: () => S.economy && S.economy.income.citation },
      { key: "pobreza", label: "Pobreza 2024", unit: "porcentaje de la población", level: "state", value: (c) => (S.economy && S.economy.poverty.states[c] ? S.economy.poverty.states[c].poverty_pct : null), format: pct, source: () => S.economy && S.economy.poverty.citation },
      { key: "pobreza-extrema", label: "Pobreza extrema 2024", unit: "porcentaje de la población", level: "state", value: (c) => (S.economy && S.economy.poverty.states[c] ? S.economy.poverty.states[c].extreme_pct : null), format: pct, source: () => S.economy && S.economy.poverty.citation },
      { key: "gasolina", label: "Gasolina regular", unit: "precio promedio por litro en las estaciones del municipio, hoy", level: "municipality", value: (c) => (S.fuel && S.fuel.municipalities[c] ? S.fuel.municipalities[c].regular : null), stateValue: (c) => (S.fuel && S.fuel.states[c] ? S.fuel.states[c].regular : null), format: money, source: () => S.fuel && S.fuel.citation },
      { key: "salario", label: "Salario mínimo 2026", unit: "pesos diarios; la zona fronteriza tiene su propio monto", level: "municipality", classes: true, value: (c) => (S.economy ? (S.economy.minimum_wage.border_municipalities.includes(c) ? S.economy.minimum_wage.border : S.economy.minimum_wage.general) : null), stateValue: () => null, format: (v) => `${v.toFixed(2)} pesos diarios`, source: () => S.economy && S.economy.minimum_wage.citation },
    ],
    seguridad: [
      { key: "homicidios-tasa", label: "Homicidios por 100 mil", unit: "víctimas de homicidio doloso por cada 100 mil habitantes, enero a septiembre de 2026", level: "state", value: (c) => (S.crime && S.crime.states[c] ? S.crime.states[c].homicide_rate : null), format: per100k, source: () => S.crime && S.crime.citation },
      { key: "homicidios", label: "Homicidios dolosos", unit: "víctimas, enero a septiembre de 2026", level: "state", value: (c) => (S.crime && S.crime.states[c] ? S.crime.states[c].homicides : null), format: count, source: () => S.crime && S.crime.citation },
      { key: "homicidios-municipio", label: "Homicidios por municipio", unit: "víctimas de homicidio doloso, enero a septiembre de 2026; sin color, los municipios sin registros", level: "municipality", value: (c) => (S.crime && S.crime.municipalities[c] ? S.crime.municipalities[c].homicides : null), stateValue: (c) => (S.crime && S.crime.states[c] ? S.crime.states[c].homicides : null), format: count, source: () => S.crime && S.crime.citation },
      { key: "homicidios-municipio-tasa", label: "Por 100 mil, municipio", unit: "víctimas por cada 100 mil habitantes del municipio (población de 2020), enero a septiembre de 2026", level: "municipality", value: (c) => { const m = S.crime && S.crime.municipalities[c]; const muni = S.muniByCode.get(c); return m && muni && muni.population ? Math.round((1e6 * m.homicides) / muni.population) / 10 : null; }, stateValue: (c) => (S.crime && S.crime.states[c] ? S.crime.states[c].homicide_rate : null), format: per100k, source: () => S.crime && S.crime.citation },
      { key: "feminicidios", label: "Feminicidios", unit: "víctimas, enero a septiembre de 2026", level: "state", value: (c) => (S.crime && S.crime.states[c] ? S.crime.states[c].feminicides : null), format: count, source: () => S.crime && S.crime.citation },
      { key: "homicidios-2025", label: "Homicidios 2025", unit: "víctimas de homicidio doloso en todo 2025", level: "state", value: (c) => (S.crime && S.crime.states[c] ? S.crime.states[c].previous_year_homicides : null), format: count, source: () => S.crime && S.crime.citation },
    ],
  }[THEME];

  // ---------- Map ----------

  const W = 960;
  const H = 640;
  const svg = d3.select("#map svg").attr("viewBox", `0 0 ${W} ${H}`).attr("preserveAspectRatio", "xMidYMid meet");
  const projection = d3.geoConicConformal().parallels([17.5, 29.5]).rotate([102, 0]);
  const path = d3.geoPath(projection);
  const underlay = $("#map canvas");
  const pen = underlay.getContext("2d");
  let zoomLayer, hoverShape, chosenOutline, zoom, graticule, stateLines, muniLines, tip;
  let transform = d3.zoomIdentity;
  let scale = null; // value -> colour for the current indicator

  function buildMap() {
    const layer = S.topo.objects.municipios;
    const factsByState = new Map(S.mapSource.states.map((s) => [s.cve_ent, s]));
    S.states = Array.from(d3.group(layer.geometries, (g) => g.properties.cve_ent), ([code, geometries]) => ({
      code,
      ...(factsByState.get(code) || { name: code }),
      feature: { type: "Feature", geometry: topojson.merge(S.topo, geometries) },
    })).sort((a, b) => a.code.localeCompare(b.code));
    projection.fitExtent([[24, 24], [W - 24, H - 24]], { type: "Feature", geometry: topojson.merge(S.topo, layer.geometries) });
    for (const state of S.states) {
      state.outline = path(state.feature);
      state.shape = new Path2D(state.outline);
      state.box = path.bounds(state.feature);
    }
    S.munis = topojson.feature(S.topo, layer).features.map((feature) => ({
      code: feature.properties.cvegeo,
      name: feature.properties.nomgeo,
      state_code: feature.properties.cve_ent,
      population: feature.properties.pob,
      outline: path(feature),
      shape: new Path2D(path(feature)),
    }));
    S.muniByCode = new Map(S.munis.map((m) => [m.code, m]));
    const sameState = (a, b) => a.properties.cve_ent === b.properties.cve_ent;
    graticule = new Path2D(path(d3.geoGraticule().extent([[-150, 0], [-55, 45]]).step([5, 5])()));
    stateLines = new Path2D(path(topojson.mesh(S.topo, layer, (a, b) => a !== b && !sameState(a, b))));
    muniLines = new Path2D(path(topojson.mesh(S.topo, layer, (a, b) => a !== b && sameState(a, b))));

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
          tip.show(event, kind + d.code, () => tipFor(d));
        })
        .on("click", (event, d) => onPick(d));
    hits(S.munis, "muni", muniTip, (muni) => select(muni.state_code));
    hits(S.states, "state", stateTip, (state) => select(state.code));

    zoom = d3
      .zoom()
      .scaleExtent([1, 40])
      .translateExtent([[-120, -60], [W + 120, H + 60]])
      .filter((event) => {
        if (event.type === "wheel") return event.ctrlKey || event.metaKey;
        if (event.type.startsWith("touch")) return event.touches.length > 1;
        return !event.button;
      })
      .on("zoom", (event) => {
        transform = event.transform;
        zoomLayer.attr("transform", transform).style("--k", transform.k);
        draw();
      });
    svg.call(zoom).on("dblclick.zoom", null);
    $("#zoom-in").addEventListener("click", () => svg.transition().duration(motionOK ? 250 : 0).call(zoom.scaleBy, 1.8));
    $("#zoom-out").addEventListener("click", () => svg.transition().duration(motionOK ? 250 : 0).call(zoom.scaleBy, 1 / 1.8));
    $("#zoom-reset").addEventListener("click", () => select(null));
    new ResizeObserver(draw).observe(underlay);
  }

  function zoomTo(state) {
    let target = d3.zoomIdentity;
    if (state) {
      const [[x0, y0], [x1, y1]] = state.box;
      const k = Math.max(1, Math.min(40, 0.7 / Math.max((x1 - x0) / W, (y1 - y0) / H)));
      target = d3.zoomIdentity.translate(W / 2, H / 2).scale(k).translate(-(x0 + x1) / 2, -(y0 + y1) / 2);
    }
    svg.transition().duration(motionOK ? 700 : 0).call(zoom.transform, target);
  }

  function draw() {
    if (!graticule || !scale) return;
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
    const k = density * fit * transform.k;
    const px = (n) => (n * density) / k;
    pen.setTransform(1, 0, 0, 1, 0, 0);
    pen.clearRect(0, 0, width, height);
    pen.setTransform(new DOMMatrix([k, 0, 0, k, density * (left + fit * transform.x), density * (top + fit * transform.y)]));
    pen.strokeStyle = "#c3d0d9";
    pen.lineWidth = px(0.6);
    pen.stroke(graticule);
    const ind = S.indicator;
    if (ind.level === "state") {
      for (const state of S.states) {
        const v = ind.value(state.code);
        pen.fillStyle = v == null ? NO_DATA : scale(v);
        pen.fill(state.shape);
      }
    } else {
      pen.fillStyle = NO_DATA;
      for (const state of S.states) pen.fill(state.shape);
      for (const muni of S.munis) {
        const v = ind.value(muni.code);
        if (v == null) continue;
        pen.fillStyle = scale(v);
        pen.fill(muni.shape);
      }
      pen.strokeStyle = "rgba(255,255,255,0.5)";
      pen.lineWidth = px(0.4);
      pen.stroke(muniLines);
    }
    pen.strokeStyle = "#ffffff";
    pen.lineWidth = px(1.4);
    pen.stroke(stateLines);
  }

  // ---------- Scale and legend ----------

  function makeScale(ind) {
    const places = ind.level === "state" ? S.states.map((s) => s.code) : S.munis.map((m) => m.code);
    const values = places.map(ind.value).filter((v) => v != null);
    if (ind.classes) {
      const distinct = [...new Set(values)].sort((a, b) => a - b);
      const colours = d3.quantize(d3.interpolateRgb(RAMP[THEME][0], RAMP[THEME][4]), Math.max(2, distinct.length));
      const fn = (v) => colours[distinct.indexOf(v)];
      fn.legend = distinct.map((v, i) => ({ colour: colours[i], label: ind.format(v) }));
      return fn;
    }
    if (ind.diverging) {
      const limit = Math.max(1, d3.max(values, (v) => Math.abs(v)));
      const steps = [-limit, (-2 * limit) / 3, -limit / 3, 0, limit / 3, (2 * limit) / 3, limit];
      const colours = [...DIVERGING.negative, ...DIVERGING.positive];
      const fn = (v) => colours[Math.min(5, Math.max(0, d3.bisect(steps.slice(1, -1), v)))];
      fn.legend = colours.map((colour, i) => ({ colour, label: `${ind.format(steps[i])} a ${ind.format(steps[i + 1])}` }));
      return fn;
    }
    const quantile = d3.scaleQuantile().domain(values).range(RAMP[THEME]);
    const fn = (v) => quantile(v);
    const edges = [d3.min(values), ...quantile.quantiles(), d3.max(values)];
    fn.legend = RAMP[THEME].map((colour, i) => ({ colour, label: `${ind.format(edges[i])} a ${ind.format(edges[i + 1])}` }));
    return fn;
  }

  function renderLegend() {
    const ind = S.indicator;
    const source = ind.source();
    $("#legend").replaceChildren(
      el("figcaption", {}, ind.label),
      el("p", { class: "inset__note" }, ind.unit),
      el("ul", { class: "scale" }, scale.legend.map((step) => el("li", {}, el("span", { class: "scale__swatch", style: `background:${step.colour}` }), step.label)), el("li", {}, el("span", { class: "scale__swatch", style: `background:${NO_DATA}` }), "Sin dato")),
      source ? el("p", { class: "inset__key" }, "Fuente: ", link(source.url, source.source_name), source.published_at ? `, del ${day(source.published_at)}` : "", `; leída el ${day(source.retrieved_at)}.`) : null,
      el("p", { class: "inset__key" }, ind.level === "state" ? "Cada entidad lleva el color de su valor. Pulsa una para ver sus cifras." : "Cada municipio lleva el color de su valor. Pulsa uno para ver las cifras de su entidad.")
    );
  }

  // ---------- Hover boxes, ranking and the panel ----------

  const rankAmongStates = (code, valueOf) => {
    const sorted = S.states.map((s) => [s.code, valueOf(s.code)]).filter(([, v]) => v != null).sort((a, b) => b[1] - a[1]);
    const i = sorted.findIndex(([c]) => c === code);
    return i < 0 ? null : ordinal(i + 1, sorted.length);
  };

  function stateTip(state) {
    const ind = S.indicator;
    const v = ind.level === "state" ? ind.value(state.code) : ind.stateValue(state.code);
    return [el("p", { class: "tooltip__place" }, stateName(state.code)), el("p", {}, `${ind.label}: ${v == null ? "sin dato" : ind.format(v)}`), v != null && ind.level === "state" ? el("p", { class: "tooltip__sub" }, `Lugar ${rankAmongStates(state.code, ind.value)}`) : null, el("p", { class: "tooltip__sub" }, "Pulsa para ver sus cifras")];
  }

  function muniTip(muni) {
    const ind = S.indicator;
    const v = ind.value(muni.code);
    return [el("p", {}, muni.name), el("p", { class: "tooltip__place" }, stateName(muni.state_code)), el("p", {}, `${ind.label}: ${v == null ? "sin dato" : ind.format(v)}`), el("p", { class: "tooltip__sub" }, "Pulsa para ver las cifras de la entidad")];
  }

  function select(code) {
    S.selected = code;
    const state = code ? stateOf(code) : null;
    chosenOutline.attr("d", state ? state.outline : null);
    zoomTo(state);
    renderPanel();
  }

  /** Every indicator of the theme for one state, each with its place. */
  function stateRows(code) {
    return INDICATORS.filter((ind) => ind.level === "state").map((ind) => {
      const v = ind.value(code);
      return [fact(ind.label, v == null ? "Sin dato" : ind.format(v)), v == null ? null : fact(`Lugar, ${ind.label.toLowerCase()}`, rankAmongStates(code, ind.value))];
    });
  }

  function renderPanel() {
    const box = $("#ficha");
    const ind = S.indicator;
    if (S.selected) {
      const munis = S.munis.filter((m) => m.state_code === S.selected && ind.value(m.code) != null).sort((a, b) => ind.value(b.code) - ind.value(a.code));
      box.replaceChildren(
        ...[
          el("h2", { class: "ficha__place" }, stateName(S.selected)),
          facts(stateRows(S.selected)),
          ind.level === "municipality" && munis.length
            ? [el("h3", {}, `${ind.label}, por municipio (${munis.length} con dato)`), el("ol", { class: "ranking" }, munis.slice(0, 40).map((m) => el("li", {}, el("span", {}, m.name), el("span", { class: "ranking__value" }, ind.format(ind.value(m.code)))))), munis.length > 40 ? el("p", { class: "ficha__intro" }, `Se muestran los 40 primeros de ${munis.length}.`) : null]
            : null,
          el("p", { class: "ficha__back" }, el("button", { type: "button", class: "link-button", onclick: () => select(null) }, "Ver todo el país")),
        ].flat().filter(Boolean)
      );
      return;
    }
    const ranked = S.states.map((s) => [s, ind.level === "state" ? ind.value(s.code) : ind.stateValue(s.code)]).filter(([, v]) => v != null).sort((a, b) => b[1] - a[1]);
    const national = ind.level === "state" ? null : ind.key === "gasolina" && S.fuel ? S.fuel.national.regular : ind.key.startsWith("homicidios") && S.crime ? S.crime.national.homicides : null;
    box.replaceChildren(
      ...[
        el("h2", { class: "ficha__place" }, ind.label),
        el("p", { class: "ficha__sub" }, ind.unit),
        national != null ? facts(fact("Nacional", ind.format(national))) : null,
        el("h3", {}, ind.level === "state" ? "Las 32 entidades, de mayor a menor" : "Promedio o total por entidad, de mayor a menor"),
        ranked.length
          ? el("ol", { class: "ranking" }, ranked.map(([s, v]) => el("li", {}, el("button", { type: "button", class: "persona__link", onclick: () => select(s.code) }, stateName(s.code)), el("span", { class: "ranking__value" }, ind.format(v)))))
          : el("p", { class: "ficha__intro" }, "Sin datos por entidad para esta cifra."),
      ].filter(Boolean)
    );
  }

  function setIndicator(key) {
    S.indicator = INDICATORS.find((i) => i.key === key) || INDICATORS[0];
    for (const button of document.querySelectorAll(".views button")) button.setAttribute("aria-pressed", String(button.dataset.view === S.indicator.key));
    $("#map").classList.toggle("level-municipality", S.indicator.level === "municipality");
    scale = makeScale(S.indicator);
    tip.hide();
    tip.reset();
    draw();
    renderLegend();
    renderPanel();
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
      [S.topo, S.mapSource, S.gdp, S.crime, S.fuel, S.economy] = await Promise.all([
        getJSON("data/municipios.topojson"),
        getJSON("data/map_source.json"),
        getJSON("data/gdp.json", true),
        getJSON("data/crime.json", true),
        getJSON("data/fuel.json", true),
        getJSON("data/economy.json", true),
      ]);
    } catch (error) {
      const notice = $("#load-error");
      notice.hidden = false;
      notice.textContent = `No se pudieron cargar los datos (${error.message}). Genera los archivos con las herramientas de tools/ y abre la página con «python tools/serve.py».`;
      return;
    }
    tip = tooltip($("#tooltip"), $(".map-area"));
    buildMap();
    $(".views").replaceChildren(...INDICATORS.map((ind) => el("button", { type: "button", "data-view": ind.key, "aria-pressed": "false", onclick: () => setIndicator(ind.key) }, ind.label)));
    const dates = [S.gdp, S.crime, S.fuel].filter(Boolean).map((d) => d.citation.retrieved_at).concat(S.economy ? [S.economy.employment.citation.retrieved_at] : []);
    $("#data-date").textContent = dates.length ? `Cifras leídas el ${moment.format(new Date(dates.sort().at(-1)))}.` : "";
    $("#map-credit").replaceChildren(`${S.mapSource.attribution}, consultado el ${day(S.mapSource.retrieved_at)}.`);
    const wanted = new URLSearchParams(location.hash.slice(1));
    setIndicator(wanted.get("indicador"));
    if (wanted.get("entidad") && stateOf(wanted.get("entidad"))) select(wanted.get("entidad"));
  }

  start();
})();
