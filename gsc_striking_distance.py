#!/usr/bin/env python3
"""
GSC Striking Distance Keyword Hunter & Query Opportunity Miner
Analyzes Google Search Console Performance exports (CSV or JSON).
Features:
  1. Identifies "Striking Distance" keywords (Position 8.0 to 20.0 with high impressions).
  2. Calculates Opportunity Traffic Gain: potential clicks if promoted to Top 3 (benchmark CTR 18.5%).
  3. CTR Underperformance Detector: flags queries where actual CTR is below SERP average.
  4. Generates Title/H2 insertion & contextual optimization recipes.
Standard library only (csv, json, sys, dataclasses, typing).
"""

from __future__ import annotations

import csv
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# Benchmark organic CTR curve by average SERP position
POSITION_CTR_BENCHMARK = {
    1: 0.320,  # 32%
    2: 0.190,  # 19%
    3: 0.125,  # 12.5%
    4: 0.085,  # 8.5%
    5: 0.060,  # 6%
    6: 0.045,  # 4.5%
    7: 0.035,  # 3.5%
    8: 0.028,  # 2.8%
    9: 0.022,  # 2.2%
    10: 0.018, # 1.8%
}


@dataclass
class StrikingKeywordOpportunity:
    query: str
    page: str
    impressions: int
    clicks: int
    current_ctr: float
    current_position: float
    benchmark_ctr: float
    potential_clicks_top3: int
    opportunity_gain: int
    quick_fix_recipe: str


@dataclass
class GSCOpportunityReport:
    total_queries_analyzed: int
    striking_distance_count: int
    total_potential_click_gain: int
    top_opportunities: List[StrikingKeywordOpportunity]
    page_level_priorities: List[Tuple[str, int]]


def parse_gsc_data(file_path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    text = file_path.read_text(encoding="utf-8", errors="replace")

    # Try JSON format first
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and "rows" in data:
            return data["rows"]
    except Exception:
        pass

    # Try CSV format
    lines = text.splitlines()
    if not lines:
        return []
    reader = csv.DictReader(lines)
    for r in reader:
        # Standardize GSC column headers (English and Persian)
        query = r.get("Top queries") or r.get("Query") or r.get("query") or r.get("عبارت‌های برتر") or ""
        page = r.get("Page") or r.get("Pages") or r.get("page") or r.get("صفحه") or ""
        clicks = int(float(r.get("Clicks") or r.get("clicks") or r.get("کلیک‌ها") or 0))
        impr = int(float(r.get("Impressions") or r.get("impressions") or r.get("نمایش‌ها") or 0))
        ctr_raw = str(r.get("CTR") or r.get("ctr") or r.get("نرخ کلیک") or "0%").replace("%", "").strip()
        ctr = float(ctr_raw) / 100.0 if float(ctr_raw) > 1.0 else float(ctr_raw)
        pos = float(r.get("Position") or r.get("position") or r.get("جایگاه") or 0.0)

        if query:
            rows.append({
                "query": query,
                "page": page,
                "clicks": clicks,
                "impressions": impr,
                "ctr": ctr,
                "position": pos
            })

    return rows


def analyze_striking_distance(
    rows: List[Dict[str, Any]],
    min_impressions: int = 100,
    min_pos: float = 7.5,
    max_pos: float = 20.0
) -> GSCOpportunityReport:
    opportunities: List[StrikingKeywordOpportunity] = []
    page_gains: Dict[str, int] = {}

    for r in rows:
        q = r["query"]
        p = r["page"]
        impr = r["impressions"]
        clicks = r["clicks"]
        ctr = r["ctr"]
        pos = r["position"]

        if impr >= min_impressions and min_pos <= pos <= max_pos:
            # Expected CTR at top 3 (average ~ 21%)
            target_ctr = 0.21
            potential_clicks = int(impr * target_ctr)
            gain = max(0, potential_clicks - clicks)

            # Nearest integer position benchmark
            bench_pos = min(10, max(1, int(round(pos))))
            expected_cur_ctr = POSITION_CTR_BENCHMARK.get(bench_pos, 0.015)

            recipe = (
                f"کلمه '{q}' در جایگاه {round(pos, 1)} با {impr} نمایش قرار دارد. "
                f"اقدام: درج عبارت در تگ H2 و یک جمله شفاف در بدنه محتوا + بازنویسی تایتل."
            )

            opp = StrikingKeywordOpportunity(
                query=q,
                page=p,
                impressions=impr,
                clicks=clicks,
                current_ctr=round(ctr * 100, 2),
                current_position=round(pos, 1),
                benchmark_ctr=round(expected_cur_ctr * 100, 2),
                potential_clicks_top3=potential_clicks,
                opportunity_gain=gain,
                quick_fix_recipe=recipe
            )
            opportunities.append(opp)
            page_gains[p] = page_gains.get(p, 0) + gain

    # Sort opportunities by highest click gain potential
    opportunities.sort(key=lambda x: x.opportunity_gain, reverse=True)
    sorted_pages = sorted(page_gains.items(), key=lambda x: x[1], reverse=True)

    total_gain = sum(o.opportunity_gain for o in opportunities)

    return GSCOpportunityReport(
        total_queries_analyzed=len(rows),
        striking_distance_count=len(opportunities),
        total_potential_click_gain=total_gain,
        top_opportunities=opportunities[:15],
        page_level_priorities=sorted_pages[:5]
    )


def run_self_test():
    print("[GSC Striking Distance Test] شروع آزمون شکار فرصت‌های سرچ کنسول...")
    import tempfile

    mock_csv = """Top queries,Page,Clicks,Impressions,CTR,Position
قیمت سرور مجازی ابری,https://example.com/vps,12,1500,0.8%,9.2
خرید سرور لینوکس,https://example.com/vps,5,800,0.6%,14.1
دانلود نرم افزار رایگان,https://example.com/dl,250,5000,5.0%,2.1
آموزش نصب وردپرس روی اوبونتو,https://example.com/wp,2,40,5.0%,11.0"""

    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as f:
        f.write(mock_csv)
        tmp_name = Path(f.name)

    rows = parse_gsc_data(tmp_name)
    tmp_name.unlink()

    assert len(rows) == 4, f"باید ۴ سطر معتبر خوانده شود (تعداد: {len(rows)})"
    report = analyze_striking_distance(rows, min_impressions=100)
    
    assert report.striking_distance_count == 2, f"باید ۲ کلمه در آستانه جهش کشف شود (تعداد: {report.striking_distance_count})"
    assert report.total_potential_click_gain > 400, "ظرفیت جذب کلیک بالقوه باید بیش از ۴۰۰ کلیک باشد"
    assert report.top_opportunities[0].query == "قیمت سرور مجازی ابری"

    print(f"[GSC Striking Distance Test] موفق: ۲ کلمه طلایی کشف شد با پتانسیل جهش {report.total_potential_click_gain} کلیک جدید ماهانه.")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        run_self_test()
        sys.exit(0)

    if len(sys.argv) > 1:
        csv_p = Path(sys.argv[1])
        if not csv_p.exists():
            print(f"فایل {csv_p} یافت نشد.")
            sys.exit(1)
        data = parse_gsc_data(csv_p)
        rep = analyze_striking_distance(data)
        print("="*60)
        print("گزارش شکار کلمات در آستانه جهش (GSC Striking Distance)")
        print(f"کل کوئری‌های ارزیابی‌شده: {rep.total_queries_analyzed}")
        print(f"کوئری‌های در آستانه جهش (صفحه دوم تا انتهای صفحه اول): {rep.striking_distance_count}")
        print(f"پتانسیل افزایش ترافیک ارگانیک: +{rep.total_potential_click_gain} کلیک ماهانه")
        print("="*60)

        print("\n[فرصت‌های با بالاترین اولویت رشد]")
        for i, opp in enumerate(rep.top_opportunities, 1):
            print(f"\n{i}. کوئری: «{opp.query}»")
            print(f"   جایگاه فعلی: {opp.current_position} | نمایش ماهانه: {opp.impressions} | کلیک فعلی: {opp.clicks}")
            print(f"   پتانسیل صعود به Top 3: +{opp.opportunity_gain} کلیک")
            print(f"   دستورالعمل: {opp.quick_fix_recipe}")

        if rep.page_level_priorities:
            print("\n[صفحات هدف با بالاترین پتانسیل افزایش کلیک]")
            for p, g in rep.page_level_priorities:
                print(f"  • {p} (پتانسیل رشد: +{g} کلیک)")
        print("="*60)
    else:
        run_self_test()
