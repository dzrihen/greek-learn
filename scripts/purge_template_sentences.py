# -*- coding: utf-8 -*-
"""(Modern Greek; target text lives in the `ru` field like in the Russian app.)
Find nonsense slot-template sentences produced by the old generator and
replace them (in place, keeping every lesson's length and exercise types)
with natural everyday sentences for the unit topic, hand-written in
scripts/everyday_sentences.json.

Usage: python3 scripts/purge_template_sentences.py [--dry-run] [--report out.json]
Idempotent: a second run finds nothing to replace.

Mapping: each distinct bad sentence of a unit gets its own pool sentence while
the pool lasts; when a unit had more bad sentences than pool rows, a pool row
is reused only in a *different* lesson of the same unit (never twice in one
lesson), so lessons stay free of duplicates.
"""
import ast, json, re, sys, random, collections
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA = ROOT / "data"
sys.path.insert(0, str(HERE))

import template_guard as G
from exhelpers import words_of, DISTRACTORS_RU, WRONG_POOL
from vocab_all import load_bank

POOLS = json.loads((HERE / "everyday_sentences.json").read_text(encoding="utf-8"))
LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"]
CURATED_SOURCES = ["generate_curriculum.py"]
# fixed UI strings (default dialogue distractors etc.) used by the exercise builders
LITERAL_SOURCES = ["exhelpers.py", "inject_practical_path.py", "content_lib.py"]
TARGET_SCRIPT = re.compile(r"[Α-Ωα-ωά-ώΆ-Ώϊΐϋΰ]")
P1_RE = re.compile(r"^(/\*.*?\*/\n)window\.RL_LEVEL_(\w+)=(.*);\n$", re.S)
P2_RE = re.compile(r"^(/\*.*?\*/\n)\(function\(\)\{var L=window\.RL_LEVEL_(\w+);if\(!L\)return;L\.units=L\.units\.concat\((.*)\);\}\)\(\);\n$", re.S)
HEB = re.compile(r"[\u0590-\u05FF]")


def load_parts(level):
    low = level.lower()
    s1 = (DATA / f"{low}-part1.js").read_text(encoding="utf-8")
    m1 = P1_RE.match(s1)
    s2 = (DATA / f"{low}-part2.js").read_text(encoding="utf-8")
    m2 = P2_RE.match(s2)
    if not m1 or not m2:
        raise SystemExit(f"cannot parse {level}")
    return (m1.group(1), json.loads(m1.group(3))), (m2.group(1), json.loads(m2.group(3)))


def save_parts(level, p1, p2):
    low = level.lower()
    (DATA / f"{low}-part1.js").write_text(
        p1[0] + f"window.RL_LEVEL_{level}=" + json.dumps(p1[1], ensure_ascii=False, separators=(",", ":")) + ";\n",
        encoding="utf-8")
    (DATA / f"{low}-part2.js").write_text(
        p2[0] + f"(function(){{var L=window.RL_LEVEL_{level};if(!L)return;L.units=L.units.concat("
        + json.dumps(p2[1], ensure_ascii=False, separators=(",", ":")) + ");})();\n",
        encoding="utf-8")


def curated_set():
    """Hand-written rows: seed tuples in the generators, practical packs, pools."""
    cur = set()
    for f in CURATED_SOURCES:
        p = HERE / f
        if not p.exists():
            continue
        src = p.read_text(encoding="utf-8")
        for m in re.finditer(r'\(\s*"((?:[^"\\]|\\.)+)"\s*,\s*"((?:[^"\\]|\\.)+)"', src):
            if HEB.search(m.group(2)):
                cur.add(m.group(1))
    for f in LITERAL_SOURCES:
        p = HERE / f
        if p.exists():
            for node in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
                v = getattr(node, "value", None)
                if isinstance(node, ast.Constant) and isinstance(v, str) \
                        and TARGET_SCRIPT.search(v) and not HEB.search(v):
                    cur.add(v)
    pp = HERE / "_practical_packs.json"  # local (gitignored) generator input
    packs = json.loads(pp.read_text(encoding="utf-8")) if pp.exists() else {}
    for rows in packs.values():
        for r in rows:
            cur.add(r[0])
    for rows in POOLS.values():
        for r in rows:
            cur.add(r[0])
    return cur


def nhe(s):
    return re.sub(r"[\s\.\?!,״\"']+", " ", s or "").strip()


def ex_rows(e):
    """(target, he) phrase rows carried by an exercise."""
    out = []
    t = e.get("type")
    if t in ("speak_repeat", "sentence_build", "translate_he_ru") and e.get("ru"):
        out.append((e["ru"], e.get("he")))
    if t == "listen_choice" and e.get("ru"):
        he = next((c.get("he") for c in e.get("choices", []) if c.get("correct")), None)
        out.append((e["ru"], he))
    if t == "listen_order" and e.get("ru"):
        out.append((e["ru"], None))
    for p in e.get("pairs", []) or []:
        out.append((p.get("ru"), p.get("he")))
    for tr in e.get("turns", []) or []:
        out.append((tr.get("ru"), tr.get("he")))
    return out


def blank_of(ru):
    ws = words_of(ru)
    if len(ws) < 2:
        return None, None
    return " ".join(ws[:-1] + ["___"]), ws[-1]


def fresh_distractors(words, old, rng, n=None):
    ws = set(words)
    ds = [d for d in old if d not in ws]
    extra = [d for d in DISTRACTORS_RU if d not in ws and d not in ds]
    n = len(old) if n is None else n
    while len(ds) < n and extra:
        ds.append(extra.pop(rng.randrange(len(extra))))
    return ds


def consistency_pass(unit, rng, stats):
    """Fix duplicate tiles/choices and distractors that collide with the answer."""
    pool_rows = [tuple(r) for r in POOLS.get(unit["id"], [])]
    for les in unit["lessons"]:
        rows = []
        for e in les["exercises"]:
            for ru, he in ex_rows(e):
                if ru and he and (ru, he) not in rows:
                    rows.append((ru, he))
        for e in les["exercises"]:
            t = e.get("type")
            if t == "match_pairs":
                seen_ru, seen_he, out, changed = set(), set(), [], False
                for p in e["pairs"]:
                    if p["ru"] in seen_ru or nhe(p["he"]) in seen_he:
                        alt = next((r for r in rows + pool_rows
                                    if r[0] not in seen_ru and nhe(r[1]) not in seen_he), None)
                        changed = True
                        if not alt:
                            continue
                        p = {"ru": alt[0], "he": alt[1]}
                    seen_ru.add(p["ru"]); seen_he.add(nhe(p["he"])); out.append(p)
                if changed and len(out) >= 3:
                    e["pairs"] = out
                    stats["consistency:match_pairs dedup"] += 1
            elif t == "listen_choice":
                used = set()
                for c in sorted(e["choices"], key=lambda c: not c.get("correct")):
                    if nhe(c["he"]) in used:
                        alt = [w for w in WRONG_POOL if nhe(w) not in used]
                        c["he"] = rng.choice(alt)
                        stats["consistency:listen_choice dedup"] += 1
                    used.add(nhe(c["he"]))
            elif t == "dialogue":
                users = {x.get("ru") for x in e.get("turns", [])}
                ds = e.get("distractors") or []
                if any(d in users for d in ds) or len(set(ds)) != len(ds):
                    nd = []
                    for d in ds:
                        if d in users or d in nd:
                            alt = next((r[0] for r in rows + pool_rows if r[0] not in users and r[0] not in nd and r[0] not in ds), None)
                            if alt:
                                d = alt
                        nd.append(d)
                    e["distractors"] = nd
                    stats["consistency:dialogue distractor"] += 1
            elif t in ("sentence_build", "translate_he_ru") and e.get("distractors"):
                ws = set(e.get("words") or [])
                if any(d in ws for d in e["distractors"]):
                    e["distractors"] = fresh_distractors(e["words"], e["distractors"], rng)
                    stats["consistency:build distractor"] += 1


def lesson_targets(les):
    """All target strings a lesson shows (rows + dialogue distractors)."""
    s = set()
    for e in les["exercises"]:
        for ru, _ in ex_rows(e):
            if ru:
                s.add(ru)
        if e.get("type") == "dialogue":
            s.update(e.get("distractors") or [])
    return s


def main():
    dry = "--dry-run" in sys.argv
    report_path = None
    if "--report" in sys.argv:
        report_path = sys.argv[sys.argv.index("--report") + 1]
    bank = load_bank()
    by_lemma = {}
    for x in bank:
        by_lemma.setdefault(G.norm(x["lemma"]), x)
    cur = curated_set()
    # NB: no safe-form exemption here — even a grammatical old slot row is
    # off-topic filler for its unit; safe forms only apply to future output.
    safe = None
    rng = random.Random(20261003)

    stats = collections.Counter()
    reasons = collections.Counter()
    he_broken = 0
    examples = []
    unmatched = collections.Counter()

    for level in LEVELS:
        p1, p2 = load_parts(level)
        for unit in p1[1]["units"] + p2[1]:
            uid = unit["id"]
            # 1. collect bad rows in this unit (+ the lessons they occur in)
            bad = collections.OrderedDict()
            where = collections.defaultdict(set)
            unit_ru, unit_he = set(), set()
            for li, les in enumerate(unit["lessons"]):
                for e in les["exercises"]:
                    rows = ex_rows(e)
                    if e.get("type") == "dialogue":
                        rows = rows + [(d, None) for d in e.get("distractors") or []]
                    for ru, he in rows:
                        if not ru:
                            continue
                        unit_ru.add(ru)
                        if he:
                            unit_he.add(nhe(he))
                        if ru in cur:
                            continue
                        c = G.classify_legacy(ru, he or "", by_lemma, safe)
                        if not c:
                            unmatched[ru] += 1
                            continue
                        where[ru].add(li)
                        if ru not in bad or (he and not bad[ru][0]):
                            bad[ru] = (he, c)
            if not bad:
                consistency_pass(unit, rng, stats)
                continue
            pool = [tuple(r) for r in POOLS.get(uid, []) if r[0] not in unit_ru and nhe(r[1]) not in unit_he]
            if not pool:
                raise SystemExit(f"{uid}: no everyday pool for {len(bad)} bad rows")
            # 2. assign: least-used pool row not already present in any lesson of the bad row
            use = collections.Counter()
            in_lesson = collections.defaultdict(set)
            mapping = {}
            for ru in bad:
                cands = [r for r in pool if not any(r[0] in in_lesson[li] for li in where[ru])]
                if not cands:
                    raise SystemExit(f"{uid}: pool too small for lesson-local uniqueness")
                best = min(cands, key=lambda r: (use[r[0]], pool.index(r)))
                use[best[0]] += 1
                for li in where[ru]:
                    in_lesson[li].add(best[0])
                mapping[ru] = best
            for ru, (he, (frame, why)) in bad.items():
                nru, nh = mapping[ru]
                reasons[why] += 1
                if he and G.HE_BROKEN_RE.search(he):
                    he_broken += 1
                examples.append({"unit": uid, "old_ru": ru, "old_he": he, "reason": why,
                                 "new_ru": nru, "new_he": nh})
            blank_map = {}
            for r in bad:
                b, a = blank_of(r)
                if b:
                    blank_map[(b, a)] = r

            # 3. rewrite every exercise of the unit
            for les in unit["lessons"]:
                for e in les["exercises"]:
                    t = e.get("type")
                    touched = False
                    if e.get("ru") in mapping:
                        nru, nh = mapping[e["ru"]]
                        e["ru"] = nru
                        if "he" in e or t in ("speak_repeat", "sentence_build", "translate_he_ru"):
                            e["he"] = nh
                        if "words" in e or t in ("listen_order", "sentence_build", "translate_he_ru"):
                            e["words"] = words_of(nru)
                        if t == "listen_choice":
                            for c in e.get("choices", []):
                                if c.get("correct"):
                                    c["he"] = nh
                            used = {nhe(nh)}
                            for c in e["choices"]:
                                if not c.get("correct"):
                                    if nhe(c["he"]) in used:
                                        alt = [w for w in WRONG_POOL if nhe(w) not in used]
                                        c["he"] = rng.choice(alt)
                                    used.add(nhe(c["he"]))
                        if "distractors" in e and t in ("sentence_build", "translate_he_ru"):
                            e["distractors"] = fresh_distractors(e["words"], e["distractors"], rng)
                        touched = True
                    for p in e.get("pairs", []) or []:
                        if p.get("ru") in mapping:
                            p["ru"], p["he"] = mapping[p["ru"]]
                            touched = True
                    for tr in e.get("turns", []) or []:
                        if tr.get("ru") in mapping:
                            tr["ru"], tr["he"] = mapping[tr["ru"]]
                            touched = True
                    if t == "dialogue" and e.get("distractors"):
                        nd = [mapping[d][0] if d in mapping else d for d in e["distractors"]]
                        if nd != e["distractors"]:
                            e["distractors"] = nd
                            touched = True
                    if t == "fill_blank":
                        key = (e.get("sentence"), e.get("answer"))
                        if key in blank_map:
                            nru, nh = mapping[blank_map[key]]
                            b, a = blank_of(nru)
                            e["sentence"], e["answer"] = b, a
                            if e.get("he") is not None:
                                e["he"] = nh
                            ws = set(words_of(nru))
                            opts = []
                            for o in e.get("options", []):
                                if o.get("correct"):
                                    opts.append({"ru": a, "correct": True})
                                elif o.get("ru") not in ws and o.get("ru") != a:
                                    opts.append(o)
                            have = {o["ru"] for o in opts}
                            extra = [d for d in DISTRACTORS_RU if d not in ws and d not in have]
                            while len(opts) < 4 and extra:
                                opts.append({"ru": extra.pop(rng.randrange(len(extra))), "correct": False})
                            e["options"] = opts
                            touched = True
                    if touched:
                        stats[f"exercises_touched:{t}"] += 1
            consistency_pass(unit, rng, stats)
            stats["units_touched"] += 1
            stats["unique_replaced"] += len(mapping)
            stats["new_sentences_used"] += len({v[0] for v in mapping.values()})
        if not dry:
            save_parts(level, p1, p2)

    total_ex = sum(v for k, v in stats.items() if k.startswith("exercises_touched:"))
    print(f"unique (unit, sentence) replaced: {stats['unique_replaced']} in {stats['units_touched']} units"
          f" (with {stats['new_sentences_used']} distinct new sentences)")
    print(f"exercise occurrences rewritten: {total_ex}")
    for k, v in sorted(stats.items()):
        if k.startswith("exercises_touched:"):
            print(f"  {k.split(':')[1]:16s} {v}")
    for k, v in sorted(stats.items()):
        if k.startswith("consistency:"):
            print(f"  {k}: {v}")
    print("reasons:")
    for k, v in reasons.most_common():
        print(f"  {v:4d}  {k}")
    print(f"items whose Hebrew side was itself broken: {he_broken}")
    if unmatched:
        print("non-curated rows not matching any legacy template (left as is):", len(unmatched))
        for k, v in unmatched.most_common(20):
            print("   ", k, v)
    if report_path:
        Path(report_path).write_text(json.dumps({
            "stats": stats, "reasons": reasons, "he_broken": he_broken,
            "examples": examples}, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
