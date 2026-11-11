/* =====================================================================
   대시보드 모바일 보정 JS
   ---------------------------------------------------------------------
   붙이는 법: body 맨 끝에 script 태그 한 줄로 이 파일을 불러옵니다.
     src="/static/dashboard_mobile.js"
   (HTML 안에 내용을 통째로 붙여 넣어도 동작하도록, 이 주석에는 닫는 script 태그를 쓰지 않았습니다)

   하는 일
   1) 폰에서 표가 옆으로 잘리지 않게, 모든 표에 m-cards 클래스와
      칸마다 data-label(머리글 글자)을 붙여 둡니다.
      → dashboard_mobile.css 가 600px 이하에서 '종목 한 장 = 카드 한 장'으로 바꿔 보여 줍니다.
      → 1초 푸시·10초 폴링으로 표가 다시 그려져도 화면에 그려지기 전에 다시 붙습니다.
      → 카드로 바꾸고 싶지 않은 표는 <table data-keep-table> 로 두면 건드리지 않습니다.
   2) utils/dash_status.py 의 Badge(JSON)를 화면에 그리는 도우미
        DashStatus.render(요소, {text, level, hint, key})
        DashStatus.pnlClass("−23,236,493원")  → "pnl-down"  (화면에 보이는 글자로 색 결정)
   ===================================================================== */
(function () {
  "use strict";

  var IDX_HEAD = /^(#|no\.?|번호|순번)$/i;
  var TITLE_EXACT = /^(종목명|종목|이름|name)$/i;
  var TITLE_LOOSE = /(종목|이름|name)/i;
  var CODE_HEAD = /(코드|code)/i;

  function cellText(c) {
    // 머리글이 화면에 보일 때 한 번 읽어 저장해 둔다.
    // (카드로 바뀐 뒤에는 thead 가 숨겨져서 innerText 가 줄바꿈 공백을 잃기 때문)
    var t = c.getAttribute("data-m-label");
    if (t === null) {
      t = (c.innerText || c.textContent || "").replace(/\s+/g, " ").trim();
      c.setAttribute("data-m-label", t);
    }
    return t;
  }

  function headerRow(table) {
    if (table.tHead && table.tHead.rows.length) return table.tHead.rows[table.tHead.rows.length - 1];
    var first = table.rows[0];
    if (first && first.querySelector("th") && !first.querySelector("td")) return first;
    return null;
  }

  function headerLabels(row) {
    var out = [];
    for (var i = 0; i < row.cells.length; i++) {
      var c = row.cells[i];
      var t = cellText(c);
      var span = c.colSpan || 1;
      for (var s = 0; s < span; s++) out.push(t);
    }
    return out;
  }

  function findTitleCol(labels) {
    var k;
    for (k = 0; k < labels.length; k++) if (TITLE_EXACT.test(labels[k])) return k;
    for (k = 0; k < labels.length; k++) if (TITLE_LOOSE.test(labels[k]) && !CODE_HEAD.test(labels[k])) return k;
    return -1;
  }

  function prepareTable(table) {
    if (table.hasAttribute("data-keep-table")) return;
    var hrow = headerRow(table);
    if (!hrow) return;
    if (!table.tHead || hrow.parentNode !== table.tHead) hrow.classList.add("m-head");
    var labels = headerLabels(hrow);
    var titleCol = findTitleCol(labels);

    var rows = table.rows; // tbody 여러 개 · tfoot · tbody 없이 붙인 행까지 전부
    for (var r = 0; r < rows.length; r++) {
      var tr = rows[r];
      if (tr === hrow || (table.tHead && tr.parentNode === table.tHead)) continue;
      var col = 0;
      for (var j = 0; j < tr.cells.length; j++) {
        var td = tr.cells[j];
        var span = td.colSpan || 1;
        var label = labels[col] || "";
        // 여러 칸을 합친 셀: 머리글이 모두 같을 때만 그 이름, 아니면 이름표 없음 ("주문 없음" 같은 안내 행)
        for (var s = 1; s < span; s++) {
          if ((labels[col + s] || "") !== label) { label = ""; break; }
        }
        if (td.getAttribute("data-label") !== label) td.setAttribute("data-label", label);
        if (span === 1 && IDX_HEAD.test(label)) td.classList.add("m-idx");
        if (span === 1 && col === titleCol) td.classList.add("m-title");
        col += span;
      }
    }
    table.classList.add("m-cards");
    var p = table.parentElement;
    if (p && p !== document.body) {
      var ov = window.getComputedStyle(p).overflowX;
      if (ov === "auto" || ov === "scroll") p.classList.add("m-cards-wrap");
    }
  }

  function scan() {
    var tables = document.querySelectorAll("table");
    for (var i = 0; i < tables.length; i++) {
      try { prepareTable(tables[i]); } catch (e) { /* 표 하나가 이상해도 나머지는 계속 */ }
    }
  }

  function start() {
    scan();
    if (window.MutationObserver) {
      // 화면에 그려지기 전에(마이크로태스크) 바로 다시 붙인다.
      // 우리가 바꾸는 것은 속성·클래스뿐이고 감시 대상은 childList 라서 무한 반복이 생기지 않는다.
      new MutationObserver(scan).observe(document.body, { childList: true, subtree: true });
    }
  }

  // ---------------- Badge 그리기 도우미 ----------------
  var LEVELS = ["ok", "info", "warn", "danger"];
  function render(el, badge) {
    if (typeof el === "string") el = document.querySelector(el);
    if (!el || !badge) return;
    var lv = LEVELS.indexOf(badge.level) >= 0 ? badge.level : "info";
    el.classList.remove("st", "st-ok", "st-info", "st-warn", "st-danger");
    el.classList.add("st", "st-" + lv);
    el.textContent = badge.text || "";
    if (badge.hint) el.title = badge.hint; else el.removeAttribute("title");
    if (badge.key) el.setAttribute("data-key", badge.key);
  }

  // 색은 '화면에 보이는 글자'로 정한다 → 글자와 색이 절대 어긋나지 않는다.
  // 숫자를 넘기면 부호만 본다(반올림하지 않음). 가능하면 서버의 pnl_class() 값을 그대로 쓰세요.
  function pnlClass(v) {
    if (typeof v === "number") return v > 0 ? "pnl-up" : v < 0 ? "pnl-down" : "pnl-zero";
    var s = String(v == null ? "" : v);
    if (!/[1-9]/.test(s)) return "pnl-zero";
    return /^\s*[-−▼]/.test(s) ? "pnl-down" : "pnl-up";
  }

  window.DashStatus = { render: render, pnlClass: pnlClass, refreshTables: scan };

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();
