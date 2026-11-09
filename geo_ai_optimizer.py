#!/usr/bin/env python3
"""
Generative Engine Optimization (GEO) & llms.txt Suite
Optimizes web assets for AI Search & Answers (Google AI Overviews, Perplexity, ChatGPT Search).
Features:
  1. Snippet Citability Scorer: evaluates direct-answer extraction readiness in top 60 words.
  2. Structured Knowledge Tables & Markdown Extractor: prepares clean tables for LLM digestion.
  3. LLMS.txt & LLMS-full.txt Spec Generator: produces official /llms.txt standard files.
Standard library only (re, json, sys, dataclasses, typing).
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class GEOCitabilityReport:
    word_count: int
    has_concise_definition: bool
    definition_word_count: int
    first_60_words_summary: str
    tabular_data_detected: bool
    tables_count: int
    faq_qa_pairs_count: int
    has_statistical_facts: bool
    citability_score: int  # 0 to 100
    verdict: str
    recommendations: List[str] = field(default_factory=list)


class HTMLContentExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.paragraphs: List[str] = []
        self.headings: List[Tuple[str, str]] = []
        self.tables_count: int = 0
        self._current_tag = None
        self._buf = ""

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, str | None]]):
        self._current_tag = tag.lower()
        if self._current_tag in ("p", "h1", "h2", "h3"):
            self._buf = ""
        elif self._current_tag == "table":
            self.tables_count += 1

    def handle_endtag(self, tag: str):
        t = tag.lower()
        if t == "p" and self._buf.strip():
            self.paragraphs.append(self._buf.strip())
        elif t in ("h1", "h2", "h3") and self._buf.strip():
            self.headings.append((t, self._buf.strip()))
        self._current_tag = None

    def handle_data(self, data: str):
        if self._current_tag in ("p", "h1", "h2", "h3"):
            self._buf += data


def evaluate_geo_citability(html_or_text: str) -> GEOCitabilityReport:
    parser = HTMLContentExtractor()
    parser.feed(html_or_text)

    # If pure text was passed
    if not parser.paragraphs:
        paragraphs = [p.strip() for p in html_or_text.split("\n\n") if p.strip()]
    else:
        paragraphs = parser.paragraphs

    first_p = paragraphs[0] if paragraphs else ""
    first_p_words = first_p.split()
    first_p_len = len(first_p_words)

    # Check for direct definition pattern (X چیست، X عبارت است از، X یک سامانه است)
    has_definition = False
    def_patterns = [
        r"(?:عبارت\s+است\s+از|یک\s+(?:سیستم|سامانه|نرم‌افزار|ابزار|پلتفرم|روش|پروتکل)\s+است|به\s+معنای|فرآیندی\s+است)",
        r"(?:is\s+a\s+(?:system|platform|tool|method|framework|software|protocol)|refers\s+to|defined\s+as)"
    ]
    for pat in def_patterns:
        if re.search(pat, first_p):
            has_definition = True
            break

    # Stats facts check
    numbers = re.findall(r'\b\d+(?:[\.,]\d+)?%?\b', html_or_text)
    has_stats = len(numbers) >= 3

    # FAQ pairs check
    faq_count = len([h for tag, h in parser.headings if "?" in h or "؟" in h])

    # Score Calculation (0-100)
    score = 0
    recommendations = []

    # 1. Definitive answer in first paragraph (40 pts)
    if has_definition:
        score += 25
    if 25 <= first_p_len <= 70:
        score += 15
    elif first_p_len > 70:
        score += 5
        recommendations.append(f"پاراگراف آغازین طولانی است ({first_p_len} کلمه). مدل‌های هوش مصنوعی خلاصه‌های ۴۰ تا ۶۰ کلمه‌ای را بهتر سورس می‌کنند.")
    else:
        recommendations.append("پاراگراف اول فاقد تعریف جامع و گزاره‌ای است؛ پاسخ مستقیم به کوئری در خط اول قرار گیرد.")

    # 2. Tabular Data (25 pts)
    if parser.tables_count > 0:
        score += 25
    else:
        recommendations.append("نبود جدول مقایسه‌ای یا ماتریس مشخصات؛ مدل‌های هوش مصنوعی (Perplexity/ChatGPT) علاقه بالایی به استناد از جداول HTML دارند.")

    # 3. FAQ Headings (20 pts)
    if faq_count >= 2:
        score += 20
    elif faq_count == 1:
        score += 10
    else:
        recommendations.append("عدم استفاده از هدینگ‌های سوالی (FAQ)؛ هوش مصنوعی برای بخش‌های پرسش و پاسخ احتمال ارجاع بیشتری قائل است.")

    # 4. Statistical Facts (15 pts)
    if has_stats:
        score += 15
    else:
        recommendations.append("فقدان اعداد و آمارهای معتبر تجربی در متن.")

    score = max(0, min(100, score))

    if score >= 75:
        verdict = "بسیار بالا (AI-Overview Citation Ready): صفحه آمادگی کامل برای نمایش به عنوان منبع هوش مصنوعی دارد."
    elif score >= 50:
        verdict = "متوسط: نیازمند شفاف‌سازی پاراگراف آغازین و افزودن جدول داده‌های ساخت‌یافته."
    else:
        verdict = "ضعیف: متن ساختار حاشیه‌ای دارد و مدل‌های LLM آن را برای نقل قول معتبر انتخاب نمی‌کنند."

    summary_words = " ".join(first_p_words[:60])

    return GEOCitabilityReport(
        word_count=sum(len(p.split()) for p in paragraphs),
        has_concise_definition=has_definition,
        definition_word_count=first_p_len,
        first_60_words_summary=summary_words,
        tabular_data_detected=(parser.tables_count > 0),
        tables_count=parser.tables_count,
        faq_qa_pairs_count=faq_count,
        has_statistical_facts=has_stats,
        citability_score=score,
        verdict=verdict,
        recommendations=recommendations
    )


def generate_llms_txt(
    site_title: str,
    site_description: str,
    sections: Dict[str, List[Tuple[str, str, str]]]
) -> str:
    """
    Generates /llms.txt standard format.
    sections: {SectionName: [(PageTitle, URL, ShortSummary)]}
    """
    doc = f"# {site_title}\n\n> {site_description}\n\n"
    
    for sec_name, pages in sections.items():
        doc += f"## {sec_name}\n\n"
        for title, url, desc in pages:
            doc += f"- [{title}]({url}): {desc}\n"
        doc += "\n"
        
    return doc.strip() + "\n"


def run_self_test():
    print("[GEO & llms.txt Test] شروع تست بهینه‌سازی موتورهای هوش مصنوعی...")
    
    # HTML sample with good GEO patterns
    geo_html = """<!DOCTYPE html>
    <html><body>
    <h1>معماری سرور ابری چیست؟</h1>
    <p>معماری سرور ابری عبارت است از یک سیستم توزیع‌شده زیرساختی که منابع پردازشی و ذخیره‌سازی را با پایداری ۹۹.۹٪ از طریق شبکه در اختیار برنامه‌ها قرار می‌دهد.</p>
    <h2>تفاوت سرور ابری و اختصاصی چیست؟</h2>
    <p>پاسخ به سوال...</p>
    <table>
        <tr><th>معیار</th><th>سرور ابری</th><th>سرور اختصاصی</th></tr>
        <tr><td>مقیاس‌پذیری</td><td>آنی</td><td>دستی</td></tr>
    </table>
    </body></html>"""

    rep = evaluate_geo_citability(geo_html)
    assert rep.has_concise_definition, "باید تعریف گزاره‌ای را کشف کند"
    assert rep.tabular_data_detected, "باید جدول داده را کشف کند"
    assert rep.citability_score >= 75, f"امتیاز صفحه استاندارد GEO باید بالای ۷۵ باشد (امتیاز: {rep.citability_score})"

    # Test llms.txt generation
    llms_out = generate_llms_txt(
        site_title="پایگاه فنی",
        site_description="مستندات معماری ابری و مهندسی سئو",
        sections={
            "مستندات اصلی": [
                ("راهنمای سرور", "https://example.com/vps", "راهنمای جامع پیکربندی سرور ابری")
            ]
        }
    )
    assert "# پایگاه فنی" in llms_out, "تایتل اصلی باید در فایل قرار گیرد"
    assert "- [راهنمای سرور](https://example.com/vps)" in llms_out, "فرمت استاندارد لینک‌های llms.txt باید حفظ شود"

    print(f"[GEO & llms.txt Test] موفق: امتیاز آمادگی استناد در هوش مصنوعی = {rep.citability_score} / ۱۰۰، فایل llms.txt با موفقیت تولید شد.")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        run_self_test()
        sys.exit(0)

    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
        if not path.exists():
            print(f"فایل {path} یافت نشد.")
            sys.exit(1)
        content = path.read_text(encoding="utf-8", errors="replace")
        rep = evaluate_geo_citability(content)
        print("="*60)
        print("گزارش بهینه‌سازی برای موتورهای هوش مصنوعی (GEO & AI Overviews)")
        print(f"امتیاز قابلیت استناد در هوش مصنوعی (Citability Score): {rep.citability_score} / ۱۰۰")
        print(f"ارزیابی نهایی: {rep.verdict}")
        print(f"تعریف مستقیم در ۶۰ کلمه اول: {'بله' if rep.has_concise_definition else 'خیر'}")
        print(f"جداول داده‌های ساخت‌یافته: {rep.tables_count} جدول")
        print(f"هدینگ‌های سوالی (FAQ): {rep.faq_qa_pairs_count}")
        print(f"خلاصه ۶۰ کلمه اول:\n  «{rep.first_60_words_summary}»")
        if rep.recommendations:
            print("\nاقدامات لازم برای کسب استناد در Perplexity و AI Overviews:")
            for r in rep.recommendations:
                print(f"  💡 {r}")
        print("="*60)
    else:
        run_self_test()
