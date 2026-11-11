/* =====================================================================
   대시보드 모바일 보정 JS
   ---------------------------------------------------------------------
   붙이는 법: </body> 바로 위에 한 줄
     <script src="/static/dashboard_mobile.js"></script>

   하는 일
   1) 폰에서 표가 옆으로 잘리지 않게, 모든 표에 m-cards 클래스와
      칸마다 data-label(머리글 글자)을 붙여 둡니다.
      → dashboard_mobile.css 가 600px 이하에서 '종목 한 장 = 카드 한 장'으로 바꿔 보여 줍니다.
      → 1초 푸시·10초 폴링으로 표가 다시 그려져도 자동으로 다시 붙습니다.
      → 카드로 바꾸고 싶지 않은 표는 <table data-keep-table> 로 두면 건드리지 않습니다.
   2) utils/dash_status.py 의 Badge(JSON)를 화면에 그리는 도우미
        DashStatus.render(요소, {text, level, hint, key})
   ===================================================================== */
(function () {
  "use strict";

  var IDX_HEAD = /^(#|no\.?|번호|순번)$/i;
  var TITLE_HEAD = /(종목|종목명|이름|name)/i;

  function headerTexts(table) {
    var row = table.tHead && table.tHead.rows[0];
    if (!row) {
      var first = table.rows[0];
      if (first && first.querySelector("th") && !first.querySelector("td")) row = first;
    }
    if (!row) return null;
    var out = [];
    for (var i = 0; i < row.cells.length; i++) {
      var c = row.cells[i];
      var t = (c.innerText || c.textContent || "").replace(/\s+/g, " ").trim();
      var span = c.colSpan || 1;
      for (var s = 0; s < span; s++) out.push(t);
    }
    return { row: row, labels: out };
  }

  function prepareTable(table) {
    if (table.hasAttribute("data-keep-table")) return;
    var h = headerTexts(table);
    if (!h) return;
    var titleCol = -1;
    for (var k = 0; k < h.labels.length; k++) {
      if (TITLE_HEAD.test(h.labels[k])) { titleCol = k; break; }
    }
    var rows = table.tBodies.length ? table.tBodies[0].rows : table.rows;
    for (var r = 0; r < rows.length; r++) {
      var tr = rows[r];
      if (tr === h.row) continue;
      var col = 0;
      for (var j = 0; j < tr.cells.length; j++) {
        var td = tr.cells[j];
        var label = h.labels[col] || "";
        if (td.getAttribute("data-label") !== label) td.setAttribute("data-label", label);
        if (IDX_HEAD.test(label)) td.classList.add("m-idx");
        if (col === titleCol) td.classList.add("m-title");
        col += td.colSpan || 1;
      }
    }
    table.classList.add("m-cards");
    var p = table.parentElement;
    if (p && p !== document.body) {
      var ov = window.getComputedStyle(p).overflowX;
      if (ov === "auto" || ov === "scroll") p.classList.add("m-cards-wrap");
    }
  }

  var pending = false;
  function scan() {
    pending = false;
    var tables = document.querySelectorAll("table");
    for (var i = 0; i < tables.length; i++) {
      try { prepareTable(tables[i]); } catch (e) { /* 표 하나가 이상해도 나머지는 계속 */ }
    }
  }
  function schedule() {
    if (pending) return;
    pending = true;
    (window.requestAnimationFrame || window.setTimeout)(scan, 16);
  }

  function start() {
    scan();
    if (window.MutationObserver) {
      // 우리가 붙이는 data-label/class 변화는 감시하지 않으므로(childList 만) 무한 반복이 없습니다.
      new MutationObserver(schedule).observe(document.body, { childList: true, subtree: true });
    }
  }

  // ---------------- Badge 그리기 도우미 ----------------
  var LEVELS = { ok: 1, info: 1, warn: 1, danger: 1 };
  function render(el, badge) {
    if (typeof el === "string") el = document.querySelector(el);
    if (!el || !badge) return;
    var lv = LEVELS[badge.level] ? badge.level : "info";
    el.className = el.className.replace(/\bst(-\w+)?\b/g, "").trim() + " st st-" + lv;
    el.textContent = badge.text || "";
    if (badge.hint) el.title = badge.hint; else el.removeAttribute("title");
    if (badge.key) el.setAttribute("data-key", badge.key);
  }
  function pnlClass(v, decimals) {
    var d = Math.pow(10, decimals || 0);
    var r = Math.round(Number(v || 0) * d) / d;
    return r > 0 ? "pnl-up" : r < 0 ? "pnl-down" : "pnl-zero";
  }

  window.DashStatus = { render: render, pnlClass: pnlClass, refreshTables: scan };

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();
