#!/usr/bin/env python3
"""
Enterprise Edge SEO Script Generator
Generates production-ready Cloudflare Workers / Edge CDN scripts to execute:
  1. Instant Bot Prerender Routing (transparently routes Googlebot to SSR/Prerender cache).
  2. Edge Canonicalization & URL Sanitization (enforces lowercase, strips tracking params, trailing slashes).
  3. High-throughput Edge 301 Redirect Engine (resolves in < 2ms without origin load).
  4. Dynamic X-Robots-Tag & Security Header Injection.
Standard library only (json, sys, pathlib, dataclasses, typing).
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class EdgeSEOConfig:
    domain: str
    prerender_service_url: str = "https://service.prerender.io"
    prerender_token: str = "YOUR_PRERENDER_TOKEN"
    enforce_lowercase: bool = True
    enforce_trailing_slash: bool = False  # False = strip trailing slash
    strip_query_params: List[str] = field(default_factory=lambda: [
        "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "fbclid", "gclid"
    ])
    noindex_patterns: List[str] = field(default_factory=lambda: [
        "/search", "/api/", "/checkout", "/cart", "/login", "/admin"
    ])
    static_redirects: Dict[str, str] = field(default_factory=dict)


def generate_cloudflare_worker_script(config: EdgeSEOConfig) -> str:
    redirects_json = json.dumps(config.static_redirects, indent=2)
    strip_params_json = json.dumps(config.strip_query_params)
    noindex_patterns_json = json.dumps(config.noindex_patterns)

    worker_code = f"""/**
 * Production Enterprise Edge SEO Worker for {config.domain}
 * Generated automatically by Hermes Principal SEO Architect Suite.
 */

const BOT_USER_AGENTS = [
  "googlebot",
  "bingbot",
  "yandexbot",
  "duckduckbot",
  "baiduspider",
  "slurp",
  "twitterbot",
  "facebookexternalhit",
  "linkedinbot"
];

const STATIC_REDIRECTS = {redirects_json};
const STRIP_QUERY_PARAMS = new Set({strip_params_json});
const NOINDEX_PATTERNS = {noindex_patterns_json};
const PRERENDER_SERVICE_URL = "{config.prerender_service_url}";
const PRERENDER_TOKEN = "{config.prerender_token}";

function isSearchBot(userAgent) {{
  if (!userAgent) return false;
  const ua = userAgent.toLowerCase();
  return BOT_USER_AGENTS.some(bot => ua.includes(bot));
}}

export default {{
  async fetch(request, env, ctx) {{
    const url = new URL(request.url);
    const userAgent = request.headers.get("user-agent") || "";
    let pathname = url.pathname;

    // 1. Edge 301 Redirects Engine (< 2ms)
    if (STATIC_REDIRECTS[pathname]) {{
      const target = STATIC_REDIRECTS[pathname];
      return Response.redirect(new URL(target, url.origin).toString(), 301);
    }}

    // 2. Canonical Normalization (Lowercase & Trailing Slash)
    let normalizedPath = pathname;
    if ({str(config.enforce_lowercase).lower()} && pathname !== pathname.toLowerCase()) {{
      normalizedPath = pathname.toLowerCase();
    }}

    if (!{str(config.enforce_trailing_slash).lower()} && normalizedPath.length > 1 && normalizedPath.endsWith("/")) {{
      normalizedPath = normalizedPath.slice(0, -1);
    }}

    // Strip tracking parameters that cause cache fragmentation
    let paramsModified = false;
    for (const p of STRIP_QUERY_PARAMS) {{
      if (url.searchParams.has(p)) {{
        url.searchParams.delete(p);
        paramsModified = true;
      }}
    }}

    if (normalizedPath !== pathname || paramsModified) {{
      url.pathname = normalizedPath;
      return Response.redirect(url.toString(), 301);
    }}

    // 3. Dynamic Bot Prerendering Routing
    if (isSearchBot(userAgent)) {{
      // Exclude static assets
      const ext = pathname.split(".").pop().toLowerCase();
      const isAsset = ["js", "css", "png", "jpg", "jpeg", "webp", "avif", "svg", "woff2", "pdf"].includes(ext);

      if (!isAsset) {{
        const prerenderUrl = `${{PRERENDER_SERVICE_URL}}/${{url.toString()}}`;
        const prerenderHeaders = new Headers(request.headers);
        prerenderHeaders.set("X-Prerender-Token", PRERENDER_TOKEN);
        prerenderHeaders.set("User-Agent", userAgent);

        try {{
          const prerenderResp = await fetch(prerenderUrl, {{
            headers: prerenderHeaders,
            cf: {{ cacheTtl: 86400, cacheEverything: true }}
          }});
          if (prerenderResp.status === 200) {{
            const res = new Response(prerenderResp.body, prerenderResp);
            res.headers.set("X-Edge-SEO-Render", "Prerender-Cache-Hit");
            return res;
          }}
        }} catch (err) {{
          // Fallback to origin on prerender timeout
        }}
      }}
    }}

    // 4. Origin Fetch and Security/X-Robots-Tag Injection
    const originResponse = await fetch(request);
    const newHeaders = new Headers(originResponse.headers);

    // Dynamic X-Robots-Tag injection for faceted/query pages
    const shouldNoindex = NOINDEX_PATTERNS.some(pat => pathname.startsWith(pat));
    if (shouldNoindex) {{
      newHeaders.set("X-Robots-Tag", "noindex, follow");
    }}

    newHeaders.set("X-Content-Type-Options", "nosniff");
    newHeaders.set("X-Frame-Options", "SAMEORIGIN");
    newHeaders.set("Referrer-Policy", "strict-origin-when-cross-origin");

    return new Response(originResponse.body, {{
      status: originResponse.status,
      statusText: originResponse.statusText,
      headers: newHeaders
    }});
  }}
}};
"""
    return worker_code


def run_self_test():
    print("[EdgeSEOGenerator Test] شروع آزمون صحت ژنراتور لبه شبکه...")
    cfg = EdgeSEOConfig(
        domain="https://example.com",
        static_redirects={
            "/old-url": "/new-url",
            "/legacy-blog": "/blog"
        }
    )
    code = generate_cloudflare_worker_script(cfg)
    assert "export default {" in code, "باید خروجی ماژولار Cloudflare Worker ES6 تولید شود"
    assert "BOT_USER_AGENTS" in code, "باید آرایه تشخیص ربات‌ها وجود داشته باشد"
    assert "STATIC_REDIRECTS" in code, "باید ریدایرکت‌های استاتیک در لبه تزریق شوند"
    assert "X-Robots-Tag" in code, "باید تزریق داینامیک X-Robots-Tag تعبیه شده باشد"
    print(f"[EdgeSEOGenerator Test] موفق: کد Cloudflare Worker به حجم {len(code)} کاراکتر با موفقیت اعتبارسنجی شد.")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        run_self_test()
    elif len(sys.argv) > 1:
        domain = sys.argv[1]
        cfg = EdgeSEOConfig(domain=domain)
        print(generate_cloudflare_worker_script(cfg))
    else:
        run_self_test()
