package com.example.bondpricing;

public class BondSpec {
    private final double faceValue;
    private final double couponRate;
    private final double maturityYears;
    private final int couponFrequency;
    private final double redemptionValue;

    public BondSpec(double faceValue, double couponRate, double maturityYears, int couponFrequency) {
        this(faceValue, couponRate, maturityYears, couponFrequency, faceValue);
    }

    public BondSpec(double faceValue, double couponRate, double maturityYears, int couponFrequency, double redemptionValue) {
        if (faceValue <= 0) {
            throw new IllegalArgumentException("faceValue must be positive");
        }
        if (maturityYears <= 0) {
            throw new IllegalArgumentException("maturityYears must be positive");
        }
        if (couponFrequency <= 0) {
            throw new IllegalArgumentException("couponFrequency must be positive");
        }
        if (couponRate < 0) {
            throw new IllegalArgumentException("couponRate must be non-negative");
        }
        this.faceValue = faceValue;
        this.couponRate = couponRate;
        this.maturityYears = maturityYears;
        this.couponFrequency = couponFrequency;
        this.redemptionValue = redemptionValue;
    }

    public double getFaceValue() { return faceValue; }
    public double getCouponRate() { return couponRate; }
    public double getMaturityYears() { return maturityYears; }
    public int getCouponFrequency() { return couponFrequency; }
    public double getRedemptionValue() { return redemptionValue; }

    public double getCouponPayment() {
        return faceValue * couponRate / couponFrequency;
    }

    public int getTotalPeriods() {
        return (int) Math.round(maturityYears * couponFrequency);
    }
}
