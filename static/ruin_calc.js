/* =====================================================================
   파산확률 계산기 (브라우저용) — utils/ruin.py 와 똑같은 계산
   ---------------------------------------------------------------------
   3-9 켈리·파산 시뮬레이터 슬라이더, 3-5·3-8 의 파산확률 칸이 모두 이것을 쓰면
   화면끼리 숫자가 어긋나지 않습니다. 값만 쓰지 말고 반드시 조건 문장을 같이 보여 주세요.

   Ruin.report({p:0.36, b:1.724, N:20, T:430, source:"실제 매매"})
     → { headline:"55.7%", condition:"[실제 매매] 승률 36.0% · …", verdict:"…", ... }
   ===================================================================== */
(function (g) {
  "use strict";

  function edge(p, b) { return p * b - (1 - p); }
  function kelly(p, b) { return p - (1 - p) / b; }

  function root(p, b) {
    if (edge(p, b) <= 0) return 1;                    // 기대값 0 이하 → 근 없음 → 반드시 파산
    var lo = 1e-12, hi = 1 - 1e-12;
    for (var i = 0; i < 200; i++) {
      var m = (lo + hi) / 2;
      if (p * Math.pow(m, b) + (1 - p) / m - 1 > 0) lo = m; else hi = m;
    }
    return (lo + hi) / 2;
  }

  // 끝없이 매매할 때
  function formula(p, b, N) { return Math.pow(root(p, b), N); }

  // T번 매매하는 동안 (시드 고정 난수 → 새로고침해도 같은 값)
  function monteCarlo(p, b, N, T, runs, seed) {
    runs = runs || 20000;
    var s = (seed == null ? 12345 : seed) >>> 0;
    function rnd() { s = (s + 0x6D2B79F5) >>> 0; var t = s; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }
    var hit = 0;
    for (var r = 0; r < runs; r++) {
      var cap = N;
      for (var k = 0; k < T; k++) { cap += rnd() < p ? b : -1; if (cap <= 0) { hit++; break; } }
    }
    return hit / runs;
  }

  function fmt(x) {
    var v = x * 100;
    if (v === 0) return "0%";
    if (v >= 1) return v.toFixed(1) + "%";
    var d = -Math.floor(Math.log10(v)) + 1;
    return v.toFixed(d).replace(/0+$/, "").replace(/\.$/, "") + "%";
  }

  function report(o) {
    var p = o.p, b = o.b, N = o.N, T = o.T || null, src = o.source || "실제 매매";
    var e = edge(p, b), inf = formula(p, b, N), fin = T ? monteCarlo(p, b, N, T, o.runs) : null;
    var cond = "[" + src + "] 승률 " + (p * 100).toFixed(1) + "% · 손익비 " + b.toFixed(2) +
      " · 1회 손실 = 자본의 " + (100 / N).toFixed(1) + "%(자본 " + N + "칸)" + (T ? " · " + T + "번 매매하는 동안" : " · 끝없이 계속할 때");
    var verdict = e <= 0
      ? "한 번 매매의 기대값이 " + e.toFixed(3) + "칸(마이너스)이라 계속하면 언젠가 반드시 파산합니다. 본전 승률 " +
        (100 / (1 + b)).toFixed(1) + "% 또는 본전 손익비 " + ((1 - p) / p).toFixed(2) + " 이상이 필요합니다."
      : "기대값 +" + e.toFixed(3) + "칸(플러스). 끝없이 해도 파산할 확률은 " + fmt(inf) + "입니다.";
    return { p: p, b: b, N: N, T: T, edge: e, kelly: kelly(p, b), ruinInfinite: inf, ruinFinite: fin,
      headline: fmt(fin != null ? fin : inf), condition: cond, verdict: verdict };
  }

  g.Ruin = { edge: edge, kelly: kelly, formula: formula, monteCarlo: monteCarlo, report: report, fmt: fmt };
  if (typeof module !== "undefined") module.exports = g.Ruin;
})(typeof window !== "undefined" ? window : globalThis);
