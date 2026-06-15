# main.py
"""
KOSPI 200 옵션 프라이싱, 델타 헤징, 채권가격 산정 통합 실행 스크립트.

기본 실행
    python main.py
    실행 후 `옵션산정` 또는 `채권산정` 입력

바로 실행
    python main.py 옵션산정
    python main.py 채권산정
    python main.py --mode option
    python main.py --mode bond

옵션 모드 선택 실행
    python main.py 옵션산정 --data data_0020_20260414.csv
    python main.py 옵션산정 --source api --api-config api_config.json
    python main.py 옵션산정 --plot
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from bond_pricing import run_bond_pricing_cli
from data_scraper import (
    DEFAULT_API_CONFIG_FILE,
    DEFAULT_DATA_FILE,
    build_iv_table,
    get_krx_kospi200_options,
    infer_underlying_price,
    select_atm_option,
)
from hedging_simulator import HedgeScenario, simulate_delta_hedge, stress_test_grid
from pricing_engine import (
    bs_greeks,
    bs_price,
    fdm_crank_nicolson,
    implied_volatility,
)
from visualizer import plot_volatility_surface


OPTION_MODE_ALIASES = {
    "1",
    "option",
    "options",
    "derivative",
    "derivatives",
    "option_pricing",
    "옵션",
    "옵션산정",
    "옵션가격",
    "파생상품",
    "파생상품산정",
}

BOND_MODE_ALIASES = {
    "2",
    "bond",
    "bonds",
    "bond_pricing",
    "fixed_income",
    "채권",
    "채권산정",
    "채권가격",
    "채권가격산정",
    "채권평가",
}


def format_krw(value: float) -> str:
    return f"{value:,.0f}원"


def round_to_tick(value: float, tick: float = 2.5) -> float:
    return round(value / tick) * tick


def print_section(title: str) -> None:
    print("\n" + "=" * 72)
    print(title)
    print("=" * 72)


def resolve_app_mode(mode_text: str | None) -> str | None:
    """사용자 입력을 option/bond 내부 모드명으로 정규화합니다."""
    if mode_text is None:
        return None

    normalized = str(mode_text).strip().lower().replace(" ", "").replace("-", "_")
    if normalized == "":
        return None
    if normalized in OPTION_MODE_ALIASES:
        return "option"
    if normalized in BOND_MODE_ALIASES:
        return "bond"
    return None


def prompt_app_mode() -> str:
    """터미널 입력으로 실행 모드를 선택합니다."""
    print("\n" + "=" * 72)
    print("실행 모드 선택")
    print("=" * 72)
    print("1. 옵션산정: KOSPI 200 옵션 가격, Greeks, IV, 델타 헤징")
    print("2. 채권산정: 채권가격, YTM, 듀레이션, 컨벡서티, DV01")

    try:
        user_input = input("실행할 모드를 입력하세요 [옵션산정/채권산정, 기본값: 옵션산정]: ")
    except EOFError:
        return "option"

    mode = resolve_app_mode(user_input)
    if mode is None:
        print("입력값을 인식하지 못해 기본값인 옵션산정으로 실행합니다.")
        return "option"
    return mode


def pick_scenario_from_data(df: pd.DataFrame) -> dict[str, float | str | None]:
    """
    CSV/API에 실제 옵션 데이터가 있으면 ATM 옵션을 사용하고,
    현재 샘플처럼 선물/스프레드만 있으면 이론 시나리오로 자동 전환합니다.
    """
    underlying = infer_underlying_price(df) or 897.0
    default_strike = round_to_tick(underlying, 2.5)

    scenario = {
        "S0": float(underlying),
        "K": float(default_strike),
        "option_type": "C",
        "market_price": None,
        "source": "fallback_theoretical",
    }

    try:
        atm = select_atm_option(df, underlying_price=underlying, option_type="C")
        market_price = pd.to_numeric(atm.get("종가"), errors="coerce")
        strike = pd.to_numeric(atm.get("strike"), errors="coerce")

        if np.isfinite(market_price) and np.isfinite(strike) and market_price > 0:
            scenario.update(
                {
                    "K": float(strike),
                    "market_price": float(market_price),
                    "source": str(atm.get("종목명", "KRX_ATM_OPTION")),
                }
            )
    except Exception:
        # 저장된 데이터가 선물/스프레드 중심일 때는 여기로 들어옵니다.
        pass

    return scenario


def run_quant_system(
    data_file: str | Path = DEFAULT_DATA_FILE,
    plot: bool = False,
    source: str = "csv",
    api_config: str | Path = DEFAULT_API_CONFIG_FILE,
    api_profile: str = "krx_derivatives",
    target_date: str | None = None,
) -> None:
    print_section("KOSPI 200 Option Pricing & Delta Hedging Simulator")

    data_file = Path(data_file)
    source = source.lower()

    try:
        df_options = get_krx_kospi200_options(
            target_date=target_date,
            file_path=data_file,
            source=source,
            config_path=api_config,
            api_profile=api_profile,
        )
        option_count = int(df_options.get("is_option", pd.Series(dtype=bool)).sum())
        if source == "api":
            print(f"데이터 로드 성공: API profile={api_profile}")
        else:
            print(f"데이터 로드 성공: {data_file.name}")
        print(f"전체 행 수: {len(df_options):,}개 / 인식된 옵션 행 수: {option_count:,}개")
    except FileNotFoundError as exc:
        print(f"데이터 파일 또는 API 설정을 찾지 못했습니다: {exc}")
        print("내장 이론 시나리오로 계산을 진행합니다.")
        df_options = pd.DataFrame()
    except Exception as exc:
        print(f"데이터 로드 중 문제가 발생했습니다: {exc}")
        print("내장 이론 시나리오로 계산을 진행합니다.")
        df_options = pd.DataFrame()

    # 기본 시장 가정
    days_to_expiry = 30
    risk_free_rate = 0.035
    initial_vol = 0.18
    shocked_vol = 0.20
    spot_shock = -0.01
    contracts = 1
    contract_multiplier = 250_000

    if not df_options.empty:
        picked = pick_scenario_from_data(df_options)
        S0 = float(picked["S0"])
        K = float(picked["K"])
        market_price = picked["market_price"]
        data_source = picked["source"]
    else:
        S0 = 897.0
        K = 897.5
        market_price = None
        data_source = "fallback_theoretical"

    T = days_to_expiry / 365.0

    market_iv = implied_volatility(market_price, S0, K, T, risk_free_rate, option_type="C") if market_price else np.nan
    sigma_for_pricing = float(market_iv) if np.isfinite(market_iv) else initial_vol

    bsm_price = bs_price(S0, K, T, risk_free_rate, sigma_for_pricing, option_type="C")
    greeks = bs_greeks(S0, K, T, risk_free_rate, sigma_for_pricing, option_type="C")
    fdm_price = fdm_crank_nicolson(S0, K, T, risk_free_rate, sigma_for_pricing, option_type="C", M=300, N=300)

    print_section("1. 포지션 진입 가정")
    print(f"데이터 소스: {data_source}")
    print(f"기초지수 S0: {S0:,.2f} pt")
    print(f"행사가 K: {K:,.2f} pt")
    print(f"잔존만기: {days_to_expiry}일")
    print(f"무위험금리: {risk_free_rate * 100:.2f}%")
    print(f"적용 변동성: {sigma_for_pricing * 100:.2f}%")
    if market_price is not None:
        print(f"시장가격: {market_price:.4f} pt")
        print(f"시장가격 기반 IV: {market_iv * 100:.2f}%")
    else:
        print("시장가격: 없음 — BSM 이론가격을 진입가격으로 사용")

    print_section("2. Pricing Engine 검증")
    print(f"BSM 이론가격: {bsm_price:.4f} pt")
    print(f"Crank-Nicolson FDM 가격: {fdm_price:.4f} pt")
    print(f"BSM-FDM 차이: {abs(bsm_price - fdm_price):.6f} pt")
    print(f"Delta: {greeks['Delta']:.4f}")
    print(f"Gamma: {greeks['Gamma']:.6f}")
    print(f"Theta/day: {greeks['ThetaDaily']:.6f} pt")
    print(f"Vega/1%p: {greeks['VegaPer1Pct']:.4f} pt")
    print(f"Rho/1%p: {greeks['RhoPer1Pct']:.4f} pt")

    shocked_underlying = S0 * (1 + spot_shock)
    scenario = HedgeScenario(
        initial_underlying=S0,
        shocked_underlying=shocked_underlying,
        strike=K,
        days_to_expiry=days_to_expiry,
        risk_free_rate=risk_free_rate,
        initial_vol=sigma_for_pricing,
        shocked_vol=shocked_vol,
        option_type="C",
        contracts=contracts,
        contract_multiplier=contract_multiplier,
        fee_rate=0.00003,
        slippage_points=0.0,
        market_price=market_price,
    )
    hedge_result = simulate_delta_hedge(scenario)

    print_section("3. 시장 충격 및 델타 헤징 PnL")
    print(f"충격 가정: 기초지수 {spot_shock * 100:.1f}% / IV {shocked_vol * 100:.2f}%")
    print(f"충격 후 기초지수: {shocked_underlying:,.2f} pt")
    print(f"충격 후 옵션가격: {hedge_result['shocked_option_price_pt']:.4f} pt")
    print(f"진입 Delta: {hedge_result['entry_delta']:.4f}")
    print(f"헤지 포지션: {hedge_result['hedge_position_contracts']:.4f} 계약")
    print(f"옵션 손익: {format_krw(hedge_result['option_pnl_krw'])}")
    print(f"헤지 손익: {format_krw(hedge_result['hedge_pnl_krw'])}")
    print(f"거래비용/슬리피지: -{format_krw(hedge_result['transaction_cost_krw'])}")
    print(f"Net PnL: {format_krw(hedge_result['net_pnl_krw'])}")

    print_section("4. 스트레스 테스트")
    grid = stress_test_grid(
        scenario,
        spot_shocks=[-0.03, -0.02, -0.01, 0.00, 0.01],
        vol_shocks=[-0.02, 0.00, 0.02, 0.05],
    )
    grid_df = pd.DataFrame(grid)
    summary = grid_df[["spot_shock_pct", "vol_shock_pctp", "net_pnl_krw"]].copy()
    summary["spot_shock_pct"] = (summary["spot_shock_pct"] * 100).map(lambda x: f"{x:.1f}%")
    summary["vol_shock_pctp"] = (summary["vol_shock_pctp"] * 100).map(lambda x: f"{x:+.1f}%p")
    summary["net_pnl_krw"] = summary["net_pnl_krw"].map(format_krw)
    print(summary.to_string(index=False))

    if plot and not df_options.empty:
        print_section("5. Volatility Surface")
        iv_table = build_iv_table(
            df_options,
            underlying_price=S0,
            risk_free_rate=risk_free_rate,
            days_to_expiry=days_to_expiry,
            option_type="C",
        )

        if not iv_table.empty and len(iv_table) >= 9:
            iv_table["iv"] = iv_table.apply(
                lambda row: implied_volatility(
                    row["market_price"],
                    row["S"],
                    row["K"],
                    row["T"],
                    row["r"],
                    option_type="C",
                ),
                axis=1,
            )
            iv_table = iv_table.dropna(subset=["iv"])

            if len(iv_table) >= 9:
                # 간단 예시: 실제 surface 데이터가 충분할 때만 scatter 성격으로 표시
                K_grid = iv_table["K"].to_numpy().reshape(-1, 1)
                T_grid = iv_table["T"].to_numpy().reshape(-1, 1)
                IV_grid = iv_table["iv"].to_numpy().reshape(-1, 1)
                plot_volatility_surface(K_grid, T_grid, IV_grid)
            else:
                print("IV를 계산할 수 있는 옵션 데이터가 부족해 surface를 생략합니다.")
        else:
            print("옵션 데이터가 부족해 surface를 생략합니다.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="옵션산정 및 채권산정 통합 실행기")
    parser.add_argument("mode_text", nargs="?", help="옵션산정 또는 채권산정")
    parser.add_argument("--mode", default=None, help="option/bond 또는 옵션산정/채권산정")
    parser.add_argument("--data", default=str(DEFAULT_DATA_FILE), help="옵션산정 모드용 KRX CSV 파일 경로")
    parser.add_argument("--source", choices=["csv", "api"], default="csv", help="옵션 데이터 소스")
    parser.add_argument("--api-config", default=str(DEFAULT_API_CONFIG_FILE), help="API 설정 JSON 파일 경로")
    parser.add_argument("--api-profile", default="krx_derivatives", help="API 설정 파일 내 profile 이름")
    parser.add_argument("--target-date", default=None, help="API 조회 기준일. 예: 20260615")
    parser.add_argument("--plot", action="store_true", help="옵션 데이터가 충분할 경우 변동성 곡면 표시")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    mode = resolve_app_mode(args.mode or args.mode_text)

    if mode is None:
        mode = prompt_app_mode()

    if mode == "bond":
        run_bond_pricing_cli()
    else:
        run_quant_system(
            data_file=args.data,
            plot=args.plot,
            source=args.source,
            api_config=args.api_config,
            api_profile=args.api_profile,
            target_date=args.target_date,
        )


if __name__ == "__main__":
    main()
