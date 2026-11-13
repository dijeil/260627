/* =====================================================================
   HtsChart — lightweight-charts 를 증권사 HTS 차트처럼 쓰게 해 주는 도구
   ---------------------------------------------------------------------
   lightweight-charts 4.x / 5.x 둘 다 동작합니다. (먼저 라이브러리를 불러온 뒤 이 파일)

   한 줄 요약
     var chart = HtsChart.create(상자);              // 한국식 색·날짜·원 단위·자동 크기
     var c = HtsChart.candles(chart, 일봉);          // 캔들
     HtsChart.legend(chart, 범례상자, {candle:c, ...}); // 십자선 위치의 시고저종·등락률·지표값
     HtsChart.keyboard(chart, 상자);                  // ← → 한 봉 이동, + - 확대, Home 최신
     HtsChart.sync([위차트, 아래차트]);               // 보조지표 차트와 십자선·스크롤 맞춤

   일봉 데이터 형식: [{time:"2026-11-13", open, high, low, close, volume}, ...] (날짜 오름차순)
   ===================================================================== */
(function (global) {
  "use strict";
  var LC = global.LightweightCharts;
  if (!LC) { console.error("[HtsChart] lightweight-charts 를 먼저 불러오세요."); return; }

  var V5 = typeof LC.CandlestickSeries !== "undefined";   // 5.x 에는 시리즈 정의 객체가 있다
  var UP = "#e8443a", DOWN = "#2f7de1";                    // 한국식: 상승 빨강, 하락 파랑

  function won(p) { return p == null || !isFinite(p) ? "-" : Math.round(p).toLocaleString("ko-KR"); }
  function pct(p) { return (p > 0 ? "+" : "") + p.toFixed(2) + "%"; }
  function vol(v) {
    if (v == null) return "-";
    if (v >= 1e8) return (v / 1e8).toFixed(2) + "억";
    if (v >= 1e4) return (v / 1e4).toFixed(1) + "만";
    return Math.round(v).toLocaleString("ko-KR");
  }
  function timeKey(t) {
    if (t == null) return "";
    if (typeof t === "object") return t.year + "-" + ("0" + t.month).slice(-2) + "-" + ("0" + t.day).slice(-2);
    if (typeof t === "number") { var d = new Date(t * 1000); return d.toISOString().slice(0, 10) + (t % 86400 ? " " + d.toISOString().slice(11, 16) : ""); }
    return String(t);
  }
  var DAYS = ["일", "월", "화", "수", "목", "금", "토"];
  function dateLabel(t) {
    var k = timeKey(t), d = new Date(k.slice(0, 10) + "T00:00:00");
    return isNaN(d) ? k : k + " (" + DAYS[d.getDay()] + ")";
  }

  /* ---------- 1) 차트 만들기: 한국식 기본값 + 자동 크기(십자선 어긋남 방지) ---------- */
  function create(el, extra) {
    var opts = {
      autoSize: true,                                   // ★ 상자 크기가 바뀌어도 마우스 좌표가 맞게 유지
      layout: { background: { type: "solid", color: "#131722" }, textColor: "#c9d1d9", fontSize: 12 },
      grid: { vertLines: { color: "#1f2633" }, horzLines: { color: "#1f2633" } },
      crosshair: {
        mode: LC.CrosshairMode.Normal,                  // 자석 모드는 HtsChart.magnet(chart, true)
        vertLine: { labelBackgroundColor: "#3a4252" },
        horzLine: { labelBackgroundColor: "#3a4252" }
      },
      rightPriceScale: { borderColor: "#2a3140", scaleMargins: { top: 0.08, bottom: 0.25 } },
      timeScale: { borderColor: "#2a3140", rightOffset: 5, barSpacing: 8, minBarSpacing: 2 },
      localization: {
        locale: "ko-KR",
        priceFormatter: won,                            // 가격축·십자선 가격표: 52,300
        timeFormatter: function (t) { return dateLabel(t); } // 십자선 날짜표: 2026-11-02 (월)  ← "02 11월 '26" 대신
      }
    };
    return LC.createChart(el, merge(opts, extra || {}));
  }

  // autoSize 를 못 쓰는 경우: 상자 크기를 직접 따라가게 한다
  function fit(chart, el) {
    var ro = new ResizeObserver(function () {
      var r = el.getBoundingClientRect();
      if (r.width > 0 && r.height > 0) chart.resize(Math.floor(el.clientWidth), Math.floor(el.clientHeight));
    });
    ro.observe(el);
    return function () { ro.disconnect(); };
  }

  function merge(a, b) {
    Object.keys(b).forEach(function (k) {
      if (b[k] && typeof b[k] === "object" && !Array.isArray(b[k]) && a[k] && typeof a[k] === "object") merge(a[k], b[k]);
      else a[k] = b[k];
    });
    return a;
  }

  /* ---------- 2) 시리즈 추가 (4.x / 5.x 공통) ---------- */
  function add(chart, kind, opts, pane) {
    if (V5) return chart.addSeries(LC[kind + "Series"], opts, pane || 0);
    return chart["add" + kind + "Series"](opts);
  }

  function candles(chart, data, opts) {
    var s = add(chart, "Candlestick", merge({
      upColor: UP, downColor: DOWN, borderUpColor: UP, borderDownColor: DOWN, wickUpColor: UP, wickDownColor: DOWN,
      priceFormat: { type: "price", precision: 0, minMove: 1 }
    }, opts || {}));
    s.setData(data.map(function (d) { return { time: d.time, open: d.open, high: d.high, low: d.low, close: d.close }; }));
    s._hts = data;
    chart._htsLen = data.length;
    return s;
  }

  // 거래량: 같은 차트 아래쪽 25% (5.x 에서 pane 을 주면 따로 칸을 만든다)
  function volume(chart, data, pane) {
    var s = add(chart, "Histogram", { priceFormat: { type: "volume" }, priceScaleId: pane ? "right" : "vol", lastValueVisible: false, priceLineVisible: false }, pane);
    if (!pane) chart.priceScale("vol").applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } });
    s.setData(data.map(function (d, i) {
      var up = i === 0 ? d.close >= d.open : d.close >= data[i - 1].close;
      return { time: d.time, value: d.volume || 0, color: up ? "rgba(232,68,58,.45)" : "rgba(47,125,225,.45)" };
    }));
    return s;
  }

  function line(chart, points, color, title, pane, extra) {
    var s = add(chart, "Line", merge({ color: color, lineWidth: 1, title: "", lastValueVisible: false, priceLineVisible: false,
      crosshairMarkerVisible: false }, extra || {}), pane);
    s.setData(points);
    s._htsTitle = title;
    s._htsColor = color;
    return s;
  }

  /* ---------- 3) 지표 계산 ---------- */
  function sma(data, n) {
    var out = [], sum = 0;
    for (var i = 0; i < data.length; i++) {
      sum += data[i].close;
      if (i >= n) sum -= data[i - n].close;
      if (i >= n - 1) out.push({ time: data[i].time, value: sum / n });
    }
    return out;
  }
  function bollinger(data, n, k) {
    n = n || 20; k = k || 2;
    var up = [], mid = [], dn = [];
    for (var i = n - 1; i < data.length; i++) {
      var m = 0, v = 0, j;
      for (j = i - n + 1; j <= i; j++) m += data[j].close;
      m /= n;
      for (j = i - n + 1; j <= i; j++) v += Math.pow(data[j].close - m, 2);
      var sd = Math.sqrt(v / n);
      up.push({ time: data[i].time, value: m + k * sd });
      mid.push({ time: data[i].time, value: m });
      dn.push({ time: data[i].time, value: m - k * sd });
    }
    return { upper: up, middle: mid, lower: dn };
  }
  function rsi(data, n) {
    n = n || 14;
    var out = [], g = 0, l = 0;
    for (var i = 1; i < data.length; i++) {
      var ch = data[i].close - data[i - 1].close, gu = Math.max(ch, 0), lo = Math.max(-ch, 0);
      if (i <= n) { g += gu; l += lo; if (i === n) { g /= n; l /= n; } else continue; }
      else { g = (g * (n - 1) + gu) / n; l = (l * (n - 1) + lo) / n; }
      out.push({ time: data[i].time, value: l === 0 ? 100 : 100 - 100 / (1 + g / l) });
    }
    return out;
  }

  /* ---------- 4) 매수·매도 표시, 평단가·손절가 가로선 ---------- */
  function markers(series, list) {
    var m = list.map(function (x) {
      var buy = x.side === "매수" || x.side === "buy";
      return { time: x.time, position: buy ? "belowBar" : "aboveBar", color: buy ? UP : DOWN,
        shape: buy ? "arrowUp" : "arrowDown", text: (buy ? "매수" : "매도") + (x.qty ? " " + x.qty : "") };
    }).sort(function (a, b) { return timeKey(a.time) < timeKey(b.time) ? -1 : 1; });
    if (V5 && LC.createSeriesMarkers) return LC.createSeriesMarkers(series, m);
    series.setMarkers(m);
    return series;
  }
  function priceLine(series, price, title, color) {
    return series.createPriceLine({ price: price, color: color || "#f5c542", lineWidth: 1, lineStyle: LC.LineStyle.Dashed,
      axisLabelVisible: true, title: title || "" });
  }

  /* ---------- 5) 범례(데이터 창): 십자선이 가리키는 봉의 값을 그대로 보여 줌 ---------- */
  // 사진 속 "커서와 지표가 따로 노는" 문제를 눈으로도 확인할 수 있게, 값은 반드시 같은 time 으로 찾는다.
  function legend(chart, box, cfg) {
    var data = cfg.candle._hts || [], byTime = {};
    data.forEach(function (d, i) { byTime[timeKey(d.time)] = i; });
    var lines = cfg.lines || [];

    function render(i, seriesData) {
      if (i == null || !data[i]) return;
      var d = data[i], prev = data[i - 1], base = prev ? prev.close : d.open;
      var chg = d.close - base, c = chg > 0 ? UP : chg < 0 ? DOWN : "#c9d1d9";
      var html = '<b>' + (cfg.title || "") + '</b> <span style="opacity:.7">' + dateLabel(d.time) + '</span><br>' +
        '시 <b>' + won(d.open) + '</b> 고 <b style="color:' + UP + '">' + won(d.high) + '</b> 저 <b style="color:' + DOWN + '">' + won(d.low) +
        '</b> 종 <b style="color:' + c + '">' + won(d.close) + '</b> <span style="color:' + c + '">' + (chg > 0 ? "▲" : chg < 0 ? "▼" : "") +
        won(Math.abs(chg)) + ' (' + pct(base ? chg / base * 100 : 0) + ')</span>' +
        (d.volume != null ? ' &nbsp;거래량 <b>' + vol(d.volume) + '</b>' : '');
      if (lines.length) {
        html += '<br>' + lines.map(function (s) {
          var p = seriesData && seriesData.get ? seriesData.get(s) : null;
          var v = p && p.value != null ? p.value : lastValueAt(s, d.time);
          return '<span style="color:' + s._htsColor + '">' + s._htsTitle + ' ' + won(v) + '</span>';
        }).join(' &nbsp;');
      }
      box.innerHTML = html;
    }
    function lastValueAt(s, t) {
      if (!s._htsIndex) { s._htsIndex = {}; (s.data ? s.data() : []).forEach(function (p) { s._htsIndex[timeKey(p.time)] = p.value; }); }
      return s._htsIndex[timeKey(t)];
    }

    chart.subscribeCrosshairMove(function (param) {
      var i = param && param.time != null ? byTime[timeKey(param.time)] : null;
      render(i == null ? data.length - 1 : i, i == null ? null : param.seriesData);  // 차트 밖이면 마지막 봉
    });
    render(data.length - 1, null);
  }

  /* ---------- 6) 자석 모드: 십자선 가로줄이 종가에 딱 붙음 ---------- */
  function magnet(chart, on) {
    var M = LC.CrosshairMode;
    chart.applyOptions({ crosshair: { mode: on ? (M.MagnetOHLC != null ? M.MagnetOHLC : M.Magnet) : M.Normal } });
  }

  /* ---------- 7) 여러 차트(가격 / 거래량 / RSI ...) 스크롤·확대·십자선 맞추기 ---------- */
  // charts: [{chart, series}] — series 는 그 차트의 아무 시리즈 하나 (십자선을 올릴 기준)
  function sync(list) {
    var busy = false;
    list.forEach(function (a) {
      a.chart.timeScale().subscribeVisibleLogicalRangeChange(function (r) {
        if (busy || !r) return; busy = true;
        list.forEach(function (b) { if (b !== a) b.chart.timeScale().setVisibleLogicalRange(r); });
        busy = false;
      });
      a.chart.subscribeCrosshairMove(function (param) {
        if (busy) return; busy = true;
        list.forEach(function (b) {
          if (b === a || !b.chart.setCrosshairPosition) return;
          if (param.time == null) { b.chart.clearCrosshairPosition(); return; }
          var p = param.seriesData.get(a.series), price = p ? (p.close != null ? p.close : p.value) : 0;
          var own = b.series.data ? b.series.data().filter(function (x) { return timeKey(x.time) === timeKey(param.time); })[0] : null;
          b.chart.setCrosshairPosition(own ? (own.close != null ? own.close : own.value) : price, param.time, b.series);
        });
        busy = false;
      });
    });
  }

  /* ---------- 8) 키보드·더블클릭: HTS 처럼 손에 붙는 조작 ---------- */
  function keyboard(chart, el) {
    el.tabIndex = el.tabIndex >= 0 ? el.tabIndex : 0;      // 차트를 클릭하면 키보드가 먹도록
    el.style.outline = "none";
    el.addEventListener("keydown", function (e) {
      var ts = chart.timeScale(), r = ts.getVisibleLogicalRange();
      if (!r) return;
      var w = r.to - r.from;
      if (e.key === "ArrowLeft") ts.setVisibleLogicalRange({ from: r.from - 1, to: r.to - 1 });
      else if (e.key === "ArrowRight") ts.setVisibleLogicalRange({ from: r.from + 1, to: r.to + 1 });
      else if (e.key === "+" || e.key === "=" || e.key === "ArrowUp") ts.setVisibleLogicalRange({ from: r.from + w * 0.1, to: r.to - w * 0.1 });
      else if (e.key === "-" || e.key === "ArrowDown") ts.setVisibleLogicalRange({ from: r.from - w * 0.1, to: r.to + w * 0.1 });
      else if (e.key === "Home" || e.key === "End") ts.scrollToRealTime();
      else return;
      e.preventDefault();
    });
    el.addEventListener("dblclick", function () { chart.timeScale().resetTimeScale(); chart.priceScale("right").applyOptions({ autoScale: true }); });
  }

  // 기간 버튼: showLast(chart, 60) → 최근 60봉만 보이게
  function showLast(chart, count) {
    var ts = chart.timeScale(), n = (chart._htsLen || 0);
    if (!n) { ts.fitContent(); return; }
    ts.setVisibleLogicalRange({ from: n - count, to: n + 3 });
  }

  global.HtsChart = {
    create: create, fit: fit, candles: candles, volume: volume, line: line,
    sma: sma, bollinger: bollinger, rsi: rsi, markers: markers, priceLine: priceLine,
    legend: legend, magnet: magnet, sync: sync, keyboard: keyboard, showLast: showLast,
    format: { won: won, pct: pct, vol: vol, date: dateLabel }, colors: { up: UP, down: DOWN }, isV5: V5
  };
})(window);
