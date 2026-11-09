#!/usr/bin/env python3
"""
SEO Business Value & Executive Revenue Impact Translator
Translates complex technical SEO signals into cold business currency (Toman & USD).
Features:
  1. Organic Traffic Value (Ad Replacement Cost): calculates equivalent Google Ads budget.
  2. Core Web Vitals to Revenue Impact: models latency reduction (TTFB/LCP) to conversion uplift.
  3. Executive Memo Generator: prints a concise 1-page financial brief for C-Level & Board.
Standard library only (math, sys, dataclasses, typing).
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ExecutiveFinancialMemo:
    monthly_organic_sessions: int
    blended_cpc_toman: int
    monthly_ad_replacement_value_toman: int
    annual_ad_replacement_value_toman: int
    current_conversion_rate: float
    average_order_value_toman: int
    current_monthly_organic_revenue_toman: int
    improved_conversion_rate: float
    speed_uplift_revenue_delta_toman: int
    roi_multiple: float
    one_page_memo_markdown: str


def calculate_seo_business_value(
    monthly_organic_sessions: int,
    blended_cpc_toman: int = 4500,
    current_conversion_rate: float = 0.015,  # 1.5%
    average_order_value_toman: int = 850000,
    lcp_improvement_ms: int = 600,
    technical_investment_toman: int = 35000000
) -> ExecutiveFinancialMemo:
    # 1. Ad Replacement Value
    monthly_ad_value = monthly_organic_sessions * blended_cpc_toman
    annual_ad_value = monthly_ad_value * 12

    # 2. Baseline Revenue
    base_orders = int(monthly_organic_sessions * current_conversion_rate)
    base_revenue = base_orders * average_order_value_toman

    # 3. Core Web Vitals Latency Model: Each 100ms improvement yields ~ 0.8% conversion lift (Google/Deloitte Benchmark)
    lift_ratio = (lcp_improvement_ms / 100.0) * 0.008
    new_cr = current_conversion_rate * (1.0 + lift_ratio)
    new_orders = int(monthly_organic_sessions * new_cr)
    new_revenue = new_orders * average_order_value_toman
    speed_delta = max(0, new_revenue - base_revenue)

    # 4. ROI Multiple on Engineering Investment
    total_monthly_gain = (monthly_ad_value * 0.20) + speed_delta
    roi = round((total_monthly_gain * 12) / max(1, technical_investment_toman), 2)

    # 5. Build One-Page Memo
    memo = f"""# یادداشت اجرایی عملکرد و ارزش مالی سئو برای هیئت‌مدیره

## ۱. شاخص‌های اقتصادی و کاهش هزینه‌های بازاریابی
- **حجم بازدید ارگانیک ماهانه:** {monthly_organic_sessions:,} جلسه (Sessions)
- **ارزش جایگزین تبلیغات کلیکی (Ad Replacement Value):** {monthly_ad_value:,} تومان در ماه ({annual_ad_value:,} تومان سالانه)
  *این عدد نشان‌دهنده بودجه‌ای است که در صورت نبود سئو، باید به طور مستقیم برای خرید ورودی از گوگل ادز پرداخت می‌شد.*

## ۲. اثر بهبود زیرساخت فنی و سرعت (Core Web Vitals) بر درآمد
- **میزان کاهش تاخیر بارگذاری (LCP):** {lcp_improvement_ms} میلی‌ثانیه بهبود
- **نرخ تبدیل فروش:** از {round(current_conversion_rate*100, 2)}٪ به {round(new_cr*100, 2)}٪ افزایش یافت.
- **رشد درآمد خالص ماهانه از کانال ارگانیک:** +{speed_delta:,} تومان در ماه

## ۳. بازگشت سرمایه‌گذاری مهندسی (ROI)
- **کل سرمایه‌گذاری فنی:** {technical_investment_toman:,} تومان
- **نسبت بازگشت سرمایه سالانه (Annual ROI Multiple):** {roi}x برابر
"""

    return ExecutiveFinancialMemo(
        monthly_organic_sessions=monthly_organic_sessions,
        blended_cpc_toman=blended_cpc_toman,
        monthly_ad_replacement_value_toman=monthly_ad_value,
        annual_ad_replacement_value_toman=annual_ad_value,
        current_conversion_rate=current_conversion_rate,
        average_order_value_toman=average_order_value_toman,
        current_monthly_organic_revenue_toman=base_revenue,
        improved_conversion_rate=new_cr,
        speed_uplift_revenue_delta_toman=speed_delta,
        roi_multiple=roi,
        one_page_memo_markdown=memo
    )


def run_self_test():
    print("[SEOBusinessValue Test] شروع آزمون مدلسازی مالی سئو...")
    memo = calculate_seo_business_value(
        monthly_organic_sessions=100000,
        blended_cpc_toman=5000,
        current_conversion_rate=0.02,
        average_order_value_toman=1000000,
        lcp_improvement_ms=500,
        technical_investment_toman=50000000
    )

    assert memo.monthly_ad_replacement_value_toman == 500000000, "ارزش تبلیغاتی ۱۰۰ هزار کلیک ۵ هزار تومانی باید ۵۰۰ میلیون تومان باشد"
    assert memo.speed_uplift_revenue_delta_toman > 0, "کاهش تاخیر باید منجر به افزایش سود شود"
    assert memo.roi_multiple > 1.0, "نرخ ROI باید مثبت و بالاتر از ۱ باشد"
    assert "یادداشت اجرایی عملکرد" in memo.one_page_memo_markdown

    print(f"[SEOBusinessValue Test] موفق: ارزش ماهانه تبلیغات جایگزین = {memo.monthly_ad_replacement_value_toman:,} تومان، ضریب بازگشت سرمایه = {memo.roi_multiple}x.")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        run_self_test()
        sys.exit(0)

    if len(sys.argv) >= 2:
        sessions = int(sys.argv[1])
        cpc = int(sys.argv[2]) if len(sys.argv) >= 3 else 4500
        memo = calculate_seo_business_value(monthly_organic_sessions=sessions, blended_cpc_toman=cpc)
        print(memo.one_page_memo_markdown)
    else:
        run_self_test()
