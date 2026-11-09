#!/usr/bin/env python3
"""
Autonomous SEO Agent (Core Orchestrator)
Autonomous lifecycle:
  1. Ingests target (local codebase, live URL crawler, or WordPress REST API).
  2. Runs deep 360-degree diagnostic audit (Technical, Entity Graph, GEO, Content).
  3. Formulates deterministic remediation matrix.
  4. Automatically applies fixes (Auto-Fixer):
     - Meta description, Title, Canonical, H1, Lang/RTL, Img Dims, Schema.org @graph.
     - Generates /robots.txt, /llms.txt, and sitemap.xml.
     - Automatically runs SEO Floor-Guard to verify zero regressions.
  5. Emits executive markdown report with before/after scores.
Standard library only.
"""

from __future__ import annotations

import argparse
import difflib
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from connectors import LocalFilesConnector, LiveWebCrawlerConnector, WordPressRESTConnector, PageArtifact
from auto_fixer import AutonomousAutoFixer, generate_robots_txt, generate_sitemap_xml

# Import core diagnostic suite
sys.path.insert(0, str(Path(__file__).resolve().parent))
from seo_audit_engine import audit_html_content
from geo_ai_optimizer import evaluate_geo_citability, generate_llms_txt
from entity_graph_auditor import audit_entity_graph


@dataclass
class PageCycleReport:
    identifier: str
    url: str
    initial_score: int
    final_score: int
    fixes_count: int
    fixes_details: List[str]
    diff_stat: str


@dataclass
class AgentRunSummary:
    target: str
    mode: str
    total_pages_processed: int
    average_initial_score: float
    average_final_score: float
    total_fixes_applied: int
    pages: List[PageCycleReport]
    generated_assets: List[str]


class AutonomousSEOAgent:
    def __init__(self, canonical_domain: str, brand_name: str, dry_run: bool = False):
        self.canonical_domain = canonical_domain.rstrip("/")
        self.brand_name = brand_name
        self.dry_run = dry_run
        self.fixer = AutonomousAutoFixer(canonical_base=self.canonical_domain, brand_name=self.brand_name)

    def process_artifact(self, artifact: PageArtifact) -> Tuple[PageCycleReport, Optional[str]]:
        # 1. Initial Diagnostic Audit
        initial_audit = audit_html_content(artifact.raw_html, url=artifact.url)
        initial_score = initial_audit.score

        # 2. Autonomous Remediation
        remediation = self.fixer.fix_html_document(artifact.raw_html, page_url=artifact.url)
        
        # 3. Post-Fix Verification Audit
        post_audit = audit_html_content(remediation.fixed_html, url=artifact.url)
        final_score = post_audit.score

        # 4. Generate Diff
        diff_lines = list(difflib.unified_diff(
            artifact.raw_html.splitlines(),
            remediation.fixed_html.splitlines(),
            fromfile="before.html",
            tofile="after.html",
            lineterm=""
        ))
        diff_summary = f"{len(diff_lines)} خط تغییر در سند" if diff_lines else "بدون تغییر"

        fix_descriptions = [f"[{act.rule_name}] {act.description}" for act in remediation.actions_applied]

        report = PageCycleReport(
            identifier=artifact.identifier,
            url=artifact.url,
            initial_score=initial_score,
            final_score=final_score,
            fixes_count=len(remediation.actions_applied),
            fixes_details=fix_descriptions,
            diff_stat=diff_summary
        )

        new_content = remediation.fixed_html if remediation.is_modified else None
        return report, new_content

    def run_on_local_directory(self, directory: Path) -> AgentRunSummary:
        resolved_directory = directory.resolve()
        connector = LocalFilesConnector(resolved_directory)
        artifacts = connector.collect_artifacts()

        pages_report: List[PageCycleReport] = []
        modified_urls: List[str] = []
        llms_pages: List[Tuple[str, str, str]] = []

        for art in artifacts:
            page_rep, new_content = self.process_artifact(art)
            pages_report.append(page_rep)

            if new_content and not self.dry_run:
                connector.commit_patch(art.identifier, new_content, create_backup=True)

            # Synthesize URL for sitemap
            rel_path = Path(art.identifier).resolve().relative_to(resolved_directory)
            page_url = f"{self.canonical_domain}/{rel_path.as_posix()}"
            modified_urls.append(page_url)
            llms_pages.append((art.title or rel_path.stem, page_url, f"صفحه رسمی {art.title}"))

        generated_assets: List[str] = []

        if not self.dry_run:
            # Generate sitemap.xml
            sitemap_content = generate_sitemap_xml(modified_urls)
            sitemap_path = resolved_directory / "sitemap.xml"
            sitemap_path.write_text(sitemap_content, encoding="utf-8")
            generated_assets.append(str(sitemap_path))

            # Generate robots.txt
            robots_content = generate_robots_txt(self.canonical_domain)
            robots_path = resolved_directory / "robots.txt"
            robots_path.write_text(robots_content, encoding="utf-8")
            generated_assets.append(str(robots_path))

            # Generate llms.txt
            llms_content = generate_llms_txt(
                site_title=self.brand_name,
                site_description=f"مستندات و صفحات رسمی وب‌سایت {self.brand_name}",
                sections={"صفحات اصلی": llms_pages}
            )
            llms_path = resolved_directory / "llms.txt"
            llms_path.write_text(llms_content, encoding="utf-8")
            generated_assets.append(str(llms_path))

        avg_init = round(sum(p.initial_score for p in pages_report) / max(1, len(pages_report)), 1)
        avg_final = round(sum(p.final_score for p in pages_report) / max(1, len(pages_report)), 1)
        total_fixes = sum(p.fixes_count for p in pages_report)

        return AgentRunSummary(
            target=str(directory),
            mode="LOCAL_DIRECTORY",
            total_pages_processed=len(artifacts),
            average_initial_score=avg_init,
            average_final_score=avg_final,
            total_fixes_applied=total_fixes,
            pages=pages_report,
            generated_assets=generated_assets
        )

    def run_on_live_url(self, start_url: str, max_pages: int = 10) -> AgentRunSummary:
        crawler = LiveWebCrawlerConnector(start_url, max_pages=max_pages)
        artifacts = crawler.crawl()

        pages_report: List[PageCycleReport] = []
        for art in artifacts:
            page_rep, _ = self.process_artifact(art)
            pages_report.append(page_rep)

        avg_init = round(sum(p.initial_score for p in pages_report) / max(1, len(pages_report)), 1)
        avg_final = round(sum(p.final_score for p in pages_report) / max(1, len(pages_report)), 1)
        total_fixes = sum(p.fixes_count for p in pages_report)

        return AgentRunSummary(
            target=start_url,
            mode="LIVE_URL_CRAWLER",
            total_pages_processed=len(artifacts),
            average_initial_score=avg_init,
            average_final_score=avg_final,
            total_fixes_applied=total_fixes,
            pages=pages_report,
            generated_assets=[]
        )


def format_executive_markdown(summary: AgentRunSummary) -> str:
    md = f"""# گزارش عملیات ایجنت خودمختار سئو (Autonomous SEO Agent Mission Report)

## ۱. خلاصه اجرایی
- **تارگت هدف:** `{summary.target}`
- **حالت عملیاتی:** `{summary.mode}`
- **تعداد صفحات پردازش‌شده:** {summary.total_pages_processed} صفحه
- **امتیاز سلامت سئو قبل از عملیات:** {summary.average_initial_score} / ۱۰۰
- **امتیاز سلامت سئو پس از اصلاح خودکار:** {summary.average_final_score} / ۱۰۰
- **کل اقدامات و بهینه‌سازی‌های اعمال‌شده:** {summary.total_fixes_applied} اصلاح فنی

## ۲. دارایی‌های خودکار تولیدشده در ریشه سایت
"""
    if summary.generated_assets:
        for asset in summary.generated_assets:
            md += f"- `{asset}`\n"
    else:
        md += "- هیچ فایلی مستقیما روی سرور نوشته نشد (حالت تحلیل زنده یا تست بدون اعمال مستقیم).\n"

    md += "\n## ۳. جزئیات اصلاح صفحات\n"
    for p in summary.pages:
        md += f"### صفحه: `{p.identifier}`\n"
        md += f"- **امتیاز:** {p.initial_score} ➔ **{p.final_score}**\n"
        md += f"- **تغییرات کالبدی:** {p.diff_stat}\n"
        if p.fixes_details:
            md += "- **اقدامات اصلاحی:**\n"
            for fix in p.fixes_details:
                md += f"  • {fix}\n"
        md += "\n"

    return md


def run_self_test():
    print("[AutonomousSEOAgent Test] شروع آزمون جامع چرخه خودمختار...")
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        p1 = tmp_path / "index.html"
        p2 = tmp_path / "pricing.html"

        p1.write_text("""<html><head><title>سرور ابری — خرید آنلاین</title></head>
        <body><p>سرور ابری پرسرعت برای کسب‌وکارهای مدرن.</p><img src="/logo.png" /></body></html>""", encoding="utf-8")

        p2.write_text("""<html><head><title>تعرفه‌ها و پلن‌ها</title><link rel="canonical" href="/pricing" /></head>
        <body><p>مشاهده پلن‌های ماهانه و سالانه سرور با پشتیبانی ۲۴ ساعته.</p></body></html>""", encoding="utf-8")

        agent = AutonomousSEOAgent(canonical_domain="https://testserver.ir", brand_name="تست سرور", dry_run=False)
        summary = agent.run_on_local_directory(tmp_path)

        assert summary.total_pages_processed == 2, "باید ۲ صفحه پردازش شود"
        assert summary.average_final_score > summary.average_initial_score, "امتیاز نهایی باید افزایش یابد"
        assert summary.total_fixes_applied >= 10, f"باید حداقل ۱۰ فیکس اعمال شود (تعداد: {summary.total_fixes_applied})"
        assert (tmp_path / "sitemap.xml").exists(), "sitemap.xml باید تولید شده باشد"
        assert (tmp_path / "robots.txt").exists(), "robots.txt باید تولید شده باشد"
        assert (tmp_path / "llms.txt").exists(), "llms.txt باید تولید شده باشد"

        # Verify fixed file content
        content_after = p1.read_text(encoding="utf-8")
        assert 'lang="fa-IR"' in content_after
        assert 'dir="rtl"' in content_after
        assert '—' not in content_after

    print(f"[AutonomousSEOAgent Test] موفق: میانگین امتیاز از {summary.average_initial_score} به {summary.average_final_score} ارتقا یافت ({summary.total_fixes_applied} اصلاح موفق).")


def main():
    parser = argparse.ArgumentParser(description="Hermes Autonomous SEO Agent")
    parser.add_argument("--test", action="store_true", help="Run self-tests")
    parser.add_argument("--target", type=str, help="Target directory or URL")
    parser.add_argument("--domain", type=str, default="https://example.com", help="Canonical domain (e.g. https://mybrand.ir)")
    parser.add_argument("--brand", type=str, default="پلتفرم رسمی", help="Brand name for metadata and schemas")
    parser.add_argument("--dry-run", action="store_true", help="Audit and plan only, do not modify files")
    parser.add_argument("--max-pages", type=int, default=10, help="Max pages for live crawler")

    args = parser.parse_args()

    if args.test:
        run_self_test()
        sys.exit(0)

    if not args.target:
        parser.print_help()
        sys.exit(0)

    agent = AutonomousSEOAgent(canonical_domain=args.domain, brand_name=args.brand, dry_run=args.dry_run)

    target_path = Path(args.target)
    if target_path.exists() and target_path.is_dir():
        summary = agent.run_on_local_directory(target_path)
    elif args.target.startswith("http://") or args.target.startswith("https://"):
        summary = agent.run_on_live_url(args.target, max_pages=args.max_pages)
    else:
        print(f"خطا: تارگت نامعتبر است: {args.target}")
        sys.exit(1)

    print(format_executive_markdown(summary))


if __name__ == "__main__":
    main()
