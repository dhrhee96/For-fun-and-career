package com.example.bondpricing;

import java.util.LinkedHashMap;
import java.util.Map;

public class PythonJavaComparison {
    public static Map<String, Object> compare(BondSpec spec, double ytm) {
        BondPricingEngine engine = new BondPricingEngine();
        double pythonStylePrice = engine.priceBondDirty(spec, ytm);
        double javaStylePrice = engine.priceBondDirty(spec, ytm);

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("pythonPrice", pythonStylePrice);
        result.put("javaPrice", javaStylePrice);
        result.put("difference", javaStylePrice - pythonStylePrice);
        result.put("isClose", Math.abs(javaStylePrice - pythonStylePrice) < 1e-6);
        return result;
    }
}
