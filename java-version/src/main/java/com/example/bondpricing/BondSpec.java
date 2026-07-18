package com.example.bondpricing;

import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.util.Set;

public class BondSpec {
    private static final Set<String> SUPPORTED_DAY_COUNTS = Set.of("ACT/365", "ACT/ACT", "30/360");

    private final double faceValue;
    private final double couponRate;
    private final double maturityYears;
    private final int couponFrequency;
    private final double redemptionValue;
    private final LocalDate issueDate;
    private final LocalDate maturityDate;
    private final LocalDate settlementDate;
    private final String dayCount;

    public BondSpec(double faceValue, double couponRate, double maturityYears, int couponFrequency) {
        this(faceValue, couponRate, maturityYears, couponFrequency, faceValue);
    }

    public BondSpec(double faceValue, double couponRate, double maturityYears, int couponFrequency, double redemptionValue) {
        this(faceValue, couponRate, maturityYears, couponFrequency, redemptionValue, null, null, null, "ACT/365");
    }

    public BondSpec(
            double faceValue,
            double couponRate,
            double maturityYears,
            int couponFrequency,
            String issueDate,
            String maturityDate,
            String settlementDate
    ) {
        this(faceValue, couponRate, maturityYears, couponFrequency, faceValue, issueDate, maturityDate, settlementDate, "ACT/365");
    }

    public BondSpec(
            double faceValue,
            double couponRate,
            double maturityYears,
            int couponFrequency,
            double redemptionValue,
            String issueDate,
            String maturityDate,
            String settlementDate,
            String dayCount
    ) {
        if (faceValue <= 0) {
            throw new IllegalArgumentException("faceValue must be positive");
        }
        if (maturityYears <= 0) {
            throw new IllegalArgumentException("maturityYears must be positive");
        }
        if (couponFrequency <= 0) {
            throw new IllegalArgumentException("couponFrequency must be positive");
        }
        if (12 % couponFrequency != 0) {
            throw new IllegalArgumentException("couponFrequency must divide 12");
        }
        if (couponRate < 0) {
            throw new IllegalArgumentException("couponRate must be non-negative");
        }
        String normalizedDayCount = dayCount == null || dayCount.isBlank() ? "ACT/365" : dayCount.trim().toUpperCase();
        if (!SUPPORTED_DAY_COUNTS.contains(normalizedDayCount)) {
            throw new IllegalArgumentException("unsupported dayCount: " + dayCount);
        }
        LocalDate parsedMaturityDate = parseDate(maturityDate, "maturityDate");
        LocalDate parsedSettlementDate = parseDate(settlementDate, "settlementDate");
        if ((parsedMaturityDate == null) != (parsedSettlementDate == null)) {
            throw new IllegalArgumentException("maturityDate and settlementDate must be provided together");
        }
        if (parsedMaturityDate != null && parsedSettlementDate.isAfter(parsedMaturityDate)) {
            throw new IllegalArgumentException("settlementDate must be on or before maturityDate");
        }

        this.faceValue = faceValue;
        this.couponRate = couponRate;
        this.maturityYears = maturityYears;
        this.couponFrequency = couponFrequency;
        this.redemptionValue = redemptionValue;
        this.issueDate = parseDate(issueDate, "issueDate");
        this.maturityDate = parsedMaturityDate;
        this.settlementDate = parsedSettlementDate;
        this.dayCount = normalizedDayCount;
    }

    public double getFaceValue() { return faceValue; }
    public double getCouponRate() { return couponRate; }
    public double getMaturityYears() { return maturityYears; }
    public int getCouponFrequency() { return couponFrequency; }
    public double getRedemptionValue() { return redemptionValue; }
    public LocalDate getIssueDate() { return issueDate; }
    public LocalDate getMaturityDate() { return maturityDate; }
    public LocalDate getSettlementDate() { return settlementDate; }
    public String getDayCount() { return dayCount; }

    public boolean hasDateInputs() {
        return maturityDate != null && settlementDate != null;
    }

    public double getCouponPayment() {
        return faceValue * couponRate / couponFrequency;
    }

    public int getTotalPeriods() {
        return (int) Math.round(maturityYears * couponFrequency);
    }

    private static LocalDate parseDate(String value, String fieldName) {
        if (value == null || value.isBlank()) {
            return null;
        }
        String text = value.trim();
        for (DateTimeFormatter formatter : new DateTimeFormatter[]{
                DateTimeFormatter.ISO_LOCAL_DATE,
                DateTimeFormatter.BASIC_ISO_DATE,
                DateTimeFormatter.ofPattern("yyyy/MM/dd")
        }) {
            try {
                return LocalDate.parse(text, formatter);
            } catch (DateTimeParseException ignored) {
                // try next accepted Python-compatible format
            }
        }
        throw new IllegalArgumentException(fieldName + " must use YYYY-MM-DD, YYYYMMDD, or YYYY/MM/DD");
    }
}
