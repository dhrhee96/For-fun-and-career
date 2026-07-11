package com.example.bondpricing;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

public class BondPricingEngineTest {

    @Test
    void testDirtyPriceMatchesReference() {
        BondSpec spec = new BondSpec(10000, 0.035, 3.0, 2);
        BondPricingEngine engine = new BondPricingEngine();

        double price = engine.priceBondDirty(spec, 0.038);

        assertEquals(9915.6942, price, 1e-4);
    }

    @Test
    void testCleanPriceIsDirtyMinusAccruedInterest() {
        BondSpec spec = new BondSpec(10000, 0.04, 3.0, 2);
        BondPricingEngine engine = new BondPricingEngine();

        double dirty = engine.priceBondDirty(spec, 0.035);
        double clean = engine.priceBondClean(spec, 0.035);

        assertTrue(clean < dirty);
        assertEquals(dirty - 200.0, clean, 1e-9);
    }

    @Test
    void testDurationAndConvexityArePositive() {
        BondSpec spec = new BondSpec(10000, 0.035, 3.0, 2);
        BondPricingEngine engine = new BondPricingEngine();

        double[] metrics = engine.durationConvexity(spec, 0.035);

        assertTrue(metrics[1] > 0.0);
        assertTrue(metrics[2] > 0.0);
        assertTrue(metrics[3] > 0.0);
    }
}
