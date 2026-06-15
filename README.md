# For-fun-and-career

금융공학과 퀀트 리스크 관리를 실험하는 포트폴리오용 저장소입니다. 현재 활성 프로젝트는 `파생상품/` 폴더의 KOSPI 200 옵션 프라이싱, 델타 헤징, 채권 가격 산정 시뮬레이터입니다.

## Active Project

- [파생상품/Readme.md](파생상품/Readme.md): 실행 방법, API 설정, 옵션/채권 계산 예시
- [파생상품/main.py](파생상품/main.py): 옵션산정/채권산정 통합 CLI
- [파생상품/pricing_engine.py](파생상품/pricing_engine.py): BSM, Greeks, IV, FDM 엔진
- [파생상품/bond_pricing.py](파생상품/bond_pricing.py): 채권 YTM, Duration, Convexity, DV01, Clean/Dirty Price, Accrued Interest

## Repository Layout

```text
.
├── README.md
└── 파생상품/
    ├── api_config.example.json
    ├── bond_pricing.py
    ├── data_0020_20260414.csv
    ├── data_scraper.py
    ├── hedging_simulator.py
    ├── main.py
    ├── pricing_engine.py
    ├── Readme.md
    ├── requirements.txt
    ├── tests/
    └── visualizer.py
```

## Quick Start

```bash
cd 파생상품
pip install -r requirements.txt
python main.py --mode bond
```

또는 옵션 모드는 다음처럼 실행합니다.

```bash
python main.py --mode option
```

## Notes

- `api_config.json`, `.env`, Python cache, 로그 파일은 커밋하지 않습니다.
- 계산 결과는 연구/포트폴리오용이며 실제 투자 판단용이 아닙니다.
