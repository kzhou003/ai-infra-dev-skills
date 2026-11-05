/* ai-infra-dev-skills · shared page behaviour. Pure DOM, no dependencies, works from file:// and in print. */
(function () {
  "use strict";
  var NS = "http://www.w3.org/2000/svg";
  var BODY = document.body || document.documentElement;
  var KEY = (BODY.getAttribute && BODY.getAttribute("data-store")) || "aids";
  var store = {
    get: function (k, d) { try { var v = localStorage.getItem(KEY + ":" + k); return v === null ? d : JSON.parse(v); } catch (e) { return d; } },
    set: function (k, v) { try { localStorage.setItem(KEY + ":" + k, JSON.stringify(v)); } catch (e) {} }
  };
  var PRINT = /[?&]print\b/.test(location.search) || window.__PRINT__;
  function each(sel, fn, root) { Array.prototype.forEach.call((root || document).querySelectorAll(sel), fn); }

  // ------------------------------------------------------------------ theme
  function applyTheme(t) { if (t) document.documentElement.setAttribute("data-theme", t); else document.documentElement.removeAttribute("data-theme"); }
  applyTheme(PRINT ? "light" : store.get("theme", null));
  function initTheme() {
    var b = document.getElementById("theme-btn"); if (!b) return;
    b.addEventListener("click", function () {
      var cur = document.documentElement.getAttribute("data-theme");
      var dark = cur ? cur === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
      applyTheme(dark ? "light" : "dark"); store.set("theme", dark ? "light" : "dark");
    });
  }

  // ------------------------------------------------------------------ flow diagrams (React-Flow style, static SVG)
  function el(tag, attrs, parent) { var e = document.createElementNS(NS, tag); for (var k in attrs) e.setAttribute(k, attrs[k]); if (parent) parent.appendChild(e); return e; }
  function txt(parent, x, y, s, cls, anchor) { var t = el("text", { x: x, y: y, "class": cls, "text-anchor": anchor || "middle" }, parent); t.textContent = s; return t; }
  function renderFlow(host, spec) {
    var cfg = spec.cfg || {}, CW = cfg.cw || 200, RH = cfg.rh || 88, NW = cfg.nw || 160, PAD = 26;
    var N = {}, maxX = 0, maxY = 0;
    spec.nodes.forEach(function (n) {
      var w = NW * n.w, h = n.s ? 52 : 38, x = PAD + n.c * CW, y = PAD + 14 + n.r * RH;
      N[n.id] = { n: n, x: x, y: y, w: w, h: h, cx: x + w / 2, cy: y + h / 2 };
      maxX = Math.max(maxX, x + w); maxY = Math.max(maxY, y + h);
    });
    var groups = (spec.groups || []).map(function (g) {
      var x0 = PAD + g.c0 * CW - 14, y0 = PAD + 14 + g.r0 * RH - 28, x1 = PAD + g.c1 * CW + NW + 14, y1 = PAD + 14 + g.r1 * RH + 52 + 14;
      maxX = Math.max(maxX, x1); maxY = Math.max(maxY, y1); return { g: g, x0: x0, y0: y0, x1: x1, y1: y1 };
    });
    var W = maxX + PAD, H = maxY + PAD;
    var svg = el("svg", { viewBox: "0 0 " + W + " " + H, width: W, role: "img", "aria-label": spec.title });
    var uid = "f" + Math.random().toString(36).slice(2, 8);
    var pat = el("pattern", { id: uid + "dot", width: 16, height: 16, patternUnits: "userSpaceOnUse" }, el("defs", {}, svg));
    el("circle", { cx: 1, cy: 1, r: 1, "class": "f-bgdot" }, pat);
    var bg = el("rect", { x: 0, y: 0, width: W, height: H, fill: "url(#" + uid + "dot)" }, svg);
    groups.forEach(function (G) {
      var gg = el("g", { "class": "f-grp" + (G.g.k ? " k-" + G.g.k : "") }, svg);
      el("rect", { x: G.x0, y: G.y0, width: G.x1 - G.x0, height: G.y1 - G.y0, rx: 10 }, gg);
      txt(gg, G.x0 + 10, G.y0 + 15, G.g.t, "", "start");
    });
    var edgeLayer = el("g", {}, svg), nodeLayer = el("g", {}, svg), topLayer = el("g", {}, svg);
    function side(A, B) {
      var dx = B.cx - A.cx, dy = B.cy - A.cy;
      if (Math.abs(dx) >= Math.abs(dy) * 0.9) return dx >= 0 ? ["r", "l"] : ["l", "r"];
      return dy >= 0 ? ["b", "t"] : ["t", "b"];
    }
    function port(P, s) { return s === "r" ? [P.x + P.w, P.cy] : s === "l" ? [P.x, P.cy] : s === "t" ? [P.cx, P.y] : [P.cx, P.y + P.h]; }
    function dir(s) { return s === "r" ? [1, 0] : s === "l" ? [-1, 0] : s === "t" ? [0, -1] : [0, 1]; }
    var nodeEdges = {};
    spec.edges.forEach(function (e) {
      var as = e.a.split(":"), bs = e.b.split(":"), A = N[as[0]], B = N[bs[0]];
      var auto = side(A, B), sa = as[1] || auto[0], sb = bs[1] || auto[1];
      var p0 = port(A, sa), p3 = port(B, sb), d0 = dir(sa), d3 = dir(sb);
      var dist = Math.hypot(p3[0] - p0[0], p3[1] - p0[1]), off = Math.max(36, Math.min(140, dist * 0.45));
      if (sa === sb) off = Math.max(off, 60);
      var p1 = [p0[0] + d0[0] * off, p0[1] + d0[1] * off], p2 = [p3[0] + d3[0] * (off + 6), p3[1] + d3[1] * (off + 6)];
      var end = [p3[0] + d3[0] * 8, p3[1] + d3[1] * 8];
      var k = e.k ? " k-" + e.k : "", eid = as[0] + ">" + bs[0];
      var path = el("path", { d: "M" + p0 + " C" + p1 + " " + p2 + " " + end, "class": "f-e" + k + (e.anim ? " anim" : "") + (e.dash ? " dash" : ""), "data-edge": eid }, edgeLayer);
      // arrowhead: tip on the target port, body outside the node, drawn above the nodes
      var bx = p3[0] + d3[0] * 9, by = p3[1] + d3[1] * 9;
      var ah = el("path", { d: "M" + p3 + " L" + (bx + d3[1] * 4.5) + "," + (by - d3[0] * 4.5) + " L" + (bx - d3[1] * 4.5) + "," + (by + d3[0] * 4.5) + " z", "class": "f-ah" + k, "data-edge": eid }, topLayer);
      var items = [path, ah];
      if (e.t) {
        var t = 0.5, mx = Math.pow(1 - t, 3) * p0[0] + 3 * Math.pow(1 - t, 2) * t * p1[0] + 3 * (1 - t) * t * t * p2[0] + t * t * t * end[0];
        var my = Math.pow(1 - t, 3) * p0[1] + 3 * Math.pow(1 - t, 2) * t * p1[1] + 3 * (1 - t) * t * t * p2[1] + t * t * t * end[1];
        var lg = el("g", { "class": "f-el", "data-edge": eid }, topLayer);
        var tw = 12; for (var ci = 0; ci < e.t.length; ci++) tw += e.t.charCodeAt(ci) > 0x2E7F ? 11.5 : 6.6; tw = Math.max(24, tw);
        var horiz = (sa === "l" || sa === "r") && (sb === "l" || sb === "r");
        var gap = horiz ? Math.abs(end[0] - p0[0]) : Math.abs(end[1] - p0[1]);
        if (horiz && tw > gap - 6) my = Math.min(p0[1], end[1]) - 15;
        else if (!horiz && sa !== sb && 20 > gap - 4) mx = Math.max(p0[0], end[0]) + tw / 2 + 8;
        el("rect", { x: mx - tw / 2, y: my - 10, width: tw, height: 18, rx: 5 }, lg);
        txt(lg, mx, my + 3.5, e.t, "");
        items.push(lg);
      }
      [as[0], bs[0]].forEach(function (id) { (nodeEdges[id] = nodeEdges[id] || []).push({ items: items, other: id === as[0] ? bs[0] : as[0] }); });
    });
    var nodeEls = {};
    spec.nodes.forEach(function (n) {
      var P = N[n.id], g = el("g", { "class": "f-node" + (n.k ? " k-" + n.k : ""), "data-node": n.id }, nodeLayer);
      el("rect", { x: P.x, y: P.y, width: P.w, height: P.h, rx: 9, "class": "f-box" }, g);
      txt(g, P.cx, P.y + (n.s ? 21 : 23.5), n.t, "f-t");
      if (n.s) txt(g, P.cx, P.y + 39, n.s, "f-s");
      [[P.x, P.cy], [P.x + P.w, P.cy], [P.cx, P.y], [P.cx, P.y + P.h]].forEach(function (h) { el("circle", { cx: h[0], cy: h[1], r: 2.6, "class": "f-handle" }, g); });
      nodeEls[n.id] = g;
      g.addEventListener("mouseenter", function () {
        if (svg.classList.contains("f-step")) return;
        svg.classList.add("f-on"); g.classList.add("hl");
        (nodeEdges[n.id] || []).forEach(function (c) { c.items.forEach(function (x) { x.classList.add("hl"); }); nodeEls[c.other].classList.add("hl"); });
      });
      g.addEventListener("mouseleave", function () {
        if (svg.classList.contains("f-step")) return;
        svg.classList.remove("f-on"); each(".hl", function (x) { x.classList.remove("hl"); }, svg);
      });
    });
    host.appendChild(svg);
    try {   // grow the canvas to whatever was drawn (loop edges can swing outside the grid)
      var bb = svg.getBBox(), x0 = Math.min(0, bb.x - 12), y0 = Math.min(0, bb.y - 12);
      var x1 = Math.max(W, bb.x + bb.width + 12), y1 = Math.max(H, bb.y + bb.height + 12);
      svg.setAttribute("viewBox", x0 + " " + y0 + " " + (x1 - x0) + " " + (y1 - y0)); svg.setAttribute("width", x1 - x0);
      bg.setAttribute("x", x0); bg.setAttribute("y", y0); bg.setAttribute("width", x1 - x0); bg.setAttribute("height", y1 - y0);
    } catch (err) {}
  }
  function initFlows() {
    each(".flow-body[data-flow]", function (h) {
      try { renderFlow(h, JSON.parse(h.getAttribute("data-flow"))); } catch (e) { h.textContent = "diagram error: " + e; }
    });
  }

  // ------------------------------------------------------------------ steppers (with flow highlighting + autoplay)
  function initStepper(root) {
    var steps = Array.prototype.slice.call(root.querySelectorAll(":scope > .st-body > .step"));
    if (!steps.length) return;
    root.classList.add("js");
    var count = root.querySelector(".st-count"), prev = root.querySelector(".st-prev"), next = root.querySelector(".st-next");
    var play = root.querySelector(".st-play"), dotsBox = root.querySelector(".st-dots"), dia = root.querySelector(".st-diagram");
    var seen = {}, cur = 0, timer = null;
    var dots = steps.map(function (s, i) {
      var b = document.createElement("button"); b.className = "st-dot"; b.type = "button"; b.textContent = String(i + 1);
      b.title = (s.querySelector(".step-title") || {}).textContent || "";
      b.addEventListener("click", function () { stop(); show(i); }); dotsBox.appendChild(b); return b;
    });
    function show(i) {
      cur = Math.max(0, Math.min(steps.length - 1, i)); seen[cur] = true;
      steps.forEach(function (s, j) { s.classList.toggle("active", j === cur); });
      dots.forEach(function (d, j) { d.classList.toggle("on", j === cur); d.classList.toggle("seen", !!seen[j]); });
      count.textContent = (cur + 1) + " / " + steps.length; prev.disabled = cur === 0; next.disabled = cur === steps.length - 1;
      if (!dia) return;
      var hl = (steps[cur].getAttribute("data-hl") || "").split(",").map(function (x) { return x.trim(); }).filter(Boolean);
      each("svg", function (svg) { svg.classList.toggle("f-step", hl.length > 0); }, dia);
      each("[data-node]", function (n) { n.classList.toggle("hl", hl.indexOf(n.getAttribute("data-node")) >= 0); }, dia);
      each("[data-edge]", function (e) { var ab = e.getAttribute("data-edge").split(">"); e.classList.toggle("hl", hl.indexOf(ab[0]) >= 0 && hl.indexOf(ab[1]) >= 0); }, dia);
    }
    function stop() { if (timer) { clearInterval(timer); timer = null; play.textContent = play.getAttribute("data-play"); } }
    play.addEventListener("click", function () {
      if (timer) { stop(); return; }
      if (cur === steps.length - 1) show(0);
      play.textContent = play.getAttribute("data-pause");
      timer = setInterval(function () { if (cur >= steps.length - 1) stop(); else show(cur + 1); }, 2600);
    });
    prev.addEventListener("click", function () { stop(); show(cur - 1); });
    next.addEventListener("click", function () { stop(); show(cur + 1); });
    root.setAttribute("tabindex", "0");
    root.addEventListener("keydown", function (e) {
      if (e.target !== root) return;
      if (e.key === "ArrowRight") { stop(); show(cur + 1); e.preventDefault(); }
      if (e.key === "ArrowLeft") { stop(); show(cur - 1); e.preventDefault(); }
    });
    show(0);
  }

  // ------------------------------------------------------------------ tabs, copy, scroll-spy, progress
  function initTabs() {
    each(".tabs", function (t) {
      var btns = t.querySelectorAll(":scope > .tab-heads > .tab-btn"), panes = t.querySelectorAll(":scope > .tab-pane");
      Array.prototype.forEach.call(btns, function (b, i) {
        b.addEventListener("click", function () {
          Array.prototype.forEach.call(btns, function (x, j) { x.classList.toggle("on", i === j); });
          Array.prototype.forEach.call(panes, function (x, j) { x.classList.toggle("on", i === j); });
        });
      });
    });
  }
  function initCopy() {
    each(".codebox .copy", function (b) {
      b.addEventListener("click", function () {
        var code = b.closest(".codebox").querySelector("code").innerText, label = b.textContent;
        var done = function () { b.textContent = BODY.getAttribute("data-copied") || "✓"; setTimeout(function () { b.textContent = label; }, 1200); };
        if (navigator.clipboard) navigator.clipboard.writeText(code).then(done, function () {}); else done();
      });
    });
  }
  function initSpy() {
    var links = Array.prototype.slice.call(document.querySelectorAll(".sidebar a[href^='#'], .outline a[href^='#']"));
    if (!links.length) return;
    var targets = links.map(function (a) { return document.getElementById(decodeURIComponent(a.getAttribute("href").slice(1))); });
    function onScroll() {
      var best = -1;
      targets.forEach(function (t, i) { if (t && t.getBoundingClientRect().top < 130) best = i; });
      var id = best >= 0 && targets[best] ? targets[best].id : null;
      links.forEach(function (a) { a.classList.toggle("cur", !!id && a.getAttribute("href") === "#" + id); });
    }
    addEventListener("scroll", onScroll, { passive: true }); onScroll();
  }
  function initProgress() {
    var done = store.get("done", {}) || {};
    var box = document.getElementById("done-box");
    if (box) {
      var id = box.getAttribute("data-id"); box.checked = !!done[id];
      box.addEventListener("change", function () { var d = store.get("done", {}) || {}; if (box.checked) d[id] = true; else delete d[id]; store.set("done", d); });
    }
    each(".sidebar a[data-id]", function (a) { a.classList.toggle("done", !!done[a.getAttribute("data-id")]); });
    var cards = document.querySelectorAll(".card[data-id]");
    if (!cards.length) return;
    function refresh() {
      var d = store.get("done", {}) || {}, n = 0, mins = 0, total = 0;
      Array.prototype.forEach.call(cards, function (c) {
        var m = +c.getAttribute("data-min") || 0, on = !!d[c.getAttribute("data-id")]; total += m;
        c.classList.toggle("done", on); var cb = c.querySelector("input.chk"); if (cb) cb.checked = on;
        if (on) { n += 1; mins += m; }
      });
      var bar = document.getElementById("prog-bar"), t = document.getElementById("prog-text");
      if (bar) bar.style.width = (100 * n / cards.length).toFixed(1) + "%";
      if (t) t.textContent = (t.getAttribute("data-fmt") || "{n} / {N} · {m} / {M} min")
        .replace("{n}", n).replace("{N}", cards.length).replace("{m}", mins).replace("{M}", total);
    }
    each("input.chk", function (cb) {
      cb.addEventListener("click", function (e) { e.stopPropagation(); });
      cb.addEventListener("change", function () {
        var d = store.get("done", {}) || {}, id = cb.closest(".card").getAttribute("data-id");
        if (cb.checked) d[id] = true; else delete d[id]; store.set("done", d); refresh();
      });
    });
    refresh();
  }

  function boot() {
    initTheme(); initFlows(); each(".stepper", initStepper); initTabs(); initCopy(); initSpy(); initProgress();
    if (window.hljs) each("pre code[class*='language-']", function (c) { try { window.hljs.highlightElement(c); } catch (e) {} });
    if (PRINT) each("details", function (d) { d.open = true; });
    document.documentElement.setAttribute("data-ready", "1");
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot); else boot();
})();
