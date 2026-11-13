/* =====================================================================
   캔들차트 십자선 어긋남 진단기  (붙여 넣기 한 번으로 원인 확인)
   ---------------------------------------------------------------------
   증상: 마우스 커서 위치와 점선 십자선(크로스헤어)·지표 점이 서로 다른 곳에 있음.

   쓰는 법
     1) 대시보드에서 차트가 보이는 상태로 F12 → Console(콘솔) 탭
     2) 이 파일 내용을 통째로 붙여 넣고 Enter
     3) 화면에 뜨는 안내창 + 콘솔 표에 "원인"과 "고치는 법"이 나옵니다.
   (대시보드에 <script src="/static/chart_check.js"> 로 넣어 두면 주소 끝에
    ?chartcheck 를 붙였을 때만 자동으로 실행됩니다.)

   찾아 주는 원인 3가지
     A) CSS zoom      : html/body/상위 상자에 zoom 이 걸려 있음 (가장 흔함)
     B) transform     : 상위 상자에 transform: scale(...) 이 걸려 있음
     C) 늘어난 캔버스  : 차트를 만든 뒤 상자 크기가 바뀌었는데 차트가 모름
                        (CSS 로 canvas 를 width:100% 로 늘리면 그림만 늘어나고
                         마우스 좌표는 그대로 → 오른쪽으로 갈수록 더 어긋남)
   ===================================================================== */
(function () {
  "use strict";

  function num(v, d) { var n = parseFloat(v); return isFinite(n) ? n : d; }

  function scaleOfTransform(t) {
    if (!t || t === "none") return 1;
    var m = t.match(/matrix\(([^)]+)\)/);
    if (m) { var p = m[1].split(",").map(Number); return Math.sqrt(p[0] * p[0] + p[1] * p[1]); }
    var m3 = t.match(/matrix3d\(([^)]+)\)/);
    if (m3) { var q = m3[1].split(",").map(Number); return Math.sqrt(q[0] * q[0] + q[1] * q[1] + q[2] * q[2]); }
    return 1;
  }

  function label(el) {
    if (!el || !el.tagName) return "?";
    var s = el.tagName.toLowerCase();
    if (el.id) s += "#" + el.id;
    if (el.classList && el.classList.length) s += "." + Array.prototype.slice.call(el.classList, 0, 2).join(".");
    return s;
  }

  function findCharts() {
    // lightweight-charts 는 .tv-lightweight-charts 상자를 만든다. 없으면 큰 canvas 를 차트로 본다.
    var roots = Array.prototype.slice.call(document.querySelectorAll(".tv-lightweight-charts"));
    if (roots.length) return roots;
    return Array.prototype.slice.call(document.querySelectorAll("canvas")).filter(function (c) {
      var r = c.getBoundingClientRect(); return r.width > 200 && r.height > 100;
    });
  }

  function check() {
    var problems = [];
    var charts = findCharts();
    if (!charts.length) {
      problems.push({ 원인: "차트 없음", 위치: "-", 내용: "화면에서 차트를 찾지 못했습니다. 차트가 보이는 상태에서 다시 실행하세요.", 고치는법: "-" });
    }

    var seen = new Set();
    charts.forEach(function (root, idx) {
      var name = "차트" + (idx + 1);

      // A, B) 상위 상자들의 zoom / transform (서로 상쇄되어 전체 배율이 1이면 문제 아님)
      var found = [], total = 1;
      for (var el = root; el && el.nodeType === 1; el = el.parentElement) {
        var cs = getComputedStyle(el);
        var z = num(cs.zoom, 1), s = scaleOfTransform(cs.transform);
        if (z !== 1) { total *= z; found.push({ el: el, kind: "zoom", v: z }); }
        if (Math.abs(s - 1) > 0.001) { total *= s; found.push({ el: el, kind: "transform", v: s }); }
      }
      if (Math.abs(total - 1) > 0.005) {
        found.forEach(function (f) {
          if (seen.has(f.el)) return;
          seen.add(f.el);
          if (f.kind === "zoom") problems.push({
            원인: "A) CSS zoom " + f.v, 위치: label(f.el), 내용: name + " 위쪽 상자에 zoom 이 걸려 있어 마우스 좌표가 " + f.v + "배로 어긋납니다.",
            고치는법: "zoom 을 지우고 글자 크기(font-size)로 키우세요. 꼭 둬야 하면 차트 상자에 zoom:" + (1 / total).toFixed(4) + " 을 주어 되돌리세요."
          });
          else problems.push({
            원인: "B) transform 배율 " + f.v.toFixed(3), 위치: label(f.el), 내용: name + " 위쪽 상자가 transform 으로 확대·축소되어 있습니다.",
            고치는법: "차트를 감싸는 상자에서 transform: scale(...) 을 빼세요(애니메이션이면 끝난 뒤 transform:none)."
          });
        });
      }

      // C) 캔버스가 CSS 로 늘어났는지: 차트가 알고 있는 크기(style 픽셀) vs 실제 화면 크기
      var canvases = root.tagName === "CANVAS" ? [root] : Array.prototype.slice.call(root.querySelectorAll("canvas"));
      canvases.forEach(function (c) {
        var set = num(c.style.width, NaN);
        if (!isFinite(set) || set < 50) return;
        var shown = c.getBoundingClientRect().width;
        // zoom/transform 이 있으면 화면 크기도 같이 변하므로 그 비율은 빼고 본다
        var k = 1;
        for (var p = c; p && p.nodeType === 1; p = p.parentElement) {
          var pcs = getComputedStyle(p); k *= num(pcs.zoom, 1) * scaleOfTransform(pcs.transform);
        }
        // 크롬 새 zoom 방식에서는 getBoundingClientRect 가 이미 zoom 을 반영하므로 두 경우 모두 허용
        var r1 = shown / set, r2 = shown / (set * k);
        if (Math.abs(r1 - 1) > 0.02 && Math.abs(r2 - 1) > 0.02 && Math.abs(r1 - k) > 0.02) {
          if (!seen.has(root)) {
            seen.add(root);
            problems.push({
              원인: "C) 캔버스 늘어남 ×" + r1.toFixed(2), 위치: label(root),
              내용: name + " 은 폭 " + Math.round(set) + "px 로 그려졌는데 화면에는 " + Math.round(shown) + "px 로 늘어나 보입니다. 마우스가 오른쪽으로 갈수록 십자선이 더 멀어집니다.",
              고치는법: "createChart 옵션에 autoSize:true 를 주거나, chart_hts_kit.js 의 HtsChart.fit(chart, 상자) 를 쓰세요. canvas 에 width:100% 를 주는 CSS 는 지우세요."
            });
          }
        }
      });

      // C-2) 차트 폭과 감싸는 상자 폭이 다른 경우(나중에 상자가 커졌거나 작아짐)
      var host = root.parentElement;
      if (!found.length && host && root.classList && root.classList.contains("tv-lightweight-charts")) {
        var rw = root.getBoundingClientRect().width, hw = host.getBoundingClientRect().width;
        if (hw > 0 && Math.abs(rw - hw) > 4 && !seen.has(root)) {
          seen.add(root);
          problems.push({
            원인: "C) 폭 불일치", 위치: label(host),
            내용: name + " 폭 " + Math.round(rw) + "px, 감싸는 상자 폭 " + Math.round(hw) + "px. 창 크기·사이드바가 바뀐 뒤 차트가 따라가지 못했습니다.",
            고치는법: "autoSize:true 또는 HtsChart.fit(chart, 상자)."
          });
        }
      }
    });

    if (window.top !== window.self) {
      problems.push({ 원인: "참고) iframe 안", 위치: "-", 내용: "차트가 iframe 안에 있습니다. 바깥 페이지의 zoom/transform 은 여기서 볼 수 없습니다.", 고치는법: "바깥 페이지에서도 이 진단을 한 번 더 실행하세요." });
    }

    var real = problems.filter(function (p) { return /^[ABC]\)/.test(p.원인); });
    console.log("%c[차트 진단] devicePixelRatio=" + window.devicePixelRatio + ", 찾은 차트 " + charts.length + "개", "font-weight:bold");
    if (console.table) console.table(problems.length ? problems : [{ 원인: "문제 없음", 내용: "zoom·transform·크기 불일치 모두 없음. 십자선은 정상이어야 합니다." }]);

    var msg = real.length
      ? "십자선 어긋남 원인 " + real.length + "개를 찾았습니다.\n\n" + real.map(function (p, i) { return (i + 1) + ". " + p.원인 + "  [" + p.위치 + "]\n   → " + p.고치는법; }).join("\n\n")
      : (problems.length ? problems[0].내용 : "문제를 찾지 못했습니다. (zoom·transform·크기 불일치 없음)");
    try { alert(msg); } catch (e) { /* 알림창이 막힌 환경 */ }
    return problems;
  }

  window.chartCheck = check;
  var auto = !document.currentScript || /[?&]chartcheck\b/.test(location.search);
  if (auto) {
    if (document.readyState === "complete") setTimeout(check, 300);
    else window.addEventListener("load", function () { setTimeout(check, 800); });
  }
})();
