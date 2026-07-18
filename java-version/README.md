# Java Version: Bond Pricing

This folder contains a Java port of the core bond pricing features from the Python project.

> **Python vs Java** — 채권 가격·YTM·듀레이션 계산, 예외 처리,
> JUnit 테스트, Python 결과 비교

## Included features
- Bond price calculation
- YTM-based pricing
- Clean/dirty price separation
- Basic duration and convexity estimation
- CSV input conversion for bond data
- API response mapping for bond inputs
- Python/Java result comparison utility
- JUnit-based validation

## Structure
- src/main/java/com/example/bondpricing/BondSpec.java
- src/main/java/com/example/bondpricing/BondPricingEngine.java
- src/main/java/com/example/bondpricing/ApiResponseMapper.java
- src/main/java/com/example/bondpricing/PythonJavaComparison.java
- src/main/java/com/example/bondpricing/data/CsvToBondInput.java
- src/test/java/com/example/bondpricing/BondPricingEngineTest.java
- src/test/java/com/example/bondpricing/DataMappingAndComparisonTest.java

## Build and test
```bash
mvn test
```

From the repository root, run both the Python and Java unit tests with a
single, readable report:

```powershell
.\run-tests.ps1
```

The command prints every Python and Java test and finishes with one combined
pass/fail result.

Prerequisites are Python dependencies from `requirements.txt`, JDK 17, and
Maven available on `PATH`. Missing prerequisites are reported as `SKIP`
instead of terminating the report abruptly.

## Python vs Java 결과 비교

저장소 루트에서 다음 명령을 실행하면 동일한 채권 조건을 Python과
Java로 각각 계산합니다. Java 소스는 실행 전에 자동으로 컴파일됩니다.

```powershell
python compare_bond_results.py
```

비교 조건은 액면가 10,000원, 표면금리 3.5%, 만기 3년, 연 2회 이자 지급,
YTM 3.8%입니다.

```text
Python vs Java bond calculation
==============================================================================
Metric                           Python             Java    Abs. difference
------------------------------------------------------------------------------
Bond price                9915.69424751    9915.69424800       0.0000004862
Implied YTM (%)              3.80000000       3.80000000       0.0000000003
Macaulay duration            2.87328670       2.87328670       0.0000000010
Modified duration            2.81971217       2.81971217       0.0000000002
Convexity                    9.54438131       9.54438131       0.0000000009
DV01                         2.79594037       2.79594037       0.0000000042
------------------------------------------------------------------------------
Result: MATCH
```

표의 `Abs. difference`는 두 구현의 절대 차이입니다. 출력 자릿수에서 생긴
미세한 반올림 차이를 제외하면 결과가 일치하며, 허용 오차 `1e-6` 이내이면
`MATCH`로 표시됩니다.

## 예외 처리

두 구현은 잘못된 액면가·만기·쿠폰 지급 횟수, 지원하지 않는 day-count,
0 이하의 시장가격, 계산할 수 없는 YTM 범위를 명시적인 예외로 처리합니다.
Java에서는 `IllegalArgumentException`, Python에서는 `ValueError`가 발생합니다.

## Example
```java
BondSpec spec = new BondSpec(10000, 0.035, 3.0, 2);
BondPricingEngine engine = new BondPricingEngine();

System.out.println(engine.priceBondDirty(spec, 0.038));
```
