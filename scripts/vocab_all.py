# -*- coding: utf-8 -*-
"""Merged Modern Greek lemma bank loader."""
import re

def load_bank():
    from vocab_entries import ENTRIES
    items = []
    seen = set()
    def add(lem, he, pos, theme, cefr):
        lem = lem.strip()
        k = lem.lower()
        if not k or k in seen:
            return
        if re.search(r"[A-Za-zА-Яа-яЁё]", lem):
            return
        if not re.search(r"[Α-Ωα-ωάέήίόύώΆΈΉΊΌΎΏϊΐϋΰ]", lem):
            return
        if re.search(r"[Α-Ωα-ωάέήίόύώ]", he or ""):
            # allow Greek in he only if pure — drop mixed corrupt
            if re.search(r"[\u0590-\u05FF]", he or ""):
                pass  # has Hebrew too, ok-ish
            else:
                return
        seen.add(k)
        items.append({"lemma": lem, "he": he, "pos": pos, "theme": theme, "cefr": cefr})
    for t in ENTRIES:
        add(*t)
    return items

if __name__ == "__main__":
    b = load_bank()
    print(len(b))
