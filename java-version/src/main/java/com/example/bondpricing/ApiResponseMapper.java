package com.example.bondpricing;

import java.util.LinkedHashMap;
import java.util.Map;

public class ApiResponseMapper {
    public static Map<String, Object> mapApiResponse(Map<String, Object> raw) {
        Map<String, Object> mapped = new LinkedHashMap<>();
        mapped.put("faceValue", toDouble(raw.get("faceValue"), 10000.0));
        mapped.put("couponRate", toDouble(raw.get("couponRate"), 0.035));
        mapped.put("maturityYears", toDouble(raw.get("maturityYears"), 3.0));
        mapped.put("couponFrequency", toInt(raw.get("couponFrequency"), 2));
        mapped.put("marketPrice", toDouble(raw.get("marketPrice"), 10000.0));
        mapped.put("ytm", toDouble(raw.get("ytm"), 0.035));
        mapped.put("issueDate", toString(raw.get("issueDate"), null));
        mapped.put("maturityDate", toString(raw.get("maturityDate"), null));
        mapped.put("settlementDate", toString(raw.get("settlementDate"), null));
        mapped.put("dayCount", toString(raw.get("dayCount"), "ACT/365"));
        return mapped;
    }

    private static double toDouble(Object value, double fallback) {
        if (value instanceof Number number) {
            return number.doubleValue();
        }
        if (value instanceof String text) {
            try {
                return Double.parseDouble(text);
            } catch (NumberFormatException ignored) {
                return fallback;
            }
        }
        return fallback;
    }

    private static int toInt(Object value, int fallback) {
        if (value instanceof Number number) {
            return number.intValue();
        }
        if (value instanceof String text) {
            try {
                return Integer.parseInt(text);
            } catch (NumberFormatException ignored) {
                return fallback;
            }
        }
        return fallback;
    }

    private static String toString(Object value, String fallback) {
        if (value == null) {
            return fallback;
        }
        String text = String.valueOf(value).trim();
        return text.isEmpty() ? fallback : text;
    }
}
