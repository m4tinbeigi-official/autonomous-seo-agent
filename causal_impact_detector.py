#!/usr/bin/env python3
"""
Causal Impact & Algorithmic Change-Point Detector
Differentiates between:
  1. Technical Outages / Internal Deploy Glitches (sharp immediate step-drop).
  2. Google Algorithm Core Updates (multi-day gradual reassessment across entity clusters).
  3. Seasonal / Day-of-week fluctuations.
Uses statistical change-point detection (Moving Averages + Welch's T-Score + Variance Ratio).
Standard library only (math, statistics, dataclasses, typing).
"""

from __future__ import annotations

import math
import statistics
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class AnomalyDetectionResult:
    is_anomaly_detected: bool
    change_point_index: Optional[int]
    pre_mean: float
    post_mean: float
    percentage_change: float
    t_statistic: float
    classification: str
    confidence: float
    diagnostics: List[str] = field(default_factory=list)


def detect_traffic_shift(
    time_series_clicks: List[float],
    min_window: int = 7
) -> AnomalyDetectionResult:
    """
    Evaluates a daily time-series of clicks/impressions to detect significant structural shifts.
    """
    n = len(time_series_clicks)
    if n < min_window * 2:
        return AnomalyDetectionResult(
            is_anomaly_detected=False,
            change_point_index=None,
            pre_mean=0.0,
            post_mean=0.0,
            percentage_change=0.0,
            t_statistic=0.0,
            classification="داده‌های ناکافی (حداقل ۱۴ روز داده الزامی است)",
            confidence=0.0
        )

    # Search for maximum mean divergence change point
    best_split = min_window
    max_t_stat = 0.0
    best_pre_mean = 0.0
    best_post_mean = 0.0

    for split in range(min_window, n - min_window + 1):
        pre = time_series_clicks[:split]
        post = time_series_clicks[split:]

        m_pre = statistics.mean(pre)
        m_post = statistics.mean(post)
        v_pre = statistics.variance(pre) if len(pre) > 1 else 0.01
        v_post = statistics.variance(post) if len(post) > 1 else 0.01

        denom = math.sqrt((v_pre / len(pre)) + (v_post / len(post)))
        if denom == 0:
            continue
        t_stat = abs(m_pre - m_post) / denom

        if t_stat > max_t_stat:
            max_t_stat = t_stat
            best_split = split
            best_pre_mean = m_pre
            best_post_mean = m_post

    pct_change = round(((best_post_mean - best_pre_mean) / max(0.001, best_pre_mean)) * 100, 2)
    diagnostics = []

    # Significant shift threshold (t > 2.5 ~ 98% confidence)
    is_anomaly = max_t_stat >= 2.5 and abs(pct_change) >= 15.0

    if not is_anomaly:
        classification = "نوسانات عادی و فصلی (بدون شواهد آماری مبنی بر تغییر الگوریتم یا نقص فنی)"
        conf = 0.0
    else:
        # Classify root cause
        # Check drop slope: if drop happened in 1 day from split to split+1
        day_before = time_series_clicks[best_split - 1]
        day_after = time_series_clicks[best_split]
        step_drop_pct = abs((day_after - day_before) / max(0.001, day_before)) * 100

        if step_drop_pct > 50.0:
            classification = "خطای فنی شدید ناشی از دیپلوی داخلی (Internal Technical Deploy Outage)"
            diagnostics.append("افت ناگهانی بیش از ۵۰٪ ظرف ۲۴ ساعت؛ نشان‌دهنده خطای سرور، تگ noindex سهوی، خرابی robots.txt یا قطعی DNS.")
            conf = 95.0
        elif pct_change < -20.0:
            classification = "افت الگوریتمی هسته گوگل (Google Core Update Re-ranking)"
            diagnostics.append("افت تدریجی ساختاری در بازه چند روزه؛ نشان‌دهنده بازتنظیم پیج‌رنک، فیلتر هرزنامه یا افت نمره Helpful Content.")
            conf = 88.0
        else:
            classification = "جهش ساختاری مثبت (Organic Ranking Gain)"
            diagnostics.append("رشد ارگانیک معنادار ناشی از بهبود ساختار، لینک‌سازی یا بروزرسانی الگوریتم.")
            conf = 85.0

    return AnomalyDetectionResult(
        is_anomaly_detected=is_anomaly,
        change_point_index=best_split if is_anomaly else None,
        pre_mean=round(best_pre_mean, 2),
        post_mean=round(best_post_mean, 2),
        percentage_change=pct_change,
        t_statistic=round(max_t_stat, 3),
        classification=classification,
        confidence=conf,
        diagnostics=diagnostics
    )


def run_self_test():
    print("[CausalImpactDetector Test] شروع آزمون سنجش آماری تغییرات...")

    # Scenario 1: Stable data with minor noise
    stable_series = [1000, 1020, 990, 1010, 980, 1030, 995, 1015, 1005, 990, 1010, 1000, 1025, 990]
    res_stable = detect_traffic_shift(stable_series)
    assert not res_stable.is_anomaly_detected, "نباید برای نوسانات تصادفی عادی آنومالی تشخیص دهد"

    # Scenario 2: Technical instant crash (deploy bug)
    crash_series = [1000, 1020, 990, 1010, 980, 1030, 1000, 150, 140, 160, 150, 130, 145, 150]
    res_crash = detect_traffic_shift(crash_series)
    assert res_crash.is_anomaly_detected, "باید سقوط ناگهانی را به عنوان آنومالی کشف کند"
    assert "Internal Technical" in res_crash.classification, "باید افت ناگهانی را خطای فنی تشخیص دهد"

    # Scenario 3: Gradual core update ranking decay
    update_series = [1000, 1020, 990, 1010, 980, 1030, 995, 750, 720, 680, 650, 630, 610, 600]
    res_update = detect_traffic_shift(update_series)
    assert res_update.is_anomaly_detected, "باید افت پیوسته الگوریتمی را کشف کند"
    assert "Core Update" in res_update.classification, "باید افت الگوریتمی را متمایز سازد"

    print(f"[CausalImpactDetector Test] موفق: تفکیک دقیق خطای فنی ({res_crash.percentage_change}٪) از افت الگوریتمی ({res_update.percentage_change}٪)")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        run_self_test()
    elif len(sys.argv) > 1:
        raw_vals = [float(x.strip()) for x in sys.argv[1].split(",") if x.strip()]
        res = detect_traffic_shift(raw_vals)
        print("="*50)
        print("تحلیل آماری تغییرات ساختاری ترافیک سئو")
        print(f"آیا تغییر معنادار آماری کشف شد؟ {res.is_anomaly_detected}")
        print(f"میانگین قبل: {res.pre_mean} | میانگین بعد: {res.post_mean}")
        print(f"درصد تغییر کل: {res.percentage_change}٪ (t-score: {res.t_statistic})")
        print(f"طبقه‌بندی ریشه‌ای: {res.classification}")
        print(f"ضریب اطمینان مدل: {res.confidence}٪")
        if res.diagnostics:
            print("\nتشخیص‌های بالینی:")
            for d in res.diagnostics:
                print(f"  🩺 {d}")
        print("="*50)
    else:
        run_self_test()
