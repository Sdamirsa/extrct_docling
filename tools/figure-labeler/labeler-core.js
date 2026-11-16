/* Figure labeler core: constants, calibration maths, parsing, CSV and the schema check.
 * No DOM; loaded before labeler.js in the page (window.LabelerCore) and by Node tests (require). */
(function (root) {
  "use strict";

  // ---------------------------------------------------------------- constants
  const SCHEMA = "extrct.figure-data/1";
  const KINDS = ["bar", "stacked_bar", "grouped_bar", "line", "scatter", "box", "forest", "kaplan_meier", "pie", "heatmap", "other"];
  const SOURCES = ["human", "printed", "agent", "vector", "raster", "vlm"];
  const SOURCE_KINDS = ["unknown", "vector", "raster", "mixed"];
  const SCALES = ["linear", "log", "categorical"];
  const COLS = ["category", "x", "series", "value", "err_lo", "err_hi", "label_printed", "source", "confidence"];
  const NUM_COLS = ["value", "err_lo", "err_hi", "confidence"];
  const ALIASES = { y: "value", lo: "err_lo", hi: "err_hi", lower: "err_lo", upper: "err_hi", label: "label_printed", printed: "label_printed", conf: "confidence" };
  const COL_HELP = {
    category: "Category label (bar group, study name, heatmap row)", x: "Numeric x (line, scatter, KM time) or heatmap column",
    series: "Legend entry", value: "Plotted quantity in axis units; empty = null (unknown)", err_lo: "Absolute lower end (not a delta)",
    err_hi: "Absolute upper end (not a delta)", label_printed: "Number printed on the figure, verbatim", source: "How the value was obtained",
    confidence: "How sure you are, 0..1 (1 when printed)",
  };
  const TYPE_KIND = { bar_chart: "bar", line_chart: "line", scatter_plot: "scatter", box_plot: "box", forest_plot: "forest", kaplan_meier: "kaplan_meier", roc_curve: "line", heatmap: "heatmap", pie_chart: "pie" };
  const BARLIKE = ["bar", "stacked_bar", "grouped_bar", "box", "forest"];
  const NUM = "[-+]?\\d+(?:\\.\\d+)?";

  // ------------------------------------------------------------ pure helpers
  function parseNum(s) {
    if (s === null || s === undefined) return null;
    if (typeof s === "number") return Number.isFinite(s) ? s : null;
    let t = String(s).trim().replace(/[−–]/g, "-").replace(/\s*%$/, "");
    t = t.replace(/(\d),(\d{3})(?!\d)/g, "$1$2");
    return /^[-+]?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?$/.test(t) ? Number(t) : null;
  }

  /** Value (and CI) from a printed label: "1.23 (0.98-1.55)", "22/138 (15.9%)", "42%". */
  function parsePrinted(s) {
    const t = String(s || "").replace(/−/g, "-");
    const ci = t.match(new RegExp(`^\\s*(${NUM})\\s*[(\\[]\\s*(${NUM})\\s*(?:to|[-–—,;])\\s*(${NUM})\\s*[)\\]]`));
    if (ci) return { value: Number(ci[1]), err_lo: Number(ci[2]), err_hi: Number(ci[3]) };
    const pct = t.match(new RegExp(`(${NUM})\\s*%`));
    if (pct) return { value: Number(pct[1]) };
    const any = t.match(new RegExp(NUM));
    return any ? { value: Number(any[0]) } : null;
  }

  /** Round to the precision one pixel can carry (step = axis units per pixel). */
  function roundStep(v, step) {
    if (!Number.isFinite(v)) return null;
    if (!step) return Number(v.toPrecision(3));
    return Number(v.toFixed(Math.max(0, Math.min(10, Math.ceil(-Math.log10(step))))));
  }

  /** Pixel <-> axis map from two reference ticks c = [{px, val}, {px, val}]. */
  function axisMap(A, c) {
    if (!A || !c || !c[0] || !c[1] || c[0].px == null || c[1].px == null || c[0].px === c[1].px) return null;
    const p1 = c[0].px, p2 = c[1].px;
    if (A.scale === "categorical") {
      const ticks = (A.ticks || []).map(String);
      const i1 = ticks.indexOf(String(c[0].val).trim()), i2 = ticks.indexOf(String(c[1].val).trim());
      if (i1 < 0 || i2 < 0 || i1 === i2) return null;
      const per = (p2 - p1) / (i2 - i1);
      return {
        cat: true, step: 1,
        toVal: (p) => ticks[Math.max(0, Math.min(ticks.length - 1, Math.round(i1 + (p - p1) / per)))],
        toPx: (v) => { const k = ticks.indexOf(String(v)); return k < 0 ? null : p1 + (k - i1) * per; },
      };
    }
    const v1 = parseNum(c[0].val), v2 = parseNum(c[1].val);
    if (v1 === null || v2 === null || v1 === v2) return null;
    if (A.scale === "log") {
      if (v1 <= 0 || v2 <= 0) return null;
      const l1 = Math.log10(v1), k = (Math.log10(v2) - l1) / (p2 - p1);
      return { cat: false, step: null, toVal: (p) => 10 ** (l1 + (p - p1) * k), toPx: (v) => (v > 0 ? p1 + (Math.log10(v) - l1) / k : null) };
    }
    const k = (v2 - v1) / (p2 - p1);
    return { cat: false, step: Math.abs(k), toVal: (p) => v1 + (p - p1) * k, toPx: (v) => p1 + (v - v1) / k };
  }

  function parseTicks(text, scale) {
    const items = String(text || "").split(/[,;\n\t]/).map((t) => t.trim()).filter(Boolean);
    if (!items.length) return null;
    const nums = items.map(parseNum);
    return scale !== "categorical" && nums.every((n) => n !== null) ? nums : items;
  }

  function parseCSV(text) {
    const first = text.split(/\r?\n/, 1)[0];
    const delim = first.includes("\t") ? "\t" : first.includes(";") && !first.includes(",") ? ";" : ",";
    const rows = [];
    let row = [], field = "", quoted = false;
    for (let i = 0; i < text.length; i++) {
      const ch = text[i];
      if (quoted) {
        if (ch !== '"') field += ch;
        else if (text[i + 1] === '"') { field += '"'; i++; } else quoted = false;
      } else if (ch === '"' && field === "") quoted = true;
      else if (ch === delim) { row.push(field); field = ""; }
      else if (ch === "\n" || ch === "\r") {
        if (ch === "\r" && text[i + 1] === "\n") i++;
        row.push(field); rows.push(row); row = []; field = "";
      } else field += ch;
    }
    if (field !== "" || row.length) { row.push(field); rows.push(row); }
    return rows;
  }

  function blankRow(d) {
    return { category: null, x: null, series: d.series ?? null, value: null, err_lo: null, err_hi: null, label_printed: null, source: "human", confidence: d.confidence ?? 0.8 };
  }

  /** Parse one typed cell into the row; returns false when the text is not acceptable. */
  function setField(row, col, text, defaultConf) {
    const t = String(text ?? "").trim();
    if (NUM_COLS.includes(col)) {
      const v = t === "" ? null : parseNum(t);
      row[col] = col === "confidence" && v === null && t === "" && defaultConf !== undefined ? defaultConf : v;
      return (t === "" || v !== null) && !(col === "confidence" && v !== null && (v < 0 || v > 1));
    }
    if (col === "x") row.x = t === "" ? null : parseNum(t) ?? t;
    else if (col === "source") row.source = SOURCES.includes(t) ? t : "human";
    else row[col] = t === "" ? null : t;
    return true;
  }

  /** CSV with a header row: long (columns named after the grid) or wide (category + one column per series). */
  function csvRows(text, conf) {
    const table = parseCSV(text).filter((r) => r.some((c) => c.trim() !== ""));
    if (table.length < 2) return { error: "Need a header row and at least one data row." };
    const head = table[0].map((c) => c.trim());
    const keys = head.map((c) => { const k = c.toLowerCase().replace(/\s+/g, "_"); return COLS.includes(k) ? k : ALIASES[k] || null; });
    const rows = [], series = [];
    if (keys.slice(1).some(Boolean) || head.length === 1) {
      for (const line of table.slice(1)) {
        const row = blankRow({ confidence: conf });
        keys.forEach((k, j) => { if (k && j < line.length) setField(row, k, line[j], conf); });
        if (row.label_printed && row.value === null) Object.assign(row, parsePrinted(row.label_printed) || {}, { confidence: 1 });
        rows.push(row);
        if (row.series && !series.includes(row.series)) series.push(row.series);
      }
    } else {
      const names = head.slice(1);
      names.forEach((n) => n && series.push(n));
      const firstCol = head[0].toLowerCase() === "x" ? "x" : "category";
      for (const line of table.slice(1)) {
        names.forEach((n, j) => {
          const row = blankRow({ series: n || null, confidence: conf });
          setField(row, firstCol, line[0]);
          setField(row, "value", line[j + 1] ?? "");
          rows.push(row);
        });
      }
    }
    return { rows, series };
  }

  function blankDoc(fig, name, today) {
    return {
      schema: SCHEMA,
      figure: { bundle: fig.bundle, self_ref: fig.self_ref, image_path: fig.image_path ?? null, page: fig.page ?? null, bbox: fig.bbox ?? null },
      source_kind: "unknown", panels: [],
      labeler: { kind: "human", name: name || null, date: today, time_minutes: null },
      uncertain: [],
    };
  }

  function fileName(d) { return `${d.figure.bundle}__pictures${String(d.figure.self_ref).split("/").pop()}.json`; }

  /** Hand-written check of the schema contract (mirrors validate.py); returns error strings. */
  function validateDoc(d) {
    const E = [];
    const isNum = (v) => typeof v === "number" && Number.isFinite(v);
    const isObj = (v) => v !== null && typeof v === "object" && !Array.isArray(v);
    const keys = (o, req, opt, w) => {
      if (!isObj(o)) { E.push(`${w}: object expected`); return false; }
      req.forEach((k) => { if (!(k in o)) E.push(`${w}.${k}: required (use null when unknown)`); });
      Object.keys(o).forEach((k) => { if (!req.includes(k) && !opt.includes(k)) E.push(`${w}.${k}: unknown field`); });
      return true;
    };
    const strOrNull = (v, w) => { if (v !== null && v !== undefined && typeof v !== "string") E.push(`${w}: text or null`); };
    const numOrNull = (v, w) => { if (v !== null && v !== undefined && !isNum(v)) E.push(`${w}: number or null`); };
    const oneOf = (v, list, w, nullable) => { if (!(nullable && v == null) && !list.includes(v)) E.push(`${w}: one of ${list.join(" | ")}${nullable ? " | null" : ""}`); };
    if (!keys(d, ["schema", "figure", "source_kind", "panels", "labeler"], ["uncertain"], "doc")) return E;
    if (d.schema !== SCHEMA) E.push(`schema: must be "${SCHEMA}"`);
    const f = d.figure;
    if (keys(f, ["bundle", "self_ref", "image_path", "page", "bbox"], [], "figure")) {
      if (!f.bundle || typeof f.bundle !== "string") E.push("figure.bundle: required text");
      if (!/^#\/pictures\/\d+$/.test(f.self_ref || "")) E.push("figure.self_ref: #/pictures/N");
      if (f.bbox != null && !(Array.isArray(f.bbox) && f.bbox.length === 4 && f.bbox.every(isNum))) E.push("figure.bbox: four numbers or null");
    }
    oneOf(d.source_kind, SOURCE_KINDS, "source_kind");
    if (!Array.isArray(d.panels)) E.push("panels: list expected");
    const ids = new Set();
    (Array.isArray(d.panels) ? d.panels : []).forEach((p, i) => {
      const w = `panel ${p && p.id ? p.id : i + 1}`;
      if (!keys(p, ["id", "bbox_px", "title", "kind", "orientation", "axes", "series", "data"], ["notes"], w)) return;
      if (!p.id || typeof p.id !== "string") E.push(`${w}: id required`);
      else if (ids.has(p.id)) E.push(`${w}: duplicate id`);
      ids.add(p.id);
      oneOf(p.kind, KINDS, `${w} kind`);
      oneOf(p.orientation, ["vertical", "horizontal"], `${w} orientation`, true);
      strOrNull(p.title, `${w} title`);
      const b = p.bbox_px;
      if (!(Array.isArray(b) && b.length === 4 && b.every(isNum) && b[0] < b[2] && b[1] < b[3])) E.push(`${w} bbox_px: [x0, y0, x1, y1] with x0 < x1, y0 < y1`);
      if (p.axes !== null && keys(p.axes, ["x", "y"], [], `${w} axes`)) {
        for (const ax of ["x", "y"]) {
          const A = p.axes[ax], aw = `${w} ${ax}-axis`;
          if (A === null || !keys(A, ["name", "unit", "scale", "range", "ticks"], [], aw)) continue;
          strOrNull(A.name, `${aw} name`); strOrNull(A.unit, `${aw} unit`);
          oneOf(A.scale, SCALES, `${aw} scale`, true);
          if (A.range != null && !(Array.isArray(A.range) && A.range.length === 2 && A.range.every(isNum))) E.push(`${aw} range: two numbers or null`);
          if (A.ticks != null && !(Array.isArray(A.ticks) && A.ticks.every((t) => isNum(t) || typeof t === "string"))) E.push(`${aw} ticks: list of numbers/texts or null`);
        }
      }
      const names = new Set();
      (Array.isArray(p.series) ? p.series : (E.push(`${w} series: list expected`), [])).forEach((s, k) => {
        if (!keys(s, ["name", "color"], [], `${w} series ${k + 1}`)) return;
        if (!s.name || typeof s.name !== "string") E.push(`${w} series ${k + 1}: name required`);
        else if (names.has(s.name)) E.push(`${w} series "${s.name}": duplicate name`);
        names.add(s.name);
        strOrNull(s.color, `${w} series ${k + 1} color`);
      });
      if (p.notes !== undefined && !(Array.isArray(p.notes) && p.notes.every((n) => typeof n === "string"))) E.push(`${w} notes: list of texts`);
      (Array.isArray(p.data) ? p.data : (E.push(`${w} data: list expected`), [])).forEach((r, k) => {
        const rw = `${w} row ${k + 1}`;
        if (!keys(r, COLS, [], rw)) return;
        ["category", "series", "label_printed"].forEach((c) => strOrNull(r[c], `${rw} ${c}`));
        ["value", "err_lo", "err_hi"].forEach((c) => numOrNull(r[c], `${rw} ${c}`));
        if (r.x != null && !isNum(r.x) && typeof r.x !== "string") E.push(`${rw} x: number, text or null`);
        oneOf(r.source, SOURCES, `${rw} source`);
        if (!isNum(r.confidence) || r.confidence < 0 || r.confidence > 1) E.push(`${rw} confidence: number 0..1`);
        if (isNum(r.err_lo) && isNum(r.err_hi) && r.err_lo > r.err_hi) E.push(`${rw}: err_lo > err_hi`);
      });
    });
    const L = d.labeler;
    if (keys(L, ["kind", "name", "date", "time_minutes"], [], "labeler")) {
      oneOf(L.kind, ["human", "agent", "engine"], "labeler.kind");
      strOrNull(L.name, "labeler.name");
      if (L.date !== null && !/^\d{4}-\d{2}-\d{2}$/.test(L.date || "")) E.push("labeler.date: YYYY-MM-DD or null");
      if (L.time_minutes !== null && !(isNum(L.time_minutes) && L.time_minutes >= 0)) E.push("labeler.time_minutes: number >= 0 or null");
    }
    if (d.uncertain !== undefined && !(Array.isArray(d.uncertain) && d.uncertain.every((u) => typeof u === "string"))) E.push("uncertain: list of texts");
    return E;
  }

  const api = { SCHEMA, KINDS, SOURCES, SOURCE_KINDS, SCALES, COLS, COL_HELP, TYPE_KIND, BARLIKE, parseNum, parsePrinted, roundStep, axisMap, parseTicks, parseCSV, csvRows, setField, blankDoc, blankRow, fileName, validateDoc };
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.LabelerCore = api;
})(typeof window !== "undefined" ? window : globalThis);
