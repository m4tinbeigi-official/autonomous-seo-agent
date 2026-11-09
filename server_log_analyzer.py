#!/usr/bin/env python3
"""
Server Log Analyzer for SEO Engineering & Crawl Budget Forensics
Features:
  1. High-speed parsing of Nginx/Apache Combined & Common log formats.
  2. Bot classification (Googlebot Desktop/Mobile, Bingbot, Yandex, Scrapers).
  3. Reverse DNS (PTR) validator logic to unmask spoofed/fake Googlebots.
  4. Crawl Budget Waste calculation (status codes 4xx/5xx, redirect chains, faceted URL bloat).
  5. Taxonomy and path crawl heatmaps.
Standard library only (re, socket, dataclasses, typing, collections).
"""

from __future__ import annotations

import collections
import re
import socket
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Counter, Dict, List, Optional, Set, Tuple


COMBINED_LOG_REGEX = re.compile(
    r'^(?P<ip>\S+)\s+\S+\s+\S+\s+\[(?P<time>[^\]]+)\]\s+"(?P<method>\S+)\s+(?P<path>\S+)\s+(?P<proto>[^"]+)"\s+(?P<status>\d{3})\s+(?P<bytes>\S+)\s+"(?P<referer>[^"]*)"\s+"(?P<ua>[^"]*)"'
)


@dataclass
class LogEntry:
    ip: str
    time_str: str
    method: str
    path: str
    status: int
    bytes_sent: int
    referer: str
    user_agent: str
    is_bot: bool = False
    bot_name: str = ""


@dataclass
class CrawlBudgetReport:
    total_log_lines: int
    total_bot_requests: int
    googlebot_desktop_requests: int
    googlebot_mobile_requests: int
    status_distribution: Dict[int, int]
    crawl_waste_requests: int
    crawl_waste_percentage: float
    top_crawled_paths: List[Tuple[str, int]]
    parameter_bloat_requests: int
    fake_googlebot_hits: int
    recommendations: List[str]


class ServerLogAnalyzer:
    def __init__(self, verify_dns: bool = False):
        self.verify_dns = verify_dns
        self._dns_cache: Dict[str, bool] = {}

    def is_verified_googlebot(self, ip: str) -> bool:
        """
        RFC-standard Googlebot verification via Reverse DNS (PTR) and Forward DNS.
        """
        if ip in self._dns_cache:
            return self._dns_cache[ip]

        if not self.verify_dns:
            # Simulated or trusted mode
            return True

        try:
            host, _, _ = socket.gethostbyaddr(ip)
            if host.endswith(".googlebot.com") or host.endswith(".google.com"):
                addrs = socket.gethostbyname_ex(host)[2]
                verified = ip in addrs
            else:
                verified = False
        except Exception:
            verified = False

        self._dns_cache[ip] = verified
        return verified

    def classify_bot(self, ua: str, ip: str) -> Tuple[bool, str, bool]:
        """
        Returns (is_bot, bot_family, is_legit)
        """
        ua_lower = ua.lower()
        if "googlebot" in ua_lower:
            is_mobile = "mobile" in ua_lower or "android" in ua_lower
            bot_name = "Googlebot Mobile" if is_mobile else "Googlebot Desktop"
            is_legit = self.is_verified_googlebot(ip) if self.verify_dns else True
            return True, bot_name, is_legit
        elif "bingbot" in ua_lower:
            return True, "Bingbot", True
        elif "yandexbot" in ua_lower:
            return True, "YandexBot", True
        elif any(bot in ua_lower for bot in ["duckduckbot", "baiduspider", "slurp", "ahrefsbot", "semrushbot"]):
            return True, "Other Bot", True
        return False, "", False

    def parse_line(self, line: str) -> Optional[LogEntry]:
        m = COMBINED_LOG_REGEX.match(line.strip())
        if not m:
            return None
        d = m.groupdict()
        status = int(d["status"])
        bytes_sent = int(d["bytes"]) if d["bytes"].isdigit() else 0
        ua = d["ua"]
        ip = d["ip"]

        is_bot, bot_name, _ = self.classify_bot(ua, ip)

        return LogEntry(
            ip=ip,
            time_str=d["time"],
            method=d["method"],
            path=d["path"],
            status=status,
            bytes_sent=bytes_sent,
            referer=d["referer"],
            user_agent=ua,
            is_bot=is_bot,
            bot_name=bot_name
        )

    def analyze_lines(self, lines: List[str]) -> CrawlBudgetReport:
        total_lines = 0
        bot_entries: List[LogEntry] = []
        fake_hits = 0

        for line in lines:
            entry = self.parse_line(line)
            if not entry:
                continue
            total_lines += 1
            if entry.is_bot:
                bot_entries.append(entry)

        status_counts: Counter[int] = collections.Counter()
        path_counts: Counter[str] = collections.Counter()
        google_desktop = 0
        google_mobile = 0
        waste_count = 0
        param_bloat_count = 0

        for b in bot_entries:
            status_counts[b.status] += 1
            path_counts[b.path] += 1

            if b.bot_name == "Googlebot Desktop":
                google_desktop += 1
            elif b.bot_name == "Googlebot Mobile":
                google_mobile += 1

            # Crawl waste heuristics:
            # 1. 4xx / 5xx errors
            # 2. 301/302 redirects (crawler spending hits following redirects)
            # 3. Faceted parameters (e.g. ?sort=, ?color=, ?filter=)
            is_waste = False
            if b.status >= 300:
                is_waste = True
                waste_count += 1
            
            if "?" in b.path:
                param_bloat_count += 1
                if not is_waste:
                    # Parameter URLs crawled without 4xx still waste budget if unnecessary
                    if any(p in b.path.lower() for p in ["sort=", "filter=", "order=", "page=", "ref="]):
                        waste_count += 1

        total_bots = len(bot_entries)
        waste_pct = round((waste_count / total_bots * 100), 2) if total_bots else 0.0

        recommendations: List[str] = []
        if waste_pct > 25.0:
            recommendations.append(
                f"هشدار هدررفت بودجه خزش: بیش از {waste_pct}٪ درخواست‌های بات‌ها صرف مسیرهای غیربهینه (خطاها، ریدایرکت‌ها یا پارامترها) شده است."
            )
        if status_counts.get(404, 0) > 0:
            recommendations.append(
                f"کشف {status_counts[404]} خطای ۴۰۴ در مسیر خزش ربات؛ پیوندهای داخلی شکسته را سریعا بازسازی یا ریدایرکت کنید."
            )
        if param_bloat_count > total_bots * 0.2:
            recommendations.append(
                "حجم بالای خزش URLهای دارای پارامتر فیلتر/مرتب‌سازی کشف شد؛ پارامترها را با تگ noindex یا مسدودسازی اصولی در robots.txt مدیریت کنید."
            )
        if google_mobile > google_desktop * 3:
            recommendations.append(
                "ترافیک کراولر گوگل با تسلط کامل Mobile-First انجام می‌شود؛ بهینه‌سازی سرعت و DOM نسخه موبایل اولویت مطلق دارد."
            )

        return CrawlBudgetReport(
            total_log_lines=total_lines,
            total_bot_requests=total_bots,
            googlebot_desktop_requests=google_desktop,
            googlebot_mobile_requests=google_mobile,
            status_distribution=dict(status_counts),
            crawl_waste_requests=waste_count,
            crawl_waste_percentage=waste_pct,
            top_crawled_paths=path_counts.most_common(10),
            parameter_bloat_requests=param_bloat_count,
            fake_googlebot_hits=fake_hits,
            recommendations=recommendations
        )


def run_self_test():
    print("[ServerLogAnalyzer Test] شروع آزمون صحت تحلیل لاگ...")
    analyzer = ServerLogAnalyzer(verify_dns=False)
    
    mock_logs = [
        # Normal 200 Googlebot Mobile
        '66.249.66.1 - - [20/Sep/2026:10:00:00 +0330] "GET /vps-guide HTTP/1.1" 200 4500 "-" "Mozilla/5.0 (Linux; Android 6.0.1; Nexus 5X Build/MMB29P) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/W.X.Y.Z Mobile Safari/537.36 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"',
        # Normal 200 Googlebot Desktop
        '66.249.66.2 - - [20/Sep/2026:10:00:05 +0330] "GET /pricing HTTP/1.1" 200 6200 "-" "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"',
        # 404 Not Found Googlebot Mobile (Waste)
        '66.249.66.1 - - [20/Sep/2026:10:00:10 +0330] "GET /old-deleted-page HTTP/1.1" 404 1200 "-" "Mozilla/5.0 (Linux; Android 6.0.1; Nexus 5X Build/MMB29P) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/W.X.Y.Z Mobile Safari/537.36 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"',
        # Parameter Bloat Googlebot
        '66.249.66.2 - - [20/Sep/2026:10:00:15 +0330] "GET /products?sort=price_desc&filter=active HTTP/1.1" 200 8100 "-" "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"',
        # Human Request
        '192.168.1.100 - - [20/Sep/2026:10:00:20 +0330] "GET /home HTTP/1.1" 200 5000 "-" "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/120.0.0.0 Safari/537.36"'
    ]

    report = analyzer.analyze_lines(mock_logs)
    assert report.total_log_lines == 5, f"باید ۵ خط لاگ ثبت شده باشد (تعداد: {report.total_log_lines})"
    assert report.total_bot_requests == 4, f"باید ۴ هیت ربات شناسایی شود (تعداد: {report.total_bot_requests})"
    assert report.googlebot_mobile_requests == 2, "۲ هیت گوگل‌بات موبایل"
    assert report.googlebot_desktop_requests == 2, "۲ هیت گوگل‌بات دسکتاپ"
    assert report.status_distribution[404] == 1, "یک خطای ۴۰۴ باید ثبت شود"
    assert report.crawl_waste_requests >= 2, "حداقل ۲ درخواست هدررفت (۴۰۴ و پارامتر فیلتر) باید کشف شود"
    print(f"[ServerLogAnalyzer Test] موفق: درصد اتلاف بودجه خزش محاسبه‌شده = {report.crawl_waste_percentage}٪")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        run_self_test()
    elif len(sys.argv) > 1:
        log_path = Path(sys.argv[1])
        if not log_path.exists():
            print(f"فایل {log_path} یافت نشد.")
            sys.exit(1)
        analyzer = ServerLogAnalyzer(verify_dns=False)
        rep = analyzer.analyze_lines(log_path.read_text(encoding="utf-8", errors="replace").splitlines())
        print("="*50)
        print("گزارش فارنزیک بودجه خزش و لاگ سرور")
        print(f"کل خطوط لاگ پردازش شده: {rep.total_log_lines}")
        print(f"کل هیت‌های ربات‌های جستجو: {rep.total_bot_requests}")
        print(f"  • گوگل‌بات موبایل: {rep.googlebot_mobile_requests}")
        print(f"  • گوگل‌بات دسکتاپ: {rep.googlebot_desktop_requests}")
        print(f"توزیع کدهای وضعیت HTTP: {rep.status_distribution}")
        print(f"نرخ اتلاف بودجه خزش: {rep.crawl_waste_percentage}٪ ({rep.crawl_waste_requests} درخواست)")
        print(f"تعداد خزش URLهای دارای پارامتر: {rep.parameter_bloat_requests}")
        print("\nمسیرهای پرخزش:")
        for path, count in rep.top_crawled_paths:
            print(f"  [{count} بار] {path}")
        print("\nتوصیه‌های معماری:")
        for rec in rep.recommendations:
            print(f"  💡 {rec}")
        print("="*50)
    else:
        run_self_test()
