package com.example.bondpricing;

public class BondPricingEngine {

    public double priceBondDirty(BondSpec spec, double ytm) {
        if (ytm <= -0.999) {
            throw new IllegalArgumentException("YTM is too low");
        }

        double discountBase = 1.0 + ytm / spec.getCouponFrequency();
        double price = 0.0;
        int periods = spec.getTotalPeriods();

        for (int i = 1; i <= periods; i++) {
            double cashFlow = spec.getCouponPayment();
            if (i == periods) {
                cashFlow += spec.getRedemptionValue();
            }
            price += cashFlow / Math.pow(discountBase, i);
        }

        return price;
    }

    public double priceBondClean(BondSpec spec, double ytm) {
        double dirtyPrice = priceBondDirty(spec, ytm);
        return dirtyPrice - accruedInterest(spec);
    }

    public double accruedInterest(BondSpec spec) {
        double couponPayment = spec.getCouponPayment();
        return couponPayment * 0.5;
    }

    public double yieldToMaturityFromPrice(BondSpec spec, double marketPrice) {
        if (marketPrice <= 0) {
            throw new IllegalArgumentException("marketPrice must be positive");
        }

        double lower = -0.95;
        double upper = 1.0;
        double mid = 0.0;

        for (int i = 0; i < 200; i++) {
            mid = (lower + upper) / 2.0;
            double value = priceBondDirty(spec, mid) - marketPrice;
            if (Math.abs(value) < 1e-8) {
                return mid;
            }
            if (value > 0) {
                upper = mid;
            } else {
                lower = mid;
            }
        }
        return mid;
    }

    public double[] durationConvexity(BondSpec spec, double ytm) {
        double price = priceBondDirty(spec, ytm);
        double macaulayDuration = 0.0;
        int periods = spec.getTotalPeriods();

        for (int i = 1; i <= periods; i++) {
            double cashFlow = spec.getCouponPayment();
            if (i == periods) {
                cashFlow += spec.getRedemptionValue();
            }
            double pv = cashFlow / Math.pow(1.0 + ytm / spec.getCouponFrequency(), i);
            macaulayDuration += (i / (double) spec.getCouponFrequency()) * pv;
        }

        macaulayDuration /= price;
        double modifiedDuration = macaulayDuration / (1.0 + ytm / spec.getCouponFrequency());
        double convexity = 0.0;

        for (int i = 1; i <= periods; i++) {
            double cashFlow = spec.getCouponPayment();
            if (i == periods) {
                cashFlow += spec.getRedemptionValue();
            }
            double pv = cashFlow / Math.pow(1.0 + ytm / spec.getCouponFrequency(), i);
            convexity += (i / (double) spec.getCouponFrequency()) * ((i / (double) spec.getCouponFrequency()) + 1.0) * pv;
        }

        convexity /= price * Math.pow(1.0 + ytm / spec.getCouponFrequency(), 2.0);

        return new double[]{price, macaulayDuration, modifiedDuration, convexity};
    }
}
