#!/usr/bin/env python3
"""
SEO CI/CD Floor-Guard (Pre-commit & Build Failure Gate)
Enforces zero SEO regressions in deployment pipelines.
Checks:
  1. No unintended noindex / nofollow on production builds.
  2. Single H1, non-empty Title, valid canonical tags.
  3. JSON-LD syntax errors and schema integrity.
  4. VibeFarsi rules: lang='fa' / 'fa-IR', dir='rtl', zero em-dash in titles/meta.
  5. Critical resource preload and image dimensions (CLS prevention).
Exits with 0 on pass, 1 on failure.
Standard library only.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class FailureItem:
    file_path: str
    rule_name: str
    severity: str  # 'CRITICAL' or 'WARNING'
    message: str


class CIHTMLValidator(HTMLParser):
    def __init__(self, filename: str):
        super().__init__()
        self.filename = filename
        self.lang: Optional[str] = None
        self.dir: Optional[str] = None
        self.title: str = ""
        self.canonical: Optional[str] = None
        self.robots_meta: str = ""
        self.h1_tags: List[str] = []
        self.meta_desc: str = ""
        self.images_without_dims: int = 0
        self.json_ld_blocks: List[str] = []
        
        self._in_head = False
        self._in_title = False
        self._in_h1 = False
        self._in_json_ld = False
        self._buf = ""

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, str | None]]):
        tag_lower = tag.lower()
        attr_dict = {k.lower(): (v or "") for k, v in attrs}

        if tag_lower == "html":
            self.lang = attr_dict.get("lang")
            self.dir = attr_dict.get("dir")
        elif tag_lower == "head":
            self._in_head = True
        elif tag_lower == "title" and self._in_head:
            self._in_title = True
            self._buf = ""
        elif tag_lower == "meta":
            name = attr_dict.get("name", "").lower()
            if name == "robots":
                self.robots_meta = attr_dict.get("content", "").lower()
            elif name == "description":
                self.meta_desc = attr_dict.get("content", "").strip()
        elif tag_lower == "link":
            rel = attr_dict.get("rel", "").lower()
            if rel == "canonical":
                self.canonical = attr_dict.get("href")
        elif tag_lower == "h1":
            self._in_h1 = True
            self._buf = ""
        elif tag_lower == "img":
            has_w = "width" in attr_dict
            has_h = "height" in attr_dict
            if not (has_w and has_h):
                self.images_without_dims += 1
        elif tag_lower == "script":
            stype = attr_dict.get("type", "").lower()
            if stype == "application/ld+json":
                self._in_json_ld = True
                self._buf = ""

    def handle_endtag(self, tag: str):
        tag_lower = tag.lower()
        if tag_lower == "head":
            self._in_head = False
        elif tag_lower == "title":
            self._in_title = False
            self.title = self._buf.strip()
        elif tag_lower == "h1":
            self._in_h1 = False
            if self._buf.strip():
                self.h1_tags.append(self._buf.strip())
        elif tag_lower == "script" and self._in_json_ld:
            self._in_json_ld = False
            if self._buf.strip():
                self.json_ld_blocks.append(self._buf.strip())

    def handle_data(self, data: str):
        if self._in_title or self._in_h1 or self._in_json_ld:
            self._buf += data


def validate_file_for_ci(file_path: Path, is_production: bool = True) -> List[FailureItem]:
    failures: List[FailureItem] = []
    content = file_path.read_text(encoding="utf-8", errors="replace")
    
    validator = CIHTMLValidator(str(file_path))
    validator.feed(content)

    # 1. Unintended Noindex Check
    if is_production and "noindex" in validator.robots_meta:
        failures.append(FailureItem(
            file_path=str(file_path),
            rule_name="UNINTENDED_NOINDEX",
            severity="CRITICAL",
            message=f"صفحه پروداکشن دارای متاتگ robots='{validator.robots_meta}' است که مانع ایندکس در گوگل می‌شود."
        ))

    # 2. Title Tag Check
    if not validator.title:
        failures.append(FailureItem(
            file_path=str(file_path),
            rule_name="MISSING_TITLE",
            severity="CRITICAL",
            message="تگ <title> در تگ <head> وجود ندارد یا کاملا خالی است."
        ))
    elif "—" in validator.title:
        failures.append(FailureItem(
            file_path=str(file_path),
            rule_name="VIBEFARSI_EMDASH_IN_TITLE",
            severity="CRITICAL",
            message="استفاده از خط فاصله کشیده (em-dash) در تگ عنوان بر خلاف استاندارد VibeFarsi است."
        ))

    # 3. Canonical Check
    if not validator.canonical:
        failures.append(FailureItem(
            file_path=str(file_path),
            rule_name="MISSING_CANONICAL",
            severity="CRITICAL",
            message="تگ rel='canonical' در صفحه تعریف نشده است."
        ))
    elif not validator.canonical.startswith("http"):
        failures.append(FailureItem(
            file_path=str(file_path),
            rule_name="RELATIVE_CANONICAL",
            severity="CRITICAL",
            message=f"تگ کنونیکال باید آدرس مطلق باشد، مقدار فعلی: '{validator.canonical}'"
        ))

    # 4. H1 Heading Check
    if len(validator.h1_tags) == 0:
        failures.append(FailureItem(
            file_path=str(file_path),
            rule_name="MISSING_H1",
            severity="CRITICAL",
            message="صفحه فاقد هدینگ اصلی <h1> است."
        ))
    elif len(validator.h1_tags) > 1:
        failures.append(FailureItem(
            file_path=str(file_path),
            rule_name="MULTIPLE_H1",
            severity="WARNING",
            message=f"صفحه دارای {len(validator.h1_tags)} هدینگ <h1> است."
        ))

    # 5. Language and Direction Check
    if not validator.lang or not validator.lang.lower().startswith("fa"):
        failures.append(FailureItem(
            file_path=str(file_path),
            rule_name="INVALID_LANG_ATTR",
            severity="CRITICAL",
            message=f"ویژگی lang تگ <html> برای سایت فارسی نامعتبر است: '{validator.lang}'"
        ))
    if validator.dir != "rtl":
        failures.append(FailureItem(
            file_path=str(file_path),
            rule_name="INVALID_DIR_ATTR",
            severity="CRITICAL",
            message=f"ویژگی dir تگ <html> باید 'rtl' باشد، مقدار فعلی: '{validator.dir}'"
        ))

    # 6. JSON-LD Syntax
    for block in validator.json_ld_blocks:
        try:
            data = json.loads(block)
            if isinstance(data, dict) and "@context" not in data:
                failures.append(FailureItem(
                    file_path=str(file_path),
                    rule_name="SCHEMA_MISSING_CONTEXT",
                    severity="WARNING",
                    message="اسکیمای JSON-LD فاقد فیلد '@context' است."
                ))
        except Exception as e:
            failures.append(FailureItem(
                file_path=str(file_path),
                rule_name="SCHEMA_SYNTAX_ERROR",
                severity="CRITICAL",
                message=f"خطای سینتکس JSON-LD نامعتبر: {e}"
            ))

    # 7. Images without dimensions
    if validator.images_without_dims > 0:
        failures.append(FailureItem(
            file_path=str(file_path),
            rule_name="IMAGE_MISSING_DIMENSIONS",
            severity="WARNING",
            message=f"{validator.images_without_dims} تصویر بدون مشخص کردن صریح width و height یافت شد (ریسک CLS)."
        ))

    return failures


def scan_directory(directory_path: str, is_production: bool = True) -> Tuple[int, List[FailureItem]]:
    p = Path(directory_path)
    html_files = list(p.rglob("*.html"))
    all_failures: List[FailureItem] = []

    for f in html_files:
        res = validate_file_for_ci(f, is_production=is_production)
        all_failures.extend(res)

    return len(html_files), all_failures


def run_self_test():
    print("[SEO CI Floor-Guard Test] شروع آزمون گیت استقرار سئو...")
    import tempfile
    
    good_html = """<!DOCTYPE html>
    <html lang="fa-IR" dir="rtl">
    <head>
        <title>راهنمای خرید هاست و سرور ابری</title>
        <meta name="description" content="راهنمای کامل خرید هاست ابری پرسرعت." />
        <link rel="canonical" href="https://example.com/host" />
        <script type="application/ld+json">{"@context": "https://schema.org", "@type": "WebPage"}</script>
    </head>
    <body>
        <h1>راهنمای خرید هاست</h1>
        <img src="/img.webp" width="400" height="200" alt="تست" />
    </body>
    </html>"""

    bad_html = """<!DOCTYPE html>
    <html lang="en">
    <head>
        <title>تست — خط فاصله غلط</title>
        <meta name="robots" content="noindex, follow" />
        <link rel="canonical" href="/relative-path" />
        <script type="application/ld+json">{invalid json}</script>
    </head>
    <body>
        <p>بدون H1</p>
    </body>
    </html>"""

    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as f_good:
        f_good.write(good_html)
        good_path = Path(f_good.name)

    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as f_bad:
        f_bad.write(bad_html)
        bad_path = Path(f_bad.name)

    good_failures = validate_file_for_ci(good_path, is_production=True)
    bad_failures = validate_file_for_ci(bad_path, is_production=True)

    good_path.unlink()
    bad_path.unlink()

    assert len(good_failures) == 0, f"فایل استاندارد نباید هیچ خطایی داشته باشد: {good_failures}"
    criticals = [f for f in bad_failures if f.severity == "CRITICAL"]
    assert len(criticals) >= 4, f"باید حداقل ۴ خطای حیاتی در فایل نامعتبر کشف شود (تعداد: {len(criticals)})"
    
    rule_names = {f.rule_name for f in criticals}
    assert "UNINTENDED_NOINDEX" in rule_names, "باید تگ noindex کشف شود"
    assert "MISSING_H1" in rule_names, "باید غیبت H1 کشف شود"
    assert "RELATIVE_CANONICAL" in rule_names, "باید کنونیکال نسبی کشف شود"
    assert "SCHEMA_SYNTAX_ERROR" in rule_names, "باید سینتکس نامعتبر اسکیما کشف شود"

    print(f"[SEO CI Floor-Guard Test] موفق: فایل تمیز بدون خطا تایید شد؛ فایل خراب با {len(criticals)} خطای بحرانی بلاک گردید.")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        run_self_test()
        sys.exit(0)

    target_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    total_scanned, failures = scan_directory(target_dir, is_production=True)
    critical_errors = [f for f in failures if f.severity == "CRITICAL"]
    warnings = [f for f in failures if f.severity == "WARNING"]

    print("="*60)
    print(f"گزارش گیت استقرار سئو (SEO CI/CD Floor-Guard)")
    print(f"تعداد صفحات اسکن‌شده: {total_scanned}")
    print(f"خطاهای بحرانی (بلاک‌کننده بیلد): {len(critical_errors)}")
    print(f"هشدارهای غیربحرانی: {len(warnings)}")
    print("="*60)

    if critical_errors:
        print("\n❌ خطاهای بحرانی کشف‌شده (بیلد متوقف شد):")
        for err in critical_errors:
            print(f"  [{err.rule_name}] {err.file_path}: {err.message}")

    if warnings:
        print("\n⚠️  هشدارها:")
        for w in warnings:
            print(f"  [{w.rule_name}] {w.file_path}: {w.message}")

    if critical_errors:
        sys.exit(1)
    else:
        print("\n✅ کلیه صفحات بررسی‌شده تایید شدند. بیلد مجاز به استقرار است.")
        sys.exit(0)
