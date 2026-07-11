package com.example.bondpricing;

public class Main {
    public static void main(String[] args) {
        BondSpec spec = new BondSpec(10000, 0.035, 3.0, 2);
        BondPricingEngine engine = new BondPricingEngine();

        double dirty = engine.priceBondDirty(spec, 0.038);
        double clean = engine.priceBondClean(spec, 0.035);
        double ytm = engine.yieldToMaturityFromPrice(spec, 9915.6942);

        System.out.println("Dirty price: " + dirty);
        System.out.println("Clean price: " + clean);
        System.out.println("Implied YTM: " + ytm);
    }
}
