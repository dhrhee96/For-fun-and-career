# bond_pricing.py
"""
채권 가격 산정 및 금리 민감도 분석 모듈.

핵심 기능
- 고정금리 이표채 가격 산정
- 시장가격 기반 YTM 역산
- Macaulay Duration, Modified Duration, Convexity 계산
- 1bp 금리 변화에 따른 가격 민감도(DV01) 계산
- 간단한 CLI 입력 흐름 제공

주의
- 본 모듈은 학습/포트폴리오 목적의 연구용 코드입니다.
- 실제 채권 평가는 결제일, 직전/차기 이표일, 경과이자, 영업일 조정, 세금, 유동성 프리미엄,
  신용스프레드, 콜/풋 조항 등을 추가로 반영해야 합니다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import numpy as np
import pandas as pd
from scipy.optimize import brentq


@dataclass(frozen=True)
class BondSpec:
    """고정금리 이표채 기본 입력값."""
    face_value: float = 10_000.0
    coupon_rate: float = 0.035
    maturity_years: float = 3.0
    coupon_frequency: int = 2
    redemption_value: float | None = None

    def __post_init__(self) -> None:
        if self.face_value <= 0:
            raise ValueError("face_value는 0보다 커야 합니다.")
        if self.maturity_years <= 0:
            raise ValueError("maturity_years는 0보다 커야 합니다.")
        if self.coupon_frequency <= 0:
            raise ValueError("coupon_frequency는 1 이상이어야 합니다.")
        if self.coupon_rate < 0:
            raise ValueError("coupon_rate는 음수가 될 수 없습니다.")

    @property
    def redemption(self) -> float:
        return float(self.face_value if self.redemption_value is None else self.redemption_value)

    @property
    def total_periods(self) -> int:
        return int(round(self.maturity_years * self.coupon_frequency))

    @property
    def coupon_payment(self) -> float:
        return self.face_value * self.coupon_rate / self.coupon_frequency


def build_cashflow_table(spec: BondSpec) -> pd.DataFrame:
    """채권의 기간별 현금흐름 테이블을 생성합니다."""
    periods = np.arange(1, spec.total_periods + 1)
    times = periods / spec.coupon_frequency
    cashflows = np.full(spec.total_periods, spec.coupon_payment, dtype=float)
    cashflows[-1] += spec.redemption

    return pd.DataFrame(
        {
            "period": periods,
            "time_years": times,
            "cash_flow": cashflows,
        }
    )


def price_bond(spec: BondSpec, ytm: float) -> float:
    """
    YTM을 기준으로 고정금리 이표채 가격을 계산합니다.

    ytm은 연율 기준이며, coupon_frequency와 동일한 복리 주기로 할인합니다.
    """
    if ytm <= -0.999:
        raise ValueError("ytm이 너무 낮습니다. -99.9% 이하의 금리는 허용하지 않습니다.")

    cashflows = build_cashflow_table(spec)
    periods = cashflows["period"].to_numpy(dtype=float)
    cf = cashflows["cash_flow"].to_numpy(dtype=float)
    discount_base = 1 + ytm / spec.coupon_frequency

    if discount_base <= 0:
        raise ValueError("할인계수가 0 이하입니다. ytm과 coupon_frequency를 확인하세요.")

    return float(np.sum(cf / discount_base**periods))


def price_bond_with_table(spec: BondSpec, ytm: float) -> tuple[float, pd.DataFrame]:
    """가격과 현금흐름별 현재가치 테이블을 함께 반환합니다."""
    table = build_cashflow_table(spec)
    discount_base = 1 + ytm / spec.coupon_frequency
    table["discount_factor"] = 1 / discount_base ** table["period"]
    table["present_value"] = table["cash_flow"] * table["discount_factor"]
    price = float(table["present_value"].sum())
    return price, table


def yield_to_maturity_from_price(
    spec: BondSpec,
    market_price: float,
    lower: float = -0.95,
    upper: float = 1.00,
) -> float:
    """시장가격을 만족하는 YTM을 역산합니다."""
    if market_price <= 0:
        raise ValueError("market_price는 0보다 커야 합니다.")

    def objective(rate: float) -> float:
        return price_bond(spec, rate) - market_price

    try:
        return float(brentq(objective, lower, upper, xtol=1e-10, maxiter=200))
    except ValueError as exc:
        raise ValueError("입력 가격을 만족하는 YTM을 찾지 못했습니다. 가격 또는 탐색 범위를 확인하세요.") from exc


def duration_convexity(spec: BondSpec, ytm: float) -> Dict[str, float]:
    """
    Macaulay Duration, Modified Duration, Convexity, DV01을 계산합니다.
    """
    price, table = price_bond_with_table(spec, ytm)
    periods = table["period"].to_numpy(dtype=float)
    times = table["time_years"].to_numpy(dtype=float)
    pv = table["present_value"].to_numpy(dtype=float)

    macaulay_duration = float(np.sum(times * pv) / price)
    modified_duration = float(macaulay_duration / (1 + ytm / spec.coupon_frequency))

    # 이산복리 기준 convexity. 단위는 year^2에 가깝게 해석합니다.
    convexity = float(
        np.sum(
            pv * periods * (periods + 1) / (spec.coupon_frequency**2 * (1 + ytm / spec.coupon_frequency) ** 2)
        )
        / price
    )

    dv01 = float(price * modified_duration * 0.0001)

    return {
        "price": price,
        "macaulay_duration": macaulay_duration,
        "modified_duration": modified_duration,
        "convexity": convexity,
        "dv01": dv01,
    }


def approximate_price_change(price: float, modified_duration: float, convexity: float, delta_y: float) -> Dict[str, float]:
    """Duration + Convexity 근사로 금리 변화에 따른 가격 변화를 계산합니다."""
    duration_effect = -modified_duration * delta_y
    convexity_effect = 0.5 * convexity * delta_y**2
    pct_change = duration_effect + convexity_effect
    price_change = price * pct_change

    return {
        "delta_y": delta_y,
        "duration_effect_pct": duration_effect,
        "convexity_effect_pct": convexity_effect,
        "total_change_pct": pct_change,
        "price_change": price_change,
        "estimated_price": price + price_change,
    }


def run_sample_bond_pricing() -> Dict[str, float]:
    """기본 예시 입력값으로 채권 가격 산정 결과를 반환합니다."""
    spec = BondSpec(face_value=10_000, coupon_rate=0.035, maturity_years=3, coupon_frequency=2)
    ytm = 0.038
    price, _ = price_bond_with_table(spec, ytm)
    risk = duration_convexity(spec, ytm)
    ytm_back = yield_to_maturity_from_price(spec, price)

    return {
        "price": price,
        "ytm": ytm,
        "ytm_back": ytm_back,
        **risk,
    }


def _read_float(prompt: str, default: float) -> float:
    raw = input(f"{prompt} [기본값: {default}]: ").strip()
    if raw == "":
        return float(default)
    return float(raw.replace(",", ""))


def _read_int(prompt: str, default: int) -> int:
    raw = input(f"{prompt} [기본값: {default}]: ").strip()
    if raw == "":
        return int(default)
    return int(raw.replace(",", ""))


def _format_krw(value: float) -> str:
    return f"{value:,.2f}원"


def run_bond_pricing_cli() -> None:
    """터미널에서 바로 사용할 수 있는 채권 가격 산정 입력 흐름입니다."""
    print("\n" + "=" * 72)
    print("채권가격 산정 모드")
    print("=" * 72)
    print("입력을 비우면 기본 예시값으로 계산합니다.")

    try:
        face_value = _read_float("액면가", 10_000)
        coupon_rate_pct = _read_float("표면금리(%)", 3.5)
        maturity_years = _read_float("잔존만기(년)", 3.0)
        coupon_frequency = _read_int("연 이자 지급 횟수: 1=연, 2=반기, 4=분기", 2)
        ytm_pct = _read_float("시장 YTM(%)", 3.8)
        market_price_for_ytm = _read_float("YTM 역산용 시장가격", 9_918.97)
    except ValueError:
        print("입력값을 숫자로 해석하지 못했습니다. 쉼표와 % 기호를 제외하고 다시 입력하세요.")
        return

    spec = BondSpec(
        face_value=face_value,
        coupon_rate=coupon_rate_pct / 100,
        maturity_years=maturity_years,
        coupon_frequency=coupon_frequency,
    )
    ytm = ytm_pct / 100

    price, cashflow_table = price_bond_with_table(spec, ytm)
    risk = duration_convexity(spec, ytm)

    try:
        implied_ytm = yield_to_maturity_from_price(spec, market_price_for_ytm)
    except ValueError:
        implied_ytm = float("nan")

    shock_up_1bp = approximate_price_change(price, risk["modified_duration"], risk["convexity"], 0.0001)
    shock_up_100bp = approximate_price_change(price, risk["modified_duration"], risk["convexity"], 0.01)
    shock_down_100bp = approximate_price_change(price, risk["modified_duration"], risk["convexity"], -0.01)

    print("\n" + "-" * 72)
    print("1. 채권 가격 산정 결과")
    print("-" * 72)
    print(f"액면가: {_format_krw(spec.face_value)}")
    print(f"표면금리: {coupon_rate_pct:.4f}%")
    print(f"YTM: {ytm_pct:.4f}%")
    print(f"잔존만기: {maturity_years:.4f}년")
    print(f"이자 지급 횟수: 연 {coupon_frequency}회")
    print(f"이론가격: {_format_krw(price)}")

    print("\n" + "-" * 72)
    print("2. 금리 민감도")
    print("-" * 72)
    print(f"Macaulay Duration: {risk['macaulay_duration']:.6f}년")
    print(f"Modified Duration: {risk['modified_duration']:.6f}")
    print(f"Convexity: {risk['convexity']:.6f}")
    print(f"DV01: {_format_krw(risk['dv01'])}  # 금리 1bp 변화 시 가격 민감도")
    print(f"+1bp 예상 가격: {_format_krw(shock_up_1bp['estimated_price'])} ({shock_up_1bp['price_change']:+,.4f}원)")
    print(f"+100bp 예상 가격: {_format_krw(shock_up_100bp['estimated_price'])} ({shock_up_100bp['price_change']:+,.4f}원)")
    print(f"-100bp 예상 가격: {_format_krw(shock_down_100bp['estimated_price'])} ({shock_down_100bp['price_change']:+,.4f}원)")

    print("\n" + "-" * 72)
    print("3. 시장가격 기반 YTM 역산")
    print("-" * 72)
    print(f"입력 시장가격: {_format_krw(market_price_for_ytm)}")
    if np.isfinite(implied_ytm):
        print(f"역산 YTM: {implied_ytm * 100:.6f}%")
    else:
        print("역산 YTM: 계산 실패")

    print("\n" + "-" * 72)
    print("4. 현금흐름 현재가치 테이블")
    print("-" * 72)
    display_table = cashflow_table.copy()
    display_table["time_years"] = display_table["time_years"].map(lambda x: f"{x:.4f}")
    display_table["cash_flow"] = display_table["cash_flow"].map(lambda x: f"{x:,.2f}")
    display_table["discount_factor"] = display_table["discount_factor"].map(lambda x: f"{x:.8f}")
    display_table["present_value"] = display_table["present_value"].map(lambda x: f"{x:,.2f}")
    print(display_table.to_string(index=False))
