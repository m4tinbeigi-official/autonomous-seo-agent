#!/usr/bin/env python3
"""
Entity Knowledge Graph Auditor & Unified Schema.org @graph Engine
Features:
  1. Semantic Triplet Extraction (Subject-Predicate-Object) from Persian and English texts.
  2. Entity Salience & Disambiguation auditor (Wikidata sameAs, Organization anchoring).
  3. Unified Schema.org @graph Validator (replaces disconnected fragmented schemas with a linked entity mesh).
  4. Enterprise JSON-LD Graph Generator with automatic node anchoring (@id references).
Standard library only (re, json, sys, dataclasses, typing).
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


# Known entity patterns (Tech, Platforms, Protocols, Concepts)
RECOGNIZED_ENTITIES = {
    "google": ("Google", "https://www.wikidata.org/wiki/Q95"),
    "گوگل": ("Google", "https://www.wikidata.org/wiki/Q95"),
    "next.js": ("Next.js", "https://www.wikidata.org/wiki/Q110852077"),
    "نکست": ("Next.js", "https://www.wikidata.org/wiki/Q110852077"),
    "react": ("React", "https://www.wikidata.org/wiki/Q193988"),
    "پایتون": ("Python", "https://www.wikidata.org/wiki/Q28865"),
    "python": ("Python", "https://www.wikidata.org/wiki/Q28865"),
    "nginx": ("Nginx", "https://www.wikidata.org/wiki/Q27339"),
    "cloudflare": ("Cloudflare", "https://www.wikidata.org/wiki/Q11053"),
    "linux": ("Linux", "https://www.wikidata.org/wiki/Q388"),
    "لینوکس": ("Linux", "https://www.wikidata.org/wiki/Q388"),
    "سئو": ("Search Engine Optimization", "https://www.wikidata.org/wiki/Q180711"),
    "seo": ("Search Engine Optimization", "https://www.wikidata.org/wiki/Q180711"),
}

COMMON_RELATIONS_FA = [
    (r"مبتنی\s+بر", "basedOn"),
    (r"متصل\s+به", "connectedTo"),
    (r"پشتیبانی\s+از", "supports"),
    (r"توسعه\s+داده\s+شده\s+توسط", "developedBy"),
    (r"بهینه‌سازی\s+برای", "optimizesFor"),
    (r"کاهش\s+می‌دهد", "reduces"),
    (r"افزایش\s+می‌دهد", "increases"),
    (r"پیکربندی\s+روی", "configuredOn"),
]


@dataclass
class SemanticTriplet:
    subject: str
    predicate: str
    object_entity: str
    confidence: float


@dataclass
class EntityGraphReport:
    extracted_entities: List[Dict[str, str]]
    semantic_triplets: List[SemanticTriplet]
    has_unified_graph_schema: bool
    schema_nodes_count: int
    missing_entity_links: List[str]
    graph_connectivity_score: int  # 0 to 100
    recommendations: List[str] = field(default_factory=list)


def extract_entities_and_triplets(text: str) -> Tuple[List[Dict[str, str]], List[SemanticTriplet]]:
    norm_text = text.replace("ي", "ی").replace("ك", "ک").replace("—", " ").replace("\u200c", "")
    
    found_entities: Dict[str, Dict[str, str]] = {}
    for kw, (canonical, wikidata) in RECOGNIZED_ENTITIES.items():
        if re.search(r'\b' + re.escape(kw) + r'\b', norm_text, re.IGNORECASE):
            found_entities[canonical] = {
                "name": canonical,
                "wikidata_uri": wikidata
            }

    # Extract triplets based on heuristic grammatical clauses
    triplets: List[SemanticTriplet] = []
    clauses = re.split(r'[\.\n،؛]+', text)
    
    for clause in clauses:
        clause_norm = clause.replace("ي", "ی").replace("ك", "ک").replace("\u200c", "")
        # Find if two recognized entities appear in the same clause with a relation
        entities_in_clause = [
            canonical for kw, (canonical, _) in RECOGNIZED_ENTITIES.items()
            if re.search(r'\b' + re.escape(kw) + r'\b', clause_norm, re.IGNORECASE)
        ]
        entities_in_clause = list(dict.fromkeys(entities_in_clause))  # dedupe preserve order

        if len(entities_in_clause) >= 2:
            subj = entities_in_clause[0]
            obj = entities_in_clause[1]
            pred = "relatesTo"
            for rel_pat, rel_name in COMMON_RELATIONS_FA:
                if re.search(rel_pat, clause_norm):
                    pred = rel_name
                    break
            triplets.append(SemanticTriplet(subject=subj, predicate=pred, object_entity=obj, confidence=0.85))

    return list(found_entities.values()), triplets


class JSONLDGraphParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.raw_scripts: List[str] = []
        self._in_script = False
        self._buf = ""

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, str | None]]):
        attr_dict = {k.lower(): (v or "") for k, v in attrs}
        if tag.lower() == "script" and attr_dict.get("type", "").lower() == "application/ld+json":
            self._in_script = True
            self._buf = ""

    def handle_endtag(self, tag: str):
        if tag.lower() == "script" and self._in_script:
            self._in_script = False
            if self._buf.strip():
                self.raw_scripts.append(self._buf.strip())

    def handle_data(self, data: str):
        if self._in_script:
            self._buf += data


def audit_entity_graph(html_or_text: str) -> EntityGraphReport:
    parser = JSONLDGraphParser()
    parser.feed(html_or_text)

    has_unified_graph = False
    schema_nodes = 0
    missing_links: List[str] = []
    recommendations: List[str] = []

    for raw in parser.raw_scripts:
        try:
            data = json.loads(raw)
            if isinstance(data, dict):
                if "@graph" in data and isinstance(data["@graph"], list):
                    has_unified_graph = True
                    nodes = data["@graph"]
                    schema_nodes += len(nodes)
                    
                    # Verify @id interconnection
                    node_ids = {n.get("@id") for n in nodes if isinstance(n, dict) and "@id" in n}
                    for n in nodes:
                        if not isinstance(n, dict):
                            continue
                        ntype = n.get("@type")
                        if ntype == "WebPage" and "isPartOf" not in n:
                            missing_links.append("گره WebPage فاقد ارجاع isPartOf به @id سایت مرکزی (WebSite) است.")
                        if ntype in ("Article", "Product") and "publisher" not in n:
                            missing_links.append(f"گره {ntype} فاقد ارجاع ناشر (publisher) به @id سازمان (Organization) است.")
        except Exception:
            pass

    entities, triplets = extract_entities_and_triplets(html_or_text)

    score = 0
    if len(entities) >= 3:
        score += 35
    elif len(entities) > 0:
        score += 20
    else:
        recommendations.append("هیچ موجودیت شناخته‌شده‌ای در گراف مفهومی صفحه ثبت نشد؛ صفحه نیازمند شفاف‌سازی هسته موضوعی است.")

    if len(triplets) >= 1:
        score += 25
    else:
        recommendations.append("سه‌گانه‌های معنایی فاعل-رابطه-مفعول در متن یافت نشد؛ جملات باید گزاره‌های روشن و قطعی بین موجودیت‌ها بسازند.")

    if has_unified_graph:
        score += 40
        if missing_links:
            score -= (len(missing_links) * 10)
    else:
        recommendations.append("صفحه از اسکیماهای پراکنده استفاده می‌کند؛ کل ساختار باید در یک گراف یکپارچه JSON-LD با شناسه @id به هم متصل گردند.")

    score = max(0, min(100, score))

    return EntityGraphReport(
        extracted_entities=entities,
        semantic_triplets=triplets,
        has_unified_graph_schema=has_unified_graph,
        schema_nodes_count=schema_nodes,
        missing_entity_links=missing_links,
        graph_connectivity_score=score,
        recommendations=recommendations
    )


def generate_enterprise_jsonld_graph(
    domain: str,
    page_url: str,
    page_title: str,
    page_description: str,
    brand_name: str,
    logo_url: str,
    author_name: str,
    same_as_links: List[str]
) -> Dict[str, Any]:
    """
    Generates a linked multi-entity Schema.org @graph according to enterprise standards.
    """
    org_id = f"{domain}/#organization"
    site_id = f"{domain}/#website"
    page_id = f"{page_url}#webpage"
    article_id = f"{page_url}#article"
    author_id = f"{domain}/#/schema/person/{abs(hash(author_name))}"

    return {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "Organization",
                "@id": org_id,
                "name": brand_name,
                "url": domain,
                "logo": {
                    "@type": "ImageObject",
                    "@id": f"{domain}/#logo",
                    "inLanguage": "fa-IR",
                    "url": logo_url
                },
                "sameAs": same_as_links
            },
            {
                "@type": "WebSite",
                "@id": site_id,
                "url": domain,
                "name": brand_name,
                "inLanguage": "fa-IR",
                "publisher": {"@id": org_id}
            },
            {
                "@type": "WebPage",
                "@id": page_id,
                "url": page_url,
                "name": page_title,
                "isPartOf": {"@id": site_id},
                "inLanguage": "fa-IR",
                "description": page_description,
                "breadcrumb": {
                    "@type": "BreadcrumbList",
                    "itemListElement": [
                        {"@type": "ListItem", "position": 1, "name": "صفحه اصلی", "item": domain},
                        {"@type": "ListItem", "position": 2, "name": page_title, "item": page_url}
                    ]
                }
            },
            {
                "@type": "Article",
                "@id": article_id,
                "isPartOf": {"@id": page_id},
                "author": {
                    "@type": "Person",
                    "@id": author_id,
                    "name": author_name
                },
                "headline": page_title,
                "mainEntityOfPage": {"@id": page_id},
                "publisher": {"@id": org_id},
                "inLanguage": "fa-IR"
            }
        ]
    }


def run_self_test():
    print("[EntityGraphAuditor Test] شروع آزمون اعتبارسنجی گراف موجودیت‌ها...")
    
    text = "پروژه Next.js مبتنی بر React است و سئو سرور را با پایتون بهینه‌سازی می‌کند."
    entities, triplets = extract_entities_and_triplets(text)
    assert len(entities) >= 3, f"باید حداقل ۳ موجودیت شناسایی شوند (تعداد: {len(entities)})"
    assert len(triplets) >= 1, "باید حداقل یک سه‌گانه معنایی استخراج شود"

    # Test enterprise graph generation
    graph = generate_enterprise_jsonld_graph(
        domain="https://example.com",
        page_url="https://example.com/vps-seo",
        page_title="راهنمای سئو سرور",
        page_description="راهنمای جامع پیکربندی سرور",
        brand_name="سازمان نمونه",
        logo_url="https://example.com/logo.png",
        author_name="ریک سانچز",
        same_as_links=["https://twitter.com/example", "https://linkedin.com/company/example"]
    )
    nodes = graph["@graph"]
    assert len(nodes) == 4, "باید ۴ گره متصل در گراف ایجاد شود"
    assert nodes[2]["isPartOf"]["@id"] == "https://example.com/#website", "پیوند گراف بین WebPage و WebSite باید برقرار باشد"
    
    # Audit rendered HTML containing graph
    html_with_graph = f"<html><head><script type=\"application/ld+json\">{json.dumps(graph)}</script></head><body>{text}</body></html>"
    rep = audit_entity_graph(html_with_graph)
    assert rep.has_unified_graph_schema, "باید وجود گراف یکپارچه را تایید کند"
    assert rep.graph_connectivity_score >= 80, f"نمره اتصال گراف باید بالای ۸۰ باشد (نمره: {rep.graph_connectivity_score})"
    print(f"[EntityGraphAuditor Test] موفق: نمره همبستگی گراف = {rep.graph_connectivity_score} / ۱۰۰، تعداد سه‌گانه‌ها = {len(rep.semantic_triplets)}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        run_self_test()
    elif len(sys.argv) > 1:
        src = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")
        rep = audit_entity_graph(src)
        print("="*50)
        print("گزارش ممیزی گراف دانش و موجودیت‌های سئو")
        print(f"نمره همبستگی گراف موجودیت: {rep.graph_connectivity_score} / ۱۰۰")
        print(f"آیا اسکیما به صورت گراف یکپارچه متصل است؟ {rep.has_unified_graph_schema}")
        print(f"تعداد گره‌های شناسنامه‌دار اسکیما: {rep.schema_nodes_count}")
        print("\nموجودیت‌های استخراج‌شده در گراف دانش:")
        for ent in rep.extracted_entities:
            print(f"  • {ent['name']} -> {ent['wikidata_uri']}")
        print("\nسه‌گانه‌های معنایی کشف‌شده:")
        for t in rep.semantic_triplets:
            print(f"  ⟨{t.subject}⟩ --[{t.predicate}]--> ⟨{t.object_entity}⟩ (اطمینان: {t.confidence})")
        if rep.missing_entity_links:
            print("\nنقص در پیوندهای داخلی گراف:")
            for m in rep.missing_entity_links:
                print(f"  ⚠️  {m}")
        if rep.recommendations:
            print("\nتوصیه‌های ارتقای اعتبار موجودیت:")
            for r in rep.recommendations:
                print(f"  💡 {r}")
        print("="*50)
    else:
        run_self_test()
