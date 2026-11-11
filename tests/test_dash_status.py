# -*- coding: utf-8 -*-
"""utils/dash_status.py 검사.

설치 없이 실행:  python -m unittest tests.test_dash_status -v
"""

import json
import os
import sys
import tempfile
import unittest
from datetime import date, datetime, time, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.dash_status import (  # noqa: E402
    KST,
    Badge,
    account_badge,
    engine_badge,
    fmt_pct,
    fmt_won,
    freshness_badge,
    holdings_badge,
    is_trading_day,
    killswitch_badge,
    market_phase,
    pnl_class,
    prev_trading_day,
    read_status,
    scan_badge,
    slots_badge,
    stoploss_badge,
    top_alerts,
    unprotected_badge,
    watch_badge,
)

# 2026-11-11(수) 14:26 — 문제의 캡처 시각
T1426 = datetime(2026, 11, 11, 14, 26, tzinfo=KST)

HELD_9 = ["000660", "010140", "010640", "024110", "035250", "078130", "079940", "308170", "425420"]
NAMES = {
    "000660": "SK하이닉스", "010140": "삼성중공업", "010640": "진양폴리", "024110": "기업은행",
    "035250": "강원랜드", "078130": "에스엠국일", "079940": "가비아", "308170": "씨티알모빌리티",
    "425420": "티에프이", "036540": "SFA반도체",
}


class TestReplay20261111(unittest.TestCase):
    """2026-11-11 14:26 화면을 이 모듈로 다시 그렸을 때 무엇이 보여야 하는지."""

    def test_장상태는_장외가_아니라_정규장(self):
        m = market_phase(T1426)
        self.assertEqual(m.key, "open")
        self.assertEqual(m.text, "정규장 · 마감까지 1시간 4분")
        self.assertNotIn("장외", m.text)

    def test_엔진이_없으면_장중엔_빨강(self):
        e = engine_badge(None, T1426)
        self.assertEqual(e.level, "danger")
        self.assertIn("자동매매 꺼짐", e.text)

    def test_status_파일이_없어도_예외없이_빨강(self):
        e = engine_badge(os.path.join(tempfile.gettempdir(), "없는파일_status.json"), T1426)
        self.assertEqual((e.level, e.key), ("danger", "never"))

    def test_엔진이_꺼져있으면_어떤_배지도_초록이_아님(self):
        e = engine_badge(None, T1426)
        badges = [
            e,
            killswitch_badge(e, tripped=False, balance_ok=True),
            stoploss_badge(e, enabled=True, balance_ok=True),
            market_phase(T1426),
        ]
        self.assertTrue(all(b.level != "ok" for b in badges), [b.to_dict() for b in badges])

    def test_잔고실패면_보유없음이라고_하지_않음(self):
        h = holdings_badge(False, 0, eval_pnl=-6_595_925, now=T1426)
        self.assertEqual(h.level, "danger")
        self.assertNotIn("없음", h.text)
        self.assertIn("-6,595,925원", h.hint)

    def test_감시밖_보유9종목_경고(self):
        b = unprotected_badge(HELD_9 + ["036540"], ["036540"], names=NAMES)
        self.assertEqual(b.level, "danger")
        self.assertEqual(b.text, "손절 보호 안 되는 보유 종목 9개")
        self.assertIn("SK하이닉스(000660)", b.hint)
        self.assertNotIn("036540", b.hint)

    def test_잔고실패면_손절보류_빨강(self):
        alive = engine_badge(T1426 - timedelta(seconds=5), T1426)
        self.assertEqual(alive.key, "alive")
        s = stoploss_badge(alive, enabled=True, balance_ok=False)
        self.assertEqual((s.level, s.key), ("danger", "held"))
        k = killswitch_badge(alive, tripped=False, balance_ok=False)
        self.assertEqual((k.level, k.key), ("warn", "partial"))

    def test_자리문구는_한가지로만_읽힘(self):
        self.assertEqual(slots_badge(0, 10).text, "오늘 산 종목 0 / 최대 10 · 남은 자리 10")
        self.assertIn("모두 사용", slots_badge(10, 10).text)
        self.assertEqual(slots_badge(None).key, "unknown")

    def test_감시1개면_최대1종목만_살수있다고_경고(self):
        w = watch_badge(1, from_scan=0, fixed=1)
        self.assertEqual(w.text, "감시 종목 1 / 최대 20 (밤스캔 0개 · 고정 1개)")
        self.assertEqual(w.level, "warn")
        self.assertIn("최대 1종목", w.hint)

    def test_지정종목만_모드를_화면에_드러냄(self):
        s = scan_badge(None, today=date(2026, 11, 11), fixed_only=True)
        self.assertEqual(s.key, "fixed_only")
        self.assertIn("UNIVERSE_FIXED_ONLY", s.hint)

    def test_0원은_중립색(self):
        self.assertEqual(pnl_class(0), "pnl-zero")
        self.assertEqual(pnl_class(-0.004, 2), "pnl-zero")
        self.assertEqual(pnl_class(-23_236_493), "pnl-down")
        self.assertEqual(pnl_class(1), "pnl-up")

    def test_맨위_경고띠는_빨강부터(self):
        e = engine_badge(None, T1426)
        alerts = top_alerts(
            market_phase(T1426),
            watch_badge(1),
            e,
            unprotected_badge(HELD_9, ["036540"]),
            None,
        )
        self.assertEqual([a.level for a in alerts], ["danger", "danger", "warn"])


class TestMarketPhase(unittest.TestCase):
    def test_시간대별(self):
        d = date(2026, 11, 11)
        f = lambda h, m: market_phase(datetime.combine(d, time(h, m), KST)).key  # noqa: E731
        self.assertEqual(f(8, 59), "pre")
        self.assertEqual(f(9, 0), "open")
        self.assertEqual(f(15, 29), "open")
        self.assertEqual(f(15, 30), "closed")

    def test_주말_휴장일(self):
        self.assertEqual(market_phase(datetime(2026, 11, 14, 10, 0, tzinfo=KST)).key, "holiday")
        self.assertEqual(market_phase(datetime(2026, 11, 11, 10, 0, tzinfo=KST), ["2026-11-11"]).key, "holiday")

    def test_수능날_시간변경(self):
        sp = {"2026-11-19": (time(10, 0), time(16, 30))}
        self.assertEqual(market_phase(datetime(2026, 11, 19, 9, 30, tzinfo=KST), special_sessions=sp).key, "pre")
        self.assertEqual(market_phase(datetime(2026, 11, 19, 16, 0, tzinfo=KST), special_sessions=sp).key, "open")

    def test_UTC_시각을_넣어도_한국시간으로(self):
        utc = datetime(2026, 11, 11, 5, 26, tzinfo=timezone.utc)  # = 14:26 KST
        self.assertEqual(market_phase(utc).key, "open")

    def test_시간대없는_datetime은_한국시간으로_봄(self):
        self.assertEqual(market_phase(datetime(2026, 11, 11, 14, 26)).key, "open")


class TestEngine(unittest.TestCase):
    def test_작동중만_초록(self):
        self.assertEqual(engine_badge(T1426 - timedelta(seconds=10), T1426).level, "ok")

    def test_장중_멈춤(self):
        b = engine_badge(datetime(2026, 11, 11, 10, 49, tzinfo=KST), T1426)
        self.assertEqual((b.level, b.key), ("danger", "stale"))
        self.assertIn("10:49", b.text)
        self.assertIn("3시간 37분", b.text)

    def test_장외_멈춤은_회색(self):
        night = datetime(2026, 11, 11, 20, 0, tzinfo=KST)
        self.assertEqual(engine_badge(T1426, night).level, "info")

    def test_파일_수정시각으로_판단(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump({"x": 1}, f)
            p = f.name
        try:
            now = datetime.fromtimestamp(os.path.getmtime(p), KST) + timedelta(seconds=3)
            self.assertEqual(engine_badge(p, now, market=Badge("정규장", key="open")).key, "alive")
        finally:
            os.remove(p)

    def test_미래시각은_0초로(self):
        self.assertEqual(engine_badge(T1426 + timedelta(seconds=5), T1426).key, "alive")


class TestReadStatus(unittest.TestCase):
    def test_BOM과_깨진파일(self):
        d = tempfile.mkdtemp()
        good = os.path.join(d, "s.json")
        with open(good, "w", encoding="utf-8-sig") as f:
            json.dump({"보유": 0}, f, ensure_ascii=False)
        data, mtime = read_status(good)
        self.assertEqual(data, {"보유": 0})
        self.assertIsNotNone(mtime)

        bad = os.path.join(d, "bad.json")
        with open(bad, "w", encoding="utf-8") as f:
            f.write('{"쓰는 중')
        data, mtime = read_status(bad)
        self.assertIsNone(data)
        self.assertIsNotNone(mtime)

        self.assertEqual(read_status(os.path.join(d, "없음.json")), (None, None))


class TestHoldings(unittest.TestCase):
    def test_정말_0종목일때만_없음(self):
        b = holdings_badge(True, 0, eval_pnl=0, as_of=T1426, now=T1426)
        self.assertEqual(b.text, "보유 종목 없음 (14:26 한투 잔고 기준)")

    def test_0종목인데_평가손익있으면_불일치(self):
        self.assertEqual(holdings_badge(True, 0, eval_pnl=-1000, now=T1426).key, "mismatch")

    def test_감시밖_개수(self):
        b = holdings_badge(True, 10, outside_watch=9, now=T1426)
        self.assertEqual(b.text, "보유 10종목 · 그중 9종목 감시 밖")
        self.assertEqual(b.level, "warn")

    def test_종목코드_앞자리0_보정(self):
        self.assertIsNone(unprotected_badge([660, "36540"], ["000660", 36540]))


class TestScan(unittest.TestCase):
    def test_어젯밤_결과(self):
        b = scan_badge("2026-11-10", today="2026-11-11")
        self.assertEqual((b.level, b.key), ("ok", "fresh"))
        self.assertIn("어젯밤", b.text)

    def test_월요일엔_금요일_결과가_새것(self):
        b = scan_badge("20261106", today="2026-11-09")
        self.assertEqual(b.key, "fresh")
        self.assertIn("직전 거래일(11-06)", b.text)  # 금요일 밤은 '어젯밤'이 아님

    def test_같은날_결과는_날짜_한번만(self):
        self.assertEqual(scan_badge("2026-11-11", today="2026-11-11").text, "밤스캔 11-11 결과 사용 중")

    def test_엔진꺼지면_밤스캔도_초록아님(self):
        e = engine_badge(None, T1426)
        self.assertEqual(scan_badge("2026-11-10", today="2026-11-11", engine=e).level, "info")
        self.assertEqual(scan_badge("2026-11-10", today="2026-11-11").level, "ok")

    def test_숫자로_저장된_날짜(self):
        self.assertEqual(scan_badge(20261110, today=20261111).key, "fresh")
        self.assertEqual(market_phase(T1426, [20261111]).key, "holiday")

    def test_시간대가_붙은_날짜문자열은_한국날짜로(self):
        # 11-10 20:00 UTC = 11-11 05:00 KST
        self.assertEqual(scan_badge("2026-11-10T20:00:00Z", today="2026-11-12").text, "밤스캔 어젯밤(11-11) 결과 사용 중")

    def test_오래된_결과(self):
        b = scan_badge("2026-11-06", today="2026-11-11")
        self.assertEqual(b.key, "stale")
        self.assertIn("3거래일 전", b.text)  # 11-10(1) · 11-09(2) · 11-06(3)
        self.assertIn("2거래일 전", scan_badge("2026-11-09", today="2026-11-11").text)
        self.assertIn("2거래일 전", scan_badge("2026-11-12", today="2026-11-15").text)  # 일요일에 본 목요일 결과
        self.assertIn("장후일괄_20261110", b.hint)

    def test_기록없음(self):
        for v in (None, "-", ""):
            self.assertEqual(scan_badge(v, today="2026-11-11").key, "none")

    def test_거래일_계산(self):
        self.assertTrue(is_trading_day("2026-11-11"))
        self.assertFalse(is_trading_day("2026-11-15"))
        self.assertEqual(prev_trading_day("2026-11-09"), date(2026, 11, 6))
        self.assertEqual(prev_trading_day("2026-11-11", ["2026-11-10"]), date(2026, 11, 9))


class TestFreshness(unittest.TestCase):
    def test_새값_묵은값(self):
        self.assertEqual(freshness_badge(T1426 - timedelta(seconds=3), now=T1426).text, "한투 잔고 14:25:57 기준 (3초 전)")
        b = freshness_badge(T1426 - timedelta(minutes=6), now=T1426)
        self.assertEqual(b.level, "warn")
        self.assertIn("6분 전 값", b.text)
        self.assertEqual(freshness_badge(None, now=T1426).key, "unknown")


class TestRobustInputs(unittest.TestCase):
    """검증에서 찾은 입력들: 이런 값이 와도 죽지 않고, 초록으로 속이지 않아야 한다."""

    def test_미래_신호시각은_초록이_아님(self):
        # 한국 시각에 Z 를 붙인 흔한 실수: 14:20 KST 를 '14:20Z' 로 저장 → 23:20 KST 로 읽힘
        e = engine_badge("2026-11-11T14:20:00Z", datetime(2026, 11, 11, 15, 0, tzinfo=KST),
                         market=Badge("정규장", key="open"))
        self.assertEqual((e.level, e.key), ("danger", "clock"))
        self.assertNotEqual(killswitch_badge(e, tripped=False).level, "ok")
        self.assertNotEqual(stoploss_badge(e).level, "ok")
        self.assertEqual(engine_badge(T1426 + timedelta(days=1), T1426).key, "clock")
        self.assertEqual(freshness_badge(T1426 + timedelta(hours=9), now=T1426).key, "unknown")

    def test_파이썬310이_못읽던_ISO모양(self):
        for s in ("2026-11-11T14:25:50+0900", "2026-11-11T14:25:50.1234567+09:00",
                  "2026-11-11T14:25:50.12+09:00", "2026-11-11T05:25:50z", "2026-11-11 14:25:50"):
            self.assertEqual(engine_badge(s, T1426).key, "alive", s)

    def test_밀리초_NaN_무한대(self):
        self.assertEqual(engine_badge(T1426.timestamp() * 1000 - 3000, T1426).key, "alive")
        for bad in (float("nan"), float("inf"), -1e30):
            self.assertEqual(engine_badge(bad, T1426).key, "never")
        self.assertEqual(freshness_badge(float("nan"), now=T1426).key, "unknown")

    def test_보유수_모르면_없음이라_하지않음(self):
        self.assertEqual(holdings_badge(True, None, now=T1426).key, "unknown")
        self.assertEqual(holdings_badge(True, now=T1426).key, "unknown")
        self.assertEqual(holdings_badge(True, float("nan"), now=T1426).key, "unknown")

    def test_평가손익_반올림0이면_보유있다고_안함(self):
        h = holdings_badge(False, 0, eval_pnl=0.3, now=T1426)
        self.assertNotIn("보유 주식이 있습니다", h.hint)
        self.assertEqual(holdings_badge(False, 0, eval_pnl=float("nan"), now=T1426).key, "unknown")

    def test_잔고_모름이면_초록아님(self):
        alive = engine_badge(T1426, T1426)
        self.assertEqual(killswitch_badge(alive, tripped=False, balance_ok=None).level, "warn")
        self.assertEqual(stoploss_badge(alive, balance_ok=None).level, "warn")

    def test_bool_엔진은_장시간을_지어내지_않음(self):
        b = stoploss_badge(False)
        self.assertNotIn("장 시간", b.text)
        self.assertEqual(b.key, "off")

    def test_긴급정지_힌트가_상태와_맞음(self):
        alive = engine_badge(T1426, T1426)
        self.assertNotIn("신호가 없어", killswitch_badge(alive, tripped=None).hint)
        self.assertNotIn("손절은 계속", killswitch_badge(alive, tripped=True, balance_ok=False).hint)
        self.assertIn("손절은 계속", killswitch_badge(alive, tripped=True, balance_ok=True).hint)

    def test_판다스_실수_종목코드(self):
        self.assertIsNone(unprotected_badge([660.0, 36540.0], ["000660", "036540"]))

    def test_숫자아님(self):
        self.assertEqual(fmt_won(float("nan")), "-")
        self.assertEqual(fmt_won(float("inf")), "-")
        self.assertEqual(fmt_pct(float("nan")), "-")
        self.assertEqual(fmt_won(None), "0원")
        self.assertEqual(pnl_class(float("nan")), "pnl-zero")
        self.assertEqual(slots_badge(float("nan")).key, "unknown")
        self.assertEqual(watch_badge(float("nan")).key, "empty")


class TestFormat(unittest.TestCase):
    def test_원(self):
        self.assertEqual(fmt_won(-23_236_493), "-23,236,493원")
        self.assertEqual(fmt_won(120_000), "+120,000원")
        self.assertEqual(fmt_won(120_000, sign=False), "120,000원")
        self.assertEqual(fmt_won(0), "0원")
        self.assertEqual(fmt_won(-0.4), "0원")

    def test_퍼센트(self):
        self.assertEqual(fmt_pct(-23_236_493 / 500_000_000 * 100), "-4.65%")
        self.assertEqual(fmt_pct(-0.001), "0.00%")
        self.assertEqual(fmt_pct(1.5), "+1.50%")

    def test_계좌배지(self):
        self.assertEqual(account_badge(True).text, "모의투자")
        self.assertEqual(account_badge(False).level, "danger")

    def test_badge_html_escape(self):
        h = Badge("<b>", "warn", 'a"b', "k").html()
        self.assertIn("&lt;b&gt;", h)
        self.assertIn("st st-warn", h)
        self.assertIn("&quot;", h)

    def test_잘못된_level(self):
        with self.assertRaises(ValueError):
            Badge("x", "green")


if __name__ == "__main__":
    unittest.main()
