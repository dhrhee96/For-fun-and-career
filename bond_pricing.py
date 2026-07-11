# bond_pricing.py
"""
채권 가격 산정 및 금리 민감도 분석 모듈.

핵심 기능
- 고정금리 이표채 가격 산정
- Clean Price / Dirty Price / Accrued Interest 분리
- 시장가격 기반 YTM 역산
- Macaulay Duration, Modified Duration, Convexity 계산
- 1bp 금리 변화에 따른 가격 민감도(DV01) 계산
- 간단한 CLI 입력 흐름 제공

주의
- 본 모듈은 학습/포트폴리오 목적의 연구용 코드입니다.
- 실제 채권 평가는 영업일 조정, 휴일 캘린더, 세금, 유동성 프리미엄,
  신용스프레드, 콜/풋 조항 등을 추가로 반영해야 합니다.
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, datetime
from typing import Dict

import numpy as np
import pandas as pd

try:
    from scipy.optimize import brentq
except ModuleNotFoundError:
    def brentq(func, lower: float, upper: float, xtol: float = 1e-10, maxiter: int = 200) -> float:
        """Small bisection fallback used when SciPy is not installed."""

        f_lower = func(lower)
        f_upper = func(upper)
        if f_lower == 0:
            return lower
        if f_upper == 0:
            return upper
        if f_lower * f_upper > 0:
            raise ValueError("Root is not bracketed.")

        lo, hi = lower, upper
        for _ in range(maxiter):
            mid = (lo + hi) / 2
            f_mid = func(mid)
            if abs(f_mid) < xtol or abs(hi - lo) < xtol:
                return mid
            if f_lower * f_mid <= 0:
                hi = mid
                f_upper = f_mid
            else:
                lo = mid
                f_lower = f_mid
        return (lo + hi) / 2


SUPPORTED_DAY_COUNTS = {"ACT/365", "ACT/ACT", "30/360"}


@dataclass(frozen=True)
class BondSpec:
    """고정금리 이표채 기본 입력값."""

    face_value: float = 10_000.0
    coupon_rate: float = 0.035
    maturity_years: float = 3.0
    coupon_frequency: int = 2
    redemption_value: float | None = None
    issue_date: date | str | None = None
    maturity_date: date | str | None = None
    settlement_date: date | str | None = None
    day_count: str = "ACT/365"

    def __post_init__(self) -> None:
        if self.face_value <= 0:
            raise ValueError("face_value는 0보다 커야 합니다.")
        if self.maturity_years <= 0:
            raise ValueError("maturity_years는 0보다 커야 합니다.")
        if self.coupon_frequency <= 0:
            raise ValueError("coupon_frequency는 1 이상이어야 합니다.")
        if 12 % self.coupon_frequency != 0:
            raise ValueError("coupon_frequency는 1, 2, 4, 6, 12처럼 12를 나눌 수 있어야 합니다.")
        if self.coupon_rate < 0:
            raise ValueError("coupon_rate는 음수가 될 수 없습니다.")
        if self.day_count.upper() not in SUPPORTED_DAY_COUNTS:
            raise ValueError(f"지원하지 않는 day_count입니다: {self.day_count}")

    @property
    def redemption(self) -> float:
        return float(self.face_value if self.redemption_value is None else self.redemption_value)

    @property
    def total_periods(self) -> int:
        return int(round(self.maturity_years * self.coupon_frequency))

    @property
    def coupon_payment(self) -> float:
        return self.face_value * self.coupon_rate / self.coupon_frequency

    @property
    def has_date_inputs(self) -> bool:
        return self.maturity_date is not None and self.settlement_date is not None


def _parse_date(value: date | str | None, field_name: str) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        text = value.strip()
        for fmt in ("%Y-%m-%d", "%Y%m%d", "%Y/%m/%d"):
            try:
                return datetime.strptime(text, fmt).date()
            except ValueError:
                pass
    raise ValueError(f"{field_name}은 YYYY-MM-DD, YYYYMMDD, YYYY/MM/DD 형식이어야 합니다.")


def _add_months(day: date, months: int) -> date:
    month_index = day.month - 1 + months
    year = day.year + month_index // 12
    month = month_index % 12 + 1
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(day.day, last_day))


def _day_count_days(start: date, end: date, convention: str) -> int:
    convention = convention.upper()
    if end < start:
        raise ValueError("end date는 start date보다 빠를 수 없습니다.")
    if convention in {"ACT/365", "ACT/ACT"}:
        return (end - start).days
    if convention == "30/360":
        start_day = min(start.day, 30)
        end_day = min(end.day, 30) if start_day == 30 else end.day
        return (end.year - start.year) * 360 + (end.month - start.month) * 30 + (end_day - start_day)
    raise ValueError(f"지원하지 않는 day_count입니다: {convention}")


def _year_fraction(start: date, end: date, convention: str) -> float:
    convention = convention.upper()
    days = _day_count_days(start, end, convention)
    if convention == "ACT/ACT":
        if start.year == end.year:
            return days / (366 if calendar.isleap(start.year) else 365)
        total = 0.0
        current = start
        while current < end:
            next_year = date(current.year + 1, 1, 1)
            segment_end = min(next_year, end)
            total += (segment_end - current).days / (366 if calendar.isleap(current.year) else 365)
            current = segment_end
        return total
    if convention == "30/360":
        return days / 360
    return days / 365


def _date_inputs(spec: BondSpec) -> tuple[date | None, date | None, date | None]:
    issue = _parse_date(spec.issue_date, "issue_date")
    maturity = _parse_date(spec.maturity_date, "maturity_date")
    settlement = _parse_date(spec.settlement_date, "settlement_date")
    if (maturity is None) != (settlement is None):
        raise ValueError("maturity_date와 settlement_date는 함께 입력해야 합니다.")
    if maturity is not None and settlement is not None and settlement > maturity:
        raise ValueError("settlement_date는 maturity_date보다 늦을 수 없습니다.")
    return issue, maturity, settlement


def generate_coupon_schedule(spec: BondSpec) -> pd.DataFrame:
    """만기일에서 역산한 이표 스케줄과 결제일 기준 직전/다음 이표일을 반환합니다."""

    issue, maturity, settlement = _date_inputs(spec)
    if maturity is None or settlement is None:
        raise ValueError("이표 스케줄을 만들려면 maturity_date와 settlement_date가 필요합니다.")

    months = 12 // spec.coupon_frequency
    coupon_dates = [maturity]
    while True:
        previous = _add_months(coupon_dates[-1], -months)
        if issue is not None and previous < issue:
            if issue not in coupon_dates:
                coupon_dates.append(issue)
            break
        if previous <= settlement and (issue is None or previous <= issue):
            coupon_dates.append(previous)
            break
        coupon_dates.append(previous)

    coupon_dates = sorted(set(coupon_dates))
    if settlement in coupon_dates:
        previous_coupon = settlement
        next_candidates = [d for d in coupon_dates if d > settlement]
        next_coupon = next_candidates[0] if next_candidates else settlement
    else:
        previous_candidates = [d for d in coupon_dates if d < settlement]
        next_candidates = [d for d in coupon_dates if d > settlement]
        previous_coupon = previous_candidates[-1] if previous_candidates else _add_months(next_candidates[0], -months)
        next_coupon = next_candidates[0]

    rows = []
    for coupon_date in coupon_dates:
        rows.append(
            {
                "coupon_date": coupon_date,
                "is_previous_coupon": coupon_date == previous_coupon,
                "is_next_coupon": coupon_date == next_coupon,
                "after_settlement": coupon_date > settlement,
            }
        )
    return pd.DataFrame(rows)


def accrued_interest_details(spec: BondSpec) -> Dict[str, float | int | date]:
    """경과이자와 계산에 사용한 이표기간 정보를 반환합니다."""

    _, _, settlement = _date_inputs(spec)
    if settlement is None:
        return {
            "accrued_interest": 0.0,
            "previous_coupon_date": None,
            "next_coupon_date": None,
            "elapsed_days": 0,
            "coupon_period_days": 0,
        }

    schedule = generate_coupon_schedule(spec)
    previous_coupon = schedule.loc[schedule["is_previous_coupon"], "coupon_date"].iloc[0]
    next_coupon = schedule.loc[schedule["is_next_coupon"], "coupon_date"].iloc[0]

    if previous_coupon == settlement:
        elapsed_days = 0
    else:
        elapsed_days = _day_count_days(previous_coupon, settlement, spec.day_count)
    coupon_period_days = _day_count_days(previous_coupon, next_coupon, spec.day_count)
    accrued = 0.0 if coupon_period_days == 0 else spec.coupon_payment * elapsed_days / coupon_period_days

    return {
        "accrued_interest": float(accrued),
        "previous_coupon_date": previous_coupon,
        "next_coupon_date": next_coupon,
        "elapsed_days": int(elapsed_days),
        "coupon_period_days": int(coupon_period_days),
    }


def accrued_interest(spec: BondSpec) -> float:
    """직전 이표일 이후 결제일까지의 경과이자를 계산합니다."""

    return float(accrued_interest_details(spec)["accrued_interest"])


def build_cashflow_table(spec: BondSpec) -> pd.DataFrame:
    """채권의 기간별 현금흐름 테이블을 생성합니다."""

    if spec.has_date_inputs:
        return _build_dated_cashflow_table(spec)

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


def _build_dated_cashflow_table(spec: BondSpec) -> pd.DataFrame:
    _, maturity, settlement = _date_inputs(spec)
    if maturity is None or settlement is None:
        raise ValueError("날짜 기반 현금흐름에는 maturity_date와 settlement_date가 필요합니다.")

    schedule = generate_coupon_schedule(spec)
    future = schedule[schedule["after_settlement"]].copy()
    if future.empty:
        return pd.DataFrame(columns=["period", "time_years", "cash_flow", "coupon_date", "discount_period"])

    cashflows = np.full(len(future), spec.coupon_payment, dtype=float)
    cashflows[-1] += spec.redemption
    future = future.reset_index(drop=True)
    future["period"] = np.arange(1, len(future) + 1)
    future["time_years"] = future["coupon_date"].map(lambda d: _year_fraction(settlement, d, spec.day_count))
    future["cash_flow"] = cashflows

    details = accrued_interest_details(spec)
    remaining_days = _day_count_days(settlement, details["next_coupon_date"], spec.day_count)
    period_days = details["coupon_period_days"]
    first_period = 0.0 if period_days == 0 else remaining_days / period_days
    future["discount_period"] = first_period + np.arange(len(future))

    return future[["period", "time_years", "cash_flow", "coupon_date", "discount_period"]]


def price_bond_dirty(spec: BondSpec, ytm: float) -> float:
    """결제일 이후 현금흐름을 할인한 Dirty Price를 계산합니다."""

    if ytm <= -0.999:
        raise ValueError("ytm이 너무 낮습니다. -99.9% 이하의 금리는 허용하지 않습니다.")

    table = build_cashflow_table(spec)
    if table.empty:
        return 0.0

    discount_base = 1 + ytm / spec.coupon_frequency
    if discount_base <= 0:
        raise ValueError("할인계수가 0 이하입니다. ytm과 coupon_frequency를 확인하세요.")

    periods = table.get("discount_period", table["period"]).to_numpy(dtype=float)
    cf = table["cash_flow"].to_numpy(dtype=float)
    return float(np.sum(cf / discount_base**periods))


def price_bond_clean(spec: BondSpec, ytm: float) -> float:
    """Dirty Price에서 경과이자를 차감한 Clean Price를 계산합니다."""

    return price_bond_dirty(spec, ytm) - accrued_interest(spec)


def price_bond(spec: BondSpec, ytm: float) -> float:
    """
    YTM을 기준으로 고정금리 이표채 가격을 계산합니다.

    날짜 정보가 있으면 dirty price를, 없으면 기존 단순 가격을 반환합니다.
    """

    return price_bond_dirty(spec, ytm)


def price_bond_with_table(spec: BondSpec, ytm: float) -> tuple[float, pd.DataFrame]:
    """가격과 현금흐름별 현재가치 테이블을 함께 반환합니다."""

    table = build_cashflow_table(spec)
    discount_base = 1 + ytm / spec.coupon_frequency
    discount_periods = table.get("discount_period", table["period"]).to_numpy(dtype=float)
    table["discount_factor"] = 1 / discount_base**discount_periods
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
    """Macaulay Duration, Modified Duration, Convexity, DV01을 계산합니다."""

    price, table = price_bond_with_table(spec, ytm)
    periods = table.get("discount_period", table["period"]).to_numpy(dtype=float)
    times = table["time_years"].to_numpy(dtype=float)
    pv = table["present_value"].to_numpy(dtype=float)

    macaulay_duration = float(np.sum(times * pv) / price)
    modified_duration = float(macaulay_duration / (1 + ytm / spec.coupon_frequency))

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
    try:
        raw = input(f"{prompt} [기본값: {default}]: ").strip()
    except EOFError:
        return float(default)
    if raw == "":
        return float(default)
    return float(raw.replace(",", ""))


def _read_int(prompt: str, default: int) -> int:
    try:
        raw = input(f"{prompt} [기본값: {default}]: ").strip()
    except EOFError:
        return int(default)
    if raw == "":
        return int(default)
    return int(raw.replace(",", ""))


def _read_text(prompt: str, default: str = "") -> str:
    default_label = default if default else "빈 값"
    try:
        raw = input(f"{prompt} [기본값: {default_label}]: ").strip()
    except EOFError:
        return default
    return raw or default


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
        issue_date = _read_text("발행일 또는 직전 이표일(YYYY-MM-DD, 선택)", "")
        maturity_date = _read_text("만기일(YYYY-MM-DD, 선택)", "")
        settlement_date = _read_text("결제일(YYYY-MM-DD, 선택)", "")
        day_count = _read_text("Day count convention(ACT/365, ACT/ACT, 30/360)", "ACT/365")
    except ValueError:
        print("입력값을 숫자로 해석하지 못했습니다. 쉼표와 % 기호를 제외하고 다시 입력하세요.")
        return

    try:
        spec = BondSpec(
            face_value=face_value,
            coupon_rate=coupon_rate_pct / 100,
            maturity_years=maturity_years,
            coupon_frequency=coupon_frequency,
            issue_date=issue_date or None,
            maturity_date=maturity_date or None,
            settlement_date=settlement_date or None,
            day_count=day_count,
        )
    except ValueError as exc:
        print(f"채권 입력값 오류: {exc}")
        return

    ytm = ytm_pct / 100
    price, cashflow_table = price_bond_with_table(spec, ytm)
    risk = duration_convexity(spec, ytm)
    dirty_price = price_bond_dirty(spec, ytm)
    accrued = accrued_interest(spec)
    clean_price = price_bond_clean(spec, ytm)
    ai_details = accrued_interest_details(spec)

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
    print(f"Dirty Price: {_format_krw(dirty_price)}")
    print(f"Accrued Interest: {_format_krw(accrued)}")
    print(f"Clean Price: {_format_krw(clean_price)}")
    print(f"이론가격: {_format_krw(price)}")
    if spec.has_date_inputs:
        print(f"직전 이표일: {ai_details['previous_coupon_date']}")
        print(f"다음 이표일: {ai_details['next_coupon_date']}")
        print(f"경과일수 / 전체 이표기간일수: {ai_details['elapsed_days']} / {ai_details['coupon_period_days']}")

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
    if "coupon_date" in display_table:
        display_table["coupon_date"] = display_table["coupon_date"].map(str)
    display_table["time_years"] = display_table["time_years"].map(lambda x: f"{x:.4f}")
    display_table["cash_flow"] = display_table["cash_flow"].map(lambda x: f"{x:,.2f}")
    display_table["discount_factor"] = display_table["discount_factor"].map(lambda x: f"{x:.8f}")
    display_table["present_value"] = display_table["present_value"].map(lambda x: f"{x:,.2f}")
    print(display_table.to_string(index=False))
