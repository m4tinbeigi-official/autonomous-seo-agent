#!/usr/bin/env python3
"""
Information Gain & Content Originality Analyzer
Based on Google Information Gain Patent (US20200349156A1) & Helpful Content System.
Evaluates:
  1. Lexical & Semantic Novelty against baseline/competitor texts.
  2. Entity & Empirical Data Density (numbers, statistics, tables, direct measurements).
  3. Fluff / Boilerplate Index (detects corporate intro clichés & generic filler words).
  4. Net Information Gain Score (0-100).
Standard library only (math, re, collections, typing, dataclasses).
"""

from __future__ import annotations

import collections
import math
import re
import sys
from dataclasses import dataclass, field
from typing import Counter, Dict, List, Set, Tuple


PERSIAN_STOPWORDS = {
    "و", "در", "به", "از", "که", "این", "را", "با", "است", "برای", "آن", "یک", "شود", "شده",
    "خود", "تا", "کرد", "بر", "نیز", "اما", "وی", "شد", "های", "ها", "می", "هم", "دارد", "باید"
}

PERSIAN_FLUFF_PATTERNS = [
    r"امروزه\s+با\s+پیشرفت",
    r"همان[‌\s]?طور\s+که\s+می[‌\s]?دانید",
    r"در\s+دنیای\s+امروز",
    r"یکی\s+از\s+مهم[‌\s]?ترین",
    r"لازم\s+به\s+ذکر\s+است",
    r"شایان\s+ذکر\s+است",
    r"بر\s+کسی\s+پوشیده\s+نیست",
    r"در\s+این\s+مقاله\s+قصد\s+داریم",
    r"با\s+ما\s+همراه\s+باشید"
]


@dataclass
class InformationGainReport:
    total_words: int
    unique_words: int
    lexical_diversity_ttr: float  # Type-Token Ratio
    shannon_entropy: float
    data_points_count: int  # Numbers, percentages, metrics
    fluff_phrases_count: int
    novelty_vs_baseline_ratio: float  # 0.0 to 1.0
    information_gain_score: int  # 0 to 100
    verdict: str
    highlights: List[str] = field(default_factory=list)


def extract_clean_tokens(text: str) -> List[str]:
    # Normalize Persian letters
    norm = text.replace("ي", "ی").replace("ك", "ک").replace("—", " ").replace("\u200c", "")
    words = re.findall(r'[\u0600-\u06FFa-zA-Z0-9]+', norm.lower())
    return [w for w in words if len(w) > 1 and w not in PERSIAN_STOPWORDS]


def calculate_entropy(tokens: List[str]) -> float:
    if not tokens:
        return 0.0
    counts = collections.Counter(tokens)
    total = len(tokens)
    return round(-sum((c / total) * math.log2(c / total) for c in counts.values()), 3)


def analyze_information_gain(
    candidate_text: str,
    baseline_corpus: List[str] | None = None
) -> InformationGainReport:
    tokens = extract_clean_tokens(candidate_text)
    total_tokens = len(tokens)
    if total_tokens == 0:
        return InformationGainReport(0, 0, 0.0, 0.0, 0, 0, 0.0, 0, "محتوای خالی یا نامعتبر")

    unique_tokens = set(tokens)
    ttr = round(len(unique_tokens) / total_tokens, 4)
    entropy = calculate_entropy(tokens)

    # Detect empirical data points (numbers, %, metrics)
    numbers = re.findall(r'\b\d+(?:[\.,]\d+)?%?\b', candidate_text)
    data_points_count = len(numbers)

    # Detect fluff phrases
    fluff_count = 0
    for pat in PERSIAN_FLUFF_PATTERNS:
        fluff_count += len(re.findall(pat, candidate_text))

    # Novelty comparison
    if baseline_corpus:
        baseline_tokens: Set[str] = set()
        for doc in baseline_corpus:
            baseline_tokens.update(extract_clean_tokens(doc))
        novel_tokens = unique_tokens - baseline_tokens
        novelty_ratio = round(len(novel_tokens) / len(unique_tokens), 4) if unique_tokens else 0.0
    else:
        # Standalone assessment
        novelty_ratio = 1.0

    # Calculate Information Gain Score (0-100)
    score = 0
    score += min(25, int(ttr * 50))
    score += min(25, data_points_count * 3)
    
    if baseline_corpus:
        score += int(novelty_ratio * 35)
    else:
        # In standalone mode, award novelty proportionally to lexical entropy and absence of clichés
        novelty_base = max(0, 30 - (fluff_count * 10))
        score += novelty_base

    score += min(15, int((entropy / 8.0) * 15))

    # Fluff penalty: -8 per cliché
    score -= (fluff_count * 8)
    score = max(0, min(100, score))

    highlights = []
    if fluff_count > 0:
        highlights.append(f"تعداد {fluff_count} عبارت کلیشه‌ای و حاشیه‌پردازی (Fluff) کشف شد که باید با گزاره‌های مستقیم جایگزین شوند.")
    if data_points_count >= 5:
        highlights.append(f"چگالی اطلاعات تجربی و عددی عالی است ({data_points_count} فاکتور عددی/آماری).")
    elif data_points_count == 0:
        highlights.append("فقدان هرگونه داده عددی، آماری، جدول یا شاخص تجربی در متن؛ خطر ارزیابی به عنوان محتوای کلیشه‌ای.")

    if novelty_ratio < 0.20 and baseline_corpus:
        highlights.append(f"ضریب نوآوری اطلاعاتی بسیار پایین است ({round(novelty_ratio * 100, 1)}٪ نسبت به رقبا)؛ بازنویسی کپی بدون ارزش افزوده.")

    if score >= 75:
        verdict = "عالی (High Information Gain): محتوا دارای زاویه دید متمایز، فکت‌های عددی و ارزش نوآورانه برای رتبه‌گیری پایدار است."
    elif score >= 50:
        verdict = "متوسط: محتوا قابل قبول است اما نیاز به تقویت جدول‌های مقایسه‌ای و داده‌های دست اول دارد."
    else:
        verdict = "ضعیف (Regurgitated Content): متن حاوی تعارفات کلی، تکرار داده‌های موجود و ریسک ضربه از آپدیت‌های Helpful Content."

    return InformationGainReport(
        total_words=total_tokens,
        unique_words=len(unique_tokens),
        lexical_diversity_ttr=ttr,
        shannon_entropy=entropy,
        data_points_count=data_points_count,
        fluff_phrases_count=fluff_count,
        novelty_vs_baseline_ratio=novelty_ratio,
        information_gain_score=score,
        verdict=verdict,
        highlights=highlights
    )


def run_self_test():
    print("[InformationGainAnalyzer Test] شروع تست اعتبارسنجی...")
    
    # Text with fluff and zero empirical data
    slop_text = """امروزه با پیشرفت تکنولوژی خرید سرور بسیار مهم است. همانطور که می دانید سرورها کامپیوترهای قوی هستند.
    در این مقاله قصد داریم با ما همراه باشید تا بهترین سرور را معرفی کنیم."""
    
    rep_slop = analyze_information_gain(slop_text)
    assert rep_slop.fluff_phrases_count >= 3, "باید عبارات کلیشه‌ای را شناسایی کند"
    assert rep_slop.information_gain_score < 40, f"متن کلیشه‌ای باید امتیاز پایینی بگیرد (امتیاز: {rep_slop.information_gain_score})"

    # High-value engineering text with numbers, benchmarks, unique entities
    high_gain_text = """آزمون بنچمارک روی سرور ابری با پردازنده AMD EPYC نشان داد تاخیر TTFB از ۳۴۰ میلی‌ثانیه به ۴۲ میلی‌ثانیه کاهش می‌یابد.
    در تست بار با ۱۲۰۰۰ درخواست هم‌زمان، مصرف حافظه رم روی ۴۵۰ مگابایت تثبیت شد و نرخ موفقیت ۹۹.۸٪ ثبت گردید."""
    
    rep_high = analyze_information_gain(high_gain_text)
    assert rep_high.data_points_count >= 5, "باید اعداد و فاکتورهای عددی را بشمارد"
    assert rep_high.information_gain_score >= 65, f"متن غنی باید امتیاز بالایی بگیرد (امتیاز: {rep_high.information_gain_score})"

    print(f"[InformationGainAnalyzer Test] موفق: متن کلیشه‌ای = {rep_slop.information_gain_score} / ۱۰۰، متن غنی = {rep_high.information_gain_score} / ۱۰۰")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        run_self_test()
    elif len(sys.argv) > 1:
        txt = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")
        rep = analyze_information_gain(txt)
        print("="*50)
        print("گزارش سنجش Information Gain و تمایز محتوایی")
        print(f"کل کلمات مفید: {rep.total_words}")
        print(f"تنوع واژگان (TTR): {rep.lexical_diversity_ttr}")
        print(f"آنتروپی شانون معنایی: {rep.shannon_entropy}")
        print(f"تعداد داده‌های عددی و آماری: {rep.data_points_count}")
        print(f"تعداد عبارات کلیشه‌ای زرد: {rep.fluff_phrases_count}")
        print(f"نمره کسب اطلاعات (Information Gain): {rep.information_gain_score} / ۱۰۰")
        print(f"ارزیابی نهایی: {rep.verdict}")
        if rep.highlights:
            print("\nنکات و تحلیل‌های اختصاصی:")
            for h in rep.highlights:
                print(f"  • {h}")
        print("="*50)
    else:
        run_self_test()
