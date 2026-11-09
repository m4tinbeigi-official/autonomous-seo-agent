#!/usr/bin/env python3
"""
Hydration Diff Checker & JavaScript Rendering Auditor
Compares Raw Static HTML (First-Wave Crawl) vs Post-Hydration Rendered DOM.
Unmasks:
  1. Content invisibility (large text blocks missing in raw HTML).
  2. Hidden links (internal links only created by client-side JavaScript).
  3. Heading hydration delays (H1/H2 missing in initial source).
  4. Dynamically injected Schema markup risks.
Calculates JS Rendering Dependency Index (0-100%).
Standard library only.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Dict, List, Set, Tuple


class TextAndLinkExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text_tokens: List[str] = []
        self.links: Set[str] = set()
        self.h1_tags: List[str] = []
        self.schemas: List[str] = []
        self._in_script = False
        self._in_style = False
        self._in_h1 = False
        self._in_json_ld = False
        self._buf = ""

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, str | None]]):
        tag_lower = tag.lower()
        attr_dict = {k.lower(): (v or "") for k, v in attrs}
        if tag_lower == "script":
            self._in_script = True
            if attr_dict.get("type", "").lower() == "application/ld+json":
                self._in_json_ld = True
                self._buf = ""
        elif tag_lower == "style":
            self._in_style = True
        elif tag_lower == "h1":
            self._in_h1 = True
            self._buf = ""
        elif tag_lower == "a":
            href = attr_dict.get("href", "")
            if href and not href.startswith("#") and not href.startswith("javascript:"):
                self.links.add(href.strip())

    def handle_endtag(self, tag: str):
        tag_lower = tag.lower()
        if tag_lower == "script":
            self._in_script = False
            if self._in_json_ld:
                self.schemas.append(self._buf.strip())
                self._in_json_ld = False
        elif tag_lower == "style":
            self._in_style = False
        elif tag_lower == "h1":
            self._in_h1 = False
            if self._buf.strip():
                self.h1_tags.append(self._buf.strip())

    def handle_data(self, data: str):
        if self._in_json_ld:
            self._buf += data
            return
        if self._in_script or self._in_style:
            return
        if self._in_h1:
            self._buf += data
        
        words = [w.strip() for w in re.split(r'\s+', data) if len(w.strip()) > 1]
        self.text_tokens.extend(words)


@dataclass
class HydrationDiffReport:
    raw_word_count: int
    rendered_word_count: int
    word_count_diff: int
    js_content_dependency_ratio: float
    raw_links_count: int
    rendered_links_count: int
    hidden_client_only_links: List[str]
    raw_h1_present: bool
    rendered_h1_present: bool
    schema_injected_via_js: bool
    rendering_risk_score: int  # 0 to 100 (higher = riskier for SEO)
    verdict: str
    warnings: List[str] = field(default_factory=list)


def compare_hydration(raw_html: str, rendered_html: str) -> HydrationDiffReport:
    p_raw = TextAndLinkExtractor()
    p_raw.feed(raw_html)

    p_rendered = TextAndLinkExtractor()
    p_rendered.feed(rendered_html)

    raw_words = len(p_raw.text_tokens)
    rend_words = len(p_rendered.text_tokens)
    word_diff = max(0, rend_words - raw_words)

    js_dep_ratio = round((word_diff / rend_words), 4) if rend_words > 0 else 0.0

    client_only_links = sorted(list(p_rendered.links - p_raw.links))
    raw_h1 = len(p_raw.h1_tags) > 0
    rend_h1 = len(p_rendered.h1_tags) > 0

    schema_via_js = (len(p_raw.schemas) == 0 and len(p_rendered.schemas) > 0)

    # Compute risk score (0-100)
    risk_score = 0
    warnings = []

    if js_dep_ratio > 0.40:
        risk_score += int(js_dep_ratio * 40)
        warnings.append(
            f"بیش از {round(js_dep_ratio * 100, 1)}٪ محتوای متنی صفحه وابسته به رندر جاوااسکریپت کلاینت است. در موج اول خزش گوگل، صفحه خالی یا نازک ارزیابی می‌شود."
        )

    if client_only_links:
        risk_score += min(30, len(client_only_links) * 5)
        warnings.append(
            f"{len(client_only_links)} پیوند ناوبری یا داخلی فقط پس از اجرای جاوااسکریپت تولید می‌شوند؛ کشف این صفحات توسط بات‌های بدون JS مسدود است."
        )

    if not raw_h1 and rend_h1:
        risk_score += 20
        warnings.append("هدینگ اصلی H1 در سورس اولیه HTML غایب است و صرفا بعد از آب‌رسانی React/Vue ظاهر می‌شود.")

    if schema_via_js:
        risk_score += 15
        warnings.append("اسکیمای ساختاریافته JSON-LD فقط در رندر نهایی کلاینت تزریق شده و در HTML سرور وجود ندارد.")

    risk_score = min(100, risk_score)

    if risk_score < 15:
        verdict = "عالی (SSR / SSG پایدار): محتوا و پیوندهای کلیدی در سورس اولیه قرار دارند."
    elif risk_score < 45:
        verdict = "متوسط: بخش‌هایی از داده‌ها به هیدریشن وابسته است اما اسکلت صفحه حاضر است."
    else:
        verdict = "بحرانی (CSR شدید): ریسک بسیار بالای تاخیر ایندکس یا نادیده‌گرفته شدن محتوا در WRS گوگل."

    return HydrationDiffReport(
        raw_word_count=raw_words,
        rendered_word_count=rend_words,
        word_count_diff=word_diff,
        js_content_dependency_ratio=js_dep_ratio,
        raw_links_count=len(p_raw.links),
        rendered_links_count=len(p_rendered.links),
        hidden_client_only_links=client_only_links[:10],
        raw_h1_present=raw_h1,
        rendered_h1_present=rend_h1,
        schema_injected_via_js=schema_via_js,
        rendering_risk_score=risk_score,
        verdict=verdict,
        warnings=warnings
    )


def run_self_test():
    print("[HydrationDiffChecker Test] شروع آزمون صحت سنجش آب‌رسانی...")
    raw = """<html><head><title>App</title></head><body><div id="root"></div></body></html>"""
    rendered = """<html><head><title>App</title><script type="application/ld+json">{"@context":"https://schema.org"}</script></head>
    <body><div id="root"><h1>عنوان اصلی صفحه سرور</h1><p>توضیحات طولانی و تکمیلی درباره محصولات که در کلاینت رندر شده است...</p>
    <a href="/internal-link-1">لینک داخلی</a><a href="/internal-link-2">لینک دوم</a></div></body></html>"""

    rep = compare_hydration(raw, rendered)
    assert rep.rendering_risk_score > 60, f"صفحه خالی در سورس اولیه باید ریسک بالای ۶۰ داشته باشد (مقدار: {rep.rendering_risk_score})"
    assert rep.schema_injected_via_js, "باید تشخیص دهد اسکیما در کلاینت تزریق شده است"
    assert len(rep.hidden_client_only_links) == 2, "باید ۲ لینک کلاینتی کشف کند"
    assert not rep.raw_h1_present and rep.rendered_h1_present, "باید غیبت H1 در سورس اولیه را کشف کند"
    print(f"[HydrationDiffChecker Test] موفق: شاخص ریسک محاسبه‌شده = {rep.rendering_risk_score} / ۱۰۰ ({rep.verdict})")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        run_self_test()
    elif len(sys.argv) >= 3:
        f1 = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")
        f2 = Path(sys.argv[2]).read_text(encoding="utf-8", errors="replace")
        rep = compare_hydration(f1, f2)
        print("="*50)
        print("گزارش تفاوت هیدریشن و تحلیل WRS گوگل")
        print(f"تعداد کلمات در سورس اولیه (Raw HTML): {rep.raw_word_count}")
        print(f"تعداد کلمات پس از رندر کلاینت (Rendered DOM): {rep.rendered_word_count}")
        print(f"نسبت وابستگی محتوا به جاوااسکریپت: {round(rep.js_content_dependency_ratio*100, 1)}٪")
        print(f"نمره ریسک رندرینگ سئو: {rep.rendering_risk_score} / ۱۰۰")
        print(f"وضعیت کلی: {rep.verdict}")
        if rep.warnings:
            print("\nهشدارها:")
            for w in rep.warnings:
                print(f"  ⚠️  {w}")
        if rep.hidden_client_only_links:
            print("\nلینک‌های مخفی در سورس سرور:")
            for l in rep.hidden_client_only_links:
                print(f"  🔗 {l}")
        print("="*50)
    else:
        run_self_test()
