package com.example.bondpricing;

public class Main {
    public static void main(String[] args) {
        BondSpec spec = new BondSpec(10000, 0.035, 3.0, 2);
        BondPricingEngine engine = new BondPricingEngine();
        double inputYtm = 0.038;

        double dirty = engine.priceBondDirty(spec, inputYtm);
        double clean = engine.priceBondClean(spec, inputYtm);
        double impliedYtm = engine.yieldToMaturityFromPrice(spec, dirty);
        double[] risk = engine.durationConvexity(spec, inputYtm);

        System.out.printf("%-20s %15s%n", "Metric", "Java result");
        System.out.println("-------------------------------------");
        System.out.printf("%-20s %,15.6f%n", "Dirty price", dirty);
        System.out.printf("%-20s %,15.6f%n", "Clean price", clean);
        System.out.printf("%-20s %,14.8f%%%n", "Implied YTM", impliedYtm * 100.0);
        System.out.printf("%-20s %,15.8f%n", "Macaulay duration", risk[1]);
        System.out.printf("%-20s %,15.8f%n", "Modified duration", risk[2]);
        System.out.printf("%-20s %,15.8f%n", "Convexity", risk[3]);
        System.out.printf("%-20s %,15.8f%n", "DV01", risk[4]);
    }
}
