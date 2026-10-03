# -*- coding: utf-8 -*-
"""Greek lemma tracker + natural sentence templates."""
from collections import defaultdict
import re, random

def build_all_lemmas():
    from vocab_all import load_bank
    return load_bank()

class LemmaTracker:
    @staticmethod
    def norm(s):
        return (s or "").lower().replace("ς", "σ")

    def __init__(self, bank=None):
        self.bank = bank or build_all_lemmas()
        self.by_lemma = {self.norm(x["lemma"]): x for x in self.bank}
        self.usage = defaultdict(int)
        self.introduced = set()

    def mark_text(self, text):
        toks = re.findall(r"[Α-Ωα-ωάέήίόύώΆΈΉΊΌΎΏϊΐϋΰ\-]+", text or "")
        for w in toks:
            low = self.norm(w)
            hit = None
            if low in self.by_lemma:
                hit = low
            else:
                # strip common Modern Greek endings
                for end in ("ους","εις","ων","ες","ας","ος","ης","η","ο","α","ι","υ","ω","ει","ουν","ουνε","ουμε","ετε","άνε","άτε"):
                    if len(low) > len(end) + 2 and low.endswith(end):
                        stem = low[:-len(end)]
                        for cand in (stem, stem+"ος", stem+"η", stem+"ο", stem+"ω", stem+"ώ", stem+"ας", stem+"ης"):
                            if cand in self.by_lemma:
                                hit = cand
                                break
                        if hit:
                            break
            if hit:
                self.usage[hit] += 1
                self.introduced.add(hit)

    def unused(self, cefr=None, theme=None, pos=None, limit=50):
        out = []
        for x in self.bank:
            key = self.norm(x["lemma"])
            if key in self.introduced and self.usage[key] >= 3:
                continue
            if cefr and x["cefr"] not in cefr:
                continue
            if theme and x["theme"] != theme:
                continue
            if pos and x["pos"] != pos:
                continue
            out.append(x)
            if len(out) >= limit:
                break
        out.sort(key=lambda x: self.usage[self.norm(x["lemma"])])
        return out

    def pick(self, n, cefr=None, theme=None, pos=None):
        return self.unused(cefr=cefr, theme=theme, pos=pos, limit=n)

    def sample_band(self, n, cefr=None, pos=None):
        pool = []
        for x in self.bank:
            if cefr and x["cefr"] not in cefr:
                continue
            if pos and x["pos"] != pos:
                continue
            pool.append(x)
        pool.sort(key=lambda x: (self.usage[self.norm(x["lemma"])], x["lemma"]))
        return pool[:n]

    def stats(self):
        return {
            "bank_size": len(self.bank),
            "introduced": len(self.introduced),
            "total_uses": sum(self.usage.values()),
        }

import template_guard as G

# NOTE: open slot frames used to be filled with *any* unused bank lemma in its
# dictionary form (people, places, bare verbs, adjectives without agreement,
# pseudo-lemmas with placeholder Hebrew), producing nonsense such as
# «Χρειάζομαι κόρη.», «Πόσο κοστίζει γιαγιά;», «Αυτό είναι καλός μητέρα.»,
# «Θέλω να αυξανομαι.» (= «אני רוצה לפעול/αυξα») and meta filler like
# «Ας εξετάσουμε τη λέξη «X».».  Slots are now restricted to
# template_guard.SAFE_NOUNS (concrete nouns with verified Hebrew gloss and the
# correct Greek article/case forms), each template only accepts the categories
# that make sense in it, and everything else becomes a plain vocab row
# (word = gloss) or is skipped (placeholder lemmas).  Unit content itself
# comes from the hand-written scripts/everyday_sentences.json pools.


def _plain_row_ok(u):
    lem, he = u.get("lemma") or "", u.get("he") or ""
    return bool(lem) and not G.PLACEHOLDER_RE.search(lem) and not G.HE_PLACEHOLDER_RE.search(he)


def natural_rows_for_lemma(u, rng=None):
    """Safe template rows for whitelisted nouns, otherwise the plain word row."""
    rng = rng or random.Random(hash(u["lemma"]) % 10_000)
    if G.slot_ok(u):
        tids = [t[0] for t in G.TEMPLATES if G.slot_ok(u, t[0])]
        rng.shuffle(tids)
        rows = [G.render(t, u["lemma"]) for t in tids[:3]]
        return [r for r in rows if r]
    return [(u["lemma"], u["he"])] if _plain_row_ok(u) else []


def generate_lemma_sentences(tracker, cefr=("a1",), theme=None, count=8):
    """Template sentences ONLY for whitelisted concrete nouns (see template_guard)."""
    if isinstance(cefr, str):
        cefr = (cefr,)
    unused = tracker.pick(count * 6, cefr=cefr, theme=theme) or tracker.pick(count * 6, cefr=cefr) or tracker.pick(count * 6)
    nouns = [x for x in unused if G.slot_ok(x)]
    rng = random.Random(42 + len(tracker.introduced))
    rows = []
    for n in nouns:
        if len(rows) >= count:
            break
        tids = [t[0] for t in G.TEMPLATES if G.slot_ok(n, t[0])]
        if not tids:
            continue
        row = G.render(rng.choice(tids), n["lemma"])
        if not row:
            continue
        rows.append(row)
        tracker.mark_text(row[0])
    return rows

if __name__ == "__main__":
    t = LemmaTracker()
    print("bank", t.stats())
