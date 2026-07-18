package com.example.bondpricing;

import java.time.LocalDate;
import java.time.Year;
import java.time.temporal.ChronoUnit;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

public class BondPricingEngine {
    private record CashFlow(int period, double timeYears, double cashFlow, double discountPeriod) {}
    public record AccruedInterestDetails(
            double accruedInterest,
            LocalDate previousCouponDate,
            LocalDate nextCouponDate,
            int elapsedDays,
            int couponPeriodDays
    ) {}

    public double priceBondDirty(BondSpec spec, double ytm) {
        if (ytm <= -0.999) {
            throw new IllegalArgumentException("YTM is too low");
        }

        double discountBase = 1.0 + ytm / spec.getCouponFrequency();
        if (discountBase <= 0) {
            throw new IllegalArgumentException("discount factor base must be positive");
        }
        double price = 0.0;
        for (CashFlow cashFlow : buildCashflows(spec)) {
            price += cashFlow.cashFlow() / Math.pow(discountBase, cashFlow.discountPeriod());
        }

        return price;
    }

    public double priceBondClean(BondSpec spec, double ytm) {
        double dirtyPrice = priceBondDirty(spec, ytm);
        return dirtyPrice - accruedInterest(spec);
    }

    public double accruedInterest(BondSpec spec) {
        return accruedInterestDetails(spec).accruedInterest();
    }

    public AccruedInterestDetails accruedInterestDetails(BondSpec spec) {
        if (!spec.hasDateInputs()) {
            return new AccruedInterestDetails(0.0, null, null, 0, 0);
        }

        CouponDates couponDates = couponDatesAroundSettlement(spec);
        int elapsedDays = couponDates.previous().equals(spec.getSettlementDate())
                ? 0
                : dayCountDays(couponDates.previous(), spec.getSettlementDate(), spec.getDayCount());
        int couponPeriodDays = dayCountDays(couponDates.previous(), couponDates.next(), spec.getDayCount());
        double accrued = couponPeriodDays == 0 ? 0.0 : spec.getCouponPayment() * elapsedDays / couponPeriodDays;

        return new AccruedInterestDetails(
                accrued,
                couponDates.previous(),
                couponDates.next(),
                elapsedDays,
                couponPeriodDays
        );
    }

    public double yieldToMaturityFromPrice(BondSpec spec, double marketPrice) {
        if (marketPrice <= 0) {
            throw new IllegalArgumentException("marketPrice must be positive");
        }

        double lower = -0.95;
        double upper = 1.0;
        double mid = 0.0;
        double lowerValue = priceBondDirty(spec, lower) - marketPrice;
        double upperValue = priceBondDirty(spec, upper) - marketPrice;

        if (lowerValue == 0.0) {
            return lower;
        }
        if (upperValue == 0.0) {
            return upper;
        }
        if (lowerValue * upperValue > 0) {
            throw new IllegalArgumentException("No YTM found in search range");
        }

        for (int i = 0; i < 200; i++) {
            mid = (lower + upper) / 2.0;
            double midValue = priceBondDirty(spec, mid) - marketPrice;
            if (Math.abs(midValue) < 1e-10) {
                return mid;
            }
            if (lowerValue * midValue <= 0) {
                upper = mid;
                upperValue = midValue;
            } else {
                lower = mid;
                lowerValue = midValue;
            }
        }
        return mid;
    }

    public double[] durationConvexity(BondSpec spec, double ytm) {
        double price = priceBondDirty(spec, ytm);
        double macaulayDuration = 0.0;
        List<CashFlow> cashFlows = buildCashflows(spec);
        double discountBase = 1.0 + ytm / spec.getCouponFrequency();

        for (CashFlow cashFlow : cashFlows) {
            double pv = cashFlow.cashFlow() / Math.pow(discountBase, cashFlow.discountPeriod());
            macaulayDuration += cashFlow.timeYears() * pv;
        }

        macaulayDuration /= price;
        double modifiedDuration = macaulayDuration / discountBase;
        double convexity = 0.0;

        for (CashFlow cashFlow : cashFlows) {
            double pv = cashFlow.cashFlow() / Math.pow(discountBase, cashFlow.discountPeriod());
            double period = cashFlow.discountPeriod();
            convexity += pv * period * (period + 1.0)
                    / (Math.pow(spec.getCouponFrequency(), 2.0) * Math.pow(discountBase, 2.0));
        }

        convexity /= price;
        double dv01 = price * modifiedDuration * 0.0001;

        return new double[]{price, macaulayDuration, modifiedDuration, convexity, dv01};
    }

    public double[] approximatePriceChange(double price, double modifiedDuration, double convexity, double deltaY) {
        double durationEffect = -modifiedDuration * deltaY;
        double convexityEffect = 0.5 * convexity * deltaY * deltaY;
        double totalChange = durationEffect + convexityEffect;
        double priceChange = price * totalChange;
        return new double[]{deltaY, durationEffect, convexityEffect, totalChange, priceChange, price + priceChange};
    }

    private List<CashFlow> buildCashflows(BondSpec spec) {
        if (spec.hasDateInputs()) {
            return buildDatedCashflows(spec);
        }

        List<CashFlow> cashFlows = new ArrayList<>();
        for (int period = 1; period <= spec.getTotalPeriods(); period++) {
            double cashFlow = spec.getCouponPayment();
            if (period == spec.getTotalPeriods()) {
                cashFlow += spec.getRedemptionValue();
            }
            cashFlows.add(new CashFlow(
                    period,
                    period / (double) spec.getCouponFrequency(),
                    cashFlow,
                    period
            ));
        }
        return cashFlows;
    }

    private List<CashFlow> buildDatedCashflows(BondSpec spec) {
        List<LocalDate> futureCouponDates = futureCouponDates(spec);
        if (futureCouponDates.isEmpty()) {
            return List.of();
        }

        AccruedInterestDetails details = accruedInterestDetails(spec);
        int remainingDays = dayCountDays(spec.getSettlementDate(), details.nextCouponDate(), spec.getDayCount());
        double firstPeriod = details.couponPeriodDays() == 0
                ? 0.0
                : remainingDays / (double) details.couponPeriodDays();

        List<CashFlow> cashFlows = new ArrayList<>();
        for (int index = 0; index < futureCouponDates.size(); index++) {
            LocalDate couponDate = futureCouponDates.get(index);
            double cashFlow = spec.getCouponPayment();
            if (index == futureCouponDates.size() - 1) {
                cashFlow += spec.getRedemptionValue();
            }
            cashFlows.add(new CashFlow(
                    index + 1,
                    yearFraction(spec.getSettlementDate(), couponDate, spec.getDayCount()),
                    cashFlow,
                    firstPeriod + index
            ));
        }
        return cashFlows;
    }

    private List<LocalDate> futureCouponDates(BondSpec spec) {
        int months = 12 / spec.getCouponFrequency();
        List<LocalDate> dates = new ArrayList<>();
        LocalDate couponDate = spec.getMaturityDate();

        while (couponDate.isAfter(spec.getSettlementDate())) {
            if (spec.getIssueDate() == null || !couponDate.isBefore(spec.getIssueDate())) {
                dates.add(couponDate);
            }
            couponDate = couponDate.minusMonths(months);
        }

        dates.sort(Comparator.naturalOrder());
        return dates;
    }

    private record CouponDates(LocalDate previous, LocalDate next) {}

    private CouponDates couponDatesAroundSettlement(BondSpec spec) {
        int months = 12 / spec.getCouponFrequency();
        LocalDate next = spec.getMaturityDate();

        while (next.minusMonths(months).isAfter(spec.getSettlementDate())
                || next.minusMonths(months).equals(spec.getSettlementDate())) {
            next = next.minusMonths(months);
        }

        LocalDate previous = next.minusMonths(months);
        if (spec.getIssueDate() != null && previous.isBefore(spec.getIssueDate())) {
            previous = spec.getIssueDate();
        }
        if (spec.getSettlementDate().equals(previous)) {
            return new CouponDates(previous, next);
        }
        if (spec.getSettlementDate().equals(next)) {
            LocalDate following = next.plusMonths(months);
            return new CouponDates(next, following);
        }
        return new CouponDates(previous, next);
    }

    private int dayCountDays(LocalDate start, LocalDate end, String convention) {
        if (end.isBefore(start)) {
            throw new IllegalArgumentException("end date must be on or after start date");
        }
        return switch (convention.toUpperCase()) {
            case "ACT/365", "ACT/ACT" -> (int) ChronoUnit.DAYS.between(start, end);
            case "30/360" -> {
                int startDay = Math.min(start.getDayOfMonth(), 30);
                int endDay = startDay == 30 ? Math.min(end.getDayOfMonth(), 30) : end.getDayOfMonth();
                yield (end.getYear() - start.getYear()) * 360
                        + (end.getMonthValue() - start.getMonthValue()) * 30
                        + (endDay - startDay);
            }
            default -> throw new IllegalArgumentException("unsupported day count: " + convention);
        };
    }

    private double yearFraction(LocalDate start, LocalDate end, String convention) {
        int days = dayCountDays(start, end, convention);
        if ("ACT/ACT".equalsIgnoreCase(convention)) {
            if (start.getYear() == end.getYear()) {
                return days / (double) (Year.isLeap(start.getYear()) ? 366 : 365);
            }
            double total = 0.0;
            LocalDate current = start;
            while (current.isBefore(end)) {
                LocalDate nextYear = LocalDate.of(current.getYear() + 1, 1, 1);
                LocalDate segmentEnd = nextYear.isBefore(end) ? nextYear : end;
                total += ChronoUnit.DAYS.between(current, segmentEnd)
                        / (double) (Year.isLeap(current.getYear()) ? 366 : 365);
                current = segmentEnd;
            }
            return total;
        }
        if ("30/360".equalsIgnoreCase(convention)) {
            return days / 360.0;
        }
        return days / 365.0;
    }
}
