# pricing_engine.py
"""
KOSPI 200 옵션 프라이싱 엔진.

핵심 기능
- Black-Scholes-Merton 가격 산출(Call/Put)
- 5대 Greeks 산출
- 내재변동성(Implied Volatility) 역산
- European Option Crank-Nicolson FDM 검증기

주의
- 본 모듈은 학습/포트폴리오 목적의 연구용 코드입니다.
- 실제 매매에는 호가, 체결 가능성, 증거금, 슬리피지, 세금/수수료가 추가로 반영되어야 합니다.
"""

from __future__ import annotations

from typing import Dict, Literal

import numpy as np
from scipy.optimize import brentq
from scipy.stats import norm

OptionType = Literal["C", "P", "call", "put", "CALL", "PUT"]


def normalize_option_type(option_type: OptionType) -> str:
    """옵션 타입을 내부 표준값 C/P로 변환합니다."""
    value = str(option_type).strip().upper()
    if value in {"C", "CALL", "콜", "콜옵션"}:
        return "C"
    if value in {"P", "PUT", "풋", "풋옵션"}:
        return "P"
    raise ValueError("option_type은 'C', 'P', 'call', 'put' 중 하나여야 합니다.")


def _validate_positive(name: str, value: float) -> None:
    if value <= 0:
        raise ValueError(f"{name}은 0보다 커야 합니다. 입력값: {value}")


def intrinsic_value(S: float, K: float, option_type: OptionType = "C") -> float:
    """만기 시점의 내재가치 또는 무만기 경계값을 계산합니다."""
    option_type = normalize_option_type(option_type)
    if option_type == "C":
        return max(float(S) - float(K), 0.0)
    return max(float(K) - float(S), 0.0)


def _d1_d2(S: float, K: float, T: float, r: float, sigma: float, q: float = 0.0) -> tuple[float, float]:
    _validate_positive("S", S)
    _validate_positive("K", K)
    _validate_positive("T", T)
    _validate_positive("sigma", sigma)

    sqrt_t = np.sqrt(T)
    d1 = (np.log(S / K) + (r - q + 0.5 * sigma**2) * T) / (sigma * sqrt_t)
    d2 = d1 - sigma * sqrt_t
    return float(d1), float(d2)


def bs_price(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    option_type: OptionType = "C",
    q: float = 0.0,
) -> float:
    """
    Black-Scholes-Merton 옵션 가격을 계산합니다.

    Parameters
    ----------
    S : float
        기초자산 가격
    K : float
        행사가격
    T : float
        잔존만기(연 단위)
    r : float
        무위험이자율(연속복리)
    sigma : float
        변동성
    option_type : {"C", "P", "call", "put"}
        옵션 타입
    q : float
        배당수익률 또는 편의수익률. 지수 옵션에서는 필요 시 0으로 둡니다.
    """
    option_type = normalize_option_type(option_type)

    if T <= 0:
        return intrinsic_value(S, K, option_type)

    d1, d2 = _d1_d2(S, K, T, r, sigma, q)
    discounted_spot = S * np.exp(-q * T)
    discounted_strike = K * np.exp(-r * T)

    if option_type == "C":
        return float(discounted_spot * norm.cdf(d1) - discounted_strike * norm.cdf(d2))
    return float(discounted_strike * norm.cdf(-d2) - discounted_spot * norm.cdf(-d1))


def bs_call(S: float, K: float, T: float, r: float, sigma: float, q: float = 0.0) -> float:
    """기존 코드 호환용 콜옵션 가격 함수."""
    return bs_price(S, K, T, r, sigma, option_type="C", q=q)


def bs_put(S: float, K: float, T: float, r: float, sigma: float, q: float = 0.0) -> float:
    """풋옵션 가격 함수."""
    return bs_price(S, K, T, r, sigma, option_type="P", q=q)


def bs_greeks(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    option_type: OptionType = "C",
    q: float = 0.0,
) -> Dict[str, float]:
    """
    Black-Scholes-Merton 5대 Greeks를 계산합니다.

    반환값 기준
    - Delta/Gamma: 기초자산 1pt 변화 기준
    - Theta: 연 단위 시간가치 변화
    - ThetaDaily: 1일 경과 기준 시간가치 변화
    - Vega: 변동성 1.00 변화 기준
    - VegaPer1Pct: 변동성 1%p 변화 기준
    - Rho: 금리 1.00 변화 기준
    - RhoPer1Pct: 금리 1%p 변화 기준
    """
    option_type = normalize_option_type(option_type)

    if T <= 0:
        return {
            "Delta": 0.0,
            "Gamma": 0.0,
            "Theta": 0.0,
            "ThetaDaily": 0.0,
            "Vega": 0.0,
            "VegaPer1Pct": 0.0,
            "Rho": 0.0,
            "RhoPer1Pct": 0.0,
        }

    d1, d2 = _d1_d2(S, K, T, r, sigma, q)
    sqrt_t = np.sqrt(T)
    pdf_d1 = norm.pdf(d1)
    discounted_spot_factor = np.exp(-q * T)
    discounted_strike_factor = np.exp(-r * T)

    gamma = discounted_spot_factor * pdf_d1 / (S * sigma * sqrt_t)
    vega = S * discounted_spot_factor * sqrt_t * pdf_d1

    if option_type == "C":
        delta = discounted_spot_factor * norm.cdf(d1)
        theta = (
            -(S * discounted_spot_factor * pdf_d1 * sigma) / (2 * sqrt_t)
            - r * K * discounted_strike_factor * norm.cdf(d2)
            + q * S * discounted_spot_factor * norm.cdf(d1)
        )
        rho = K * T * discounted_strike_factor * norm.cdf(d2)
    else:
        delta = discounted_spot_factor * (norm.cdf(d1) - 1)
        theta = (
            -(S * discounted_spot_factor * pdf_d1 * sigma) / (2 * sqrt_t)
            + r * K * discounted_strike_factor * norm.cdf(-d2)
            - q * S * discounted_spot_factor * norm.cdf(-d1)
        )
        rho = -K * T * discounted_strike_factor * norm.cdf(-d2)

    return {
        "Delta": float(delta),
        "Gamma": float(gamma),
        "Theta": float(theta),
        "ThetaDaily": float(theta / 365.0),
        "Vega": float(vega),
        "VegaPer1Pct": float(vega * 0.01),
        "Rho": float(rho),
        "RhoPer1Pct": float(rho * 0.01),
    }


def bs_greeks_call(S: float, K: float, T: float, r: float, sigma: float, q: float = 0.0) -> Dict[str, float]:
    """기존 코드 호환용 콜옵션 Greeks 함수."""
    return bs_greeks(S, K, T, r, sigma, option_type="C", q=q)


def implied_volatility(
    market_price: float,
    S: float,
    K: float,
    T: float,
    r: float,
    option_type: OptionType = "C",
    q: float = 0.0,
    initial_vol: float = 0.20,
    tol: float = 1e-6,
    max_iter: int = 100,
    lower: float = 1e-6,
    upper: float = 5.0,
) -> float:
    """
    시장가격으로부터 내재변동성을 역산합니다.

    Newton-Raphson으로 먼저 탐색하고, 발산 가능성이 있으면 Brent 방법으로 보정합니다.
    가격이 무차익 경계보다 낮거나 수치적으로 해가 없으면 np.nan을 반환합니다.
    """
    option_type = normalize_option_type(option_type)

    if T <= 0 or market_price <= 0:
        return float("nan")

    lower_bound = intrinsic_value(S, K, option_type)
    if market_price < lower_bound - 1e-8:
        return float("nan")

    sigma = float(initial_vol)

    for _ in range(max_iter):
        price = bs_price(S, K, T, r, sigma, option_type=option_type, q=q)
        diff = price - market_price

        if abs(diff) < tol:
            return float(sigma)

        vega = bs_greeks(S, K, T, r, sigma, option_type=option_type, q=q)["Vega"]
        if abs(vega) < 1e-10:
            break

        next_sigma = sigma - diff / vega
        if not np.isfinite(next_sigma) or next_sigma <= lower or next_sigma >= upper:
            break
        sigma = float(next_sigma)

    def objective(vol: float) -> float:
        return bs_price(S, K, T, r, vol, option_type=option_type, q=q) - market_price

    try:
        if objective(lower) * objective(upper) > 0:
            return float("nan")
        return float(brentq(objective, lower, upper, xtol=tol, maxiter=max_iter))
    except ValueError:
        return float("nan")


def implied_volatility_call(
    market_price: float,
    S: float,
    K: float,
    T: float,
    r: float,
    tol: float = 1e-5,
    max_iter: int = 100,
    q: float = 0.0,
) -> float:
    """기존 코드 호환용 콜옵션 IV 함수."""
    return implied_volatility(
        market_price,
        S,
        K,
        T,
        r,
        option_type="C",
        q=q,
        tol=tol,
        max_iter=max_iter,
    )


def fdm_crank_nicolson(
    S0: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    option_type: OptionType = "C",
    q: float = 0.0,
    M: int = 400,
    N: int = 400,
    S_max: float | None = None,
) -> float:
    """
    European option 가격을 Crank-Nicolson 유한차분법으로 계산합니다.

    BSM closed-form과의 교차검증용으로 사용하기 좋습니다.
    """
    option_type = normalize_option_type(option_type)

    if T <= 0:
        return intrinsic_value(S0, K, option_type)

    if M < 5 or N < 5:
        raise ValueError("M과 N은 최소 5 이상이어야 합니다.")

    S_max = float(S_max or max(4 * K, 2 * S0))
    dt = T / N

    grid_S = np.linspace(0.0, S_max, M + 1)
    values = np.maximum(grid_S - K, 0.0) if option_type == "C" else np.maximum(K - grid_S, 0.0)

    i = np.arange(1, M)
    alpha = 0.25 * dt * ((sigma**2) * (i**2) - (r - q) * i)
    beta = -0.5 * dt * ((sigma**2) * (i**2) + r)
    gamma = 0.25 * dt * ((sigma**2) * (i**2) + (r - q) * i)

    A = np.diag(1.0 - beta)
    A += np.diag(-alpha[1:], k=-1)
    A += np.diag(-gamma[:-1], k=1)

    B = np.diag(1.0 + beta)
    B += np.diag(alpha[1:], k=-1)
    B += np.diag(gamma[:-1], k=1)

    def lower_boundary(tau: float) -> float:
        if option_type == "C":
            return 0.0
        return K * np.exp(-r * tau)

    def upper_boundary(tau: float) -> float:
        if option_type == "C":
            return S_max * np.exp(-q * tau) - K * np.exp(-r * tau)
        return 0.0

    for step in range(N):
        tau_old = step * dt
        tau_new = (step + 1) * dt

        rhs = B @ values[1:M]
        rhs[0] += alpha[0] * (lower_boundary(tau_old) + lower_boundary(tau_new))
        rhs[-1] += gamma[-1] * (upper_boundary(tau_old) + upper_boundary(tau_new))

        values[1:M] = np.linalg.solve(A, rhs)
        values[0] = lower_boundary(tau_new)
        values[M] = upper_boundary(tau_new)

    return float(np.interp(S0, grid_S, values))


def fdm_crank_nicolson_call(S0: float, K: float, T: float, r: float, sigma: float, M: int = 400, N: int = 400) -> float:
    """기존 코드 호환용 콜옵션 FDM 함수."""
    return fdm_crank_nicolson(S0, K, T, r, sigma, option_type="C", M=M, N=N)
