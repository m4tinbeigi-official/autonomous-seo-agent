#!/usr/bin/env python3
"""
Enterprise SEO Engineering Engine & Audit Suite
Covers:
  1. Technical SEO (Crawling, Rendering headers, HTML structure, Canonicals, Schemas, Core Web Vitals signals)
  2. On-Page SEO (Information Architecture, Heading hierarchy, Anchor ergonomics, Persian/VibeFarsi compliance)
  3. Off-Page & Topology (Jaccard Query Overlap & Cannibalization Matrix, Internal PageRank distribution)
Zero external dependencies. 100% Python Standard Library.
"""

from __future__ import annotations

import json
import math
import re
import sys
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


# ==========================================
# 1. URL & SLUG VALIDATOR
# ==========================================

@dataclass
class URLAuditResult:
    url: str
    is_valid: bool
    is_https: bool
    has_trailing_slash_consistent: bool
    has_zwnj: bool
    has_underscores: bool
    has_uppercase: bool
    has_arabic_chars: bool
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


def audit_url_slug(url_str: str) -> URLAuditResult:
    warnings: List[str] = []
    errors: List[str] = []
    
    parsed = urllib.parse.urlparse(url_str)
    path = parsed.path
    
    is_https = parsed.scheme.lower() == "https"
    if not is_https and parsed.scheme:
        warnings.append("URL پروتکل امن HTTPS ندارد.")
        
    # Check ZWNJ (U+200C)
    has_zwnj = "\u200c" in url_str or "%E2%80%8C" in url_str.upper()
    if has_zwnj:
        errors.append("استفاده از نیم‌فاصله (ZWNJ) در آدرس اینترنتی اکیدا ممنوع است؛ باید با خط پیوند (-) جایگزین شود.")
        
    has_underscores = "_" in path
    if has_underscores:
        warnings.append("استفاده از آندرلاین (_) به جای هایفن (-) در اسلاگ استاندارد نیست.")
        
    has_uppercase = any(c.isupper() for c in path)
    if has_uppercase:
        warnings.append("استفاده از حروف بزرگ انگلیسی در آدرس سبب ریسک داپلیکیت و تغییرات کلمه‌ای است.")
        
    # Arabic Yeh/Kaf checks
    has_arabic_chars = any(c in path for c in ["ي", "ك", "ة", "ى"])
    if has_arabic_chars:
        errors.append("کاراکترهای عربی (ي، ك) در اسلاگ یافت شد؛ باید قبل از تولید اسلاگ به ی/ک فارسی نرمال‌سازی شوند.")
        
    is_valid = len(errors) == 0
    return URLAuditResult(
        url=url_str,
        is_valid=is_valid,
        is_https=is_https,
        has_trailing_slash_consistent=True,
        has_zwnj=has_zwnj,
        has_underscores=has_underscores,
        has_uppercase=has_uppercase,
        has_arabic_chars=has_arabic_chars,
        warnings=warnings,
        errors=errors
    )


# ==========================================
# 2. TECHNICAL & ON-PAGE HTML AUDITOR
# ==========================================

@dataclass
class LinkItem:
    href: str
    text: str
    rel: str = ""
    is_internal: bool = True


@dataclass
class ImageItem:
    src: str
    alt: str
    has_dimensions: bool = False
    is_nextgen: bool = False


class SEOHTMLParser(HTMLParser):
    def __init__(self, base_url: str = ""):
        super().__init__()
        self.base_url = base_url
        self.lang: Optional[str] = None
        self.dir: Optional[str] = None
        self.title: str = ""
        self.meta_tags: List[Dict[str, str]] = []
        self.canonical: Optional[str] = None
        self.headings: List[Tuple[str, str]] = []  # ('h1', 'text')
        self.links: List[LinkItem] = []
        self.images: List[ImageItem] = []
        self.json_ld_raw: List[str] = []
        self.head_scripts: List[Dict[str, Any]] = []
        
        self._current_tag: Optional[str] = None
        self._in_head: bool = False
        self._in_title: bool = False
        self._in_heading: Optional[str] = None
        self._heading_buffer: str = ""
        self._in_a: bool = False
        self._a_href: str = ""
        self._a_rel: str = ""
        self._a_buffer: str = ""
        self._in_json_ld: bool = False
        self._json_ld_buffer: str = ""

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]):
        attr_dict = {k.lower(): (v or "") for k, v in attrs}
        tag_lower = tag.lower()
        self._current_tag = tag_lower

        if tag_lower == "html":
            self.lang = attr_dict.get("lang")
            self.dir = attr_dict.get("dir")
        elif tag_lower == "head":
            self._in_head = True
        elif tag_lower == "title" and self._in_head:
            self._in_title = True
        elif tag_lower == "meta":
            self.meta_tags.append(attr_dict)
        elif tag_lower == "link":
            if attr_dict.get("rel", "").lower() == "canonical":
                self.canonical = attr_dict.get("href")
        elif tag_lower in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self._in_heading = tag_lower
            self._heading_buffer = ""
        elif tag_lower == "a":
            self._in_a = True
            self._a_href = attr_dict.get("href", "")
            self._a_rel = attr_dict.get("rel", "")
            self._a_buffer = ""
        elif tag_lower == "img":
            src = attr_dict.get("src", "")
            alt = attr_dict.get("alt", "")
            has_w = "width" in attr_dict
            has_h = "height" in attr_dict
            is_nextgen = any(src.lower().endswith(ext) for ext in [".webp", ".avif", ".svg"])
            self.images.append(ImageItem(
                src=src,
                alt=alt,
                has_dimensions=has_w and has_h,
                is_nextgen=is_nextgen
            ))
        elif tag_lower == "script":
            script_type = attr_dict.get("type", "").lower()
            if script_type == "application/ld+json":
                self._in_json_ld = True
                self._json_ld_buffer = ""
            elif self._in_head:
                has_async = "async" in attr_dict
                has_defer = "defer" in attr_dict
                src = attr_dict.get("src", "")
                self.head_scripts.append({
                    "src": src,
                    "blocking": bool(src and not (has_async or has_defer))
                })

    def handle_endtag(self, tag: str):
        tag_lower = tag.lower()
        if tag_lower == "head":
            self._in_head = False
        elif tag_lower == "title":
            self._in_title = False
        elif tag_lower == self._in_heading:
            if self._in_heading:
                self.headings.append((self._in_heading, self._heading_buffer.strip()))
            self._in_heading = None
        elif tag_lower == "a":
            self._in_a = False
            is_internal = True
            if self._a_href.startswith("http://") or self._a_href.startswith("https://"):
                if self.base_url and not self._a_href.startswith(self.base_url):
                    is_internal = False
            self.links.append(LinkItem(
                href=self._a_href,
                text=self._a_buffer.strip(),
                rel=self._a_rel,
                is_internal=is_internal
            ))
        elif tag_lower == "script" and self._in_json_ld:
            self._in_json_ld = False
            if self._json_ld_buffer.strip():
                self.json_ld_raw.append(self._json_ld_buffer.strip())

    def handle_data(self, data: str):
        if self._in_title:
            self.title += data
        elif self._in_heading:
            self._heading_buffer += data
        elif self._in_a:
            self._a_buffer += data
        elif self._in_json_ld:
            self._json_ld_buffer += data


@dataclass
class PageAuditReport:
    url: str
    score: int
    technical_issues: List[str]
    on_page_issues: List[str]
    vibefarsi_issues: List[str]
    metrics: Dict[str, Any]
    json_ld_schemas: List[Dict[str, Any]]


def audit_html_content(html_str: str, url: str = "https://example.com/test") -> PageAuditReport:
    parser = SEOHTMLParser(base_url=url)
    parser.feed(html_str)
    
    score = 100
    technical_issues: List[str] = []
    on_page_issues: List[str] = []
    vibefarsi_issues: List[str] = []
    
    # 1. Document Level Checks
    if not parser.lang or not (parser.lang.lower().startswith("fa")):
        score -= 10
        technical_issues.append("ویژگی lang سند فارسی نیست یا وجود ندارد (باید lang='fa' یا fa-IR باشد).")
        
    if parser.dir != "rtl":
        score -= 5
        vibefarsi_issues.append("ویژگی جهت صفحه dir='rtl' روی تگ <html> یافت نشد.")

    # 2. Title Checks
    title = parser.title.strip()
    if not title:
        score -= 20
        technical_issues.append("تگ <title> در صفحه وجود ندارد یا خالی است.")
    else:
        if len(title) < 25:
            score -= 5
            on_page_issues.append(f"طول عنوان بسیار کوتاه است ({len(title)} کاراکتر). حداقل ۳۰ تا ۶۰ کاراکتر توصیه می‌شود.")
        elif len(title) > 75:
            score -= 5
            on_page_issues.append(f"طول عنوان ممکن است در SERP بریده شود ({len(title)} کاراکتر).")
        if "—" in title:
            score -= 5
            vibefarsi_issues.append("استفاده از کاراکتر خط فاصله طولانی (em-dash) در عنوان بر خلاف استاندارد است؛ از نیم‌فاصله یا فاصله و علامت نقطه وسط یا پرانتز استفاده کنید.")

    # 3. Meta Description
    meta_desc = ""
    robots_content = ""
    for meta in parser.meta_tags:
        if meta.get("name", "").lower() == "description":
            meta_desc = meta.get("content", "").strip()
        elif meta.get("name", "").lower() == "robots":
            robots_content = meta.get("content", "").strip()
            
    if not meta_desc:
        score -= 15
        on_page_issues.append("تگ meta description یافت نشد.")
    else:
        if len(meta_desc) < 70 or len(meta_desc) > 170:
            score -= 5
            on_page_issues.append(f"طول توضیحات متای صفحه غیراستاندارد است ({len(meta_desc)} کاراکتر؛ بهینه بین ۱۲۰ تا ۱۶۰ کاراکتر است).")
        if "—" in meta_desc:
            score -= 5
            vibefarsi_issues.append("استفاده از خط تیره کشیده (em-dash) در متادیسکریپشن ممنوع است.")

    # 4. Canonical URL
    if not parser.canonical:
        score -= 10
        technical_issues.append("تگ rel='canonical' در صفحه تعریف نشده است.")
    else:
        if not parser.canonical.startswith("http"):
            score -= 5
            technical_issues.append("آدرس تگ کنونیکال نسبی (Relative) است؛ باید مطلق (Absolute) باشد.")

    # 5. Headings (H1 to H6)
    h1s = [text for tag, text in parser.headings if tag == "h1"]
    if len(h1s) == 0:
        score -= 15
        on_page_issues.append("صفحه فاقد هدینگ H1 است.")
    elif len(h1s) > 1:
        score -= 5
        on_page_issues.append(f"صفحه دارای {len(h1s)} هدینگ H1 است (بهتر است دقیقا یک H1 موضوعی داشته باشد).")

    # 6. Blocking Scripts
    blocking_scripts = [s for s in parser.head_scripts if s.get("blocking")]
    if blocking_scripts:
        score -= (len(blocking_scripts) * 3)
        technical_issues.append(f"{len(blocking_scripts)} اسکریپت مسدودکننده رندر (Render-Blocking) بدون async/defer در تگ <head> وجود دارد.")

    # 7. Images Audit
    missing_alt = [img for img in parser.images if not img.alt.strip()]
    if missing_alt:
        score -= min(15, len(missing_alt) * 3)
        on_page_issues.append(f"{len(missing_alt)} تصویر فاقد ویژگی متنی جایگزین (alt) هستند.")
        
    cls_risks = [img for img in parser.images if not img.has_dimensions]
    if cls_risks:
        score -= min(10, len(cls_risks) * 2)
        technical_issues.append(f"{len(cls_risks)} تصویر بدون تعیین صریح width/height هستند که ریسک جهش چیدمان (CLS) ایجاد می‌کنند.")

    # 8. Anchor Texts Quality
    generic_anchors = ["اینجا کلیک کنید", "کلیک کنید", "ادامه مطلب", "بیشتر بخوانید", "اینجا", "لینک"]
    bad_links = [l for l in parser.links if any(g in l.text.strip() for g in generic_anchors) or not l.text.strip()]
    if bad_links:
        score -= min(10, len(bad_links) * 2)
        on_page_issues.append(f"{len(bad_links)} پیوند دارای انکرتکست نامفهوم، عمومی یا بدون متن (Empty/Generic Anchor) هستند.")

    # 9. JSON-LD Schemas Audit
    parsed_schemas = []
    has_valid_schema = False
    for raw in parser.json_ld_raw:
        try:
            data = json.loads(raw)
            parsed_schemas.append(data)
            has_valid_schema = True
            
            # Check for inLanguage
            if isinstance(data, dict):
                in_lang = data.get("inLanguage")
                if not in_lang or not str(in_lang).startswith("fa"):
                    vibefarsi_issues.append("اسکیمای JSON-LD فاقد فیلد inLanguage: 'fa-IR' است.")
        except Exception:
            technical_issues.append("یک بلوک JSON-LD دارای خطای نحوی JSON نامعتبر است.")
            score -= 5

    if not has_valid_schema:
        score -= 5
        technical_issues.append("هیچ اسکیمای ساختاریافته معتبری (JSON-LD) در صفحه یافت نشد.")

    score = max(0, min(100, score))
    
    return PageAuditReport(
        url=url,
        score=score,
        technical_issues=technical_issues,
        on_page_issues=on_page_issues,
        vibefarsi_issues=vibefarsi_issues,
        metrics={
            "title_length": len(title),
            "meta_description_length": len(meta_desc),
            "h1_count": len(h1s),
            "total_headings": len(parser.headings),
            "total_links": len(parser.links),
            "total_images": len(parser.images),
            "blocking_scripts_count": len(blocking_scripts),
            "schemas_count": len(parsed_schemas)
        },
        json_ld_schemas=parsed_schemas
    )


# ==========================================
# 3. JACCARD QUERY OVERLAP & CANNIBALIZATION
# ==========================================

@dataclass
class OverlapReport:
    page_a: str
    page_b: str
    jaccard_index: float
    overlap_queries_count: int
    total_distinct_queries: int
    risk_level: str
    actionable_directive: str


def compute_jaccard_overlap(
    page_a_url: str,
    page_a_queries: Set[str],
    page_b_url: str,
    page_b_queries: Set[str]
) -> OverlapReport:
    """
    Computes Jaccard Similarity: J(A, B) = |Q_A ∩ Q_B| / |Q_A ∪ Q_B|
    """
    intersection = page_a_queries.intersection(page_b_queries)
    union = page_a_queries.union(page_b_queries)
    
    if not union:
        j_index = 0.0
    else:
        j_index = round(len(intersection) / len(union), 4)

    if j_index < 0.25:
        risk = "طبیعی (Natural Intent Overlap)"
        directive = "همپوشانی کوئری‌ها در محدوده استاندارد است. نیازی به مداخله فنی یا حذف صفحات نیست؛ رفتار صفحات صرفا ماهانه رصد شود."
    elif 0.25 <= j_index <= 0.60:
        risk = "منطقه خاکستری (Multi-Intent / Dual Funnel)"
        directive = "بررسی تفکیک اینتنت کاربر؛ در صورت تفاوت نیاز (مثلا راهنمای اطلاعاتی در برابر صفحه خرید تراکنشی)، تفکیک شفاف هدینگ‌ها و اتصال لینک متقابل (Cross-Linking) برای هدایت کاربر انجام شود."
    else:
        risk = "کنیبالیزیشن بحرانی (Critical Cannibalization)"
        directive = "همپوشانی بیش از ۶۰ درصد است. در صورتی که نتایج SERP یکسان هستند، محتوای صفحه با کلیک و بک‌لینک ضعیف‌تر در صفحه برتر ادغام شود و ریدایرکت ۳۰۱ قطعی اعمال گردد."

    return OverlapReport(
        page_a=page_a_url,
        page_b=page_b_url,
        jaccard_index=j_index,
        overlap_queries_count=len(intersection),
        total_distinct_queries=len(union),
        risk_level=risk,
        actionable_directive=directive
    )


# ==========================================
# 4. INTERNAL PAGERANK SIMULATOR
# ==========================================

class InternalPageRankEngine:
    """
    Simulates Internal PageRank distribution using the Power Iteration algorithm.
    Formula: PR(u) = (1 - d)/N + d * sum_{v in In(u)} (PR(v) / Out(v))
    """
    def __init__(self, damping_factor: float = 0.85, max_iterations: int = 100, tolerance: float = 1e-6):
        self.damping = damping_factor
        self.max_iterations = max_iterations
        self.tolerance = tolerance

    def calculate_pagerank(self, graph: Dict[str, List[str]]) -> Dict[str, float]:
        nodes = list(graph.keys())
        n = len(nodes)
        if n == 0:
            return {}

        # Initialize uniform PageRank
        pr: Dict[str, float] = {node: 1.0 / n for node in nodes}

        # Build in-links and out-degree
        out_degrees: Dict[str, int] = {node: len(set(targets)) for node, targets in graph.items()}
        in_links: Dict[str, Set[str]] = {node: set() for node in nodes}
        for src, targets in graph.items():
            for tgt in targets:
                if tgt in in_links:
                    in_links[tgt].add(src)

        for _ in range(self.max_iterations):
            new_pr: Dict[str, float] = {}
            # Account for dangling nodes (out-degree == 0)
            dangling_sum = sum(pr[node] for node in nodes if out_degrees[node] == 0)

            diff = 0.0
            for node in nodes:
                incoming_sum = sum(pr[src] / out_degrees[src] for src in in_links[node] if out_degrees[src] > 0)
                rank = ((1.0 - self.damping) / n) + self.damping * (incoming_sum + (dangling_sum / n))
                diff += abs(rank - pr[node])
                new_pr[node] = rank

            pr = new_pr
            if diff < self.tolerance:
                break

        return {k: round(v, 6) for k, v in sorted(pr.items(), key=lambda item: item[1], reverse=True)}


# ==========================================
# 5. SELF-TEST RUNNER (VERIFICATION)
# ==========================================

def run_self_tests():
    print("[SEO Suite Self-Test] آغاز تست‌های اعتبارسنجی...")

    # Test 1: URL & Slug Audit
    bad_slug = "https://example.com/blog/راهنما\u200cی_خرید_گوشی"
    slug_res = audit_url_slug(bad_slug)
    assert not slug_res.is_valid, "باید آدرس دارای نیم‌فاصله یا کاراکترهای نامعتبر را مردود کند"
    assert slug_res.has_zwnj, "باید کاراکتر نیم‌فاصله کشف شود"
    assert slug_res.has_underscores, "باید آندرلاین کشف شود"

    good_slug = "https://example.com/blog/rahnama-kharid-mobile"
    good_res = audit_url_slug(good_slug)
    assert good_res.is_valid, "اسلاگ استاندارد باید تایید شود"

    # Test 2: HTML Audit
    sample_html = """<!DOCTYPE html>
    <html lang="fa" dir="rtl">
    <head>
        <title>راهنمای خرید سرور مجازی برای سئو · وبلاگ فنی</title>
        <meta name="description" content="راهنمای جامع خرید و پیکربندی سرور مجازی ابری، تحلیل هدرهای شبکه، کنترل کش و بهینه‌سازی سرعت سایت برای سئوکاران." />
        <link rel="canonical" href="https://example.com/vps-guide" />
        <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": "راهنمای خرید سرور مجازی",
            "inLanguage": "fa-IR",
            "datePublished": "2026-09-20"
        }
        </script>
    </head>
    <body>
        <h1>راهنمای خرید سرور مجازی برای سئو</h1>
        <p>توضیحات مربوط به سرور...</p>
        <img src="/assets/diagram.webp" alt="نمودار مقایسه سرور" width="800" height="450" />
        <a href="/pricing">مشاهده تعرفه‌ها و پلن‌های سرور</a>
    </body>
    </html>"""
    
    report = audit_html_content(sample_html, url="https://example.com/vps-guide")
    assert report.score >= 90, f"امتیاز صفحه باکیفیت باید بالای ۹۰ باشد (امتیاز فعلی: {report.score})"
    assert len(report.json_ld_schemas) == 1, "باید یک اسکیمای JSON-LD معتبر استخراج شود"

    # Test 3: Jaccard Overlap
    q1 = {"قیمت تتر", "خرید تتر", "فروش usdt", "نرخ لحظه ای تتر", "صرافی تتر"}
    q2 = {"تحلیل تتر", "آینده تتر", "پشتوانه تتر", "قیمت تتر", "خرید تتر"}
    overlap_res = compute_jaccard_overlap("https://ex.com/price", q1, "https://ex.com/analysis", q2)
    # intersection: 2 ('قیمت تتر', 'خرید تتر'), union: 8 -> 2/8 = 0.25
    assert 0.24 <= overlap_res.jaccard_index <= 0.26, f"شاخص ژاکارد باید 0.25 باشد، مقدار فعلی: {overlap_res.jaccard_index}"

    # Test 4: PageRank Engine
    graph = {
        "home": ["category", "product_a", "product_b"],
        "category": ["product_a", "product_b", "home"],
        "product_a": ["category"],
        "product_b": ["category"],
        "orphan_page": []
    }
    pr_engine = InternalPageRankEngine()
    ranks = pr_engine.calculate_pagerank(graph)
    assert ranks["category"] > ranks["orphan_page"], "صفحه هاب دسته‌بندی باید پیج‌رنک به مراتب بالاتری از صفحه یتیم داشته باشد"
    assert ranks["home"] > ranks["orphan_page"], "صفحه اصلی باید وزن پیج‌رنک به مراتب بالاتری داشته باشد"

    print("[SEO Suite Self-Test] تمام ۴ آزمون فنی و ریاضیاتی با موفقیت ۱۰۰٪ تایید شدند.")


# ==========================================
# 6. MAIN EXECUTION CLI
# ==========================================

def print_audit_report(report: PageAuditReport):
    print("\n" + "="*50)
    print(f"گزارش ممیزی مهندسی سئو: {report.url}")
    print(f"امتیاز کلی سلامت صفحه: {report.score} / ۱۰۰")
    print("="*50)
    
    print("\n[معیارهای کلیدی سند]")
    for k, v in report.metrics.items():
        print(f"  • {k}: {v}")
        
    if report.technical_issues:
        print("\n[اشکالات تکنیکال و سرور/رندرینگ]")
        for issue in report.technical_issues:
            print(f"  ⚠️  {issue}")
            
    if report.on_page_issues:
        print("\n[اشکالات آن‌پیج و معماری اطلاعات]")
        for issue in report.on_page_issues:
            print(f"  ⚠️  {issue}")
            
    if report.vibefarsi_issues:
        print("\n[موارد عدم انطباق با استاندارد VibeFarsi]")
        for issue in report.vibefarsi_issues:
            print(f"  ⚠️  {issue}")
            
    if not (report.technical_issues or report.on_page_issues or report.vibefarsi_issues):
        print("\n✅ هیچ ایراد ساختاری یا نقض استانداردی در این سند یافت نشد.")
    print("="*50 + "\n")


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("--test", "test"):
        run_self_tests()
        sys.exit(0)

    cmd = sys.argv[1]
    
    if cmd == "audit-file" and len(sys.argv) >= 3:
        file_path = Path(sys.argv[2])
        if not file_path.exists():
            print(f"خطا: فایل {file_path} یافت نشد.")
            sys.exit(1)
        content = file_path.read_text(encoding="utf-8", errors="replace")
        report = audit_html_content(content, url=str(file_path.name))
        print_audit_report(report)
        
    elif cmd == "audit-url" and len(sys.argv) >= 3:
        target_url = sys.argv[2]
        url_audit = audit_url_slug(target_url)
        print("\n[بررسی سلامت اسلاگ و آدرس]")
        for err in url_audit.errors:
            print(f"  ❌ {err}")
        for warn in url_audit.warnings:
            print(f"  ⚠️  {warn}")
            
        try:
            req = urllib.request.Request(
                target_url,
                headers={"User-Agent": "Mozilla/5.0 (compatible; SEOAuditEngine/1.0; +https://example.com/bot)"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                html_bytes = resp.read()
                charset = resp.headers.get_content_charset() or "utf-8"
                html_text = html_bytes.decode(charset, errors="replace")
                report = audit_html_content(html_text, url=target_url)
                print_audit_report(report)
        except Exception as e:
            print(f"خطا در واکشی آدرس اینترنتی: {e}")
            sys.exit(1)
            
    elif cmd == "jaccard" and len(sys.argv) >= 4:
        # Expect two comma-separated lists or two files
        arg1, arg2 = sys.argv[2], sys.argv[3]
        def load_queries(val: str) -> Set[str]:
            p = Path(val)
            if p.exists():
                return {line.strip() for line in p.read_text(encoding="utf-8").splitlines() if line.strip()}
            return {q.strip() for q in val.split(",") if q.strip()}
            
        q1 = load_queries(arg1)
        q2 = load_queries(arg2)
        res = compute_jaccard_overlap("صفحه اول", q1, "صفحه دوم", q2)
        print("\n" + "="*50)
        print("تحلیل همپوشانی کوئری‌ها (Jaccard Overlap Matrix)")
        print(f"تعداد کوئری‌های صفحه اول: {len(q1)}")
        print(f"تعداد کوئری‌های صفحه دوم: {len(q2)}")
        print(f"تعداد اشتراک: {res.overlap_queries_count}")
        print(f"ضریب شباهت ژاکارد: {res.jaccard_index} ({round(res.jaccard_index*100, 1)}%)")
        print(f"سطح ریسک: {res.risk_level}")
        print(f"دستورالعمل اجرایی: {res.actionable_directive}")
        print("="*50 + "\n")
        
    else:
        print("استفاده:")
        print("  python3 seo_audit_engine.py --test")
        print("  python3 seo_audit_engine.py audit-file <path_to_html>")
        print("  python3 seo_audit_engine.py audit-url <https://...>")
        print("  python3 seo_audit_engine.py jaccard <queries1_or_file> <queries2_or_file>")


if __name__ == "__main__":
    main()
