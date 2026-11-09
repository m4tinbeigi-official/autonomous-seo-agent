#!/usr/bin/env python3
"""
Hermes Master SEO CLI & Autonomous Engineering Terminal
Unified command-line orchestrator for:
  - Technical & On-Page 360 Audit (seo_audit_engine)
  - Knowledge Graph & Entity Triplet Extraction (entity_graph_auditor)
  - JavaScript Hydration & Blind-Spot Detection (hydration_diff_checker)
  - Google Information Gain Patent Scoring (information_gain_calculator)
  - Dense Vector Semantic Distance & Cannibalization (semantic_vector_auditor)
  - Server Log & Crawl Budget Forensics (server_log_analyzer)
  - Causal Impact & Core Update Anomaly Detection (causal_impact_detector)
  - Edge SEO Cloudflare Worker Generation (edge_seo_generator)
  - SEO CI/CD Deployment Floor-Guard (seo_ci_guard)
  - Generative Engine Optimization & llms.txt (geo_ai_optimizer)
  - GSC Striking Distance Keyword Miner (gsc_striking_distance)
  - Active Internal Link Recommender & PageRank Flow (active_graph_linker)
  - Business Revenue & CPC Replacement Value Translator (seo_business_value)
Zero external dependencies. 100% Python Standard Library.
"""

from __future__ import annotations

import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Set

from seo_audit_engine import audit_html_content, audit_url_slug
from entity_graph_auditor import audit_entity_graph, generate_enterprise_jsonld_graph
from hydration_diff_checker import compare_hydration
from information_gain_calculator import analyze_information_gain
from semantic_vector_auditor import audit_semantic_cannibalization
from server_log_analyzer import ServerLogAnalyzer
from causal_impact_detector import detect_traffic_shift
from edge_seo_generator import EdgeSEOConfig, generate_cloudflare_worker_script
from seo_ci_guard import scan_directory, validate_file_for_ci
from geo_ai_optimizer import evaluate_geo_citability, generate_llms_txt
from gsc_striking_distance import parse_gsc_data, analyze_striking_distance
from active_graph_linker import optimize_internal_links_for_target
from seo_business_value import calculate_seo_business_value


def print_banner():
    print("""
╔══════════════════════════════════════════════════════════════════╗
║        HERMES PRINCIPAL SEO ARCHITECT & ALGORITHM SUITE          ║
║      Autonomous Enterprise Information Retrieval Engine (v3.5)   ║
╚══════════════════════════════════════════════════════════════════╝
""")


def cmd_audit_360(target: str):
    print_banner()
    print(f"[*] آغاز ممیزی ۳۶۰ درجه سئو برای هدف: {target}\n")

    if target.startswith("http://") or target.startswith("https://"):
        slug_audit = audit_url_slug(target)
        print("[۱. ممیزی اسلاگ و آدرس اینترنتی]")
        if slug_audit.errors:
            for err in slug_audit.errors:
                print(f"  ❌ {err}")
        if slug_audit.warnings:
            for w in slug_audit.warnings:
                print(f"  ⚠️  {w}")
        if not slug_audit.errors and not slug_audit.warnings:
            print("  ✅ ساختار اسلاگ و آدرس کاملا استاندارد و پاکسازی‌شده است.")

        try:
            req = urllib.request.Request(
                target,
                headers={"User-Agent": "Mozilla/5.0 (compatible; HermesPrincipalSEO/3.5; +https://example.com/bot)"}
            )
            with urllib.request.urlopen(req, timeout=12) as resp:
                raw_bytes = resp.read()
                charset = resp.headers.get_content_charset() or "utf-8"
                html_text = raw_bytes.decode(charset, errors="replace")
        except Exception as e:
            print(f"\nخطا در واکشی آدرس: {e}")
            return
    else:
        path = Path(target)
        if not path.exists():
            print(f"خطا: فایل {target} یافت نشد.")
            return
        html_text = path.read_text(encoding="utf-8", errors="replace")

    # 1. Technical & On-Page
    page_report = audit_html_content(html_text, url=target)
    print("\n" + "="*50)
    print(f"[۲. سلامت تکنیکال و معماری سند] نمره: {page_report.score} / ۱۰۰")
    print("="*50)
    for k, v in page_report.metrics.items():
        print(f"  • {k}: {v}")

    if page_report.technical_issues:
        print("\n  [اشکالات تکنیکال و رندرینگ]")
        for issue in page_report.technical_issues:
            print(f"    ⚠️  {issue}")

    if page_report.on_page_issues:
        print("\n  [اشکالات محتوا و معماری اطلاعات]")
        for issue in page_report.on_page_issues:
            print(f"    ⚠️  {issue}")

    if page_report.vibefarsi_issues:
        print("\n  [ایرادات پروتکل VibeFarsi]")
        for issue in page_report.vibefarsi_issues:
            print(f"    ⚠️  {issue}")

    # 2. Entity Knowledge Graph Audit
    entity_report = audit_entity_graph(html_text)
    print("\n" + "="*50)
    print(f"[۳. گراف دانش و همبستگی موجودیت‌ها] نمره: {entity_report.graph_connectivity_score} / ۱۰۰")
    print("="*50)
    print(f"  • اسکیما دارای گراف یکپارچه (@graph): {'بله' if entity_report.has_unified_graph_schema else 'خیر'}")
    print(f"  • تعداد گره‌های متصل اسکیما: {entity_report.schema_nodes_count}")
    if entity_report.extracted_entities:
        print("  • موجودیت‌های شناخته‌شده:")
        for ent in entity_report.extracted_entities[:5]:
            print(f"    - {ent['name']} ({ent['wikidata_uri']})")

    # 3. Information Gain Score
    gain_report = analyze_information_gain(html_text)
    print("\n" + "="*50)
    print(f"[۴. نمره کسب اطلاعات (Information Gain)] نمره: {gain_report.information_gain_score} / ۱۰۰")
    print("="*50)
    print(f"  • ارزیابی تحلیلی: {gain_report.verdict}")
    print(f"  • فاکتورهای عددی و تجربی: {gain_report.data_points_count}")
    print(f"  • عبارات کلیشه‌ای و حاشیه‌پردازی: {gain_report.fluff_phrases_count}")

    # 4. GEO & AI Readiness
    geo_report = evaluate_geo_citability(html_text)
    print("\n" + "="*50)
    print(f"[۵. بهینه‌سازی برای هوش مصنوعی (GEO)] نمره: {geo_report.citability_score} / ۱۰۰")
    print("="*50)
    print(f"  • وضعیت استناد در AI Overviews: {geo_report.verdict}")
    print(f"  • جداول داده‌های ساخت‌یافته: {geo_report.tables_count}")
    print(f"  • هدینگ‌های پرسش و پاسخ: {geo_report.faq_qa_pairs_count}")

    print("\n" + "="*66)
    print("  ممیزی ۳۶۰ درجه به پایان رسید.")
    print("="*66 + "\n")


def run_all_suite_tests():
    print_banner()
    print("[*] اجرای چرخه آزمون جامع مهندسی سئو (Suite Self-Tests)...")
    
    # 1. Audit Engine
    from seo_audit_engine import run_self_tests as test_audit
    test_audit()
    
    # 2. Server log
    from server_log_analyzer import run_self_test as test_log
    test_log()
    
    # 3. Hydration
    from hydration_diff_checker import run_self_test as test_hydra
    test_hydra()
    
    # 4. Information gain
    from information_gain_calculator import run_self_test as test_gain
    test_gain()
    
    # 5. Semantic vector
    from semantic_vector_auditor import run_self_test as test_vector
    test_vector()
    
    # 6. Causal impact
    from causal_impact_detector import run_self_test as test_causal
    test_causal()

    # 7. Entity graph
    from entity_graph_auditor import run_self_test as test_entity
    test_entity()

    # 8. Edge SEO
    from edge_seo_generator import run_self_test as test_edge
    test_edge()

    # 9. CI/CD Floor-Guard
    from seo_ci_guard import run_self_test as test_ci
    test_ci()

    # 10. GEO Optimizer
    from geo_ai_optimizer import run_self_test as test_geo
    test_geo()

    # 11. Striking Distance
    from gsc_striking_distance import run_self_test as test_sd
    test_sd()

    # 12. Active Linker
    from active_graph_linker import run_self_test as test_linker
    test_linker()

    # 13. Business Value
    from seo_business_value import run_self_test as test_biz
    test_biz()

    print("\n✅ تمامی ۱۳ ماژول تخصصی مهندسی سئو با موفقیت ۱۰۰٪ تایید شدند و بدون اشکال کار می‌کنند.\n")


def print_help():
    print_banner()
    print("دستورات کنسول مهندسی سئو:")
    print("  python3 seo_master_cli.py --test                      اجرای آزمون‌های اعتبارسنجی تمام ۱۳ ماژول")
    print("  python3 seo_master_cli.py audit <url_or_html_file>    ممیزی جامع ۳۶۰ درجه (تکنیکال، گراف، آن‌پیج، اینفورمیشن گین، GEO)")
    print("  python3 seo_master_cli.py ci-guard <directory>        بررسی گیت استقرار و پیشگیری از رگرسیون در CI/CD")
    print("  python3 seo_master_cli.py geo <html_file>             تحلیل قابلیت استناد در هوش مصنوعی (Google AI Overviews)")
    print("  python3 seo_master_cli.py striking <gsc_csv>          شکار کلمات در آستانه جهش و پتانسیل جذب کلیک")
    print("  python3 seo_master_cli.py link-target <dir> <url> <kw> پیشنهاد هوشمند درج لینک‌های داخلی با انکرتکست طبیعی")
    print("  python3 seo_master_cli.py biz-value <sessions> [cpc]  محاسبه ارزش مالی، جایگزین بودجه ادز و بازگشت سرمایه برای مدیران")
    print("  python3 seo_master_cli.py hydration <raw> <rendered>  مقایسه سورس خام با دام رندرشده کلاینت")
    print("  python3 seo_master_cli.py vector-sim <doc1> <doc2>    سنجش فاصله برداری و کنیبالیزیشن عصبی")
    print("  python3 seo_master_cli.py logs <access.log>           فارنزیک لاگ سرور و اتلاف بودجه خزش")
    print("  python3 seo_master_cli.py anomaly <comma_series>      کشف علل آماری تغییر ترافیک (افت فنی در برابر الگوریتم)")
    print("  python3 seo_master_cli.py edge-gen <domain>           تولید ورکر Cloudflare برای سئوی لبه شبکه")


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("--help", "-h"):
        print_help()
        sys.exit(0)

    cmd = sys.argv[1]
    if cmd in ("--test", "test"):
        run_all_suite_tests()
        sys.exit(0)

    if cmd == "audit" and len(sys.argv) >= 3:
        cmd_audit_360(sys.argv[2])
    elif cmd == "ci-guard" and len(sys.argv) >= 3:
        total, fails = scan_directory(sys.argv[2], is_production=True)
        crits = [f for f in fails if f.severity == "CRITICAL"]
        print(f"اسکن {total} فایل: {len(crits)} خطای بحرانی")
        for c in crits:
            print(f"  ❌ {c.file_path}: {c.message}")
        sys.exit(1 if crits else 0)
    elif cmd == "geo" and len(sys.argv) >= 3:
        p = Path(sys.argv[2])
        rep = evaluate_geo_citability(p.read_text(encoding="utf-8", errors="replace"))
        print(f"نمره آمادگی استناد در هوش مصنوعی: {rep.citability_score}/۱۰۰ | ارزیابی: {rep.verdict}")
    elif cmd == "striking" and len(sys.argv) >= 3:
        data = parse_gsc_data(Path(sys.argv[2]))
        r = analyze_striking_distance(data)
        print(f"پتانسیل افزایش ترافیک: +{r.total_potential_click_gain} کلیک ماهانه در {r.striking_distance_count} کلمه")
        for o in r.top_opportunities[:5]:
            print(f"  • «{o.query}» (جایگاه {o.current_position}) -> پتانسیل +{o.opportunity_gain} کلیک")
    elif cmd == "link-target" and len(sys.argv) >= 5:
        dir_path = Path(sys.argv[2])
        tgt = sys.argv[3]
        kws = [k.strip() for k in sys.argv[4].split(",") if k.strip()]
        corpus = {f.name: f.read_text(encoding="utf-8", errors="replace") for f in dir_path.glob("*.html")}
        r = optimize_internal_links_for_target(corpus, tgt, kws)
        print(f"کشف {r.total_opportunities_found} موقعیت درج لینک | رشد تخمینی پیج‌رنک: +{r.estimated_pagerank_uplift_pct}٪")
        for o in r.opportunities[:3]:
            print(f"  • {o.source_document}: {o.recommended_html_patch}")
    elif cmd == "biz-value" and len(sys.argv) >= 3:
        s = int(sys.argv[2])
        cpc = int(sys.argv[3]) if len(sys.argv) >= 4 else 4500
        memo = calculate_seo_business_value(s, cpc)
        print(memo.one_page_memo_markdown)
    elif cmd == "hydration" and len(sys.argv) >= 4:
        raw = Path(sys.argv[2]).read_text(encoding="utf-8", errors="replace")
        rend = Path(sys.argv[3]).read_text(encoding="utf-8", errors="replace")
        rep = compare_hydration(raw, rend)
        print(f"ریسک رندرینگ: {rep.rendering_risk_score}/۱۰۰ | وابستگی به JS: {round(rep.js_content_dependency_ratio*100, 1)}٪")
    elif cmd == "vector-sim" and len(sys.argv) >= 4:
        d1 = Path(sys.argv[2]).read_text(encoding="utf-8", errors="replace")
        d2 = Path(sys.argv[3]).read_text(encoding="utf-8", errors="replace")
        r = audit_semantic_cannibalization(d1, d2)
        print(f"شباهت کسینوسی بردارها: {r.cosine_similarity} ({r.similarity_percentage}٪) | سطح ریسک: {r.risk_level}")
    elif cmd == "logs" and len(sys.argv) >= 3:
        analyzer = ServerLogAnalyzer(verify_dns=False)
        lines = Path(sys.argv[2]).read_text(encoding="utf-8", errors="replace").splitlines()
        r = analyzer.analyze_lines(lines)
        print(f"کل هیت‌های ربات‌ها: {r.total_bot_requests} | نرخ اتلاف بودجه خزش: {r.crawl_waste_percentage}٪")
    elif cmd == "anomaly" and len(sys.argv) >= 3:
        vals = [float(x.strip()) for x in sys.argv[2].split(",") if x.strip()]
        r = detect_traffic_shift(vals)
        print(f"تغییر: {r.percentage_change}٪ | طبقه‌بندی ریشه‌ای: {r.classification}")
    elif cmd == "edge-gen" and len(sys.argv) >= 3:
        cfg = EdgeSEOConfig(domain=sys.argv[2])
        print(generate_cloudflare_worker_script(cfg))
    else:
        print_help()


if __name__ == "__main__":
    main()
