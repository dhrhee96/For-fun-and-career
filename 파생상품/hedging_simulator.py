# hedging_simulator.py
"""
델타 헤징 및 시장 충격 시나리오 시뮬레이터.

목표
- 옵션 가치 변화
- 선물/지수 헤지 손익
- 거래비용 차감 후 Net PnL
을 분리해서 보여줍니다.

KOSPI 200 옵션/선물은 지수 포인트에 계약승수를 곱해 원화 손익으로 환산합니다.
계약승수, 수수료율, 슬리피지는 증권사/상품/시점에 따라 달라질 수 있으므로 입력값으로 분리했습니다.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict

import numpy as np

from pricing_engine import OptionType, bs_greeks, bs_price, implied_volatility, normalize_option_type


@dataclass(frozen=True)
class HedgeScenario:
    """단일 옵션 포지션의 델타 헤징 시나리오 입력값."""
    initial_underlying: float
    shocked_underlying: float
    strike: float
    days_to_expiry: int
    risk_free_rate: float
    initial_vol: float
    shocked_vol: float
    option_type: OptionType = "C"
    contracts: int = 1
    contract_multiplier: int = 250_000
    fee_rate: float = 0.00003
    slippage_points: float = 0.0
    elapsed_days: int = 0
    market_price: float | None = None


def simulate_delta_hedge(scenario: HedgeScenario) -> Dict[str, float]:
    """
    시장 충격 전후의 옵션·헤지 손익을 계산합니다.

    포지션 가정
    - 옵션 1계약 매수
    - 진입 시점의 Delta만큼 선물/지수 포지션을 반대로 잡아 Delta-neutral에 가깝게 구성
    - Call 매수라면 일반적으로 선물 Short, Put 매수라면 선물 Long 성격의 헤지가 잡힘
    """
    option_type = normalize_option_type(scenario.option_type)
    T0 = scenario.days_to_expiry / 365.0
    T1 = max(scenario.days_to_expiry - scenario.elapsed_days, 0) / 365.0

    theoretical_entry_price = bs_price(
        scenario.initial_underlying,
        scenario.strike,
        T0,
        scenario.risk_free_rate,
        scenario.initial_vol,
        option_type=option_type,
    )
    entry_price = float(scenario.market_price) if scenario.market_price is not None else theoretical_entry_price

    shocked_price = bs_price(
        scenario.shocked_underlying,
        scenario.strike,
        T1,
        scenario.risk_free_rate,
        scenario.shocked_vol,
        option_type=option_type,
    )

    greeks_entry = bs_greeks(
        scenario.initial_underlying,
        scenario.strike,
        T0,
        scenario.risk_free_rate,
        scenario.initial_vol,
        option_type=option_type,
    )
    greeks_after = bs_greeks(
        scenario.shocked_underlying,
        scenario.strike,
        T1,
        scenario.risk_free_rate,
        scenario.shocked_vol,
        option_type=option_type,
    )

    delta = greeks_entry["Delta"]

    # 옵션 매수 포지션의 델타를 중립화하기 위해 반대 방향으로 선물/지수 포지션을 잡음
    hedge_position = -delta * scenario.contracts

    option_pnl_krw = (shocked_price - entry_price) * scenario.contracts * scenario.contract_multiplier
    hedge_pnl_krw = hedge_position * (scenario.shocked_underlying - scenario.initial_underlying) * scenario.contract_multiplier

    option_turnover = (abs(entry_price) + abs(shocked_price)) * scenario.contracts * scenario.contract_multiplier
    hedge_turnover = (
        abs(hedge_position * scenario.initial_underlying)
        + abs(hedge_position * scenario.shocked_underlying)
    ) * scenario.contract_multiplier

    explicit_fees_krw = (option_turnover + hedge_turnover) * scenario.fee_rate
    slippage_krw = abs(scenario.slippage_points) * scenario.contracts * scenario.contract_multiplier
    total_cost_krw = explicit_fees_krw + slippage_krw

    net_pnl_krw = option_pnl_krw + hedge_pnl_krw - total_cost_krw

    return {
        **{f"input_{k}": v for k, v in asdict(scenario).items() if v is not None},
        "option_type_normalized": option_type,
        "entry_option_price_pt": float(entry_price),
        "entry_theoretical_price_pt": float(theoretical_entry_price),
        "shocked_option_price_pt": float(shocked_price),
        "entry_delta": float(delta),
        "post_shock_delta": float(greeks_after["Delta"]),
        "hedge_position_contracts": float(hedge_position),
        "option_pnl_krw": float(option_pnl_krw),
        "hedge_pnl_krw": float(hedge_pnl_krw),
        "transaction_cost_krw": float(total_cost_krw),
        "net_pnl_krw": float(net_pnl_krw),
    }


def stress_test_grid(
    base_scenario: HedgeScenario,
    spot_shocks: list[float] | np.ndarray,
    vol_shocks: list[float] | np.ndarray,
) -> list[Dict[str, float]]:
    """
    지수 충격률과 변동성 충격값을 조합해 스트레스 테스트 결과를 생성합니다.

    spot_shocks: -0.03은 기초자산 3% 하락을 의미
    vol_shocks: 0.05는 변동성 5%p 상승을 의미
    """
    results: list[Dict[str, float]] = []

    for spot_shock in spot_shocks:
        for vol_shock in vol_shocks:
            shocked_underlying = base_scenario.initial_underlying * (1 + float(spot_shock))
            shocked_vol = max(base_scenario.initial_vol + float(vol_shock), 1e-6)

            scenario = HedgeScenario(
                initial_underlying=base_scenario.initial_underlying,
                shocked_underlying=shocked_underlying,
                strike=base_scenario.strike,
                days_to_expiry=base_scenario.days_to_expiry,
                risk_free_rate=base_scenario.risk_free_rate,
                initial_vol=base_scenario.initial_vol,
                shocked_vol=shocked_vol,
                option_type=base_scenario.option_type,
                contracts=base_scenario.contracts,
                contract_multiplier=base_scenario.contract_multiplier,
                fee_rate=base_scenario.fee_rate,
                slippage_points=base_scenario.slippage_points,
                elapsed_days=base_scenario.elapsed_days,
                market_price=base_scenario.market_price,
            )
            row = simulate_delta_hedge(scenario)
            row["spot_shock_pct"] = float(spot_shock)
            row["vol_shock_pctp"] = float(vol_shock)
            results.append(row)

    return results


def calculate_market_iv_if_possible(
    market_price: float | None,
    S: float,
    K: float,
    T: float,
    r: float,
    option_type: OptionType = "C",
) -> float:
    """시장가격이 주어졌을 때만 IV를 계산하고, 없으면 NaN을 반환합니다."""
    if market_price is None:
        return float("nan")

    return implied_volatility(
        market_price=market_price,
        S=S,
        K=K,
        T=T,
        r=r,
        option_type=option_type,
    )
