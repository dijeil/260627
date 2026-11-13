# 캔들차트 십자선 어긋남 수정 + 증권사 HTS처럼 쓰기

> 함께 들어 있는 파일
> - `static/chart_check.js`: 십자선이 왜 어긋나는지 찾아 주는 진단기 (붙여 넣기 한 번)
> - `static/chart_hts_kit.js`: HTS형 차트 도구 (lightweight-charts 4.x·5.x 모두 지원)
> - `static/chart_hts_example.html`: 바로 열어 볼 수 있는 예제 (더블클릭)

---

## 1. 사진에서 보이는 문제

| 사진 속 표시 | 내용 |
|---|---|
| 파란 동그라미 | 실제 **마우스 커서**가 있는 곳 (가로 약 390px) |
| 빨간 동그라미 | **점선 십자선**과 지표 점(●)이 그려진 곳 (가로 약 525px) |

십자선이 커서보다 **오른쪽으로 약 1.35배** 멀리 그려지고 있습니다.
지표 점(볼린저 상·중·하)은 십자선 위에 정확히 붙어 있으므로 **지표 계산은 맞습니다.**
틀린 것은 **"마우스 위치 → 차트 좌표" 변환** 한 가지입니다.

이렇게 "비율만큼" 벌어지는 원인은 아래 세 가지 중 하나입니다.

| 원인 | 설명 | 흔한 예 |
|---|---|---|
| **A) CSS `zoom`** | 화면 전체나 상위 상자를 `zoom`으로 확대·축소 | `body { zoom: 0.8 }` 로 화면을 작게 만든 경우 |
| **B) `transform: scale()`** | 상위 상자를 transform으로 확대·축소 | 카드 확대 애니메이션, 모바일 축소 |
| **C) 늘어난 캔버스** | 차트를 만든 뒤 상자 크기가 바뀌었는데 차트가 모름 | `createChart(el, {width: 1000})`로 고정 폭 생성 + CSS `width:100%`, 사이드바 접기/펴기 |

마우스가 **왼쪽 끝에서는 거의 맞고 오른쪽으로 갈수록 더 벌어지면** 이 셋 중 하나가 확실합니다.

## 2. 원인 찾기 (1분)

1. 대시보드에서 차트를 띄운 상태로 **F12** → **Console(콘솔)** 탭
2. `static/chart_check.js` 내용을 통째로 붙여 넣고 **Enter**
3. 알림창에 **원인 + 고치는 법**이 나옵니다. (콘솔에는 표로도 나옵니다)

대시보드에 `<script src="/static/chart_check.js"></script>`로 넣어 두면, 주소 끝에 `?chartcheck`를 붙였을 때만 자동으로 진단합니다. 평소에는 아무 일도 하지 않습니다.

## 3. 고치는 법

### A) CSS zoom 때문이면
```css
/* ❌ 이렇게 되어 있으면 */
body { zoom: 0.8; }

/* ✅ zoom 을 빼고 글자 크기로 조절 */
html { font-size: 14px; }
```
zoom을 꼭 둬야 한다면 차트 상자에서만 되돌립니다: `body`가 0.8이면 차트 상자에 `zoom: 1.25`.

### B) transform 때문이면
차트를 감싸는 상자에서 `transform: scale(...)`을 빼세요. 애니메이션이라면 끝난 뒤 `transform: none`으로 돌려놓으면 됩니다.

### C) 늘어난 캔버스 때문이면 (가장 간단)
```js
// ❌
const chart = LightweightCharts.createChart(el, { width: 1000, height: 460 });

// ✅ 상자 크기를 자동으로 따라감 (상자에 CSS height 를 꼭 줄 것)
const chart = LightweightCharts.createChart(el, { autoSize: true });
```
그리고 `canvas { width: 100% }` 같은 CSS가 있으면 지웁니다.
`chart_hts_kit.js`의 `HtsChart.create(상자)`를 쓰면 자동 크기가 기본으로 들어가 있습니다.

### 덤: 날짜 표시 `02 11월 '26` → `2026-11-02 (월)`
사진 아래의 `02 11월 '26`은 라이브러리 기본 형식입니다. `HtsChart.create`를 쓰면 십자선 날짜는 `2026-11-02 (월)`, 가격은 `52,300`처럼 원 단위 쉼표로 나옵니다.

---

## 4. 증권사 HTS처럼 유용하게 쓰는 방법 (조사 결과, 효과 큰 순서)

키움·미래에셋·한국투자 HTS/MTS와 TradingView에서 공통으로 쓰는 기능 중, 대시보드에 바로 넣을 수 있고 체감 효과가 큰 것부터 정리했습니다.

| 순위 | 기능 | 왜 유용한가 | 키트 함수 |
|---|---|---|---|
| 1 | **데이터 창(범례)**: 십자선이 가리킨 날의 시·고·저·종·등락률·거래량·지표값 | HTS의 핵심. 커서를 대기만 하면 숫자를 바로 읽음. 십자선이 맞는지도 눈으로 확인됨 | `HtsChart.legend` |
| 2 | **한국식 색**: 상승 빨강 / 하락 파랑, 거래량 막대도 같은 색 | 한국 사용자가 헷갈리지 않음 | `HtsChart.create` 기본값 |
| 3 | **자석 십자선**: 가로줄이 종가(시고저종)에 달라붙음 | 정확한 가격을 읽기 쉬움 | `HtsChart.magnet(chart, true)` |
| 4 | **매수·매도 화살표 + 평단가 선** | 내 매매가 차트 어디서 일어났는지 한눈에 (사진의 "매도132" 표시 확장) | `HtsChart.markers`, `HtsChart.priceLine` |
| 5 | **보조지표 창 동기화**: 거래량·RSI·MACD 창이 가격 차트와 함께 스크롤·확대, 십자선도 같이 움직임 | HTS의 "분할 차트" | `HtsChart.sync` |
| 6 | **기간 버튼**: 1개월 / 3개월 / 6개월 / 1년 / 전체 | 휠 조작 없이 한 번에 | `HtsChart.showLast` |
| 7 | **키보드 조작**: ← → 한 봉 이동, + − 확대, Home 최신, 더블클릭 원위치 | HTS 사용자 손에 익은 조작 | `HtsChart.keyboard` |
| 8 | **이동평균 5·20·60·(120)일 + 볼린저(20, 2)** | 가장 많이 보는 기본 세트 | `HtsChart.sma`, `HtsChart.bollinger` |
| 9 | **RSI 70/30 기준선** (과열·침체) | 숫자 몰라도 선 위/아래로 판단 | 예제 참고 |

더 나아가 넣을 만한 것 (필요하면 다음 단계로):
- 일/주/월/분봉 전환 버튼 (일봉 데이터로 주·월봉을 묶어서 계산 가능)
- 기간 최고가·최저가 표시, 52주 신고가 표시
- Shift+드래그로 두 지점 사이 **등락률·기간 측정**
- 로그 눈금 / % 눈금 전환 (`priceScaleMode`)
- 손절가·목표가 선을 드래그로 옮기기

### 대시보드에 붙이는 순서
```html
<script src="https://unpkg.com/lightweight-charts@4.2.3/dist/lightweight-charts.standalone.production.js"></script>
<script src="/static/chart_hts_kit.js"></script>
<script>
  const chart  = HtsChart.create(document.getElementById("chart"));   // 상자에 CSS height 필요
  const candle = HtsChart.candles(chart, 일봉배열);                    // [{time:"2026-11-13", open, high, low, close, volume}]
  HtsChart.volume(chart, 일봉배열);
  const ma5 = HtsChart.line(chart, HtsChart.sma(일봉배열, 5), "#f5c542", "5일");
  HtsChart.legend(chart, document.getElementById("legend"), { candle, lines: [ma5], title: "종목명" });
  HtsChart.markers(candle, [{ time: "2026-11-10", side: "매도", qty: 132 }]);
  HtsChart.keyboard(chart, document.getElementById("chart"));
</script>
```
전체 예시는 `static/chart_hts_example.html`을 더블클릭해서 보시면 됩니다 (인터넷 연결 필요).

---

## 5. 거래 캘린더 히트맵 네모 색깔의 뜻 (3-4)

| 색 | 뜻 |
|---|---|
| **빨강** | 그날 **이익** (한국식: 오르면 빨강) |
| **파랑** | 그날 **손실** |
| **진할수록 / 밝을수록** | 그날 손익 금액이 큼 |
| **어두운 회색** | 거래가 없던 날 (토·일 포함) |
| **테두리만 있는 칸** | 오늘 |

화면 아래 요약의 `이익 18일`(빨강 글자) · `손실 20일`(파랑 글자)이 네모 색과 같은 규칙입니다.
읽는 법: 가로 한 줄이 요일(월~일), 세로 한 줄이 한 주, 왼쪽에서 오른쪽으로 갈수록 최근입니다.

**구매자를 위한 개선 제안**: 히트맵 아래에 작은 범례 한 줄을 넣고, 네모에 마우스를 올리면 날짜·손익이 뜨게 하면 설명 없이도 바로 이해됩니다.
```html
<div style="display:flex;gap:10px;align-items:center;font-size:12px;color:#8b949e">
  손실 큼 <i style="width:12px;height:12px;background:#4a90e2;border-radius:3px"></i>
  <i style="width:12px;height:12px;background:#2a4365;border-radius:3px"></i>
  <i style="width:12px;height:12px;background:#21262d;border-radius:3px"></i> 거래없음
  <i style="width:12px;height:12px;background:#5c2b2b;border-radius:3px"></i>
  <i style="width:12px;height:12px;background:#e5534b;border-radius:3px"></i> 이익 큼
</div>
<!-- 각 네모에: title="2026-11-13 (금) · +123,400원" -->
```
