# data_scraper.py
"""
KRX KOSPI 200 파생상품 CSV/API 로더 및 전처리 모듈.

현재 프로젝트는 KRX 정보데이터시스템에서 내려받은 CSV를 로컬에서 읽는 방식을 기본으로 둡니다.
추가로 `api_config.json` 형식의 설정 파일을 넣으면 KRX/ECOS/기타 공공 API에서도 데이터를 받아올 수 있게 설계했습니다.

API 키는 코드에 직접 쓰지 말고 환경변수로 관리하는 것을 권장합니다.
"""

from __future__ import annotations

import json
import os
import re
from io import StringIO
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import quote

import numpy as np
import pandas as pd
import requests

DEFAULT_DATA_FILE = Path(__file__).with_name("data_0020_20260414.csv")
DEFAULT_API_CONFIG_FILE = Path(__file__).with_name("api_config.json")
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


def _resolve_template_value(value: Any, variables: dict[str, Any] | None = None) -> Any:
    """
    문자열 내 ${VAR_NAME} 패턴을 환경변수 또는 variables 값으로 치환합니다.

    예: "${BOK_API_KEY}" -> os.environ["BOK_API_KEY"]
    """
    if variables is None:
        variables = {}

    if isinstance(value, dict):
        return {k: _resolve_template_value(v, variables) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve_template_value(v, variables) for v in value]
    if not isinstance(value, str):
        return value

    pattern = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")

    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        if key in variables and variables[key] is not None:
            return str(variables[key])
        return os.getenv(key, match.group(0))

    return pattern.sub(replace, value)


def load_api_config(config_path: str | Path = DEFAULT_API_CONFIG_FILE, profile: str = "krx_derivatives") -> dict[str, Any]:
    """
    API 설정 파일에서 특정 profile을 읽습니다.

    `api_config.example.json`을 `api_config.json`으로 복사한 뒤 실제 endpoint/API key 환경변수를 채워 사용합니다.
    """
    config_path = Path(config_path)
    if not config_path.exists():
        raise FileNotFoundError(
            f"API 설정 파일을 찾지 못했습니다: {config_path}. "
            "api_config.example.json을 api_config.json으로 복사한 뒤 수정하세요."
        )

    with config_path.open("r", encoding="utf-8") as fp:
        config = json.load(fp)

    if profile not in config:
        raise KeyError(f"API 설정 profile '{profile}'을 찾지 못했습니다. 사용 가능 profile: {list(config)}")

    return config[profile]


def _extract_json_path(payload: Any, path: list[str] | None) -> Any:
    """JSON 응답에서 data_path에 해당하는 하위 데이터를 꺼냅니다."""
    current = payload
    for key in path or []:
        if isinstance(current, dict):
            current = current.get(key, [])
        else:
            return []
    return current


def _apply_column_map(df: pd.DataFrame, column_map: dict[str, str] | None) -> pd.DataFrame:
    """API 응답 컬럼명을 프로젝트 표준 컬럼명으로 변환합니다."""
    if not column_map:
        return df

    rename_map = {source: target for source, target in column_map.items() if source in df.columns}
    return df.rename(columns=rename_map)


def fetch_tabular_api(config: dict[str, Any], variables: dict[str, Any] | None = None) -> pd.DataFrame:
    """
    JSON/CSV 형태의 API 응답을 DataFrame으로 변환합니다.

    config 주요 필드
    - url: API endpoint. ${ENV_NAME} 또는 variables 값 치환 가능
    - method: GET/POST
    - headers: 요청 헤더
    - params: query parameter
    - body/json: POST 요청 본문
    - response_format: json/csv
    - data_path: JSON 안에서 실제 row 배열까지의 경로
    - column_map: API 원본 컬럼명 -> 프로젝트 표준 컬럼명
    """
    variables = variables or {}
    resolved = _resolve_template_value(config, variables)

    url = resolved["url"]
    method = str(resolved.get("method", "GET")).upper()
    headers = dict(resolved.get("headers", {}))
    params = dict(resolved.get("params", {}))
    timeout = int(resolved.get("timeout", 20))

    api_key_env = resolved.get("api_key_env")
    api_key_value = os.getenv(api_key_env, "") if api_key_env else resolved.get("api_key")
    api_key_name = resolved.get("api_key_name", "api_key")
    api_key_location = resolved.get("api_key_location", "query")
    api_key_prefix = resolved.get("api_key_prefix", "")

    if api_key_value:
        if api_key_location == "header":
            headers[api_key_name] = f"{api_key_prefix}{api_key_value}"
        else:
            params[api_key_name] = api_key_value

    if method == "POST":
        response = requests.post(
            url,
            headers=headers,
            params=params,
            json=resolved.get("json"),
            data=resolved.get("data"),
            timeout=timeout,
        )
    else:
        response = requests.get(url, headers=headers, params=params, timeout=timeout)

    response.raise_for_status()

    response_format = str(resolved.get("response_format", "json")).lower()
    if response_format == "csv":
        df = pd.read_csv(StringIO(response.text))
    else:
        payload = response.json()
        rows = _extract_json_path(payload, resolved.get("data_path"))
        if isinstance(rows, dict):
            rows = [rows]
        df = pd.DataFrame(rows)

    return _apply_column_map(df, resolved.get("column_map"))


def fetch_krx_derivatives_api(
    config_path: str | Path = DEFAULT_API_CONFIG_FILE,
    profile: str = "krx_derivatives",
    target_date: str | None = None,
    **variables: Any,
) -> pd.DataFrame:
    """
    KRX 파생상품 API에서 데이터를 받아 프로젝트 표준 형식으로 정규화합니다.

    실제 KRX API endpoint와 파라미터는 발급받은 API 문서에 맞게 `api_config.json`에서 수정합니다.
    """
    config = load_api_config(config_path, profile)
    if target_date is not None:
        variables.setdefault("TARGET_DATE", target_date)

    raw = fetch_tabular_api(config, variables=variables)
    return normalize_krx_derivatives(raw)


def fetch_government_bond_yield_api(
    config_path: str | Path = DEFAULT_API_CONFIG_FILE,
    profile: str = "ecos_government_bond_yield",
    start_date: str | None = None,
    end_date: str | None = None,
    **variables: Any,
) -> pd.DataFrame:
    """
    국고채 금리 API 데이터를 DataFrame으로 반환합니다.

    기본 예시는 한국은행 ECOS 형식에 맞춰 두었지만, KOFIA/공공데이터포털 등 다른 API도
    `url`, `data_path`, `column_map`만 맞추면 동일한 함수로 사용할 수 있습니다.
    """
    config = load_api_config(config_path, profile)
    if start_date is not None:
        variables.setdefault("START_DATE", start_date)
    if end_date is not None:
        variables.setdefault("END_DATE", end_date)

    df = fetch_tabular_api(config, variables=variables)

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    if "yield_pct" in df.columns:
        df["yield_pct"] = pd.to_numeric(df["yield_pct"], errors="coerce")
        df["yield_decimal"] = df["yield_pct"] / 100.0

    return df


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
    """KRX 원시 CSV/API 데이터를 분석/프라이싱에 쓰기 쉬운 형태로 정규화합니다."""
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


def get_krx_kospi200_options(
    target_date: str | None = None,
    file_path: str | Path = DEFAULT_DATA_FILE,
    source: str = "csv",
    config_path: str | Path = DEFAULT_API_CONFIG_FILE,
    api_profile: str = "krx_derivatives",
    **api_variables: Any,
) -> pd.DataFrame:
    """
    KOSPI 200 옵션 데이터를 로드합니다.

    source="csv"이면 로컬 CSV를 사용하고,
    source="api"이면 `api_config.json`의 KRX API profile을 사용합니다.
    """
    if source.lower() == "api":
        return fetch_krx_derivatives_api(
            config_path=config_path,
            profile=api_profile,
            target_date=target_date,
            **api_variables,
        )

    _ = target_date
    return load_krx_derivatives_csv(file_path)


def infer_underlying_price(df: pd.DataFrame) -> float | None:
    """
    CSV/API의 현물가 컬럼에서 KOSPI 200 기초지수 값을 추정합니다.
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


def get_risk_free_rate(
    start_date: str,
    end_date: str,
    source: str = "fdr",
    config_path: str | Path = DEFAULT_API_CONFIG_FILE,
    api_profile: str = "ecos_government_bond_yield",
    **api_variables: Any,
):
    """
    국고채 금리 수집용 확장 포인트.

    source="api"이면 ECOS/KOFIA/공공데이터 API 설정을 사용합니다.
    source="fdr"이면 기존 FinanceDataReader 방식을 사용합니다.
    """
    if source.lower() == "api":
        return fetch_government_bond_yield_api(
            config_path=config_path,
            profile=api_profile,
            start_date=start_date,
            end_date=end_date,
            **api_variables,
        )

    try:
        import FinanceDataReader as fdr
    except ImportError as exc:
        raise ImportError("FinanceDataReader가 설치되어 있지 않습니다. `pip install finance-datareader` 후 다시 실행하세요.") from exc

    return fdr.DataReader("KR3YT=RR", start_date, end_date)
