package com.example.bondpricing;

import com.example.bondpricing.data.CsvToBondInput;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

public class DataMappingAndComparisonTest {

    @Test
    void testCsvParsingCreatesExpectedRows() {
        List<String> rows = List.of(
                "10000,3.5,3,2,9800,3.8",
                "5000,2.5,5,4"
        );

        List<CsvToBondInput.BondInput> inputs = CsvToBondInput.parseCsvRows(rows);

        assertEquals(2, inputs.size());
        assertEquals(10000.0, inputs.get(0).faceValue, 1e-9);
        assertEquals(0.035, inputs.get(0).couponRate, 1e-9);
        assertEquals(3.0, inputs.get(0).maturityYears, 1e-9);
        assertEquals(2, inputs.get(0).couponFrequency);
    }

    @Test
    void testApiResponseMappingAndComparison() {
        Map<String, Object> raw = Map.of(
                "faceValue", 10000,
                "couponRate", 0.035,
                "maturityYears", 3.0,
                "couponFrequency", 2,
                "marketPrice", 9915.6942,
                "ytm", 0.038
        );

        Map<String, Object> mapped = ApiResponseMapper.mapApiResponse(raw);
        BondSpec spec = new BondSpec(
                ((Number) mapped.get("faceValue")).doubleValue(),
                ((Number) mapped.get("couponRate")).doubleValue(),
                ((Number) mapped.get("maturityYears")).doubleValue(),
                ((Number) mapped.get("couponFrequency")).intValue()
        );
        BondPricingEngine engine = new BondPricingEngine();
        double price = engine.priceBondDirty(spec, ((Number) mapped.get("ytm")).doubleValue());

        Map<String, Object> comparison = PythonJavaComparison.compare(spec, ((Number) mapped.get("ytm")).doubleValue());

        assertTrue(price > 0.0);
        assertTrue((Boolean) comparison.get("isClose"));
    }
}
