/* Figure labeler UI: offline single-page app (vanilla JS, works from file://).
 * Writes one extrct.figure-data/1 JSON per figure; see schema.json and README.md.
 * Pure logic lives in labeler-core.js. */
(function (root) {
  "use strict";

  const {
    KINDS, SOURCES, SOURCE_KINDS, SCALES, COLS, COL_HELP, TYPE_KIND, BARLIKE,
    parseNum, parsePrinted, roundStep, axisMap, parseTicks, csvRows, setField, blankDoc, blankRow, fileName, validateDoc,
  } = root.LabelerCore;

  // ---------------------------------------------------------------- app state
  const M = root.LABELER_MANIFEST;
  const FIGS = M && Array.isArray(M.figures) ? M.figures : [];
  const PREFIX = "figlabel/1/";
  const $ = (id) => document.getElementById(id);
  const today = () => new Date().toISOString().slice(0, 10);
  const minutes = (ms) => Math.round(ms / 6000) / 10;
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  let storageOk = true;

  function store(key, val) {
    try { localStorage.setItem(key, JSON.stringify(val)); } catch (e) {
      if (storageOk) toast("Autosave is unavailable in this browser. Export your work often.");
      storageOk = false;
    }
  }
  function recall(key) {
    try { const s = localStorage.getItem(key); return s ? JSON.parse(s) : null; } catch (e) { return null; }
  }

  const states = FIGS.map((f) => recall(PREFIX + f.id));
  const S = { i: -1, panel: 0, row: -1, tool: "select", pick: null, z: 1, tx: 0, ty: 0, drag: null, pan: null, space: false, lastField: null, activeAt: Date.now() };
  const cur = () => states[S.i];
  const doc = () => cur().doc;
  const panel = () => (S.i >= 0 ? doc().panels[S.panel] || null : null);
  const confDefault = () => { const v = parseNum($("point-conf").value); return v !== null && v >= 0 && v <= 1 ? v : 0.8; };

  function stateOf(i) {
    if (!states[i]) states[i] = { doc: blankDoc(FIGS[i], $("labeler-name").value.trim(), today()), cal: [], ms: 0, done: false };
    return states[i];
  }

  function normalize(d) {
    d.panels = Array.isArray(d.panels) ? d.panels : [];
    d.uncertain = Array.isArray(d.uncertain) ? d.uncertain : [];
    d.labeler = d.labeler || { kind: "human", name: null, date: today(), time_minutes: null };
    for (const p of d.panels) {
      p.series = p.series || []; p.data = p.data || []; p.notes = p.notes || [];
      if (p.axes === undefined) p.axes = null;
    }
    return d;
  }

  // ------------------------------------------------------------- DOM helpers
  function h(tag, props, ...kids) {
    const el = document.createElement(tag);
    for (const [k, v] of Object.entries(props || {})) {
      if (v === undefined || v === null || v === false) continue;
      if (k === "class") el.className = v;
      else if (k === "text") el.textContent = v;
      else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
      else if (k === "value" || k === "checked") el[k] = v;
      else el.setAttribute(k, v === true ? "" : v);
    }
    for (const kid of kids.flat()) if (kid !== null && kid !== undefined && kid !== false) el.append(kid);
    return el;
  }
  function sv(tag, attrs, text) {
    const el = document.createElementNS("http://www.w3.org/2000/svg", tag);
    for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
    if (text !== undefined) el.textContent = text;
    return el;
  }
  /** Text input bound to a setter; `on: "change"` commits on blur/Enter instead of every keystroke. */
  function inp(value, set, opts = {}) {
    const { on = "input", ...attrs } = opts;
    return h("input", { value: value == null ? "" : String(value), ...attrs, ["on" + on]: (e) => set(e.target.value.trim(), e.target) });
  }
  function select(options, value, set) {
    return h("select", { onchange: (e) => set(e.target.value) }, ...options.map((o) => h("option", { value: o, text: o || "—", selected: o === value })));
  }
  const lab = (text, ...kids) => h("label", {}, text, ...kids);
  const lines = (v) => v.split("\n").map((s) => s.trim()).filter(Boolean);
  const isField = (el) => el && (el.tagName === "TEXTAREA" || el.tagName === "SELECT" || (el.tagName === "INPUT" && !["checkbox", "radio", "button", "file"].includes(el.type)));

  let flashTimer = 0, toastTimer = 0;
  function flash(msg) { $("flash").textContent = msg; clearTimeout(flashTimer); flashTimer = setTimeout(() => { $("flash").textContent = ""; }, 5000); }
  function toast(msg) { const t = $("toast"); t.textContent = msg; t.hidden = false; clearTimeout(toastTimer); toastTimer = setTimeout(() => { t.hidden = true; }, 6000); }

  // ------------------------------------------------------------ persistence
  let saveTimer = 0;
  function touch(redraw = true) {
    clearTimeout(saveTimer);
    saveTimer = setTimeout(saveNow, 300);
    if (redraw) drawOverlay();
    updateIssues();
  }
  function saveNow() {
    if (S.i < 0 || !cur()) return;
    const st = cur();
    st.doc.labeler.time_minutes = minutes(st.ms);
    store(PREFIX + FIGS[S.i].id, st);
    updateListItem(S.i);
  }

  // ------------------------------------------------------------------- list
  function statusOf(i) { const st = states[i]; return !st ? "todo" : st.done ? "done" : st.doc.panels.length ? "wip" : "todo"; }
  function renderList() {
    const ol = $("figs");
    ol.textContent = "";
    FIGS.forEach((f, i) => ol.append(h("li", { id: "li-" + i, title: f.caption_text || "", onclick: () => openFig(i) },
      h("span", { class: "dot" }), h("span", { class: "name", text: f.id }), h("span", { class: "sub" }))));
    FIGS.forEach((_, i) => updateListItem(i));
  }
  function updateListItem(i) {
    const li = $("li-" + i);
    if (!li) return;
    const st = states[i], f = FIGS[i];
    li.className = statusOf(i) + (i === S.i ? " cur" : "");
    const rows = st ? st.doc.panels.reduce((n, p) => n + p.data.length, 0) : 0;
    li.querySelector(".sub").textContent = `${f.figure_type || "?"} · p.${f.page}` + (st && st.doc.panels.length ? ` · ${st.doc.panels.length} pan · ${rows} rows` : "");
    const done = FIGS.filter((_, k) => statusOf(k) === "done").length;
    const wip = FIGS.filter((_, k) => statusOf(k) === "wip").length;
    document.querySelector("#progress .bar span").style.width = `${(100 * done) / FIGS.length}%`;
    document.querySelector("#progress .txt").textContent = `${done}/${FIGS.length} done · ${wip} in progress`;
  }

  function openFig(i) {
    if (i < 0 || i >= FIGS.length) return;
    if (S.i >= 0) saveNow();
    const prev = S.i;
    Object.assign(S, { i, panel: 0, row: -1, pick: null, drag: null, lastField: null });
    const st = stateOf(i);
    normalize(st.doc);
    st.cal = st.doc.panels.map((_, k) => (st.cal && st.cal[k]) || {});
    const f = FIGS[i], img = $("img"), ovl = $("ovl");
    img.width = f.width; img.height = f.height;
    img.src = ($("show-hires").checked && f.image_hires) || f.image;
    ovl.setAttribute("width", f.width); ovl.setAttribute("height", f.height);
    ovl.setAttribute("viewBox", `0 0 ${f.width} ${f.height}`);
    $("fig-title").textContent = `${f.id} · ${f.figure_type || "?"} · page ${f.page}`;
    $("done").checked = st.done;
    $("timer").textContent = `${minutes(st.ms).toFixed(1)} min`;
    if (prev >= 0) updateListItem(prev);
    updateListItem(i);
    store("figlabel/last", f.id);
    fit();
    renderForm();
    $("li-" + i).scrollIntoView({ block: "nearest" });
  }

  // ----------------------------------------------------------------- viewer
  function applyView() {
    $("wrap").style.transform = `translate(${S.tx}px, ${S.ty}px) scale(${S.z})`;
    $("zoom-txt").textContent = `${Math.round(S.z * 100)}%`;
    drawOverlay();
  }
  function fit() {
    if (S.i < 0) return;
    const r = $("stage").getBoundingClientRect(), f = FIGS[S.i];
    S.z = Math.max(0.05, Math.min((r.width - 24) / f.width, (r.height - 24) / f.height, 6));
    S.tx = (r.width - f.width * S.z) / 2;
    S.ty = (r.height - f.height * S.z) / 2;
    applyView();
  }
  function zoomAt(factor, cx, cy) {
    const z = Math.max(0.05, Math.min(S.z * factor, 24));
    S.tx = cx - ((cx - S.tx) * z) / S.z;
    S.ty = cy - ((cy - S.ty) * z) / S.z;
    S.z = z;
    applyView();
  }
  const zoomCentre = (factor) => { const r = $("stage").getBoundingClientRect(); zoomAt(factor, r.width / 2, r.height / 2); };
  function toPx(ev) {
    const r = $("stage").getBoundingClientRect();
    return { x: (ev.clientX - r.left - S.tx) / S.z, y: (ev.clientY - r.top - S.ty) / S.z };
  }

  function wordsShown() {
    if (S.i < 0) return [];
    const f = FIGS[S.i];
    return [
      ...($("show-docling").checked ? f.words_docling.map((w) => ({ ...w, src: "docling" })) : []),
      ...($("show-pdf").checked ? f.words_pdf.map((w) => ({ ...w, src: "pdf" })) : []),
    ];
  }
  const inBox = (p, b, pad = 0) => p.x >= b[0] - pad && p.x <= b[2] + pad && p.y >= b[1] - pad && p.y <= b[3] + pad;
  const area = (b) => (b[2] - b[0]) * (b[3] - b[1]);
  function wordAt(p) {
    let best = null;
    for (const w of wordsShown()) if (inBox(p, w.bbox_px, 2 / S.z) && (!best || area(w.bbox_px) < area(best.bbox_px))) best = w;
    return best;
  }
  function panelAt(p) {
    let best = -1;
    doc().panels.forEach((P, k) => { if (P.bbox_px && inBox(p, P.bbox_px) && (best < 0 || area(P.bbox_px) < area(doc().panels[best].bbox_px))) best = k; });
    return best;
  }
  function calOf(pi, ax) {
    const c = cur().cal[pi] || (cur().cal[pi] = {});
    return c[ax] || (c[ax] = [null, null]);
  }
  function mapOf(pi, ax) {
    const P = doc().panels[pi];
    return P && P.axes && P.axes[ax] ? axisMap(P.axes[ax], (cur().cal[pi] || {})[ax]) : null;
  }

  function selectPanel(k) {
    if (k === S.panel) return;
    S.panel = k; S.row = -1; S.pick = null;
    renderForm();
  }

  function nextPanelId() {
    const used = new Set(doc().panels.map((p) => p.id));
    for (const c of "abcdefghijklmnopqrstuvwxyz") if (!used.has(c)) return c;
    let n = 27;
    while (used.has("p" + n)) n++;
    return "p" + n;
  }
  function isBlankAxis(A) { return !A || (!A.name && !A.unit && !A.range && !A.ticks); }
  const blankAxis = (scale) => ({ name: null, unit: null, scale: scale || null, range: null, ticks: null });
  /** Fill orientation and axes that suit the kind; never overwrites what the labeler typed. */
  function shapeFor(p) {
    if (p.kind === "pie") {
      if (p.axes && isBlankAxis(p.axes.x) && isBlankAxis(p.axes.y)) p.axes = null;
      p.orientation = null;
      return;
    }
    if (!p.orientation && BARLIKE.includes(p.kind)) p.orientation = p.kind === "forest" ? "horizontal" : "vertical";
    const catAxes = BARLIKE.includes(p.kind) ? (p.orientation === "horizontal" ? "y" : "x") : p.kind === "heatmap" ? "xy" : "";
    p.axes = p.axes || { x: null, y: null };
    for (const ax of ["x", "y"]) {
      if (!p.axes[ax]) p.axes[ax] = blankAxis(catAxes.includes(ax) ? "categorical" : "linear");
      else if (isBlankAxis(p.axes[ax])) p.axes[ax].scale = catAxes.includes(ax) ? "categorical" : "linear";
    }
  }
  function addPanel(bbox) {
    const P = { id: nextPanelId(), bbox_px: bbox, title: null, kind: TYPE_KIND[FIGS[S.i].figure_type] || "other", orientation: null, axes: null, series: [], data: [], notes: [] };
    shapeFor(P);
    doc().panels.push(P);
    cur().cal.push({});
    S.panel = doc().panels.length - 1; S.row = -1;
    renderForm();
    touch();
  }
  function deletePanel(k) {
    const P = doc().panels[k];
    if (!P || !confirm(`Delete panel ${P.id} and its ${P.data.length} rows?`)) return;
    doc().panels.splice(k, 1);
    cur().cal.splice(k, 1);
    S.panel = Math.max(0, k - 1); S.row = -1;
    renderForm();
    touch();
  }

  function pickAt(p) {
    const { ax, k } = S.pick, w = wordAt(p);
    const pos = w ? { x: (w.bbox_px[0] + w.bbox_px[2]) / 2, y: (w.bbox_px[1] + w.bbox_px[3]) / 2 } : p;
    const c = calOf(S.panel, ax);
    c[k] = { px: Math.round((ax === "x" ? pos.x : pos.y) * 10) / 10, val: w ? w.text.trim() : (c[k] && c[k].val) || "" };
    S.pick = null;
    renderForm();
    touch();
    const el = document.querySelector(`[data-cal="${ax}${k}"]`);
    if (el) { el.focus(); el.select(); }
    flash(`${ax}-axis ref ${k + 1} at ${c[k].px}px` + (w ? ` = "${c[k].val}" (check it)` : ": type its value"));
  }

  function pointAt(p, ev) {
    const f = FIGS[S.i];
    if (!doc().panels.length) addPanel([0, 0, f.width, f.height]);
    const hit = panelAt(p);
    selectPanel(hit >= 0 ? hit : S.panel);
    const P = panel(), horiz = P.orientation === "horizontal";
    const vAx = horiz ? "x" : "y", cAx = horiz ? "y" : "x";
    const vm = mapOf(S.panel, vAx), cm = mapOf(S.panel, cAx);
    if (!vm || vm.cat) return flash(`Point reads positions: calibrate the numeric ${vAx} axis of panel ${P.id} first (pick ref 1 and ref 2).`);
    const target = ev.shiftKey ? "err_hi" : ev.altKey ? "err_lo" : $("target").value;
    let val = roundStep(vm.toVal(horiz ? p.x : p.y), vm.step);
    let row = P.data[S.row];
    const fresh = target === "value" && (!row || row.value !== null);
    if (fresh) {
      row = blankRow({ series: $("point-series").value || null, confidence: confDefault() });
      P.data.push(row);
      S.row = P.data.length - 1;
    } else if (!row) return flash("Select a row first (click its number in the grid).");
    if (cm && row.category === null && row.x === null) {
      const c = cm.toVal(horiz ? p.y : p.x);
      if (cm.cat) row.category = c; else row.x = roundStep(c, cm.step);
    }
    if (P.kind === "stacked_bar" && target === "value") {
      const key = row.category ?? row.x;
      const base = P.data.filter((r) => r !== row && (r.category ?? r.x) === key && r.value !== null).reduce((s, r) => s + r.value, 0);
      val = roundStep(val - base, vm.step);
    }
    row[target] = val;
    renderGrid();
    touch();
    flash(`row ${S.row + 1}: ${target} = ${val}` + (P.kind === "stacked_bar" && target === "value" ? " (segment size above the stack below)" : ""));
  }

  function useWord(w, append) {
    const el = S.lastField;
    if (!el || !document.body.contains(el)) return flash("Click a form field first, then a word to copy it there.");
    const text = w.text.trim();
    const sep = el.dataset.append ? ", " : " ";
    el.value = (append || el.dataset.append) && el.value.trim() ? el.value.replace(/[,\s]+$/, "") + sep + text : text;
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
    el.focus();
  }

  function setTool(t) {
    S.tool = t; S.pick = null;
    document.querySelectorAll("[data-tool]").forEach((b) => b.classList.toggle("on", b.dataset.tool === t));
    stageClass();
    renderForm();
  }
  function stageClass() {
    const st = $("stage");
    st.className = `tool-${S.tool}` + (S.pick ? " picking" : "") + (S.pan ? " panning" : "");
  }

  function drawOverlay() {
    const svg = $("ovl");
    svg.textContent = "";
    if (S.i < 0) return;
    const z = S.z, fs = 12 / z;
    for (const w of wordsShown()) {
      const b = w.bbox_px;
      const r = sv("rect", { x: b[0], y: b[1], width: b[2] - b[0], height: b[3] - b[1], class: "word" + (w.src === "pdf" ? " pdf" : ""), "stroke-width": 1 });
      r.append(sv("title", {}, w.text));
      svg.append(r);
    }
    doc().panels.forEach((P, k) => {
      if (!P.bbox_px) return;
      const b = P.bbox_px;
      svg.append(sv("rect", { x: b[0], y: b[1], width: b[2] - b[0], height: b[3] - b[1], class: "panel" + (k === S.panel ? " sel" : ""), "stroke-width": k === S.panel ? 2.5 : 1.5 }));
      svg.append(sv("text", { x: b[0] + 3 / z, y: b[1] + fs * 1.2, class: "plabel", "font-size": fs * 1.3 }, P.id));
    });
    const P = panel();
    if (P) drawPanelMarks(svg, P, fs);
    if (S.drag) {
      const d = S.drag;
      svg.append(sv("rect", { x: Math.min(d.x0, d.x1), y: Math.min(d.y0, d.y1), width: Math.abs(d.x1 - d.x0), height: Math.abs(d.y1 - d.y0), class: "drag", "stroke-width": 1.5 }));
    }
  }
  function drawPanelMarks(svg, P, fs) {
    const f = FIGS[S.i], b = P.bbox_px || [0, 0, f.width, f.height];
    for (const ax of ["x", "y"]) {
      (cur().cal[S.panel] || {})[ax]?.forEach((c, k) => {
        if (!c || c.px == null) return;
        const line = ax === "x" ? { x1: c.px, x2: c.px, y1: b[1], y2: b[3] } : { x1: b[0], x2: b[2], y1: c.px, y2: c.px };
        svg.append(sv("line", { ...line, class: "cal", "stroke-width": 1 }));
        svg.append(sv("text", { x: line.x1 + 2 / S.z, y: (ax === "x" ? b[3] : c.px) - 2 / S.z, class: "caltxt", "font-size": fs }, `${ax}${k + 1}=${c.val}`));
      });
    }
    const horiz = P.orientation === "horizontal";
    const vm = mapOf(S.panel, horiz ? "x" : "y"), cm = mapOf(S.panel, horiz ? "y" : "x");
    if (!vm || vm.cat || !cm) return;
    const stack = {};
    P.data.forEach((r, k) => {
      const key = r.category ?? r.x;
      const cpos = cm.toPx(cm.cat ? key : r.x ?? parseNum(r.category));
      if (cpos == null || !Number.isFinite(cpos)) return;
      const pt = (v) => { const q = vm.toPx(v); return q == null || !Number.isFinite(q) ? null : horiz ? [q, cpos] : [cpos, q]; };
      const lo = r.err_lo !== null ? pt(r.err_lo) : null, hi = r.err_hi !== null ? pt(r.err_hi) : null;
      if (lo && hi) svg.append(sv("line", { x1: lo[0], y1: lo[1], x2: hi[0], y2: hi[1], class: "err", "stroke-width": 2 }));
      if (r.value === null) return;
      let v = r.value;
      if (P.kind === "stacked_bar") { stack[key] = (stack[key] || 0) + v; v = stack[key]; }
      const c = pt(v);
      if (c) svg.append(sv("circle", { cx: c[0], cy: c[1], r: (k === S.row ? 5 : 3.5) / S.z, class: "mark" + (k === S.row ? " sel" : ""), "stroke-width": 1 }));
    });
  }

  // ------------------------------------------------------------------- form
  function renderForm() {
    const F = $("form");
    F.textContent = "";
    if (S.i < 0) return;
    const f = FIGS[S.i], d = doc();
    F.append(
      h("div", { class: "meta" }, h("b", { text: f.id }), ` · ${f.self_ref} · page ${f.page} · ${f.figure_type || "?"}` +
        (f.figure_type_confidence != null ? ` (${f.figure_type_confidence})` : "") + ` · crop ${f.width}×${f.height}px · words ${f.words_docling.length} + PDF ${f.words_pdf.length}`),
      f.caption_text ? h("details", { open: true }, h("summary", { text: "Caption" }), h("div", { class: "meta", text: f.caption_text })) : null,
      f.vlm_caption ? h("details", {}, h("summary", { text: "Model description (may be wrong)" }), h("div", { class: "meta", text: f.vlm_caption })) : null,
      h("div", { class: "row" },
        lab("source kind", select(SOURCE_KINDS, d.source_kind, (v) => { d.source_kind = v; touch(false); })),
        lab("labeler kind", select(["human", "agent"], d.labeler.kind, (v) => { d.labeler.kind = v; touch(false); }))),
      h("h3", {}, "Panels", h("span", { class: "tabs" },
        ...d.panels.map((p, k) => h("button", { class: k === S.panel ? "on" : "", text: p.id, onclick: () => selectPanel(k) })),
        h("button", { text: "+ whole image", title: "Add a panel covering the whole figure", onclick: () => addPanel([0, 0, f.width, f.height]) }))),
    );
    const P = panel();
    if (P) renderPanel(F, P);
    else F.append(h("p", { class: "muted", text: "No panel yet. Press P and drag a box around each sub-panel (a, b, c… in reading order), or use “+ whole image” for a single chart." }));
    F.append(h("h3", { text: "Uncertain (one item per line)" }),
      h("textarea", { oninput: (e) => { d.uncertain = lines(e.target.value); touch(false); } }, d.uncertain.join("\n")),
      h("datalist", { id: "series-list" }), h("div", { id: "issues", class: "issues" }));
    refreshSeries();
    updateIssues();
  }

  function renderPanel(F, P) {
    const f = FIGS[S.i];
    F.append(
      h("div", { class: "row" },
        lab("id", inp(P.id, (v, el) => renamePanel(P, v, el), { size: 3, on: "change" })),
        lab("kind", select(KINDS, P.kind, (v) => { P.kind = v; shapeFor(P); renderForm(); touch(); })),
        lab("orientation", select(["", "vertical", "horizontal"], P.orientation || "", (v) => { P.orientation = v || null; touch(); })),
        h("button", { class: "danger", text: "Delete panel", title: "Del", onclick: () => deletePanel(S.panel) })),
      h("div", { class: "row" }, h("label", { class: "grow" }, "title", inp(P.title, (v) => { P.title = v || null; touch(false); }, { placeholder: "panel title as printed" }))),
      h("div", { class: "row" }, lab("bbox_px", ...[0, 1, 2, 3].map((k) => inp(P.bbox_px ? P.bbox_px[k] : "", (v) => {
        P.bbox_px = P.bbox_px || [0, 0, f.width, f.height];
        const n = parseNum(v);
        if (n !== null) P.bbox_px[k] = n;
        touch();
      }, { class: "num", title: ["x0", "y0", "x1", "y1"][k] })))),
      h("h3", {}, "Axes", h("label", { class: "inline" }, h("input", { type: "checkbox", checked: P.axes === null, onchange: (e) => {
        P.axes = e.target.checked ? null : { x: null, y: null };
        if (P.axes) shapeFor(P);
        renderForm(); touch();
      } }), "no axes (pie)")),
    );
    if (P.axes) for (const ax of ["x", "y"]) F.append(renderAxis(P, ax));
    F.append(h("h3", {}, "Series", h("button", { text: "+ series", onclick: () => {
      let n = P.series.length + 1;
      while (P.series.some((s) => s.name === `series ${n}`)) n++;
      P.series.push({ name: `series ${n}`, color: null });
      renderForm(); touch(false);
    } })));
    P.series.forEach((s, k) => {
      const sw = h("span", { class: "swatch", style: `background:${s.color || "transparent"}` });
      F.append(h("div", { class: "series-row" }, sw,
        inp(s.name, (v, el) => renameSeries(P, s, v, el), { on: "change", placeholder: "legend name" }),
        inp(s.color, (v) => { s.color = v || null; sw.style.background = v || "transparent"; touch(false); }, { size: 10, placeholder: "colour (name or #hex)" }),
        h("button", { text: "✕", title: "Remove series (rows keep their series text)", onclick: () => { P.series.splice(k, 1); renderForm(); touch(); } })));
    });
    F.append(
      h("h3", {}, h("span", { id: "data-count" }), h("button", { text: "+ row", title: "Ctrl+Enter in the grid", onclick: () => addRow(P.data.length) })),
      h("div", { class: "gridwrap", id: "gridwrap" }),
      h("details", {}, h("summary", { text: "Paste CSV / spreadsheet rows" }),
        h("textarea", { id: "csv", rows: 5, placeholder: "category,series,value,err_lo,err_hi\nCoT,AMIE,0.42,0.37,0.47\n\nor wide (one column per series):\ncategory,AMIE,PCP\nVisit 1,0.61,0.55" }),
        h("div", { class: "row" }, h("button", { text: "Append rows", onclick: () => pasteCSV(false) }), h("button", { text: "Replace rows", onclick: () => pasteCSV(true) }),
          h("span", { class: "muted", text: "header row required; tab, comma or semicolon" }))),
      h("h3", { text: "Panel notes (one per line)" }),
      h("textarea", { placeholder: "e.g. quartiles for box plots, legend overlaps", oninput: (e) => { P.notes = lines(e.target.value); touch(false); } }, P.notes.join("\n")),
    );
    renderGrid();
  }

  function renderAxis(P, ax) {
    const A = P.axes[ax];
    if (!A) return h("div", { class: "axis" }, h("button", { text: `+ ${ax} axis`, onclick: () => { P.axes[ax] = blankAxis("linear"); renderForm(); touch(); } }));
    const c = calOf(S.panel, ax);
    const ok = mapOf(S.panel, ax);
    return h("div", { class: "axis" },
      h("div", { class: "row" }, h("b", { text: `${ax.toUpperCase()} axis` }),
        h("label", { class: "grow" }, "name", inp(A.name, (v) => { A.name = v || null; touch(false); })),
        lab("unit", inp(A.unit, (v) => { A.unit = v || null; touch(false); }, { size: 5 })),
        lab("scale", select(["", ...SCALES], A.scale || "", (v) => { A.scale = v || null; A.ticks = parseTicks((A.ticks || []).join(","), A.scale); renderForm(); touch(); }))),
      h("div", { class: "row" },
        lab("range", ...[0, 1].map((k) => inp(A.range ? A.range[k] : "", (v) => {
          const r = A.range ? [...A.range] : [null, null];
          r[k] = parseNum(v);
          A.range = r[0] === null && r[1] === null ? null : r;
          touch(false);
        }, { class: "num", placeholder: k ? "max" : "min" }))),
        h("label", { class: "grow" }, "ticks", inp((A.ticks || []).join(", "), (v) => { A.ticks = parseTicks(v, A.scale); touch(); }, { "data-append": "1", placeholder: "focus, then click tick words" }))),
      h("div", { class: "row cal" }, h("span", { class: "muted", text: "calibrate" }),
        ...[0, 1].map((k) => h("span", { class: "inline" },
          h("button", { class: S.pick && S.pick.ax === ax && S.pick.k === k ? "armed" : "", text: `pick ref ${k + 1}`, title: "Then click a tick label word or the tick mark", onclick: () => {
            S.pick = { ax, k }; stageClass(); renderForm();
            flash(`Click a ${ax}-axis tick label (or tick mark) for ref ${k + 1}. Esc cancels.`);
          } }),
          h("span", { class: "muted", text: c[k] && c[k].px != null ? `@${c[k].px}` : "—" }),
          inp(c[k] ? c[k].val : "", (v) => { c[k] = c[k] || { px: null, val: "" }; c[k].val = v; touch(); }, { class: "num", "data-cal": ax + k, placeholder: A.scale === "categorical" ? "category" : "value" }))),
        h("span", { class: ok ? "" : "muted", text: ok ? "✓ calibrated" : A.scale === "categorical" ? "needs ticks + 2 refs" : "needs 2 refs" })));
  }

  function renamePanel(P, v, el) {
    if (!v || doc().panels.some((p) => p !== P && p.id === v)) { el.value = P.id; return flash("Panel ids must be unique and non-empty."); }
    P.id = v;
    renderForm(); touch();
  }
  function renameSeries(P, s, v, el) {
    if (!v || P.series.some((o) => o !== s && o.name === v)) { el.value = s.name; return flash("Series names must be unique and non-empty."); }
    const old = s.name;
    s.name = v;
    P.data.forEach((r) => { if (r.series === old) r.series = v; });
    renderGrid(); refreshSeries(); touch(false);
  }
  function refreshSeries() {
    const P = panel(), sel = $("point-series"), keep = sel.value;
    const names = P ? P.series.map((s) => s.name) : [];
    sel.textContent = "";
    sel.append(h("option", { value: "", text: "(no series)" }), ...names.map((n) => h("option", { value: n, text: n, selected: n === keep })));
    const dl = $("series-list");
    if (dl) { dl.textContent = ""; names.forEach((n) => dl.append(h("option", { value: n }))); }
  }

  // ------------------------------------------------------------- data grid
  function renderGrid() {
    const wrap = $("gridwrap"), P = panel();
    if (!wrap || !P) return;
    const a = document.activeElement, keep = a && a.dataset && a.dataset.col ? { r: +a.dataset.r, col: a.dataset.col } : null;
    const tb = h("tbody");
    P.data.forEach((row, r) => tb.append(h("tr", { class: r === S.row ? "sel" : "" },
      h("td", { class: "idx", text: String(r + 1), title: "Select row (clicks with Shift/Alt fill its errors)", onclick: () => selectRow(r) }),
      ...COLS.map((c) => h("td", {}, cell(row, r, c))),
      h("td", { class: "act" }, h("button", { text: "⧉", title: "Duplicate (Ctrl+D)", onclick: () => dupRow(r) }), h("button", { text: "✕", title: "Delete (Ctrl+Delete)", onclick: () => delRow(r) })))));
    wrap.textContent = "";
    wrap.append(h("table", { class: "grid" },
      h("colgroup", {}, h("col", { style: "width:24px" }), ...COLS.map((c) => h("col", { class: "c-" + c })), h("col", { style: "width:48px" })),
      h("thead", {}, h("tr", {}, h("th", { text: "#" }), ...COLS.map((c) => h("th", { text: c === "label_printed" ? "printed" : c === "confidence" ? "conf" : c, title: COL_HELP[c] })), h("th"))), tb));
    if (!P.data.length) wrap.append(h("div", { class: "muted", style: "padding:6px", text: "No rows yet: press A and click marks, use + row, or paste CSV." }));
    $("data-count").textContent = `Data (${P.data.length} rows) `;
    if (keep) focusCell(keep.r, keep.col);
  }
  function cell(row, r, c) {
    const common = { "data-r": r, "data-col": c, onfocus: () => selectRow(r) };
    if (c === "source") return h("select", { ...common, onchange: (e) => { row.source = e.target.value; touch(false); } }, ...SOURCES.map((s) => h("option", { value: s, text: s, selected: row.source === s })));
    return h("input", {
      ...common, value: row[c] == null ? "" : String(row[c]), list: c === "series" ? "series-list" : null, title: COL_HELP[c],
      oninput: (e) => { e.target.classList.toggle("bad", !setField(row, c, e.target.value)); touch(); },
      onchange: c === "label_printed" ? () => fromPrinted(row, r) : null,
    });
  }
  function fromPrinted(row, r) {
    if (!row.label_printed || row.value !== null) return;
    const got = parsePrinted(row.label_printed);
    if (!got) return;
    Object.assign(row, got, { confidence: 1 });
    for (const c of ["value", "err_lo", "err_hi", "confidence"]) {
      const el = document.querySelector(`[data-r="${r}"][data-col="${c}"]`);
      if (el) { el.value = row[c] == null ? "" : String(row[c]); el.classList.remove("bad"); }
    }
    touch();
    flash(`value ${row.value} taken from the printed label` + (got.err_lo !== undefined ? " (with CI)" : ""));
  }
  function selectRow(r) {
    S.row = r;
    document.querySelectorAll("table.grid tbody tr").forEach((tr, k) => tr.classList.toggle("sel", k === r));
    drawOverlay();
  }
  function focusCell(r, c) {
    const el = document.querySelector(`[data-r="${r}"][data-col="${c}"]`);
    if (el) { el.focus(); if (el.select) el.select(); }
  }
  function addRow(at, col = "category") {
    const P = panel(), above = P.data[at - 1];
    P.data.splice(at, 0, blankRow({ series: above ? above.series : $("point-series").value || null, confidence: confDefault() }));
    S.row = at;
    renderGrid(); focusCell(at, col); touch();
  }
  function dupRow(r, col = "category") {
    const P = panel();
    P.data.splice(r + 1, 0, { ...P.data[r] });
    S.row = r + 1;
    renderGrid(); focusCell(r + 1, col); touch();
  }
  function delRow(r, col = "category") {
    const P = panel();
    P.data.splice(r, 1);
    S.row = Math.min(r, P.data.length - 1);
    renderGrid();
    if (S.row >= 0) focusCell(S.row, col);
    touch();
  }
  function gridKey(ev) {
    const el = ev.target;
    if (!el.dataset || !el.dataset.col) return;
    const r = +el.dataset.r, c = el.dataset.col, P = panel(), mod = ev.ctrlKey || ev.metaKey;
    if (mod && ev.key === "Enter") { ev.preventDefault(); addRow(r + 1, c); }
    else if (mod && ev.key.toLowerCase() === "d") { ev.preventDefault(); dupRow(r, c); }
    else if (mod && (ev.key === "Delete" || ev.key === "Backspace")) { ev.preventDefault(); delRow(r, c); }
    else if (ev.key === "Enter" || (el.tagName === "INPUT" && (ev.key === "ArrowDown" || ev.key === "ArrowUp"))) {
      ev.preventDefault();
      if (c === "label_printed") fromPrinted(P.data[r], r);
      if (ev.key === "ArrowUp" || (ev.key === "Enter" && ev.shiftKey)) focusCell(Math.max(0, r - 1), c);
      else if (r + 1 < P.data.length) focusCell(r + 1, c);
      else if (ev.key === "Enter") addRow(r + 1, c);
    }
  }
  function pasteCSV(replace) {
    const P = panel(), res = csvRows($("csv").value, confDefault());
    if (res.error) return flash(res.error);
    res.series.forEach((n) => { if (!P.series.some((s) => s.name === n)) P.series.push({ name: n, color: null }); });
    if (replace) P.data = res.rows; else P.data.push(...res.rows);
    renderForm(); touch();
    flash(`${res.rows.length} rows ${replace ? "replaced" : "appended"}.`);
  }

  function updateIssues() {
    const box = $("issues");
    if (!box || S.i < 0) return;
    const E = validateDoc(finalDoc(S.i));
    const P = panel(), nulls = P ? P.data.filter((r) => r.value === null).length : 0;
    box.className = "issues " + (E.length ? "bad" : "ok");
    box.textContent = "";
    box.append(E.length ? `${E.length} problem(s) block export:` : "✓ valid against extrct.figure-data/1" + (nulls ? ` · ${nulls} null value(s) in this panel` : ""));
    if (E.length) box.append(h("ul", {}, ...E.slice(0, 12).map((e) => h("li", { text: e }))));
  }

  // -------------------------------------------------------- import / export
  function finalDoc(i) {
    const st = states[i];
    if (!st) return null;
    const d = JSON.parse(JSON.stringify(st.doc));
    d.labeler.name = $("labeler-name").value.trim() || d.labeler.name || null;
    d.labeler.date = today();
    d.labeler.time_minutes = minutes(st.ms);
    return d;
  }
  const labelled = () => FIGS.map((_, i) => i).filter((i) => states[i] && (states[i].doc.panels.length || states[i].done));
  function download(name, obj) {
    const a = h("a", { href: URL.createObjectURL(new Blob([JSON.stringify(obj, null, 2) + "\n"], { type: "application/json" })), download: name });
    document.body.append(a);
    a.click();
    setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 2000);
  }
  function blocked(list) {
    const bad = list.map((i) => [FIGS[i].id, validateDoc(finalDoc(i))]).filter(([, E]) => E.length);
    if (bad.length) toast("Not exported, fix first:\n" + bad.map(([id, E]) => `${id}: ${E[0]}${E.length > 1 ? ` (+${E.length - 1})` : ""}`).join("\n"));
    return bad.length > 0;
  }
  function exportOne() {
    if (S.i < 0) return;
    saveNow();
    if (blocked([S.i])) return;
    const d = finalDoc(S.i);
    download(fileName(d), d);
    flash(`Downloaded ${fileName(d)}: move it into labels/.`);
  }
  async function exportAll() {
    saveNow();
    const list = labelled();
    if (!list.length) return toast("Nothing labelled yet.");
    if (blocked(list)) return;
    for (const i of list) { const d = finalDoc(i); download(fileName(d), d); await sleep(350); }
    toast(`${list.length} file(s) downloaded. Move them into labels/ in this folder.`);
  }
  async function importFiles(files) {
    let n = 0;
    const notes = [];
    for (const file of files) {
      let data;
      try { data = JSON.parse(await file.text()); } catch (e) { notes.push(`${file.name}: not JSON`); continue; }
      for (const d of Array.isArray(data) ? data : [data]) {
        const ref = d && d.figure ? `${d.figure.bundle} ${d.figure.self_ref}` : "?";
        const i = FIGS.findIndex((f) => d && d.figure && f.bundle === d.figure.bundle && f.self_ref === d.figure.self_ref);
        if (i < 0) { notes.push(`${file.name}: ${ref} is not in this pack`); continue; }
        if (states[i] && states[i].doc.panels.length && !confirm(`Replace your work on ${FIGS[i].id} with ${file.name}?`)) continue;
        normalize(d);
        const old = states[i];
        // Calibration is not part of the schema: keep the browser's own for panels with the same id.
        const cal = d.panels.map((p) => { const k = old ? old.doc.panels.findIndex((q) => q.id === p.id) : -1; return (k >= 0 && old.cal[k]) || {}; });
        states[i] = { doc: d, cal, ms: Math.round(((d.labeler && d.labeler.time_minutes) || 0) * 60000), done: false };
        store(PREFIX + FIGS[i].id, states[i]);
        updateListItem(i);
        n++;
        if (i === S.i) { S.i = -1; openFig(i); }
        const E = validateDoc(d);
        if (E.length) notes.push(`${file.name}: ${E.length} problem(s), e.g. ${E[0]}`);
      }
    }
    toast(`Imported ${n} file(s).` + (notes.length ? "\n" + notes.join("\n") : ""));
  }

  // ------------------------------------------------------------ wiring
  function showHelp(on) { $("help").hidden = !on; }
  function showEmpty(html) { const e = $("empty"); e.hidden = false; e.innerHTML = `<div class="card">${html}</div>`; }

  function wire() {
    const stage = $("stage");
    stage.addEventListener("mousedown", (ev) => {
      if (S.i < 0) return;
      const p = toPx(ev);
      if (ev.button === 1 || (ev.button === 0 && S.space)) { ev.preventDefault(); S.pan = { x: ev.clientX - S.tx, y: ev.clientY - S.ty }; return stageClass(); }
      if (ev.button !== 0) return;
      ev.preventDefault(); // keeps focus in the form field so a word click can fill it
      const a = document.activeElement;
      if (a && a !== S.lastField && a !== document.body) a.blur(); // toolbar/select focus would swallow shortcuts
      if (S.pick) return pickAt(p);
      if (S.tool === "panel") { S.drag = { x0: p.x, y0: p.y, x1: p.x, y1: p.y }; return; }
      if (S.tool === "point") return pointAt(p, ev);
      const w = wordAt(p);
      if (w) return useWord(w, ev.shiftKey);
      const k = panelAt(p);
      if (k >= 0) selectPanel(k);
      S.pan = { x: ev.clientX - S.tx, y: ev.clientY - S.ty };
      stageClass();
    });
    window.addEventListener("mousemove", (ev) => {
      if (S.pan) { S.tx = ev.clientX - S.pan.x; S.ty = ev.clientY - S.pan.y; return applyView(); }
      if (S.i < 0) return;
      const p = toPx(ev), f = FIGS[S.i];
      if (S.drag) { S.drag.x1 = Math.max(0, Math.min(f.width, p.x)); S.drag.y1 = Math.max(0, Math.min(f.height, p.y)); return drawOverlay(); }
      if (!stage.contains(ev.target)) return;
      let txt = `x ${p.x.toFixed(1)} · y ${p.y.toFixed(1)} px`;
      const hit = panelAt(p), pi = hit >= 0 ? hit : S.panel;
      for (const ax of ["x", "y"]) {
        const m = mapOf(pi, ax);
        if (m) txt += ` · ${ax} = ${m.cat ? m.toVal(p[ax]) : roundStep(m.toVal(p[ax]), m.step)}`;
      }
      const w = wordAt(p);
      $("readout").textContent = txt + (w ? ` · “${w.text}”` : "");
    });
    window.addEventListener("mouseup", () => {
      if (S.pan) { S.pan = null; stageClass(); }
      if (!S.drag) return;
      const d = S.drag, f = FIGS[S.i], snap = 6 / S.z;
      S.drag = null;
      const b = [Math.min(d.x0, d.x1), Math.min(d.y0, d.y1), Math.max(d.x0, d.x1), Math.max(d.y0, d.y1)].map((v) => Math.round(v));
      if (b[0] < snap) b[0] = 0;
      if (b[1] < snap) b[1] = 0;
      if (f.width - b[2] < snap) b[2] = f.width;
      if (f.height - b[3] < snap) b[3] = f.height;
      if (b[2] - b[0] < 4 || b[3] - b[1] < 4) return drawOverlay();
      addPanel(b);
    });
    stage.addEventListener("wheel", (ev) => {
      if (S.i < 0) return;
      ev.preventDefault();
      const r = stage.getBoundingClientRect();
      zoomAt(Math.exp(-ev.deltaY * 0.0015), ev.clientX - r.left, ev.clientY - r.top);
    }, { passive: false });

    $("form").addEventListener("focusin", (ev) => { if (isField(ev.target) && ev.target.tagName !== "SELECT") S.lastField = ev.target; });
    $("form").addEventListener("keydown", gridKey);
    document.querySelectorAll("[data-tool]").forEach((b) => b.addEventListener("click", () => setTool(b.dataset.tool)));
    ["show-docling", "show-pdf"].forEach((id) => $(id).addEventListener("change", drawOverlay));
    $("show-hires").addEventListener("change", () => { if (S.i >= 0) { const f = FIGS[S.i]; $("img").src = ($("show-hires").checked && f.image_hires) || f.image; } });
    $("img").addEventListener("error", () => {
      const f = FIGS[S.i];
      if (f && f.image_hires && decodeURI($("img").src).endsWith(f.image_hires)) $("img").src = f.image;
      else flash("Figure image not found: keep the figures/ folder next to index.html.");
    });
    $("zoom-in").addEventListener("click", () => zoomCentre(1.25));
    $("zoom-out").addEventListener("click", () => zoomCentre(0.8));
    $("zoom-fit").addEventListener("click", fit);
    $("zoom-1").addEventListener("click", () => zoomCentre(1 / S.z));
    $("done").addEventListener("change", (e) => { if (S.i >= 0) { cur().done = e.target.checked; saveNow(); } });
    $("labeler-name").value = recall("figlabel/name") || "";
    $("labeler-name").addEventListener("input", (e) => { store("figlabel/name", e.target.value.trim()); if (S.i >= 0) { doc().labeler.name = e.target.value.trim() || null; touch(false); } });
    $("btn-export").addEventListener("click", exportOne);
    $("btn-export-all").addEventListener("click", exportAll);
    $("btn-import").addEventListener("click", () => $("file-import").click());
    $("file-import").addEventListener("change", (e) => { importFiles([...e.target.files]); e.target.value = ""; });
    $("btn-help").addEventListener("click", () => showHelp(true));
    $("help-close").addEventListener("click", () => showHelp(false));
    $("help").addEventListener("click", (e) => { if (e.target.id === "help") showHelp(false); });

    document.addEventListener("keydown", (ev) => {
      if ((ev.ctrlKey || ev.metaKey) && ev.key.toLowerCase() === "s") { ev.preventDefault(); return exportOne(); }
      if (ev.key === "Escape") {
        if (!$("help").hidden) return showHelp(false);
        if (S.pick || S.drag) { S.pick = null; S.drag = null; stageClass(); renderForm(); drawOverlay(); } else if (isField(ev.target)) ev.target.blur(); else setTool("select");
        return;
      }
      if (isField(ev.target) || ev.ctrlKey || ev.metaKey || ev.altKey) return;
      if (ev.key === " ") { S.space = true; ev.preventDefault(); return; }
      const target = (v) => () => { $("target").value = v; flash(`Clicks now fill ${v}.`); };
      const act = {
        v: () => setTool("select"), p: () => setTool("panel"), a: () => setTool("point"), f: fit,
        w: () => { const on = !($("show-docling").checked || $("show-pdf").checked); $("show-docling").checked = on; $("show-pdf").checked = on; drawOverlay(); },
        0: () => zoomCentre(1 / S.z), "+": () => zoomCentre(1.25), "=": () => zoomCentre(1.25), "-": () => zoomCentre(0.8),
        "[": () => openFig(S.i - 1), "]": () => openFig(S.i + 1), 1: target("value"), 2: target("err_lo"), 3: target("err_hi"),
        d: () => { if (S.i >= 0) { $("done").checked = !$("done").checked; $("done").dispatchEvent(new Event("change")); } },
        "?": () => showHelp(true), h: () => showHelp(true),
        Delete: () => { if (panel()) deletePanel(S.panel); }, Backspace: () => { if (panel()) deletePanel(S.panel); },
      }[ev.key.length === 1 ? ev.key.toLowerCase() : ev.key];
      if (act && (S.i >= 0 || "?h".includes(ev.key))) { ev.preventDefault(); act(); }
    });
    document.addEventListener("keyup", (ev) => { if (ev.key === " ") S.space = false; });
    ["mousemove", "keydown", "wheel", "mousedown"].forEach((t) => window.addEventListener(t, () => { S.activeAt = Date.now(); }, { passive: true }));
    window.addEventListener("beforeunload", saveNow);
    window.addEventListener("resize", () => { if (S.i >= 0) drawOverlay(); });
    setInterval(() => {
      if (S.i < 0 || document.hidden || !document.hasFocus() || Date.now() - S.activeAt > 120000) return;
      const st = cur();
      st.ms += 1000;
      $("timer").textContent = `${minutes(st.ms).toFixed(1)} min`;
      if (st.ms % 15000 === 0) saveNow();
    }, 1000);
  }

  function boot() {
    wire();
    if (!M) {
      showEmpty("<h2>No figures loaded</h2><p><code>manifest.js</code> is missing next to <code>index.html</code>. This page is the labelling app of a pack folder made by <code>tools/figure-labeler/pack.py</code>; open <code>index.html</code> inside such a folder.</p>");
      return;
    }
    if (!FIGS.length) { showEmpty("<h2>This pack has no figures</h2><p>Re-run <code>pack.py</code> with other bundles, <code>--types</code> or <code>--refs</code>.</p>"); return; }
    renderList();
    const last = FIGS.findIndex((f) => f.id === recall("figlabel/last"));
    const firstTodo = FIGS.findIndex((_, i) => statusOf(i) !== "done");
    setTool("select");
    openFig(last >= 0 ? last : Math.max(0, firstTodo));
    if (!recall("figlabel/seen-help")) { showHelp(true); store("figlabel/seen-help", true); }
  }
  boot();
})(window);
