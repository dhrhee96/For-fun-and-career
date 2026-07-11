package com.example.bondpricing.data;

import java.util.ArrayList;
import java.util.List;

public class CsvToBondInput {
    public static class BondInput {
        public final double faceValue;
        public final double couponRate;
        public final double maturityYears;
        public final int couponFrequency;
        public final double marketPrice;
        public final double ytm;

        public BondInput(double faceValue, double couponRate, double maturityYears, int couponFrequency, double marketPrice, double ytm) {
            this.faceValue = faceValue;
            this.couponRate = couponRate;
            this.maturityYears = maturityYears;
            this.couponFrequency = couponFrequency;
            this.marketPrice = marketPrice;
            this.ytm = ytm;
        }
    }

    public static List<BondInput> parseCsvRows(List<String> rows) {
        List<BondInput> inputs = new ArrayList<>();
        for (String row : rows) {
            if (row == null || row.isBlank()) {
                continue;
            }
            String[] parts = row.split(",");
            if (parts.length < 4) {
                continue;
            }
            try {
                double faceValue = Double.parseDouble(parts[0].trim());
                double couponRate = Double.parseDouble(parts[1].trim()) / 100.0;
                double maturityYears = Double.parseDouble(parts[2].trim());
                int couponFrequency = Integer.parseInt(parts[3].trim());
                double marketPrice = parts.length > 4 ? Double.parseDouble(parts[4].trim()) : faceValue;
                double ytm = parts.length > 5 ? Double.parseDouble(parts[5].trim()) / 100.0 : 0.035;
                inputs.add(new BondInput(faceValue, couponRate, maturityYears, couponFrequency, marketPrice, ytm));
            } catch (NumberFormatException ignored) {
                // skip invalid rows
            }
        }
        return inputs;
    }
}
