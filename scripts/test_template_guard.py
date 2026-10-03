# -*- coding: utf-8 -*-
"""Dry-run the curriculum generator in memory (no files written) and assert
that it emits no legacy slot-template nonsense.  python3 scripts/test_template_guard.py"""
import os, sys, collections
sys.path.insert(0, os.path.dirname(__file__))
import template_guard as G
import generate_curriculum as GC
from vocab_all import load_bank
from vocab_bank import LemmaTracker, generate_lemma_sentences, natural_rows_for_lemma
import purge_template_sentences as PT

bank = load_bank()
by_lemma = {}
for x in bank:
    by_lemma.setdefault(G.norm(x["lemma"]), x)
SAFE = G.safe_forms()
CURATED = PT.curated_set()  # hand-written seeds / packs / everyday pools
bad, rows_seen = collections.Counter(), 0


def check(ru, he):
    global rows_seen
    rows_seen += 1
    if ru in SAFE or ru in CURATED:
        return
    c = G.classify_legacy(ru, he, by_lemma)
    if c:
        bad[(ru, he, c[1])] += 1
    sentence = len(ru.split()) > 1  # "(מושלם)" is a fine gloss for a single verb
    if (sentence and G.HE_BROKEN_RE.search(he or "")) or G.HE_PLACEHOLDER_RE.search(he or ""):
        bad[(ru, he, "broken/placeholder hebrew")] += 1


tracker = LemmaTracker(bank)
for _ in range(60):
    for cefr in (("a1", "a2"), ("b1", "b2"), ("c1", "c2")):
        for ru, he in generate_lemma_sentences(tracker, cefr=cefr, count=8):
            check(ru, he)
for u in bank:
    for ru, he in natural_rows_for_lemma(u):
        check(ru, he)
units = list(GC.seeds_a1()) + [it for lv in ("A2", "B1", "B2", "C1", "C2") for it in GC.seeds_level(lv)]
for uid, th, tr, curated, tip, trows in units:
    for ru, he in GC.curated_plus_vocab(LemmaTracker(bank), curated, ("a1", "a2", "b1"), None, trows, uid=uid):
        check(ru, he)
print("rows checked:", rows_seen, "| bad:", sum(bad.values()))
for k, v in list(bad.items())[:20]:
    print("  BAD", k, v)
sys.exit(1 if bad else 0)
