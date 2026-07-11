# Java Version: Bond Pricing

This folder contains a Java port of the core bond pricing features from the Python project.

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

## Example
```java
BondSpec spec = new BondSpec(10000, 0.035, 3.0, 2);
BondPricingEngine engine = new BondPricingEngine();

System.out.println(engine.priceBondDirty(spec, 0.038));
```
