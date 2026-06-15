# KOSPI 200 Option Pricing & Delta Hedging Simulator

한국거래소(KRX) KOSPI 200 파생상품 CSV를 기반으로 옵션 가격, Greeks, 내재변동성, Crank-Nicolson FDM 검증, 델타 헤징 손익을 한 번에 확인하는 연구용 Python 프로젝트입니다.

이 프로젝트의 목적은 단순히 Black-Scholes-Merton 공식을 계산하는 데 그치지 않고, **시장가격 → IV 역산 → Greeks 산출 → 시장 충격 → 헤지 손익 → 거래비용 차감 후 Net PnL**의 흐름을 코드로 재현하는 것입니다.

---

## 주요 기능

### 1. Pricing Engine

- Call/Put 공통 Black-Scholes-Merton 가격 산출
- Delta, Gamma, Theta, Vega, Rho 계산
- Vega/Rho는 1.00 변화 기준과 1%p 변화 기준을 함께 제공
- Newton-Raphson + Brent 보정 방식의 내재변동성 역산
- European option Crank-Nicolson FDM 가격 계산
- 기존 함수명 `bs_call`, `bs_greeks_call`, `implied_volatility_call`도 유지

### 2. KRX CSV Data Pipeline

- `utf-8-sig`, `cp949`, `euc-kr` 인코딩 fallback
- 쉼표, 공백, 결측값이 섞인 숫자 컬럼 정규화
- 종목명에서 옵션 타입, 만기, 행사가, 주간/야간 세션 추출
- ATM 옵션 자동 선택 함수 제공
- 현재 CSV에 옵션 행이 부족해도 이론 시나리오로 실행 가능

### 3. Delta Hedging Simulator

- 옵션 가치 변화와 헤지 포지션 손익을 분리 계산
- 계약승수, 수수료율, 슬리피지를 입력값으로 분리
- 시장 충격 후 Net PnL 산출
- 지수 충격률과 변동성 충격값을 조합한 스트레스 테스트 제공

### 4. Visualization

- 옵션 데이터가 충분할 경우 IV surface 렌더링 가능
- 데이터가 부족하면 자동으로 surface 생성을 생략

---

## 프로젝트 구조

```text
파생상품/
├── data_0020_20260414.csv   # KRX 다운로드 CSV 샘플
├── data_scraper.py          # KRX CSV 로드/정규화/ATM 선택
├── hedging_simulator.py     # 델타 헤징 및 스트레스 테스트
├── main.py                  # 전체 실행 스크립트
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
pip install numpy pandas scipy matplotlib finance-datareader
```

---

## 실행

```bash
python main.py
```

다른 CSV 파일을 지정하려면:

```bash
python main.py --data your_krx_file.csv
```

옵션 데이터가 충분하고 IV surface를 보고 싶다면:

```bash
python main.py --plot
```

---

## 실행 결과 예시

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

1. **데이터 정제**: KRX 원시 CSV를 읽고, 종목명에서 옵션 타입·만기·행사가를 추출했습니다.
2. **이론가 계산**: BSM 모델로 옵션 이론가격과 Greeks를 계산했습니다.
3. **시장가격 연결**: 시장가격이 있을 경우 IV를 역산하여 단순 가정 변동성이 아니라 시장이 반영한 변동성을 사용하도록 설계했습니다.
4. **수치해석 검증**: closed-form BSM 가격과 Crank-Nicolson FDM 가격을 비교해 계산 엔진의 안정성을 확인했습니다.
5. **리스크 관리 연결**: Delta-neutral hedge를 구성하고, 지수 하락 및 IV 상승 시나리오에서 옵션 손익과 헤지 손익을 분해했습니다.
6. **스트레스 테스트**: 지수 충격과 변동성 충격을 조합해 Net PnL이 어떤 방향으로 변하는지 확인했습니다.

---

## 향후 개선 과제

- 실제 옵션 전체 체인 CSV를 추가해 volatility smile/surface 계산 고도화
- 만기일 자동 계산 로직 추가
- 선물 가격 기반 hedge와 현물지수 기반 hedge를 분리
- 거래비용, 슬리피지, 증거금 로직 세분화
- Streamlit 또는 FastAPI 기반 대시보드화
- 테스트 코드(`pytest`) 추가

---

## 면책 조항

본 프로젝트는 금융공학 및 퀀트 리스크 관리 학습을 위한 연구용 코드입니다. 실제 투자 판단이나 매매 전략으로 사용하기 위한 목적이 아니며, 실제 시장의 호가 잔량, 체결 가능성, 증거금, 세금, 수수료, 슬리피지, 급변 상황을 완전하게 반영하지 않습니다.
