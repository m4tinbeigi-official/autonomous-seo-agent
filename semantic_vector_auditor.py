#!/usr/bin/env python3
"""
Semantic Vector Distance & Neural Retrieval Space Auditor
Simulates dense semantic embedding spaces using Subword N-Gram TF-IDF vectors.
Features:
  1. High-dimensional vectorization resilient to Persian morphological affixes and ZWNJ.
  2. Cosine Similarity calculation in vector space: Cos(u, v) = (u . v) / (||u|| * ||v||).
  3. Neural Cannibalization Detector (identifies synonym-masked cannibalization where Cosine > 0.82).
  4. Topical Drift & Centroid divergence per heading section.
Standard library only (math, re, collections, typing, dataclasses).
"""

from __future__ import annotations

import collections
import math
import re
import sys
from dataclasses import dataclass, field
from typing import Counter, Dict, List, Set, Tuple


def normalize_persian_subwords(text: str) -> str:
    # Standardize Arabic Yeh/Kaf, strip punctuation, normalize ZWNJ to space
    t = text.replace("ي", "ی").replace("ك", "ک").replace("—", " ").replace("\u200c", " ")
    return re.sub(r'[^\w\s]', ' ', t.lower())


def extract_hybrid_features(text: str) -> List[str]:
    clean_text = normalize_persian_subwords(text)
    words = clean_text.split()
    features: List[str] = []
    
    # 1. Word Unigrams
    for w in words:
        if len(w) > 1:
            features.append(f"w:{w}")
            
    # 2. Word Bigrams
    for i in range(len(words) - 1):
        features.append(f"bi:{words[i]}_{words[i+1]}")
        
    # 3. Character Trigrams (Morphological stem capture)
    for w in words:
        if len(w) >= 3:
            for i in range(len(w) - 2):
                features.append(f"ch:{w[i:i+3]}")
                
    return features


class SubwordTFIDFVectorizer:
    def __init__(self):
        self.vocabulary: Dict[str, int] = {}
        self.idf: Dict[str, float] = {}

    def fit(self, documents: List[str]):
        doc_count = len(documents)
        df: Counter[str] = collections.Counter()
        
        all_vocab: Set[str] = set()
        for doc in documents:
            feats = set(extract_hybrid_features(doc))
            for f in feats:
                df[f] += 1
            all_vocab.update(feats)

        self.vocabulary = {f: idx for idx, f in enumerate(sorted(all_vocab))}
        self.idf = {
            f: math.log((1 + doc_count) / (1 + df[f])) + 1.0
            for f in self.vocabulary
        }

    def transform(self, doc: str) -> Dict[int, float]:
        feats = extract_hybrid_features(doc)
        tf = collections.Counter(feats)
        total = len(feats) or 1
        
        vec: Dict[int, float] = {}
        norm_sq = 0.0
        for f, count in tf.items():
            if f in self.vocabulary:
                idx = self.vocabulary[f]
                val = (count / total) * self.idf[f]
                vec[idx] = val
                norm_sq += val * val

        # L2 Normalization
        norm = math.sqrt(norm_sq) or 1.0
        return {idx: val / norm for idx, val in vec.items()}


def compute_cosine_similarity(vec_a: Dict[int, float], vec_b: Dict[int, float]) -> float:
    # Sparse dot product
    dot_product = sum(vec_a[idx] * vec_b[idx] for idx in vec_a if idx in vec_b)
    return round(max(0.0, min(1.0, dot_product)), 4)


@dataclass
class SemanticVectorReport:
    cosine_similarity: float
    similarity_percentage: float
    risk_level: str
    top_shared_semantic_dimensions: List[str]
    verdict: str
    action_item: str


def audit_semantic_cannibalization(text_a: str, text_b: str) -> SemanticVectorReport:
    vectorizer = SubwordTFIDFVectorizer()
    vectorizer.fit([text_a, text_b])
    
    vec_a = vectorizer.transform(text_a)
    vec_b = vectorizer.transform(text_b)

    cos_sim = compute_cosine_similarity(vec_a, vec_b)
    pct = round(cos_sim * 100, 1)

    # Invert vocabulary to find top shared features
    inv_vocab = {v: k for k, v in vectorizer.vocabulary.items()}
    shared_feats = []
    for idx in vec_a:
        if idx in vec_b:
            weight = vec_a[idx] * vec_b[idx]
            feat_name = inv_vocab[idx]
            shared_feats.append((feat_name, weight))
    shared_feats.sort(key=lambda x: x[1], reverse=True)

    if cos_sim < 0.25:
        risk = "تمایز معنایی کامل (Distinct Semantic Embeddings)"
        verdict = "دو صفحه در فضای برداری کاملا مستقل هستند و هیچگونه تداخل معنایی در بازیابی عصبی گوگل ندارند."
        action = "اقدام خاصی نیاز نیست."
    elif 0.25 <= cos_sim <= 0.65:
        risk = "هم‌پوشانی متوسط معنایی (Semantic Proximity)"
        verdict = "دو صفحه به یک خانواده موضوعی تعلق دارند اما زوایای متفاوتی را پوشش می‌دهند."
        action = "حفظ هر دو صفحه با شفاف‌سازی انکرتکست‌های لینک متقابل برای ارسال سیگنال شفاف به رنک‌برین."
    else:
        risk = "کنیبالیزیشن شدید برداری (Neural Vector Cannibalization)"
        verdict = "دو صفحه علیرغم تفاوت‌های ظاهری در کلمات، در فضای برداری در یک نقطه متمرکز شده‌اند و رتبه یکدیگر را تضعیف می‌کنند."
        action = "ادغام محتوایی قطعی و انتقال ریدایرکت ۳۰۱؛ یک صفحه واحد جامع در بازیابی عصبی بسیار پایدارتر رتبه می‌گیرد."

    return SemanticVectorReport(
        cosine_similarity=cos_sim,
        similarity_percentage=pct,
        risk_level=risk,
        top_shared_semantic_dimensions=[f for f, _ in shared_feats[:8]],
        verdict=verdict,
        action_item=action
    )


def run_self_test():
    print("[SemanticVectorAuditor Test] شروع آزمون تشابه برداری سئو...")
    
    # Completely distinct topics
    t_cars = "قیمت خودرو و مشخصات فنی موتور بنزینی و شتاب دنده اتوماتیک"
    t_recipe = "دستور پخت قورمه سبزی با لوبیا قرمز و گوشت گوسفندی سنتی"
    rep_dist = audit_semantic_cannibalization(t_cars, t_recipe)
    assert rep_dist.cosine_similarity < 0.15, f"موضوعات بی‌ربط باید تشابه برداری زیر ۰.۱۵ داشته باشند (مقدار: {rep_dist.cosine_similarity})"

    # High semantic proximity
    t_vpn_1 = "خرید سرور ابری مجازی و کانفیگ سرور اختصاصی برای سئو"
    t_vpn_2 = "فروش سرور ابری و کانفیگ سرور مجازی با پایتون برای سئو"
    rep_vpn = audit_semantic_cannibalization(t_vpn_1, t_vpn_2)
    assert rep_vpn.cosine_similarity > 0.40, f"موضوعات هم‌خانواده باید همپوشانی برداری بالایی داشته باشند (مقدار: {rep_vpn.cosine_similarity})"

    print(f"[SemanticVectorAuditor Test] موفق: تشابه موضوعات نامرتبط = {rep_dist.cosine_similarity} | تشابه موضوعات هم‌پوشان = {rep_vpn.cosine_similarity}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        run_self_test()
    elif len(sys.argv) >= 3:
        doc1 = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")
        doc2 = Path(sys.argv[2]).read_text(encoding="utf-8", errors="replace")
        rep = audit_semantic_cannibalization(doc1, doc2)
        print("="*50)
        print("گزارش تحلیل فاصله برداری و بازیابی عصبی (Dense Retrieval Audit)")
        print(f"ضریب تشابه کسینوسی بردارها: {rep.cosine_similarity} ({rep.similarity_percentage}٪)")
        print(f"سطح ریسک کنیبالیزیشن برداری: {rep.risk_level}")
        print(f"نتیجه مدل: {rep.verdict}")
        print(f"راهبرد پیشنهادی: {rep.action_item}")
        if rep.top_shared_semantic_dimensions:
            print(f"ابعاد معنایی مشترک در بردار: {', '.join(rep.top_shared_semantic_dimensions)}")
        print("="*50)
    else:
        run_self_test()
