/* =====================================================================
   대시보드 쉬운 도움말 — 화면마다 [❓ 이게 뭐예요?] 버튼 + 용어 설명 풍선
   ---------------------------------------------------------------------
   붙이는 법: body 맨 끝에 한 줄
       <script src="/static/dashboard_help.js"></script>
   기존 화면 코드는 고칠 필요 없음. 제목 글자("3-5 백테스트…")와 칸 이름("파산확률")을
   찾아서 붙이므로, 1초 푸시·10초 폴링으로 화면이 다시 그려져도 자동으로 다시 붙습니다.
   새 화면 설명을 넣으려면 아래 PANELS / TERMS 에 한 줄 추가하면 됩니다.
   ===================================================================== */
(function () {
  "use strict";
  if (window.DashHelp) return;

  /* ---------- 화면별 설명 (제목 앞 번호로 찾음) ---------- */
  var PANELS = {
    "3-4": {
      t: "거래 캘린더 히트맵",
      one: "하루 = 네모 한 칸. 그날 돈을 벌었는지 잃었는지 색으로 보여 줍니다.",
      how: ["<b style='color:#e5534b'>빨강</b> = 이익 난 날, <b style='color:#4a90e2'>파랑</b> = 손실 난 날 (진할수록 금액이 큼)",
            "어두운 회색 = 거래 없던 날(주말 포함), 테두리만 있는 칸 = 오늘",
            "가로 줄 = 요일(월~일), 세로 줄 = 한 주. 오른쪽이 최근"],
      warn: "색이 진한 정도는 화면을 보고 추정한 것입니다."
    },
    "3-5": {
      t: "백테스트 성과 리포트",
      one: "지금까지의 매매 기록으로 '이 전략이 돈을 버는 구조인가'를 채점한 성적표입니다.",
      how: ["먼저 <b>승률 × 손익비</b>를 보세요. 본전 승률 = 1 ÷ (1 + 손익비). 승률이 이보다 낮으면 오래 할수록 잃는 구조",
            "예) 승률 36%, 손익비 1.724 → 본전 승률 36.7%라 조금 모자람 → 1만원 걸 때마다 평균 190원 손실",
            "파산확률은 조건(1회 손실 크기·매매 횟수)에 따라 크게 달라집니다. 칸의 설명 풍선을 눌러 보세요"],
      warn: "노란 경고가 떠 있으면 오래된 계산입니다. 다시 계산한 뒤 보세요."
    },
    "3-6": {
      t: "모의투자 기간별 성적표",
      one: "최근 6개월 / 1년 / 전체 기간의 모의투자 성적으로 '실전에 들어가도 되나'를 판정합니다.",
      how: ["초록 = 통과, 노랑(보류) = 아직 판단 보류, 빨강 = 불합격",
            "[JSON 저장] = 지금 성적표를 기록 파일로 남기는 버튼(프로그램용). 엑셀로 보는 파일이 아니며 평소엔 안 눌러도 됩니다"],
      warn: ""
    },
    "3-7": {
      t: "몬테카를로 자산곡선 팬차트",
      one: "지금까지의 매매 결과를 섞어 1년을 5,000번 다시 살아 봤을 때 내 계좌가 어디쯤 가 있을지 보여 줍니다.",
      how: ["<b style='color:#3fb950'>초록선(중앙값)</b>만 먼저 보세요 = 가장 보통의 결과",
            "맨 위 빨간선 = 100번 중 5번 일어나는 행운, 맨 아래 파란선 = 100번 중 5번 일어나는 불운",
            "부채꼴이 넓을수록 결과가 운에 좌우됩니다. 좋은 전략은 좁고 위로 올라갑니다"],
      warn: ""
    },
    "3-8": {
      t: "수익률 확률사다리",
      one: "각 줄 = '6개월 뒤(1년 뒤) 수익률이 이 값 이상일 확률'.",
      how: ["<b>+0% 이상</b> 줄만 기억하세요: 원금 이상일 확률. 50%를 넘어야 벌 가능성이 더 높은 전략",
            "예) +0% 이상 36.7% → 6개월 뒤 손실일 확률 63.3%",
            "노란 테두리 = 지금까지 실제 모의투자 수익률이 들어 있는 칸"],
      warn: ""
    },
    "3-9": {
      t: "켈리·파산 시뮬레이터",
      one: "슬라이더로 '이런 성적이면 얼마나 걸어야 하고, 망할 확률은 얼마인가'를 바로 계산합니다.",
      how: ["승률 p, 손익비 b = 전략의 성적 / 자본단위 N = 계좌를 N칸으로 나눠 한 번 지면 1칸 잃음 (N=20 → 1회 손실 5%)",
            "켈리 f* = 돈이 가장 빨리 불어나는 베팅 비율. 실제로는 절반(하프켈리)을 권장. 0% 이하면 '걸지 마라'",
            "파산확률(공식) = 끝없이 매매할 때 계좌가 0이 될 확률"],
      warn: "슬라이더 처음 값(55%, 1.5)은 가상의 전략입니다. 내 실제 승률·손익비를 넣어야 내 이야기가 됩니다. 그래서 3-5의 파산확률과 숫자가 다릅니다."
    },
    "3-10": {
      t: "AI 학습 모니터",
      one: "실험용 AI가 뉴스로 공부해서 실력이 늘고 있는지 보는 화면입니다. 매매에는 쓰이지 않습니다.",
      how: ["<b>3초 판정</b>: 초록 막대(모델 정확도)가 회색 막대(기준선)보다 길어야 AI가 뭔가 배운 것",
            "기준선 = 생각 없이 많이 나오는 답 하나로만 찍었을 때의 정확도",
            "손실곡선: 낮을수록 좋음. 0.693 = 동전 던지기 수준",
            "학습 보류 중 = 자료 모으기는 계속, 공부(재학습)만 멈춘 상태"],
      warn: "모델 + 기준선이 정확히 100%가 되면 AI가 한쪽 답만 내고 있다는 신호입니다. 학습 코드를 점검하세요."
    }
  };

  /* ---------- 칸 이름 설명 (글자가 정확히 같을 때 붙음) ---------- */
  var TERMS = {
    "샤프(연율)": "위험을 감수한 만큼 벌었는지. 1 이상 좋음, 0 아래면 예금보다 못함.",
    "샤프": "위험을 감수한 만큼 벌었는지. 1 이상 좋음, 0 아래면 예금보다 못함.",
    "승률": "100번 매매 중 이긴 횟수.",
    "손익비": "이길 때 평균 수익 ÷ 질 때 평균 손실. 1.7이면 이길 때 1.7만원, 질 때 1만원.",
    "누적수익": "처음부터 지금까지 합친 수익률.",
    "CAGR(근사)": "1년으로 환산한 평균 수익률.",
    "CAGR": "1년으로 환산한 평균 수익률.",
    "최대연속손실": "가장 길게 연달아 진 횟수. 이만큼 연속으로 져도 버틸 각오가 필요.",
    "거래 표본": "계산에 쓴 매매 수. 많을수록 숫자를 믿을 만함(100건 이상이면 참고 가능).",
    "실측 거래 표본": "계산에 쓴 실제 매매 수. 많을수록 숫자를 믿을 만함.",
    "파산확률": "계좌가 바닥날 확률. 반드시 조건과 함께 봐야 함: 한 번 질 때 자본의 몇 %를 잃는지, 몇 번 매매하는 동안인지. 같은 성적이라도 1회 손실을 10%→2%로 줄이면 77.8%→10.5%로 떨어짐(430번 매매 기준).",
    "파산확률 (공식)": "끝없이 매매할 때 계좌가 0이 될 확률(수학 공식).",
    "파산확률 (몬테카를로 2,000회)": "가상 매매를 2,000번 돌려 실제로 0이 된 횟수. 공식값이 아주 작으면 0회가 정상.",
    "베이지안 승률 하한(95%)": "운을 감안해도 '최소 이 정도는 이긴다'고 95% 확신할 수 있는 승률.",
    "베이지안 승률 신용구간": "진짜 승률이 들어 있을 범위. 막대가 좁을수록 확실.",
    "엔진": "AI 예측 모델 종류. '폴백' = 원래 도구가 없어 대신 쓴 예비 엔진.",
    "학습/검증 샘플": "공부용 문제 수 / 시험용 문제 수.",
    "학습 시각": "마지막으로 공부한 때. 오래됐으면 최신 뉴스를 모름.",
    "누수 징후 없음": "시험 답이 공부 자료에 섞인 흔적이 없다는 뜻. 성적이 좋다는 뜻은 아님.",
    "검증 정확도 vs 다수클래스 기준선": "초록(모델)이 회색(찍기)보다 길어야 AI가 뭔가 배운 것.",
    "학습 코퍼스": "지금까지 쌓인 공부 자료 전체.",
    "자가학습 파이프라인": "자료 수집 → 꼬리표 → 재학습 자동 작업의 상태.",
    "Epoch 손실곡선": "가로 = 공부 반복 횟수, 세로 = 틀린 정도(낮을수록 좋음). 0.693은 동전 던지기 수준."
  };

  /* ---------- 모양 ---------- */
  var css = document.createElement("style");
  css.textContent =
    ".dh-btn{display:inline-flex;align-items:center;gap:4px;margin-left:10px;padding:2px 10px;border-radius:999px;border:1px solid #3d4a5c;" +
    "background:#1f2633;color:#c9d1d9;font:600 13px/1.6 inherit;cursor:pointer;vertical-align:middle;white-space:nowrap}" +
    ".dh-btn:hover{background:#2f7de1;border-color:#2f7de1;color:#fff}" +
    ".dh-term{border-bottom:1px dotted #8b949e;cursor:help}" +
    ".dh-i{display:inline-block;margin-left:4px;width:15px;height:15px;border-radius:50%;background:#30363d;color:#c9d1d9;font:700 11px/15px sans-serif;" +
    "text-align:center;cursor:pointer;vertical-align:middle;border:0;padding:0}" +
    ".dh-pop{position:fixed;z-index:99999;max-width:min(460px,calc(100vw - 32px));background:#161b22;color:#e6edf3;border:1px solid #3d4a5c;" +
    "border-radius:10px;padding:14px 16px;box-shadow:0 10px 30px rgba(0,0,0,.5);font:14px/1.65 'Malgun Gothic','Apple SD Gothic Neo',sans-serif}" +
    ".dh-pop h4{margin:0 0 6px;font-size:15px;color:#58a6ff}.dh-pop .dh-one{margin:0 0 8px;font-weight:600}" +
    ".dh-pop ul{margin:0;padding-left:18px}.dh-pop li{margin:3px 0}" +
    ".dh-pop .dh-warn{margin-top:8px;padding:6px 8px;border-radius:6px;background:rgba(210,153,34,.15);color:#e3b341}" +
    ".dh-pop .dh-x{position:absolute;top:6px;right:8px;background:none;border:0;color:#8b949e;font-size:18px;cursor:pointer}";
  document.head.appendChild(css);

  var pop = null;
  function close() { if (pop) { pop.remove(); pop = null; } }
  function open(anchor, html) {
    close();
    pop = document.createElement("div");
    pop.className = "dh-pop";
    pop.setAttribute("role", "dialog");
    pop.innerHTML = '<button class="dh-x" aria-label="닫기">×</button>' + html;
    document.body.appendChild(pop);
    var r = anchor.getBoundingClientRect(), pw = pop.offsetWidth, ph = pop.offsetHeight;
    var left = Math.min(Math.max(16, r.left), window.innerWidth - pw - 16);
    var top = r.bottom + 8 + ph > window.innerHeight ? Math.max(16, r.top - ph - 8) : r.bottom + 8;
    pop.style.left = left + "px"; pop.style.top = top + "px";
    pop.querySelector(".dh-x").onclick = close;
  }
  document.addEventListener("click", function (e) {
    if (pop && !pop.contains(e.target) && !e.target.closest(".dh-btn,.dh-i,.dh-term")) close();
  });
  document.addEventListener("keydown", function (e) { if (e.key === "Escape") close(); });
  window.addEventListener("scroll", close, true);

  function panelHtml(id, p) {
    return "<h4>" + id + " " + p.t + "</h4><p class='dh-one'>" + p.one + "</p><ul><li>" + p.how.join("</li><li>") + "</li></ul>" +
      (p.warn ? "<div class='dh-warn'>⚠ " + p.warn + "</div>" : "");
  }

  function ownText(el) {
    var s = "";
    for (var n = el.firstChild; n; n = n.nextSibling) if (n.nodeType === 3) s += n.nodeValue;
    return s.replace(/\s+/g, " ").trim();
  }

  /* ---------- 붙이기 ---------- */
  var ID_RE = /^\s*(\d+-\d+)\s+\S/;
  function scan(root) {
    // 1) 화면 제목: 자기 글자가 "3-5 백테스트…" 처럼 번호로 시작하는 요소
    var all = (root || document.body).querySelectorAll("h1,h2,h3,h4,h5,div,span,p,strong,b");
    for (var i = 0; i < all.length; i++) {
      var el = all[i];
      if (el.closest(".dh-pop")) continue;
      var txt = ownText(el), m = txt.match(ID_RE);
      if (m && PANELS[m[1]] && !el.querySelector(".dh-btn") && txt.length < 80) {
        var b = document.createElement("button");
        b.type = "button"; b.className = "dh-btn"; b.textContent = "❓ 이게 뭐예요?";
        b.setAttribute("data-dh", m[1]);
        el.appendChild(b);
      }
      // 2) 칸 이름: 글자가 TERMS 와 정확히 같은 작은 요소
      if (!el.children.length || (el.children.length === 1 && el.querySelector(".dh-i"))) {
        var key = ownText(el);
        if (TERMS[key] && !el.querySelector(".dh-i")) {
          el.classList.add("dh-term");
          el.title = TERMS[key];
          var ib = document.createElement("button");
          ib.type = "button"; ib.className = "dh-i"; ib.textContent = "?"; ib.setAttribute("aria-label", key + " 설명");
          ib.setAttribute("data-dt", key);
          el.appendChild(ib);
        }
      }
    }
  }

  document.addEventListener("click", function (e) {
    var b = e.target.closest(".dh-btn");
    if (b) { e.preventDefault(); e.stopPropagation(); var id = b.getAttribute("data-dh"); open(b, panelHtml(id, PANELS[id])); return; }
    var t = e.target.closest(".dh-i") || e.target.closest(".dh-term");
    if (t) {
      var k = t.getAttribute("data-dt") || ownText(t);
      if (TERMS[k]) { e.preventDefault(); e.stopPropagation(); open(t, "<h4>" + k + "</h4><p style='margin:0'>" + TERMS[k] + "</p>"); }
    }
  }, true);

  var timer = null;
  function later() { if (!timer) timer = setTimeout(function () { timer = null; scan(); }, 150); }
  new MutationObserver(function (list) {
    for (var i = 0; i < list.length; i++) {
      var n = list[i].target;
      if (n.nodeType === 1 && n.closest && n.closest(".dh-pop")) continue;
      later(); return;
    }
  }).observe(document.body, { childList: true, subtree: true, characterData: true });

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", function () { scan(); });
  else scan();

  window.DashHelp = { PANELS: PANELS, TERMS: TERMS, scan: scan, close: close };
})();
