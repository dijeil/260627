"""파산확률 공용 계산기 — 대시보드의 모든 화면(3-5, 3-8, 3-9)이 이것 하나만 쓴다.

왜 필요한가
    화면마다 '파산확률'이라는 같은 이름으로 서로 다른 조건의 값을 보여 줘서
    3-5·3-8 은 53.3%, 3-9 는 0.005% 처럼 앞뒤가 안 맞아 보였다.
    파산확률은 아래 3가지 조건이 함께 적혀 있어야만 뜻이 생긴다.

      1) 승률 p, 손익비 b  : 어떤 성적의 전략인가 (가상 값? 실제 매매 값?)
      2) 자본단위 N        : 계좌를 N칸으로 나눠 한 번 지면 1칸을 잃는다 (1회 손실 = 자본의 1/N)
      3) 매매 횟수 T       : 몇 번 매매하는 동안인가 (None = 끝없이 계속할 때)

    파산 = 남은 자본이 0칸 이하가 되는 것.

제공 함수
    ruin_formula(p, b, N)                  끝없이 매매할 때의 정확한 값(공식)
    ruin_monte_carlo(p, b, N, T, runs)     T번 매매하는 동안의 값(시뮬레이션)
    ruin_from_trades(r_list, N, T, runs)   실제 매매 결과(R배수 목록)를 섞어서 계산
    ruin_report(p, b, N, T)                화면에 그대로 쓰는 묶음 (값 + 조건 설명 문장)
"""
from __future__ import annotations

import math
import random
from typing import Iterable, Optional, Sequence


def edge(p: float, b: float) -> float:
    """한 번 매매의 기대값(1칸을 걸었을 때). 0 이하면 오래 할수록 잃는 전략."""
    return p * b - (1 - p)


def kelly(p: float, b: float) -> float:
    """켈리 비율 f* = p − (1−p)/b. 0 이하면 '걸지 마라'."""
    return p - (1 - p) / b


def _root(p: float, b: float) -> float:
    """p·s^b + (1−p)/s = 1 의 0<s<1 근. 기대값이 0 이하면 근이 없으므로 1을 돌려준다."""
    if edge(p, b) <= 0:
        return 1.0
    f = lambda s: p * s ** b + (1 - p) / s - 1  # noqa: E731
    lo, hi = 1e-12, 1 - 1e-12
    # f(lo) > 0, f(1⁻) < 0 (기대값 > 0 일 때) → 이분법
    for _ in range(200):
        mid = (lo + hi) / 2
        if f(mid) > 0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def ruin_formula(p: float, b: float, N: float) -> float:
    """끝없이 매매할 때 파산확률 = s^N.  기대값이 0 이하면 언젠가 반드시 파산 → 1.0."""
    _check(p, b, N)
    return _root(p, b) ** N


def ruin_monte_carlo(p: float, b: float, N: float, T: int, runs: int = 20000, seed: Optional[int] = 0) -> float:
    """T번 매매하는 동안 한 번이라도 자본이 0칸 이하가 될 확률 (시뮬레이션)."""
    _check(p, b, N)
    return ruin_from_trades(None, N, T, runs, seed, p=p, b=b)


def ruin_from_trades(r_list: Optional[Sequence[float]], N: float, T: int, runs: int = 20000,
                     seed: Optional[int] = 0, p: float = 0.0, b: float = 0.0) -> float:
    """실제 매매 결과(R배수: 손절 1번 = −1, 손익비 1.7로 익절 = +1.7)를 무작위로 뽑아 T번 매매.

    r_list 가 None 이면 승률 p·손익비 b 의 단순 모델을 쓴다.
    """
    if T <= 0 or runs <= 0:
        raise ValueError("T(매매 횟수)와 runs(시뮬레이션 횟수)는 1 이상이어야 합니다.")
    rng = random.Random(seed)
    if r_list is not None:
        r = [float(x) for x in r_list]
        if not r:
            raise ValueError("매매 결과 목록이 비어 있습니다.")
        draw = lambda: r[rng.randrange(len(r))]  # noqa: E731
    else:
        draw = lambda: b if rng.random() < p else -1.0  # noqa: E731
    hit = 0
    for _ in range(runs):
        cap = float(N)
        for _ in range(T):
            cap += draw()
            if cap <= 0:
                hit += 1
                break
    return hit / runs


def upper95_zero(runs: int) -> float:
    """시뮬레이션에서 0번 파산이 나왔을 때 실제 확률의 95% 상한 (3/n 규칙의 정확한 값)."""
    return 1 - 0.05 ** (1 / runs)


def fmt_pct(x: float) -> str:
    """0.0000501 → '0.005%', 0.533 → '53.3%' 처럼 읽기 쉬운 퍼센트."""
    v = x * 100
    if v == 0:
        return "0%"
    if v >= 1:
        return f"{v:.1f}%"
    digits = -int(math.floor(math.log10(v))) + 1          # 유효숫자 2자리
    return f"{v:.{digits}f}".rstrip("0").rstrip(".") + "%"


def ruin_report(p: float, b: float, N: float, T: Optional[int] = None, source: str = "실제 매매",
                runs: int = 20000) -> dict:
    """화면에 그대로 쓰는 묶음. 값만 보여 주지 말고 반드시 'condition' 문장을 같이 보여 줄 것."""
    _check(p, b, N)
    e = edge(p, b)
    inf = ruin_formula(p, b, N)
    fin = ruin_monte_carlo(p, b, N, T, runs) if T else None
    risk_pct = 100 / N
    cond = (f"[{source}] 승률 {p*100:.1f}% · 손익비 {b:.2f} · 1회 손실 = 자본의 {risk_pct:.1f}%(자본 {N:g}칸)"
            + (f" · {T}번 매매하는 동안" if T else " · 끝없이 계속할 때"))
    if e <= 0:
        verdict = (f"한 번 매매의 기대값이 {e:+.3f}칸(마이너스)이라 계속하면 언젠가 반드시 파산합니다. "
                   f"본전 승률 {1/(1+b)*100:.1f}% 또는 본전 손익비 {(1-p)/p:.2f} 이상이 필요합니다.")
    else:
        verdict = f"기대값 {e:+.3f}칸(플러스). 끝없이 해도 파산할 확률은 {fmt_pct(inf)}입니다."
    return {
        "p": p, "b": b, "N": N, "T": T, "edge": e, "kelly": kelly(p, b),
        "ruin_infinite": inf, "ruin_finite": fin,
        "headline": fmt_pct(fin if fin is not None else inf),
        "condition": cond, "verdict": verdict,
    }


def _check(p: float, b: float, N: float) -> None:
    if not 0 < p < 1:
        raise ValueError("승률 p 는 0과 1 사이여야 합니다 (예: 0.36).")
    if b <= 0:
        raise ValueError("손익비 b 는 0보다 커야 합니다.")
    if N <= 0:
        raise ValueError("자본단위 N 은 0보다 커야 합니다.")


if __name__ == "__main__":  # python -m utils.ruin  → 화면 숫자 대조
    for args in [(0.55, 1.5, 20, None, "3-9 기본값(가상)"), (0.36, 1.724, 20, 430, "3-5 실제")]:
        r = ruin_report(*args)
        print(r["headline"], "|", r["condition"], "|", r["verdict"])
