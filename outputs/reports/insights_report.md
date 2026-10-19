# Expense Tracker - Automated Insight Report

**Project:** Expense Tracker App v1.0.0  
**Author:** Harsha K S  
**Window:** 2025-10-01 to 2026-09-30 (12 months)  
**Users:** 50  
**Transactions analysed:** 16,179

---

## 1. Executive summary

- **Total spend:** ₹37,263,112 across 16,179 transactions (10 categories, 50 users).
- **Average transaction:** ₹2,303; **average monthly spend per user:** ₹62,105 against a ₹53,500 budget.
- **30-day burn rate per user:** ₹44,279 - 124.7% of the ₹35,500 per-user *variable* budget, i.e. the wallet is running hot.
- **Overall savings rate:** +10.0%.
- **Spend is concentrated:** 5 of 10 categories account for 77.3% of every rupee spent.

## 2. Category mix

**Rent & Utilities** is the single largest category at **27.7%** of total spend (₹10,326,927 over 571 transactions).

| Rank | Category | Spend | Share | Cumulative | Txns | Avg txn |
| ---: | --- | ---: | ---: | ---: | ---: | ---: |
| 1 | Rent & Utilities | ₹10,326,927 | 27.7% | 27.7% | 571 | ₹18,086 |
| 2 | Travel | ₹5,538,535 | 14.9% | 42.6% | 651 | ₹8,508 |
| 3 | Food & Dining | ₹5,472,478 | 14.7% | 57.3% | 5,259 | ₹1,041 |
| 4 | Shopping | ₹4,098,347 | 11.0% | 68.3% | 840 | ₹4,879 |
| 5 | Groceries | ₹3,377,844 | 9.1% | 77.3% | 1,721 | ₹1,963 |
| 6 | Transport | ₹2,631,101 | 7.1% | 84.4% | 4,066 | ₹647 |
| 7 | Education | ₹1,751,803 | 4.7% | 89.1% | 624 | ₹2,807 |
| 8 | Entertainment | ₹1,633,476 | 4.4% | 93.5% | 1,174 | ₹1,391 |
| 9 | Health | ₹1,380,419 | 3.7% | 97.2% | 625 | ₹2,209 |
| 10 | Miscellaneous | ₹1,052,182 | 2.8% | 100.0% | 648 | ₹1,624 |

> **Pareto:** the top 5 categories (Rent & Utilities, Travel, Food & Dining, Shopping, Groceries) cover 77.3% of spend. A budget review should start there and nowhere else.

## 3. Budget performance

Budgets are per user per month. Actuals are the per-user average.

| Category | Budget | Actual (per user) | Variance | Status |
| --- | ---: | ---: | ---: | :--- |
| Education | ₹1,500 | ₹2,920 | +94.6% | Over budget |
| Travel | ₹5,000 | ₹9,231 | +84.6% | Over budget |
| Miscellaneous | ₹1,500 | ₹1,754 | +16.9% | Over budget |
| Health | ₹2,000 | ₹2,301 | +15.0% | Over budget |
| Food & Dining | ₹8,000 | ₹9,121 | +14.0% | Over budget |
| Shopping | ₹6,000 | ₹6,831 | +13.8% | Over budget |
| Groceries | ₹5,000 | ₹5,630 | +12.6% | Over budget |
| Transport | ₹4,000 | ₹4,385 | +9.6% | Over budget |
| Entertainment | ₹2,500 | ₹2,722 | +8.9% | Over budget |
| Rent & Utilities | ₹18,000 | ₹17,212 | -4.4% | On track |

- **Worst overrun:** Education at +94.6% (₹1,420 per user per month above budget).
- **Best controlled:** Rent & Utilities at -4.4%.

## 4. Monthly trend

- **Peak month:** 2026-03 at ₹3,996,844.
- **Lowest month:** 2026-05 at ₹2,747,573.
- **Peak vs trough swing:** 45.5%.

| Month | Spend | MoM | Savings rate |
| --- | ---: | ---: | ---: |
| 2025-10 | ₹3,080,467 | - | +10.7% |
| 2025-11 | ₹3,782,575 | +22.8% | -9.7% |
| 2025-12 | ₹3,075,435 | -18.7% | +10.8% |
| 2026-01 | ₹2,917,897 | -5.1% | +15.4% |
| 2026-02 | ₹2,939,410 | +0.7% | +14.8% |
| 2026-03 | ₹3,996,844 | +36.0% | -15.9% |
| 2026-04 | ₹3,098,168 | -22.5% | +10.2% |
| 2026-05 | ₹2,747,573 | -11.3% | +20.3% |
| 2026-06 | ₹2,829,596 | +3.0% | +18.0% |
| 2026-07 | ₹3,077,706 | +8.8% | +10.8% |
| 2026-08 | ₹2,793,029 | -9.2% | +19.0% |
| 2026-09 | ₹2,924,413 | +4.7% | +15.2% |

## 5. Spending patterns

- **Busiest day of the week:** Sunday.
- **Weekend share of spend:** 32.9%.
- **Busiest time bucket:** Midday (10-14).
- **Top payment method:** UPI (41.9% of value).

### Top merchants (fixed bills excluded)

| Merchant | Category | Spend | Txns |
| --- | --- | ---: | ---: |
| Airbnb | Travel | ₹1,233,554 | 146 |
| IRCTC | Travel | ₹1,214,934 | 138 |
| IndiGo | Travel | ₹1,167,010 | 135 |
| Local Cafe | Food & Dining | ₹1,117,189 | 1,051 |
| Dominos | Food & Dining | ₹1,110,596 | 1,067 |
| Starbucks | Food & Dining | ₹1,089,135 | 1,071 |
| Zomato | Food & Dining | ₹1,079,548 | 1,042 |
| Swiggy | Food & Dining | ₹1,076,010 | 1,028 |

## 6. Anomaly detection

A robust z-score (median / MAD) is computed **per user**, so a flagged day means *that person* spent far more than *their own* normal day - not that the group average moved.

- **657 abnormal user-days** across 46 of 50 users.
- Threshold: robust z > 2.5 **and** spend >= ₹5,000 **and** at least 2 transactions (so a single big booking alone does not flag a day).
- Median daily discretionary spend (all users): ₹71,595; MAD: ₹17,523.
- Recurring bills (Rent & Utilities) are excluded - paying rent on time is not an anomaly.
- 30-day burn rate: ₹44,279 per user, which is **124.7%** of the per-user *variable* budget (₹35,500).

### Most extreme user-days

| Date | User | Spend | Their median day | z | Txns |
| --- | --- | ---: | ---: | ---: | ---: |
| 2026-04-27 | U044 | ₹8,065 | ₹571 | 20.7 | 3 |
| 2026-03-29 | U007 | ₹8,491 | ₹637 | 20.0 | 4 |
| 2025-12-07 | U038 | ₹21,870 | ₹1,306 | 18.7 | 3 |
| 2026-07-05 | U050 | ₹54,773 | ₹3,507 | 18.6 | 8 |
| 2026-01-05 | U013 | ₹9,516 | ₹651 | 18.5 | 2 |
| 2026-03-25 | U040 | ₹22,829 | ₹1,447 | 16.6 | 4 |
| 2026-03-25 | U013 | ₹7,484 | ₹651 | 14.2 | 2 |
| 2025-11-08 | U007 | ₹6,191 | ₹637 | 14.2 | 2 |
| 2026-03-26 | U010 | ₹19,864 | ₹1,535 | 14.1 | 5 |
| 2026-03-30 | U044 | ₹5,657 | ₹571 | 14.0 | 3 |

## 7. Savings

- Average monthly income per user: ₹68,979
- Average monthly spend per user: ₹62,105
- Overall savings rate: **+10.0%**
- Worst month: 2026-03 (-15.9%)
- Best month: 2026-05 (+20.3%)

## 8. User segments

| Segment | Users | Spend | Share | Spend / user |
| --- | ---: | ---: | ---: | ---: |
| Moderate spender | 30 | ₹19,507,958 | 52.4% | ₹650,265 |
| Heavy spender | 9 | ₹13,956,555 | 37.5% | ₹1,550,728 |
| Light spender | 11 | ₹3,798,599 | 10.2% | ₹345,327 |

> 37.5% of spend from 18.0% of users. A budgeting product should treat heavy spenders as the primary persona - they have the most to gain from an alert and the highest willingness to pay.

## 9. Recommended actions

1. **Cap the two categories that break the budget** - Education (+95%) and Travel (+85%).
2. **Set a pre-festival envelope.** The two spike months cost roughly 33% more than a normal month; saving into them in advance removes the negative savings rate.
3. **Alert on the 657 anomalous user-days**, not on every transaction - a robust per-user threshold keeps the false-positive rate low.
4. **Target heavy spenders first.** They generate the majority of value and are the ones whose budget variance actually matters in rupee terms.
5. **Watch the top 5 merchants** - they alone represent 21.7% of variable spend.

## 10. Reproduce this report

```bash
python main.py all       # regenerate data, clean, analyse, chart and write this report
python main.py dashboard # interactive Streamlit dashboard
```

Generated by Expense Tracker App - every figure above traces back to `data\processed\expenses_clean.csv` and the statistical routines in `src/analysis.py`.
