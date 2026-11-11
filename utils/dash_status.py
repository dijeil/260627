# -*- coding: utf-8 -*-
"""
대시보드 상태 문구를 '사실 그대로' 만들어 주는 모듈.

2026-11-11 점검에서 실제로 일어난 일:
  · 수요일 14:26(장중)인데 화면은 '장외/대기' + 초록 '킬스위치 정상'
  · 실제로는 자동매매 프로그램이 꺼져 있었고
  · 한투 잔고 조회가 실패해 손절이 전부 보류된 상태였으며
  · 보유 9종목은 감시 목록 밖이라 손절이 아예 돌지 않았다.
  · 그런데 화면에는 '보유 종목 없음'이라고 나왔다.

이 모듈은 그런 일이 다시 생기지 않도록 아래 규칙을 코드로 박아 둔 것입니다.

  1. 장 상태는 프로그램이 아니라 '시계'로 정한다 (프로그램이 꺼져도 '장외'로 떨어지지 않게)
  2. 프로그램 신호가 끊기거나 잔고를 확인하지 못하면 초록색 배지를 쓰지 않는다
     (scan_badge 는 engine= 을 넘겼을 때 이 규칙을 따른다)
  3. '보유 종목 없음'은 잔고 조회에 성공했고 정말 0종목일 때만 쓴다
  4. 보유 중인데 감시 밖인 종목(손절 안 됨)은 빨간 경고로 띄운다
  5. '0 / 10 남음'처럼 두 가지로 읽히는 문구를 쓰지 않는다
  6. 0원은 빨강도 파랑도 아닌 중립색으로 칠한다

모든 상태 함수는 Badge(text, level, hint, key) 를 돌려줍니다.
  level : ok(초록) · info(회색) · warn(주황) · danger(빨강)
  JSON 으로 화면에 보낼 때   → badge.to_dict()
  HTML 을 바로 만들 때       → badge.html()
  CSS 는 static/dashboard_mobile.css 의 .st-ok / .st-info / .st-warn / .st-danger

사용 예
-------
    from utils.dash_status import market_phase, engine_badge, killswitch_badge

    market = market_phase()                                  # '정규장 · 마감까지 1시간 4분'
    engine = engine_badge("status.json", market=market)     # 파일 수정 시각으로 생존 확인
    kill   = killswitch_badge(engine, tripped=False, balance_ok=False)

    payload = {"market": market.to_dict(), "engine": engine.to_dict(), "kill": kill.to_dict()}
"""

from __future__ import annotations

import html as _html
import json
import math
import os
import re
from dataclasses import asdict, dataclass
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Iterable, Mapping

__all__ = [
    "Badge",
    "KST",
    "now_kst",
    "is_trading_day",
    "prev_trading_day",
    "read_status",
    "market_phase",
    "engine_badge",
    "killswitch_badge",
    "stoploss_badge",
    "holdings_badge",
    "unprotected_badge",
    "watch_badge",
    "slots_badge",
    "scan_badge",
    "freshness_badge",
    "account_badge",
    "top_alerts",
    "pnl_class",
    "fmt_won",
    "fmt_pct",
]

# 한국은 서머타임이 없어서 +9 고정이면 정확합니다.
# (zoneinfo 를 쓰면 윈도우에서 tzdata 를 따로 깔아야 해서 일부러 쓰지 않습니다.)
KST = timezone(timedelta(hours=9), "KST")

OPEN_TIME = time(9, 0)
CLOSE_TIME = time(15, 30)

LEVELS = ("ok", "info", "warn", "danger")
_LEVEL_ORDER = {"danger": 0, "warn": 1, "info": 2, "ok": 3}


# =================================================================== Badge
@dataclass(frozen=True)
class Badge:
    """화면에 띄울 상태 한 칸.

    text  : 배지에 그대로 보여 줄 짧은 문구
    level : ok / info / warn / danger  (색)
    hint  : 눌렀을 때나 아래 줄에 보여 줄 '그래서 뭘 해야 하나' 설명
    key   : 프로그램이 분기할 때 쓰는 영문 상태값 (화면에는 안 씀)
    """

    text: str
    level: str = "info"
    hint: str = ""
    key: str = ""

    def __post_init__(self):
        if self.level not in LEVELS:
            raise ValueError(f"level 은 {LEVELS} 중 하나여야 합니다: {self.level!r}")

    @property
    def css_class(self) -> str:
        return f"st st-{self.level}"

    def to_dict(self) -> dict:
        return asdict(self)

    def html(self, tag: str = "span") -> str:
        title = f' title="{_html.escape(self.hint)}"' if self.hint else ""
        return (
            f'<{tag} class="{self.css_class}" data-key="{_html.escape(self.key)}"{title}>'
            f"{_html.escape(self.text)}</{tag}>"
        )

    def __str__(self) -> str:
        return self.text


# ============================================================ 시간 도우미
def now_kst() -> datetime:
    return datetime.now(KST)


def _now(now) -> datetime:
    if now is None:
        return now_kst()
    dt = _to_dt(now)
    if dt is None:
        raise ValueError(f"now 를 시각으로 읽을 수 없습니다: {now!r}")
    return dt


def _to_dt(x) -> datetime | None:
    """여러 모양의 '시각'을 한국시간 datetime 으로 바꾼다. 못 읽으면 None.

    받는 것: datetime / date / 숫자(유닉스 시각, 초 또는 밀리초) / ISO 문자열 / 파일 경로(→ 수정 시각)
    시간대가 없는 datetime 은 한국시간으로 봅니다.
    """
    if x is None:
        return None
    if isinstance(x, datetime):
        return x.replace(tzinfo=KST) if x.tzinfo is None else x.astimezone(KST)
    if isinstance(x, date):
        return datetime(x.year, x.month, x.day, tzinfo=KST)
    if isinstance(x, (int, float)) and not isinstance(x, bool):
        return _from_epoch(x)
    if isinstance(x, Path) or (isinstance(x, str) and os.path.exists(x)):
        try:
            return datetime.fromtimestamp(os.path.getmtime(x), KST)
        except (OSError, OverflowError, ValueError):
            return None
    if isinstance(x, str):
        s = _norm_iso(x)
        if not s:
            return None
        try:
            return _to_dt(datetime.fromisoformat(s))
        except ValueError:
            return None
    return None


def _from_epoch(x) -> datetime | None:
    """유닉스 시각 → 한국시간. 밀리초(JS Date.now())도 받는다. NaN/무한대/범위 밖은 None."""
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(v):
        return None
    if abs(v) > 1e11:          # 밀리초로 보이면 초로 바꾼다 (1e11초 = 5138년)
        v /= 1000.0
    try:
        return datetime.fromtimestamp(v, KST)
    except (OverflowError, OSError, ValueError):
        return None


_ISO_OFFSET_NOCOLON = re.compile(r"([+-]\d{2})(\d{2})$")
_ISO_FRACTION = re.compile(r"(\d{2}:\d{2}:\d{2})\.(\d+)")


def _norm_iso(s: str) -> str:
    """파이썬 3.10 의 fromisoformat 이 못 읽는 모양을 고쳐 준다.

    '...Z' / '...z' → '+00:00',  '+0900' → '+09:00',
    소수점 아래 초는 6자리로 맞춘다 (PowerShell 은 7자리, 일부는 2자리를 씀).
    """
    s = s.strip()
    if not s:
        return s
    if s[-1] in "Zz":
        s = s[:-1] + "+00:00"
    if len(s) > 10 and s[10] in "Tt ":
        s = s[:10] + "T" + s[11:]
        s = _ISO_OFFSET_NOCOLON.sub(r"\1:\2", s) if re.search(r"T\d{2}:\d{2}(:\d{2}(\.\d+)?)?[+-]\d{4}$", s) else s
        s = _ISO_FRACTION.sub(lambda m: m.group(1) + "." + (m.group(2) + "000000")[:6], s)
    return s


def _to_date(x) -> date | None:
    if x is None:
        return None
    if isinstance(x, datetime):
        return _to_dt(x).date()
    if isinstance(x, date):
        return x
    if isinstance(x, int) and not isinstance(x, bool) and 19000101 <= x <= 99991231:
        x = str(x)                                   # JSON 에 숫자로 저장된 20261110
    if isinstance(x, str):
        s = x.strip()
        if not s or s in ("-", "None", "null"):
            return None
        if len(s) > 10 and s[10] in "Tt ":           # 시각이 붙은 문자열은 시간대까지 반영해서 한국 날짜로
            dt = _to_dt(s)
            if dt:
                return dt.date()
        for fmt in ("%Y-%m-%d", "%Y%m%d", "%Y.%m.%d", "%Y/%m/%d"):
            try:
                return datetime.strptime(s[:10] if "-" in s or "." in s or "/" in s else s[:8], fmt).date()
            except ValueError:
                continue
        dt = _to_dt(s)
        return dt.date() if dt else None
    dt = _to_dt(x)
    return dt.date() if dt else None


def _holiday_set(holidays: Iterable | None) -> set[date]:
    out = set()
    for h in holidays or ():
        d = _to_date(h)
        if d:
            out.add(d)
    return out


def _dur(seconds: float) -> str:
    """초 → '45초' / '12분' / '1시간 4분' / '2일 3시간'."""
    s = max(0, int(seconds))
    if s < 60:
        return f"{s}초"
    m = s // 60
    if m < 60:
        return f"{m}분"
    h, m = divmod(m, 60)
    if h < 24:
        return f"{h}시간 {m}분" if m else f"{h}시간"
    d, h = divmod(h, 24)
    return f"{d}일 {h}시간" if h else f"{d}일"


def _finite(v):
    """숫자면 float/int 그대로, NaN·무한대·숫자 아님이면 None."""
    if v is None or isinstance(v, bool):
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(f):
        return None
    return v if isinstance(v, int) else f


def _hm(dt: datetime, now: datetime) -> str:
    """오늘이면 '14:26', 다른 날이면 '11-10 14:26'."""
    return f"{dt:%H:%M}" if dt.date() == now.date() else f"{dt:%m-%d %H:%M}"


def is_trading_day(d, holidays: Iterable | None = None) -> bool:
    """평일이고 휴장일 목록에 없으면 거래일."""
    d = _to_date(d)
    return d is not None and d.weekday() < 5 and d not in _holiday_set(holidays)


def prev_trading_day(d, holidays: Iterable | None = None) -> date:
    """d 바로 전 거래일."""
    d = _to_date(d)
    hs = _holiday_set(holidays)
    p = d - timedelta(days=1)
    while p.weekday() >= 5 or p in hs:
        p -= timedelta(days=1)
    return p


def _trading_days_between(a: date, b: date, holidays: set[date]) -> int:
    """a 다음 날부터 b 까지(포함) 거래일 수. a >= b 이면 0."""
    n, d = 0, a
    while d < b:
        d += timedelta(days=1)
        if d.weekday() < 5 and d not in holidays:
            n += 1
    return n


# ============================================================ 상태 파일
def read_status(path) -> tuple[dict | None, datetime | None]:
    """status.json 같은 상태 파일을 안전하게 읽는다.

    돌려주는 값: (내용 dict 또는 None, 파일 수정 시각 또는 None)
    파일이 없거나, 쓰는 도중이라 깨져 있어도 예외 없이 (None, …) 을 돌려줍니다.
    BOM 이 붙은 파일도 읽습니다(utf-8-sig).
    """
    p = Path(path)
    try:
        mtime = datetime.fromtimestamp(p.stat().st_mtime, KST)
    except OSError:
        return None, None
    try:
        with open(p, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
        return (data if isinstance(data, dict) else None), mtime
    except (OSError, ValueError):
        return None, mtime


# ============================================================ ① 장 상태
def market_phase(
    now=None,
    holidays: Iterable | None = None,
    *,
    open_time: time = OPEN_TIME,
    close_time: time = CLOSE_TIME,
    special_sessions: Mapping | None = None,
) -> Badge:
    """장 상태를 '시계'로 정한다. 자동매매 프로그램이 꺼져 있어도 결과가 같다.

    special_sessions: {날짜: (개장, 마감)} — 수능날처럼 시간이 바뀌는 날
                      예) {"2026-11-19": (time(10, 0), time(16, 30))}

    key: open(정규장) · pre(장 시작 전) · closed(장 마감) · holiday(휴장일)
    장 상태 배지는 사실만 알려 주므로 색은 언제나 회색(info)입니다.
    경고 색은 자동매매 배지(engine_badge)가 맡습니다.
    """
    now = _now(now)
    today = now.date()
    if special_sessions:
        for k, v in special_sessions.items():
            if _to_date(k) == today:
                open_time, close_time = v
                break

    if not is_trading_day(today, holidays):
        return Badge("휴장일", "info", "오늘은 장이 열리지 않습니다.", "holiday")

    t = now.timetz().replace(tzinfo=None)
    if t < open_time:
        return Badge(f"장 시작 전 · {open_time:%H:%M} 개장", "info", "", "pre")
    if t < close_time:
        close_dt = datetime.combine(today, close_time, KST)
        left = (close_dt - now).total_seconds()
        return Badge(f"정규장 · 마감까지 {_dur(left)}", "info", f"{close_time:%H:%M} 마감", "open")
    return Badge("장 마감", "info", f"오늘 장은 {close_time:%H:%M}에 끝났습니다.", "closed")


# ============================================================ ② 자동매매(엔진)
def engine_badge(
    last_signal,
    now=None,
    *,
    market: Badge | None = None,
    stale_after: float = 30,
    holidays: Iterable | None = None,
) -> Badge:
    """자동매매 프로그램이 살아 있는지.

    last_signal: 마지막으로 받은 신호 시각. 아래 무엇이든 됩니다.
                 - status.json 경로 (파일 수정 시각을 씀)
                 - datetime / 유닉스 시각 / ISO 문자열
                 - None (한 번도 못 받음)
    stale_after: 이 초 수보다 오래 신호가 없으면 '멈춤'으로 본다.

    key: alive(작동 중) · stale(멈춤) · never(응답 없음) · clock(신호 시각이 미래 = 시계 이상)
    장중에 멈춰 있으면 빨강, 장 시간이 아니면 회색입니다. 초록은 '작동 중'일 때뿐입니다.
    수능날처럼 장 시간이 바뀌는 날은 market=market_phase(..., special_sessions=...) 를 넘기세요.
    """
    now = _now(now)
    market = market or market_phase(now, holidays)
    in_session = market.key == "open"
    last = _to_dt(last_signal)

    if last is not None and (last - now).total_seconds() > stale_after:
        # 신호 시각이 지금보다 한참 뒤 = 시계/시간대가 어긋남. 살아 있다는 증거가 못 되므로 초록 금지.
        return Badge(
            f"자동매매 신호 시각 이상 — {_hm(last, now)} (지금보다 늦음)",
            "danger" if in_session else "warn",
            "신호 시각이 지금보다 늦게 찍혀 있어 자동매매가 살아 있는지 알 수 없습니다. "
            "PC 시계와 시간대(시각 뒤의 Z 표기 등)를 확인하세요.",
            "clock",
        )

    if last is None:
        if in_session:
            return Badge(
                "자동매매 꺼짐 — 응답 없음",
                "danger",
                "장중인데 자동매매 프로그램이 응답하지 않습니다. 지금은 매수·매도·손절이 모두 멈춰 있습니다. "
                "PC에서 자동매매 프로그램을 켜 주세요. (켜지면 이 표시가 저절로 바뀝니다)",
                "never",
            )
        return Badge("자동매매 쉬는 중 (장 시간 아님)", "info", "", "never")

    age = max(0.0, (now - last).total_seconds())
    if age <= stale_after:
        return Badge(f"자동매매 작동 중 · {_dur(age)} 전 신호", "ok", "", "alive")

    if in_session:
        return Badge(
            f"자동매매 멈춤 — 마지막 신호 {_hm(last, now)} ({_dur(age)} 전)",
            "danger",
            "장중인데 자동매매 프로그램의 신호가 끊겼습니다. 지금은 매수·매도·손절이 모두 멈춰 있습니다. "
            "PC에서 프로그램 창이 살아 있는지 확인하고, 꺼져 있으면 다시 켜 주세요.",
            "stale",
        )
    return Badge(f"자동매매 쉬는 중 · 마지막 신호 {_hm(last, now)}", "info", "", "stale")


def _alive(engine) -> bool:
    if isinstance(engine, Badge):
        return engine.key == "alive"
    return bool(engine)


# ============================================================ ③ 긴급정지(킬스위치)
def killswitch_badge(engine, tripped: bool | None = None, balance_ok: bool | None = True) -> Badge:
    """긴급정지(킬스위치) 상태.

    engine    : engine_badge() 결과 또는 True/False(살아 있음)
    tripped   : True = 긴급정지 걸림(신규 매수 멈춤), False = 안 걸림, None = 모름
    balance_ok: 한투 잔고 조회 성공 여부. True 가 아니면(실패·모름) 손실률 기준을 믿을 수 없다.

    규칙: 프로그램 신호가 없거나 잔고를 확인하지 못했으면 절대 초록이 아니다.
    """
    if not _alive(engine):
        return Badge("긴급정지 확인 불가", "info", "자동매매 프로그램 신호가 없어 긴급정지 상태를 알 수 없습니다.", "unknown")
    if tripped is None:
        return Badge("긴급정지 확인 불가", "info", "자동매매 프로그램이 긴급정지 상태를 보내 주지 않았습니다.", "unknown")
    if tripped:
        hint = "손실 한도에 걸려 오늘은 새로 사지 않습니다."
        if balance_ok is True:
            hint += " 보유 종목 청산·손절은 계속됩니다."
        else:
            hint += " 단, 잔고를 확인하지 못해 손절은 보류 중일 수 있습니다. 한국투자증권 앱에서 확인하세요."
        return Badge("긴급정지 발동 — 신규 매수 멈춤", "danger", hint, "tripped")
    if balance_ok is False:
        return Badge(
            "긴급정지 일부만 작동",
            "warn",
            "한투 잔고 조회가 실패해서 손실률(%) 기준은 쓰지 못하고 금액 기준만 지키고 있습니다.",
            "partial",
        )
    if balance_ok is not True:
        return Badge(
            "긴급정지 일부만 확인됨",
            "warn",
            "잔고 정보를 받지 못해 손실률(%) 기준이 작동하는지 알 수 없습니다.",
            "partial",
        )
    return Badge("긴급정지 대기 중 (정상)", "ok", "손실 한도에 걸리면 자동으로 신규 매수를 멈춥니다.", "armed")


# ============================================================ ④ 손절
def stoploss_badge(engine, *, enabled: bool = True, balance_ok: bool | None = True) -> Badge:
    """손절이 지금 실제로 돌고 있는지.

    2026-11-11 로그: 잔고 조회가 실패하면 프로그램이 '신선도 검사'로 손절 판정을 스스로 미룬다.
    프로그램은 켜져 있어도 손절은 멈춘 상태가 되므로 따로 알려야 한다.
    """
    if not _alive(engine):
        if not isinstance(engine, Badge):
            # True/False 만 받았으면 장 시간인지 모르므로 '장 시간 아님'이라고 지어내지 않는다.
            return Badge("손절 작동 안 함 — 자동매매 신호 없음", "warn", "자동매매 프로그램 신호가 없어 손절이 돌지 않습니다.", "off")
        if engine.level == "danger":
            return Badge("손절 작동 안 함 — 자동매매 멈춤", "danger", "자동매매가 멈춰 있어 손절도 돌지 않습니다. 한국투자증권 앱에서 직접 확인하세요.", "off")
        return Badge("손절 대기 (장 시간 아님)", "info", "", "idle")
    if not enabled:
        return Badge("손절 꺼짐 (설정)", "warn", "설정에서 손절을 꺼 두었습니다. 손실이 커져도 자동으로 팔지 않습니다.", "disabled")
    if balance_ok is False:
        return Badge(
            "손절 보류 중 — 잔고 조회 실패",
            "danger",
            "잔고를 확인하지 못해 프로그램이 안전을 위해 손절 판정을 미루고 있습니다. "
            "한국투자증권 앱에서 보유 종목을 직접 확인하세요. 계속 실패하면 한투 모의투자 신청 상태(기간 만료 등)를 확인하세요.",
            "held",
        )
    if balance_ok is not True:
        return Badge(
            "손절 상태 확인 불가 — 잔고 정보 없음",
            "warn",
            "잔고 정보를 받지 못했습니다. 잔고가 오래되면 프로그램이 손절 판정을 미룰 수 있으니 한국투자증권 앱에서 확인하세요.",
            "unknown",
        )
    return Badge("손절 작동 중", "ok", "", "on")


# ============================================================ ⑤ 보유 종목
def holdings_badge(
    balance_ok: bool | None,
    count: int | None = None,
    *,
    eval_pnl: float | None = None,
    outside_watch: int = 0,
    as_of=None,
    now=None,
) -> Badge:
    """보유 종목 칸에 쓸 문구.

    '보유 종목 없음'은 잔고 조회에 성공했고, 정말 0종목이고, 평가손익도 0일 때만 나온다.
    """
    now = _now(now)
    when = _to_dt(as_of)
    basis = f" ({_hm(when, now)} 한투 잔고 기준)" if when else ""
    eval_pnl = _finite(eval_pnl)
    count = _finite(count)
    has_pnl = eval_pnl is not None and round(eval_pnl) != 0

    if not balance_ok or count is None:
        hint = (
            "한투 잔고 조회가 실패했습니다." if not balance_ok else "보유 종목 수를 받지 못했습니다."
        ) + " 보유 주식이 없다는 뜻이 아닙니다."
        if has_pnl:
            hint += f" 마지막으로 받은 평가손익이 {fmt_won(eval_pnl)}이므로 보유 주식이 있습니다."
        hint += " 한국투자증권 앱에서 직접 확인하세요."
        return Badge("보유 종목을 불러오지 못했습니다", "danger", hint, "unknown")

    count = int(count)
    if count == 0:
        if has_pnl:
            return Badge(
                "잔고 숫자가 서로 맞지 않습니다",
                "warn",
                f"보유 0종목인데 평가손익이 {fmt_won(eval_pnl)}입니다. 잔고를 다시 불러와 주세요.",
                "mismatch",
            )
        return Badge(f"보유 종목 없음{basis}", "info", "", "none")

    text = f"보유 {count}종목"
    if outside_watch:
        text += f" · 그중 {outside_watch}종목 감시 밖"
    return Badge(text + basis, "warn" if outside_watch else "info", "", "some")


def _code(c) -> str:
    """종목코드를 6자리 문자열로. 660 / 660.0(판다스) / '660' → '000660'."""
    if isinstance(c, float) and c.is_integer():
        c = int(c)
    s = str(c).strip()
    return s.zfill(6) if s.isdigit() else s


def unprotected_badge(held: Iterable, watch: Iterable, *, names: Mapping | None = None) -> Badge | None:
    """보유 중인데 감시 목록에 없는 종목 = 실시간 시세가 없어 손절이 돌지 않는 종목.

    held  : 보유 종목코드들 (예: ["000660", "036540"])
    watch : 감시(실시간 등록) 종목코드들
    names : {코드: 종목명} — 있으면 이름도 같이 보여 준다
    없으면 None 을 돌려준다(띄울 경고 없음).
    """
    watch_set = {_code(c) for c in watch}
    seen, missing = set(), []
    for c in held:
        c = _code(c)
        if c not in watch_set and c not in seen:
            seen.add(c)
            missing.append(c)
    if not missing:
        return None
    nm = {_code(k): v for k, v in (names or {}).items()}
    items = ", ".join(f"{nm[c]}({c})" if c in nm else c for c in missing)
    return Badge(
        f"손절 보호 안 되는 보유 종목 {len(missing)}개",
        "danger",
        f"{items} — 실시간 시세를 받지 않아 손절(하드·추적·시간)이 작동하지 않습니다. "
        "'지정 종목만 모드'를 끄거나(config.json 의 UNIVERSE_FIXED_ONLY 를 false 로) 한국투자증권 앱에서 직접 관리하세요.",
        "unprotected",
    )


# ============================================================ ⑥ 감시 종목 / 오늘의 자리
def watch_badge(
    count: int,
    *,
    max_watch: int = 20,
    max_slots: int = 10,
    from_scan: int | None = None,
    fixed: int | None = None,
) -> Badge:
    """'감시 종목 1 / 최대 20' — 지금 개수와 상한을 같이 보여 준다."""
    count = int(_finite(count) or 0)
    detail = []
    if from_scan is not None:
        detail.append(f"밤스캔 {from_scan}개")
    if fixed is not None:
        detail.append(f"고정 {fixed}개")
    text = f"감시 종목 {count} / 최대 {max_watch}" + (f" ({' · '.join(detail)})" if detail else "")
    if count == 0:
        return Badge(text, "danger", "감시 종목이 없어 오늘은 아무것도 사지 않습니다.", "empty")
    if count < max_slots:
        return Badge(text, "warn", f"감시 종목이 {count}개뿐이라 오늘은 최대 {count}종목만 살 수 있습니다.", "few")
    return Badge(text, "info", "", "ok")


def slots_badge(used: int | None, max_slots: int = 10, *, known: bool = True) -> Badge:
    """'오늘 산 종목 0 / 최대 10 · 남은 자리 10' — 사용 수와 남은 수를 둘 다 숫자로 쓴다."""
    used = _finite(used)
    if not known or used is None:
        return Badge("오늘 매수 자리: 확인 불가", "info", "자동매매 프로그램 신호가 없어 알 수 없습니다.", "unknown")
    used = int(used)
    left = max(0, max_slots - used)
    if left == 0:
        return Badge(f"오늘 매수 자리 모두 사용 ({used} / {max_slots}) — 추가 매수 없음", "warn", "", "full")
    return Badge(f"오늘 산 종목 {used} / 최대 {max_slots} · 남은 자리 {left}", "info", "", "open")


# ============================================================ ⑦ 밤스캔
def scan_badge(
    scan_date=None,
    *,
    today=None,
    holidays: Iterable | None = None,
    fixed_only: bool = False,
    candidates: int | None = None,
    engine=None,
) -> Badge:
    """밤스캔 결과가 오늘 쓸 만큼 새것인지.

    scan_date : 마지막 밤스캔 날짜 (없으면 None 이나 '-')
    fixed_only: '지정 종목만 모드'(config.json UNIVERSE_FIXED_ONLY=true) 이면 True
    engine    : engine_badge() 결과. 넘기면 자동매매가 꺼져 있을 때 초록을 쓰지 않는다.
    기준: 직전 거래일 장 마감 뒤에 돈 결과여야 '새것'.
    """
    today = _to_date(today) if today is not None else now_kst().date()
    hs = _holiday_set(holidays)

    if fixed_only:
        return Badge(
            "지정 종목만 모드 — 밤스캔·보유 종목 감시 안 함",
            "warn",
            "설정에 적은 종목만 감시합니다. 밤스캔 후보와 보유 종목은 감시하지 않아 보유 종목 손절이 돌지 않습니다. "
            "해제: config.json 의 UNIVERSE_FIXED_ONLY 를 false 로 바꾸고 자동매매를 다시 켜세요.",
            "fixed_only",
        )

    d = _to_date(scan_date)
    if d is None:
        return Badge(
            "밤스캔 기록 없음 — 새 후보 0개",
            "danger",
            "밤스캔이 돈 기록이 없습니다. 장 마감 후 '장후_일괄실행'이 돌았는지 logs 폴더의 장후일괄_*.txt 를 확인하세요. "
            "오늘은 고정 종목만 감시합니다.",
            "none",
        )

    expected = prev_trading_day(today, hs)
    cand = f" · 후보 {candidates}개" if candidates is not None else ""
    if d >= expected:
        if d == today - timedelta(days=1):
            when = f"어젯밤({d:%m-%d})"
        elif d == expected:
            when = f"직전 거래일({d:%m-%d})"
        else:
            when = f"{d:%m-%d}"
        level = "ok" if engine is None or _alive(engine) else "info"
        return Badge(f"밤스캔 {when} 결과 사용 중{cand}", level, "", "fresh")

    # expected 가 1거래일 전이므로, d 가 그보다 몇 거래일 더 앞인지 + 1
    gap = _trading_days_between(d, expected, hs) + 1
    return Badge(
        f"밤스캔 결과가 오래됨 — 마지막 {d:%m-%d} ({gap}거래일 전){cand}",
        "warn",
        f"{expected:%m-%d} 장 마감 후 밤스캔이 돌지 않았습니다. logs 폴더의 장후일괄_{expected:%Y%m%d}_*.txt 를 확인하세요.",
        "stale",
    )


# ============================================================ ⑧ 숫자의 기준 시각
def freshness_badge(as_of, *, now=None, stale_after: float = 60, source: str = "한투 잔고") -> Badge:
    """'한투 잔고 14:26:05 기준 (3초 전)' — 숫자가 언제 값인지 붙여 준다.

    '1초 푸시' 화면이라도 원본 숫자가 멈춰 있으면 아무 소용이 없으므로,
    stale_after 초가 넘으면 주황으로 '갱신 안 됨'을 표시한다.
    """
    now = _now(now)
    when = _to_dt(as_of)
    if when is None:
        return Badge(f"{source} 기준 시각 없음", "warn", "이 숫자가 언제 값인지 알 수 없습니다.", "unknown")
    raw = (now - when).total_seconds()
    if raw < -stale_after:
        return Badge(
            f"{source} 기준 시각 이상 ({_hm(when, now)}, 지금보다 늦음)",
            "warn",
            "기준 시각이 지금보다 늦게 찍혀 있어 언제 값인지 알 수 없습니다. PC 시계와 시간대를 확인하세요.",
            "unknown",
        )
    age = max(0.0, raw)
    if age <= stale_after:
        return Badge(f"{source} {when:%H:%M:%S} 기준 ({_dur(age)} 전)", "info", "", "fresh")
    return Badge(f"{source} {_hm(when, now)} 기준 · {_dur(age)} 전 값 (갱신 안 됨)", "warn", "", "stale")


def account_badge(is_mock: bool) -> Badge:
    """모의투자/실전투자를 모든 화면에 붙여 둔다 (실전 전환 후 착각 방지)."""
    if is_mock:
        return Badge("모의투자", "warn", "연습 계좌입니다. 실제 돈이 오가지 않습니다.", "mock")
    return Badge("실전투자 · 실제 돈", "danger", "실제 계좌로 주문이 나갑니다.", "real")


def top_alerts(*badges) -> list[Badge]:
    """맨 위 경고 띠에 올릴 것만 골라 빨강 → 주황 순으로 돌려준다. None 은 무시한다."""
    flat = []
    for b in badges:
        if isinstance(b, (list, tuple)):
            flat.extend(b)
        else:
            flat.append(b)
    hits = [b for b in flat if isinstance(b, Badge) and b.level in ("danger", "warn")]
    return sorted(hits, key=lambda b: _LEVEL_ORDER[b.level])


# ============================================================ ⑨ 손익 색·숫자
def pnl_class(value, decimals: int = 0) -> str:
    """손익 색 클래스. 한국식: 이익 빨강(pnl-up) · 손실 파랑(pnl-down) · 0 은 중립(pnl-zero).

    화면에 보이는 자릿수로 반올림한 뒤 판단한다 (-0.001% 가 '0.00%' 로 보이면 중립).
    """
    v = _finite(value)
    if v is None:
        return "pnl-zero"
    r = round(float(v), decimals)
    if r > 0:
        return "pnl-up"
    if r < 0:
        return "pnl-down"
    return "pnl-zero"


def fmt_won(value, sign: bool = True) -> str:
    """-23236493 → '-23,236,493원', 120000 → '+120,000원', 0 → '0원'. 숫자가 아니면 '-'."""
    if value is None:
        return "0원"
    f = _finite(value)
    if f is None:
        return "-"
    v = int(round(float(f)))
    if v == 0:
        return "0원"
    s = f"{abs(v):,}원"
    if v < 0:
        return "-" + s
    return ("+" + s) if sign else s


def fmt_pct(value, decimals: int = 2, sign: bool = True) -> str:
    """-4.647 → '-4.65%', 0.001 → '0.00%' (음수 0 표시 안 함). 숫자가 아니면 '-'."""
    if value is None:
        value = 0
    f = _finite(value)
    if f is None:
        return "-"
    r = round(float(f), decimals)
    if r == 0:
        return f"{0:.{decimals}f}%"
    s = f"{abs(r):.{decimals}f}%"
    if r < 0:
        return "-" + s
    return ("+" + s) if sign else s
