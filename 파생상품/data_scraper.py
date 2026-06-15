# data_scraper.py
"""
KRX KOSPI 200 파생상품 CSV 로더/전처리 모듈.

현재 프로젝트는 KRX 정보데이터시스템에서 내려받은 CSV를 로컬에서 읽는 방식을 기본으로 둡니다.
네트워크 스크래핑보다 재현성이 높고, 면접/포트폴리오 설명 시 데이터 출처와 처리 과정을 명확히 설명할 수 있습니다.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

DEFAULT_DATA_FILE = Path(__file__).with_name("data_0020_20260414.csv")
NUMERIC_COLUMNS = ["종가", "대비", "시가", "고가", "저가", "현물가", "정산가", "거래량", "거래대금", "미결제약정"]


def _read_csv_with_fallback(file_path: str | Path, encodings: Iterable[str] = ("utf-8-sig", "cp949", "euc-kr")) -> pd.DataFrame:
    """KRX CSV에서 자주 발생하는 인코딩 차이를 순차적으로 처리합니다."""
    file_path = Path(file_path)
    last_error: Exception | None = None

    for encoding in encodings:
        try:
            return pd.read_csv(file_path, encoding=encoding)
        except UnicodeDecodeError as exc:
            last_error = exc
            continue

    if last_error is not None:
        raise last_error
    raise FileNotFoundError(file_path)


def _to_numeric(series: pd.Series) -> pd.Series:
    """쉼표, 공백, 빈 문자열이 섞인 숫자 컬럼을 float로 변환합니다."""
    cleaned = (
        series.astype(str)
        .str.replace(",", "", regex=False)
        .str.replace(" ", "", regex=False)
    )
    cleaned = cleaned.mask(cleaned.isin(["", "nan", "None"]))
    return pd.to_numeric(cleaned, errors="coerce")


def parse_kospi200_option_name(name: str) -> dict[str, object]:
    """
    KRX 종목명에서 옵션 타입, 만기, 행사가를 최대한 추출합니다.

    지원 예시
    - 코스피200 C 202606 897.5
    - 코스피200 P 202606 897.5
    - 코스피200 콜옵션 202606 897.5
    - 코스피200 풋옵션 202606 897.5

    선물(F), 스프레드(SP) 등 옵션이 아닌 종목은 option_type/strike를 비워 둡니다.
    """
    text = str(name).strip()
    result: dict[str, object] = {
        "product_family": "KOSPI200" if "코스피200" in text else None,
        "option_type": None,
        "maturity": None,
        "strike": np.nan,
        "session": None,
    }

    if "야간" in text:
        result["session"] = "야간"
    elif "주간" in text:
        result["session"] = "주간"

    type_match = re.search(r"(?:\s|^)(C|P|CALL|PUT|콜옵션|풋옵션|콜|풋)(?:\s|$)", text, flags=re.IGNORECASE)
    if type_match:
        raw_type = type_match.group(1).upper()
        if raw_type in {"C", "CALL", "콜", "콜옵션"}:
            result["option_type"] = "C"
        elif raw_type in {"P", "PUT", "풋", "풋옵션"}:
            result["option_type"] = "P"

    maturity_match = re.search(r"\b(20\d{4}|\d{4})\b", text)
    if maturity_match:
        maturity = maturity_match.group(1)
        result["maturity"] = maturity if len(maturity) == 6 else f"20{maturity}"

    # 만기 뒤에 나오는 숫자를 행사가 후보로 우선 사용합니다.
    strike_candidates = re.findall(r"\b\d{2,4}(?:\.\d+)?\b", text)
    if strike_candidates:
        numeric_candidates = [float(x) for x in strike_candidates]
        # 202606 같은 만기 숫자는 제외하고, KOSPI200 행사가로 볼 수 있는 구간만 남깁니다.
        strike_candidates_filtered = [x for x in numeric_candidates if 100 <= x <= 1500]
        if strike_candidates_filtered:
            result["strike"] = strike_candidates_filtered[-1]

    return result


def normalize_krx_derivatives(df: pd.DataFrame) -> pd.DataFrame:
    """KRX 원시 CSV를 분석/프라이싱에 쓰기 쉬운 형태로 정규화합니다."""
    cleaned = df.copy()
    cleaned.columns = [str(col).strip() for col in cleaned.columns]

    for col in NUMERIC_COLUMNS:
        if col in cleaned.columns:
            cleaned[col] = _to_numeric(cleaned[col])

    if "종목명" in cleaned.columns:
        parsed = cleaned["종목명"].apply(parse_kospi200_option_name).apply(pd.Series)
        cleaned = pd.concat([cleaned, parsed], axis=1)
    else:
        cleaned["product_family"] = None
        cleaned["option_type"] = None
        cleaned["maturity"] = None
        cleaned["strike"] = np.nan
        cleaned["session"] = None

    cleaned["is_option"] = cleaned["option_type"].isin(["C", "P"])
    cleaned["is_active"] = cleaned.get("종가", pd.Series(index=cleaned.index, dtype=float)).fillna(0) > 0

    return cleaned


def load_krx_derivatives_csv(file_path: str | Path = DEFAULT_DATA_FILE) -> pd.DataFrame:
    """로컬 KRX CSV를 읽고 정규화된 DataFrame을 반환합니다."""
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"KRX CSV 파일을 찾을 수 없습니다: {file_path}")

    raw = _read_csv_with_fallback(file_path)
    return normalize_krx_derivatives(raw)


def get_krx_kospi200_options(target_date: str | None = None, file_path: str | Path = DEFAULT_DATA_FILE) -> pd.DataFrame:
    """
    기존 코드 호환용 래퍼입니다.

    target_date는 향후 자동 다운로드 기능 확장용 인자로 남겨두었습니다.
    현재는 로컬 CSV 파일을 읽어 정규화합니다.
    """
    _ = target_date
    return load_krx_derivatives_csv(file_path)


def infer_underlying_price(df: pd.DataFrame) -> float | None:
    """
    CSV의 현물가 컬럼에서 KOSPI 200 기초지수 값을 추정합니다.
    0 또는 결측값은 제외하고 중앙값을 사용합니다.
    """
    if "현물가" not in df.columns:
        return None

    values = pd.to_numeric(df["현물가"], errors="coerce")
    values = values[(values > 0) & np.isfinite(values)]

    if values.empty:
        return None
    return float(values.median())


def select_atm_option(
    df: pd.DataFrame,
    underlying_price: float,
    option_type: str = "C",
    maturity: str | None = None,
    prefer_session: str = "주간",
) -> pd.Series:
    """
    정규화된 옵션 테이블에서 현재 기초지수와 가장 가까운 ATM 옵션을 선택합니다.
    """
    option_type = option_type.upper()
    candidates = df.copy()

    if "is_option" in candidates.columns:
        candidates = candidates[candidates["is_option"]]

    candidates = candidates[candidates["option_type"] == option_type]
    candidates = candidates[pd.to_numeric(candidates["strike"], errors="coerce").notna()]

    if maturity is not None and "maturity" in candidates.columns:
        candidates = candidates[candidates["maturity"].astype(str) == str(maturity)]

    if "session" in candidates.columns and prefer_session:
        session_candidates = candidates[candidates["session"] == prefer_session]
        if not session_candidates.empty:
            candidates = session_candidates

    if "종가" in candidates.columns:
        active_candidates = candidates[pd.to_numeric(candidates["종가"], errors="coerce").fillna(0) > 0]
        if not active_candidates.empty:
            candidates = active_candidates

    if candidates.empty:
        raise ValueError("조건에 맞는 KOSPI 200 옵션 데이터를 찾지 못했습니다.")

    distance = (pd.to_numeric(candidates["strike"], errors="coerce") - underlying_price).abs()
    return candidates.loc[distance.idxmin()]


def build_iv_table(
    df: pd.DataFrame,
    underlying_price: float,
    risk_free_rate: float,
    days_to_expiry: int,
    option_type: str = "C",
) -> pd.DataFrame:
    """
    정규화된 옵션 테이블에 IV 계산용 기본 컬럼을 붙입니다.
    실제 IV 역산은 pricing_engine.implied_volatility와 결합해서 사용합니다.
    """
    option_type = option_type.upper()
    table = df[(df.get("option_type") == option_type) & (df.get("is_active", False))].copy()

    if table.empty:
        return table

    table["S"] = float(underlying_price)
    table["K"] = pd.to_numeric(table["strike"], errors="coerce")
    table["T"] = float(days_to_expiry) / 365.0
    table["r"] = float(risk_free_rate)
    table["market_price"] = pd.to_numeric(table["종가"], errors="coerce")
    table = table.dropna(subset=["K", "market_price"])

    return table.reset_index(drop=True)


def get_risk_free_rate(start_date: str, end_date: str):
    """
    국고채 금리 수집용 확장 포인트.

    FinanceDataReader 의존성은 실행 환경마다 설치/데이터 제공 여부가 다를 수 있어 lazy import로 처리합니다.
    """
    try:
        import FinanceDataReader as fdr
    except ImportError as exc:
        raise ImportError("FinanceDataReader가 설치되어 있지 않습니다. `pip install finance-datareader` 후 다시 실행하세요.") from exc

    return fdr.DataReader("KR3YT=RR", start_date, end_date)
