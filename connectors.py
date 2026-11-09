#!/usr/bin/env python3
"""
Target Connectors & Crawler for Autonomous SEO Agent
Supports:
  1. Local Codebase / Static Site Connector (scans HTML, Next.js exports, Astro, templates).
  2. Live Web Crawler Connector (recursively discovers and fetches internal links up to max_pages/depth).
  3. WordPress REST API Connector (fetches posts, pages, and updates SEO metadata via API).
Standard library only (urllib, re, json, pathlib, dataclasses, typing).
"""

from __future__ import annotations

import collections
import json
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


@dataclass
class PageArtifact:
    url: str
    identifier: str  # File path or remote URL or post_id
    raw_html: str
    title: str = ""
    is_local: bool = True
    metadata: Dict[str, str] = field(default_factory=dict)


class SimpleLinkExtractor(HTMLParser):
    def __init__(self, base_url: str):
        super().__init__()
        self.base_url = base_url
        self.links: Set[str] = set()
        self.title: str = ""
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, str | None]]):
        tag_lower = tag.lower()
        attr_dict = {k.lower(): (v or "") for k, v in attrs}
        if tag_lower == "a":
            href = attr_dict.get("href", "")
            if href and not href.startswith("#") and not href.startswith("javascript:") and not href.startswith("mailto:"):
                resolved = urllib.parse.urljoin(self.base_url, href)
                # Strip fragments
                clean_url = urllib.parse.urldefrag(resolved)[0]
                self.links.add(clean_url)
        elif tag_lower == "title":
            self._in_title = True

    def handle_endtag(self, tag: str):
        if tag.lower() == "title":
            self._in_title = False

    def handle_data(self, data: str):
        if self._in_title:
            self.title += data


class LocalFilesConnector:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir

    def collect_artifacts(self) -> List[PageArtifact]:
        artifacts: List[PageArtifact] = []
        html_files = sorted(list(self.base_dir.rglob("*.html")))
        for f in html_files:
            content = f.read_text(encoding="utf-8", errors="replace")
            # Extract title quickly
            m = re.search(r'<title>(.*?)</title>', content, re.IGNORECASE | re.DOTALL)
            title = m.group(1).strip() if m else f.stem
            artifacts.append(PageArtifact(
                url=f"file://{f.resolve()}",
                identifier=str(f.resolve()),
                raw_html=content,
                title=title,
                is_local=True
            ))
        return artifacts

    def commit_patch(self, identifier: str, new_content: str, create_backup: bool = True) -> bool:
        path = Path(identifier)
        if not path.exists():
            return False
        if create_backup:
            backup_dir = path.parent / ".seo_backup"
            backup_dir.mkdir(exist_ok=True)
            backup_file = backup_dir / f"{path.name}.bak"
            backup_file.write_text(path.read_text(encoding="utf-8", errors="replace"), encoding="utf-8")
        path.write_text(new_content, encoding="utf-8")
        return True


class LiveWebCrawlerConnector:
    def __init__(self, start_url: str, max_pages: int = 15, timeout: int = 10):
        self.start_url = start_url
        self.max_pages = max_pages
        self.timeout = timeout
        parsed = urllib.parse.urlparse(start_url)
        self.domain = parsed.netloc

    def crawl(self) -> List[PageArtifact]:
        visited: Set[str] = set()
        queue: collections.deque[str] = collections.deque([self.start_url])
        artifacts: List[PageArtifact] = []

        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; AutonomousSEOAgent/1.0; +https://example.com/bot)"
        }

        while queue and len(artifacts) < self.max_pages:
            current_url = queue.popleft()
            if current_url in visited:
                continue
            visited.add(current_url)

            try:
                req = urllib.request.Request(current_url, headers=headers)
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    c_type = resp.headers.get("content-type", "").lower()
                    if "text/html" not in c_type:
                        continue
                    raw_bytes = resp.read()
                    charset = resp.headers.get_content_charset() or "utf-8"
                    html_content = raw_bytes.decode(charset, errors="replace")

                parser = SimpleLinkExtractor(current_url)
                parser.feed(html_content)

                artifacts.append(PageArtifact(
                    url=current_url,
                    identifier=current_url,
                    raw_html=html_content,
                    title=parser.title.strip(),
                    is_local=False
                ))

                for link in parser.links:
                    parsed_link = urllib.parse.urlparse(link)
                    if parsed_link.netloc == self.domain and link not in visited:
                        queue.append(link)
            except Exception:
                continue

        return artifacts


class WordPressRESTConnector:
    """
    Connects to WordPress REST API (/wp-json/wp/v2/posts and /pages).
    Supports fetching and patching meta/content with Application Passwords or basic auth.
    """
    def __init__(self, site_url: str, auth_user: Optional[str] = None, auth_pass: Optional[str] = None):
        self.site_url = site_url.rstrip("/")
        self.auth_user = auth_user
        self.auth_pass = auth_pass

    def fetch_posts(self, count: int = 10) -> List[PageArtifact]:
        api_url = f"{self.site_url}/wp-json/wp/v2/posts?per_page={count}&_embed"
        req = urllib.request.Request(api_url, headers={"User-Agent": "AutonomousSEOAgent/1.0"})
        if self.auth_user and self.auth_pass:
            import base64
            token = base64.b64encode(f"{self.auth_user}:{self.auth_pass}".encode()).decode()
            req.add_header("Authorization", f"Basic {token}")

        try:
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception:
            return []

        artifacts: List[PageArtifact] = []
        for post in data:
            post_id = str(post.get("id"))
            link = post.get("link", "")
            title = post.get("title", {}).get("rendered", "")
            content = post.get("content", {}).get("rendered", "")
            artifacts.append(PageArtifact(
                url=link,
                identifier=post_id,
                raw_html=content,
                title=title,
                is_local=False,
                metadata={"post_id": post_id}
            ))
        return artifacts


def run_self_test():
    print("[TargetConnectors Test] شروع آزمون صحت کانکتورها...")
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        p1 = tmp_path / "page1.html"
        p2 = tmp_path / "page2.html"
        p1.write_text("<html><head><title>صفحه اول</title></head><body><p>تست</p></body></html>", encoding="utf-8")
        p2.write_text("<html><head><title>صفحه دوم</title></head><body><p>تست ۲</p></body></html>", encoding="utf-8")

        conn = LocalFilesConnector(tmp_path)
        arts = conn.collect_artifacts()
        assert len(arts) == 2, f"باید ۲ فایل محلی استخراج شود (تعداد: {len(arts)})"
        assert arts[0].title in ("صفحه اول", "صفحه دوم")

        # Test patch with backup
        res = conn.commit_patch(str(p1), "<html><head><title>صفحه جدید</title></head></html>", create_backup=True)
        assert res, "پچ باید با موفقیت اعمال شود"
        assert (p1.parent / ".seo_backup" / "page1.html.bak").exists(), "فایل بک‌آپ باید ایجاد شده باشد"

    print("[TargetConnectors Test] موفق: کانکتور محلی و مکانیسم بک‌آپ با موفقیت تایید شد.")


if __name__ == "__main__":
    run_self_test()
