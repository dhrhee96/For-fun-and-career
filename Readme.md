# KOSPI 200 Option Pricing, Delta Hedging & Bond Pricing Simulator

한국거래소(KRX) KOSPI 200 파생상품 CSV/API 데이터를 기반으로 옵션 가격, Greeks, 내재변동성, Crank-Nicolson FDM 검증, 델타 헤징 손익을 확인하고, 추가로 **채권가격 산정, YTM 역산, 듀레이션, 컨벡서티, DV01**까지 계산하는 연구용 Python 프로젝트입니다.

이 프로젝트의 목적은 단순 계산기를 넘어서, 파생상품과 채권을 같은 금융공학 관점에서 연결해 설명할 수 있는 포트폴리오용 분석 도구를 만드는 것입니다.

---

## 주요 기능

### 1. Option Pricing Engine

- Call/Put 공통 Black-Scholes-Merton 가격 산출
- Delta, Gamma, Theta, Vega, Rho 계산
- Vega/Rho는 1.00 변화 기준과 1%p 변화 기준을 함께 제공
- Newton-Raphson + Brent 보정 방식의 내재변동성 역산
- European option Crank-Nicolson FDM 가격 계산
- 기존 함수명 `bs_call`, `bs_greeks_call`, `implied_volatility_call`도 유지

### 2. KRX CSV/API Data Pipeline

- `utf-8-sig`, `cp949`, `euc-kr` 인코딩 fallback
- 쉼표, 공백, 결측값이 섞인 숫자 컬럼 정규화
- 종목명에서 옵션 타입, 만기, 행사가, 주간/야간 세션 추출
- ATM 옵션 자동 선택 함수 제공
- 로컬 CSV와 API source 모두 지원
- API 응답 컬럼명을 프로젝트 표준 컬럼명으로 매핑 가능
- 현재 CSV/API에 옵션 행이 부족해도 이론 시나리오로 실행 가능

### 3. Delta Hedging Simulator

- 옵션 가치 변화와 헤지 포지션 손익을 분리 계산
- 계약승수, 수수료율, 슬리피지를 입력값으로 분리
- 시장 충격 후 Net PnL 산출
- 지수 충격률과 변동성 충격값을 조합한 스트레스 테스트 제공

### 4. Bond Pricing Engine

- 고정금리 이표채 가격 산정
- Clean Price / Dirty Price / Accrued Interest 분리
- 시장가격 기반 YTM 역산
- 현금흐름별 할인계수와 현재가치 테이블 생성
- Macaulay Duration, Modified Duration 계산
- Convexity 계산
- DV01 및 금리 ±1bp, ±100bp 변화 시 가격 민감도 계산

### 5. API-ready Structure

- `api_config.example.json` 기반 API 설정 템플릿 제공
- API 키는 환경변수로 관리
- `api_config.json`, `.env`는 `.gitignore` 처리
- JSON/CSV API 응답 모두 DataFrame으로 변환 가능
- KRX 파생상품 API, 한국은행 ECOS 국고채 금리 API, KOFIA/공공데이터포털 API 등으로 확장 가능

### 6. Visualization

- 옵션 데이터가 충분할 경우 IV surface 렌더링 가능
- 데이터가 부족하면 자동으로 surface 생성을 생략

---

## 프로젝트 구조

```text
파생상품/
├── .gitignore               # 로컬 API 키/환경변수 파일 제외
├── api_config.example.json  # API 연결 설정 예시
├── bond_pricing.py          # 채권가격, YTM, Duration, Convexity, DV01
├── data_0020_20260414.csv   # KRX 다운로드 CSV 샘플
├── data_scraper.py          # KRX CSV/API 로드/정규화/ATM 선택/국고채 API 로드
├── hedging_simulator.py     # 델타 헤징 및 스트레스 테스트
├── main.py                  # 옵션산정/채권산정 통합 실행 스크립트
├── pricing_engine.py        # BSM, Greeks, IV, FDM 엔진
├── requirements.txt         # 실행 의존성
└── visualizer.py            # IV surface 시각화
```

---

## 설치

```bash
cd 파생상품
pip install -r requirements.txt
```

또는 직접 설치할 경우:

```bash
pip install numpy pandas scipy matplotlib requests finance-datareader
```

---

## 실행

### 1. 메뉴에서 선택

```bash
python main.py
```

실행 후 아래처럼 입력합니다.

```text
옵션산정
```

또는

```text
채권산정
```

### 2. 옵션산정 바로 실행: CSV

```bash
python main.py 옵션산정
```

또는

```bash
python main.py --mode option
```

다른 CSV 파일을 지정하려면:

```bash
python main.py 옵션산정 --data your_krx_file.csv
```

옵션 데이터가 충분하고 IV surface를 보고 싶다면:

```bash
python main.py 옵션산정 --plot
```

### 3. 옵션산정 바로 실행: API

먼저 설정 예시 파일을 복사합니다.

```bash
cp api_config.example.json api_config.json
```

그다음 발급받은 API 문서에 맞게 `api_config.json`의 `url`, `headers`, `params`, `data_path`, `column_map`을 수정합니다.

API 키는 코드나 JSON에 직접 쓰기보다 환경변수로 넣습니다.

```bash
set KRX_API_KEY=발급받은_거래소_API_KEY
set BOK_API_KEY=발급받은_한국은행_ECOS_API_KEY
```

Windows PowerShell에서는 다음처럼 설정할 수 있습니다.

```powershell
$env:KRX_API_KEY="발급받은_거래소_API_KEY"
$env:BOK_API_KEY="발급받은_한국은행_ECOS_API_KEY"
```

API source로 실행합니다.

```bash
python main.py 옵션산정 --source api --api-config api_config.json --api-profile krx_derivatives --target-date 20260615
```

### 4. 채권산정 바로 실행

```bash
python main.py 채권산정
```

또는

```bash
python main.py --mode bond
```

채권산정 모드에서는 다음 값을 입력합니다. 입력을 비우면 기본 예시값으로 계산됩니다.

```text
액면가
표면금리(%)
잔존만기(년)
연 이자 지급 횟수
시장 YTM(%)
YTM 역산용 시장가격
발행일 또는 직전 이표일(YYYY-MM-DD, 선택)
만기일(YYYY-MM-DD, 선택)
결제일(YYYY-MM-DD, 선택)
Day count convention(ACT/365, ACT/ACT, 30/360)
```

날짜 입력을 비우면 기존처럼 `maturity_years` 기반의 단순 이표채 가격을 계산합니다. 날짜를 입력하면 결제일 이후 현금흐름만 할인해서 Dirty Price를 계산하고, 직전 이표일 이후 결제일까지의 Accrued Interest를 차감해 Clean Price를 함께 출력합니다.

예시:

```text
발행일 또는 직전 이표일: 2025-01-01
만기일: 2027-01-01
결제일: 2026-04-01
Day count convention: ACT/365
```

출력에는 아래 항목이 추가됩니다.

```text
Dirty Price
Accrued Interest
Clean Price
직전 이표일
다음 이표일
경과일수 / 전체 이표기간일수
```

### 5. 국고채 금리 API 사용 예시

`data_scraper.py`의 `get_risk_free_rate`는 기존 `FinanceDataReader` 방식과 API 방식을 모두 지원합니다.

```python
from data_scraper import get_risk_free_rate

# 기존 방식
rate_df = get_risk_free_rate("2026-01-01", "2026-06-15", source="fdr")

# API 방식: api_config.json의 ecos_government_bond_yield profile 사용
rate_df = get_risk_free_rate(
    "20260101",
    "20260615",
    source="api",
    config_path="api_config.json",
    api_profile="ecos_government_bond_yield",
    STAT_CODE="수정필요",
    ITEM_CODE="수정필요"
)
```

ECOS 통계코드와 항목코드는 한국은행 ECOS에서 확인해 `STAT_CODE`, `ITEM_CODE`에 넣으면 됩니다.

---

## API 설정 파일 구조

`api_config.example.json`은 다음 구조를 따릅니다.

```json
{
  "krx_derivatives": {
    "url": "https://example.krx.api/derivatives/all-products",
    "method": "GET",
    "response_format": "json",
    "api_key_env": "KRX_API_KEY",
    "api_key_name": "Authorization",
    "api_key_location": "header",
    "api_key_prefix": "Bearer ",
    "headers": {
      "Accept": "application/json"
    },
    "params": {
      "market": "DERIVATIVES",
      "product": "KOSPI200_OPTIONS",
      "date": "${TARGET_DATE}"
    },
    "data_path": ["data", "rows"],
    "column_map": {
      "isu_cd": "종목코드",
      "isu_nm": "종목명",
      "close": "종가"
    }
  }
}
```

핵심은 다음입니다.

- `url`: 실제 API endpoint
- `response_format`: `json` 또는 `csv`
- `data_path`: JSON 응답에서 실제 row 배열까지 내려가는 경로
- `column_map`: API 원본 컬럼명을 프로젝트 표준 컬럼명으로 바꾸는 매핑
- `api_key_env`: API 키를 읽을 환경변수명
- `${TARGET_DATE}`, `${BOK_API_KEY}` 같은 값은 실행 시 변수 또는 환경변수로 치환

---

## 채권산정 출력 예시

```text
========================================================================
채권가격 산정 모드
========================================================================
입력을 비우면 기본 예시값으로 계산합니다.

------------------------------------------------------------------------
1. 채권 가격 산정 결과
------------------------------------------------------------------------
액면가: 10,000.00원
표면금리: 3.5000%
YTM: 3.8000%
잔존만기: 3.0000년
이자 지급 횟수: 연 2회
Dirty Price: 9,915.69원
Accrued Interest: 0.00원
Clean Price: 9,915.69원
이론가격: 9,915.69원

------------------------------------------------------------------------
2. 금리 민감도
------------------------------------------------------------------------
Macaulay Duration: 2.873xxx년
Modified Duration: 2.819xxx
Convexity: 9.5xxxxx
DV01: 2.80원  # 금리 1bp 변화 시 가격 민감도
```

---

## 옵션산정 출력 예시

```text
========================================================================
KOSPI 200 Option Pricing & Delta Hedging Simulator
========================================================================
데이터 로드 성공: data_0020_20260414.csv
전체 행 수: 1개 / 인식된 옵션 행 수: 0개

========================================================================
1. 포지션 진입 가정
========================================================================
기초지수 S0: 903.17 pt
행사가 K: 902.50 pt
잔존만기: 30일
무위험금리: 3.50%
적용 변동성: 18.00%
시장가격: 없음 — BSM 이론가격을 진입가격으로 사용

========================================================================
2. Pricing Engine 검증
========================================================================
BSM 이론가격: 20.2349 pt
Crank-Nicolson FDM 가격: 20.1105 pt
Delta: 0.5382
Gamma: 0.008520
Theta/day: -0.353144 pt
Vega/1%p: 1.0282 pt
Rho/1%p: 0.3829 pt
```

---

## 면접/포트폴리오 설명 포인트

이 프로젝트는 다음 순서로 설명하면 자연스럽습니다.

1. **옵션 데이터 정제**: KRX 원시 CSV/API 데이터를 읽고, 종목명에서 옵션 타입·만기·행사가를 추출했습니다.
2. **옵션 이론가 계산**: BSM 모델로 옵션 이론가격과 Greeks를 계산했습니다.
3. **시장가격 연결**: 시장가격이 있을 경우 IV를 역산하여 단순 가정 변동성이 아니라 시장이 반영한 변동성을 사용하도록 설계했습니다.
4. **수치해석 검증**: closed-form BSM 가격과 Crank-Nicolson FDM 가격을 비교해 계산 엔진의 안정성을 확인했습니다.
5. **리스크 관리 연결**: Delta-neutral hedge를 구성하고, 지수 하락 및 IV 상승 시나리오에서 옵션 손익과 헤지 손익을 분해했습니다.
6. **채권가격 산정 확장**: 옵션뿐 아니라 고정금리 이표채 가격, YTM, Duration, Convexity, DV01을 계산하도록 확장해 금리 리스크 관점까지 연결했습니다.
7. **API 확장성**: KRX, ECOS, KOFIA 등 외부 API가 붙어도 계산 엔진은 유지하고 데이터 로더만 설정으로 바꿀 수 있도록 분리했습니다.
8. **스트레스 테스트**: 지수 충격, 변동성 충격, 금리 충격이 금융상품 가격에 어떤 영향을 주는지 정량적으로 확인할 수 있습니다.

---

## 향후 개선 과제

- 실제 옵션 전체 체인 API와 연결해 volatility smile/surface 계산 고도화
- 옵션 만기일 자동 계산 로직 추가
- 선물 가격 기반 hedge와 현물지수 기반 hedge를 분리
- 채권 결제일, 경과이자, clean price/dirty price 분리
- 국고채/회사채 신용스프레드 반영
- 국고채 금리 curve를 가져와 만기별 discount curve 구성
- 거래비용, 슬리피지, 증거금 로직 세분화
- Streamlit 또는 FastAPI 기반 대시보드화
- 테스트 코드(`pytest`) 추가

---

## 면책 조항

본 프로젝트는 금융공학 및 퀀트 리스크 관리 학습을 위한 연구용 코드입니다. 실제 투자 판단이나 매매 전략으로 사용하기 위한 목적이 아니며, 실제 시장의 호가 잔량, 체결 가능성, 증거금, 세금, 수수료, 슬리피지, 급변 상황을 완전하게 반영하지 않습니다.
