import math
import pytest
from utils.ruin import edge, kelly, ruin_formula, ruin_monte_carlo, ruin_report, upper95_zero, fmt_pct


def test_3_9_화면값과_일치():
    # 3-9 화면: p=55%, b=1.5, N=20 → 0.005%, 약 19,953번에 한 번
    q = ruin_formula(0.55, 1.5, 20)
    assert q == pytest.approx(5.012e-5, rel=1e-3)
    assert round(1 / q) == pytest.approx(19952, abs=5)
    assert kelly(0.55, 1.5) == pytest.approx(0.25)


def test_대칭_게임은_고전공식과_같음():
    # b=1 이면 고전 공식 ((1-p)/p)^N
    assert ruin_formula(0.55, 1.0, 10) == pytest.approx((0.45 / 0.55) ** 10, rel=1e-6)


def test_기대값_마이너스면_반드시_파산():
    assert edge(0.36, 1.724) < 0
    assert ruin_formula(0.36, 1.724, 20) == 1.0


def test_3_5_화면값_근처():
    # 3-5 실제 성적(36%, 1.724)을 자본 20칸, 430번 매매로 → 53.3% 근처
    q = ruin_monte_carlo(0.36, 1.724, 20, 430, runs=20000, seed=1)
    assert 0.50 < q < 0.60


def test_시뮬레이션이_공식에_수렴():
    q_f = ruin_formula(0.52, 1.0, 5)
    q_mc = ruin_monte_carlo(0.52, 1.0, 5, 3000, runs=20000, seed=2)
    assert q_mc == pytest.approx(q_f, abs=0.02)


def test_보고서_조건문장():
    r = ruin_report(0.36, 1.724, 20, 430, runs=3000)
    assert "430번 매매" in r["condition"] and "자본의 5.0%" in r["condition"]
    assert "반드시 파산" in r["verdict"] and "36.7%" in r["verdict"]


def test_보조함수():
    assert upper95_zero(2000) == pytest.approx(0.0014967, rel=1e-3)
    assert fmt_pct(0.533) == "53.3%" and fmt_pct(5.012e-5) == "0.005%" and fmt_pct(0.0015) == "0.15%"
    with pytest.raises(ValueError):
        ruin_formula(1.2, 1, 1)
