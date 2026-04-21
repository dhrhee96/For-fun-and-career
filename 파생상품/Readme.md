# 📈 KOSPI 200 Option Pricing & Delta Hedging Simulator

한국거래소(KRX)의 KOSPI 200 옵션 시장 데이터를 기반으로 구동되는 **파생상품 프라이싱 엔진 및 실전 델타 헤징(Delta Hedging) 시뮬레이터**입니다.

단순한 블랙-숄즈(Black-Scholes) 이론가 계산을 넘어, **실제 증권사 거래 수수료**, **이산적 리밸런싱(Discrete Hedging)**, 그리고 **시장 충격(Volatility Smile/Shock)** 시나리오를 반영하여 실제 시장 환경과 가장 유사한 리스크 관리 시뮬레이션을 제공합니다.

## ✨ 주요 기능 (Key Features)

  - **Robust Data Pipeline:** KRX 원시 데이터(CSV)에서 정규식을 활용해 글로벌 스탠다드 플래그(`C`/`P`)로 자동 정제 및 분류
  - **ATM Auto-Mapping:** 현재 기초자산(KOSPI 200) 지수를 입력하면, 거래소 상장 규정에 맞춰 가장 가까운 2.5pt 단위의 등가격(ATM) 행사가를 자동으로 추적
  - **Advanced Pricing Engine:**
      - Black-Scholes-Merton (BSM) 모델 기반 이론가 및 5대 그릭스(Delta, Gamma, Theta, Vega, Rho) 산출
      - Newton-Raphson 최적화 알고리즘을 이용한 시장 가격 기반 내재변동성(Implied Volatility) 역산
      - Crank-Nicolson 유한차분법(FDM) 수치해석기 탑재 (오차율 10⁻⁴ 미만 최적화)
  - **Real-world Hedging Simulator:** 주가 급락 및 IV 폭등 시나리오에서 델타 뉴트럴(Delta Neutral) 포지션의 실제 손익(Net PnL)을 수수료를 차감하여 계산
  - **3D Volatility Surface (옵션):** 행사가와 잔존만기에 따른 내재변동성 곡면 시각화 (Volatility Smile & Term Structure)

## 🛠 기술 스택 (Tech Stack)

  - **Language:** Python
  - **Data Manipulation:** `pandas`, `numpy`
  - **Quantitative Engine:** `scipy` (stats, linalg)
  - **Visualization:** `matplotlib` (mplot3d)

## 📂 프로젝트 구조 (Project Structure)

```
├── data_scraper.py      # 시장 데이터 수집 및 로컬 CSV 로드/전처리 모듈
├── pricing_engine.py    # BSM, FDM, Greeks, IV 계산 코어 퀀트 모듈
├── visualizer.py        # 3D 변동성 곡면 렌더링 모듈
├── main.py              # 전체 파이프라인 통합 및 실전 시뮬레이션 실행
├── 오늘옵션.csv          # KRX 정보데이터시스템 다운로드 원본 데이터 
└── README.md
```

## 🚀 시작하기 (Getting Started)

### 1\. 패키지 설치

이 프로젝트를 실행하기 위해 필요한 파이썬 라이브러리를 설치합니다.

```
pip install pandas numpy scipy matplotlib finance-datareader
```

### 2\. 데이터 준비

1.  [KRX 정보데이터시스템(data.krx.co.kr)](http://data.krx.co.kr) 접속
2.  `[12501] 주가지수파생 전종목 시세` 화면에서 KOSPI 200 옵션 최신 데이터를 CSV로 다운로드
3.  파일명을 `오늘옵션.csv` (또는 코드 내 지정된 이름)로 변경하여 프로젝트 최상단 디렉토리에 위치

### 3\. 시뮬레이터 실행

```
python main.py
```

### 4\. 실행 결과 예시

```
=== 🚀 KOSPI 200 실전 퀀트 시스템 (Standard C/P & Real-Price) ===

✅ 데이터 로드 성공: 전체 6348개 중 KOSPI 200 Call('C') 3174개 매핑 완료

=== [포지션 진입] 시장가 897.0 pt ===
▶ 자동 매핑된 등가격(ATM) 행사가: 897.5 (Type: C)
▶ 옵션 초기 이론가: 18.2451 pt
▶ 델타(Delta): 0.5021
💸 진입 시 총 수수료: 4,064원

=== [시장 충격 발생] 지수 1% 급락 및 공포(IV) 20%로 상승 ===
▶ 충격 후 새로운 옵션가: 20.1245 pt (Vega 상승 반영)

=== [최종 실전 PnL 결산] ===
1. Call('C') 가치 손익: 469,850원
2. 선물 헤지 방어 수익: 1,126,211원
3. 총 거래 비용(수수료): -8,115원
----------------------------------------
💰 실전 최종 순손익 (Net PnL): 1,587,946원
===========================================
```

## 📝 향후 개선 과제 (Future Work)

  - [ ] 증권사 OpenAPI 연동을 통한 실시간 KOSPI 200 데이터 파이프라인 구축
  - [ ] 양매수(Straddle), 양매도(Strangle) 등 복합 포지션 구축 로직 추가
  - [ ] 감마 리스크와 거래 수수료 최소화를 위한 최적 헤징 주기 탐색 알고리즘 고도화

## ⚠️ 면책 조항 (Disclaimer)

이 프로젝트는 금융공학 및 퀀트 트레이딩 스터디 목적으로 작성된 **학술/연구용 프로토타입**입니다. 본 코드에서 산출된 이론가 및 시뮬레이션 결과는 실제 시장의 호가 잔량, 극단적 슬리피지(Slippage) 등을 완벽히 반영하지 못할 수 있으며, 실제 투자 전략으로의 사용을 권장하지 않습니다. 본 코드를 활용한 매매로 인한 어떠한 금전적 손실에 대해서도 책임지지 않습니다.