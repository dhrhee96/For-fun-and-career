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
    void testCleanPriceMatchesDirtyWhenDatesAreAbsent() {
        BondSpec spec = new BondSpec(10000, 0.04, 3.0, 2);
        BondPricingEngine engine = new BondPricingEngine();

        double dirty = engine.priceBondDirty(spec, 0.035);
        double clean = engine.priceBondClean(spec, 0.035);

        assertEquals(0.0, engine.accruedInterest(spec), 1e-9);
        assertEquals(dirty, clean, 1e-9);
    }

    @Test
    void testAccruedInterestIsZeroOnCouponDate() {
        BondSpec spec = new BondSpec(
                10000,
                0.04,
                2.0,
                2,
                "2025-01-01",
                "2027-01-01",
                "2026-01-01"
        );
        BondPricingEngine engine = new BondPricingEngine();

        BondPricingEngine.AccruedInterestDetails details = engine.accruedInterestDetails(spec);

        assertEquals(0.0, engine.accruedInterest(spec), 1e-9);
        assertEquals("2026-01-01", details.previousCouponDate().toString());
        assertEquals("2026-07-01", details.nextCouponDate().toString());
        assertEquals(0, details.elapsedDays());
    }

    @Test
    void testAccruedInterestIsAboutHalfwayThroughPeriod() {
        BondSpec spec = new BondSpec(
                10000,
                0.04,
                2.0,
                2,
                "2025-01-01",
                "2027-01-01",
                "2026-04-01"
        );
        BondPricingEngine engine = new BondPricingEngine();

        assertEquals(100.0, engine.accruedInterest(spec), 2.0);
    }

    @Test
    void testDirtyPriceEqualsCleanPricePlusAccruedInterestForDatedBond() {
        BondSpec spec = new BondSpec(
                10000,
                0.04,
                2.0,
                2,
                "2025-01-01",
                "2027-01-01",
                "2026-04-01"
        );
        BondPricingEngine engine = new BondPricingEngine();
        double ytm = 0.035;

        assertEquals(
                engine.priceBondDirty(spec, ytm),
                engine.priceBondClean(spec, ytm) + engine.accruedInterest(spec),
                1e-9
        );
    }

    @Test
    void testYieldToMaturityRoundTrip() {
        BondSpec spec = new BondSpec(10000, 0.035, 3.0, 2);
        BondPricingEngine engine = new BondPricingEngine();

        double marketPrice = engine.priceBondDirty(spec, 0.038);
        double ytm = engine.yieldToMaturityFromPrice(spec, marketPrice);

        assertEquals(0.038, ytm, 1e-9);
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
