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

TEMPLATES_A1 = [
    ("Αυτό είναι {n}.", "זה {n_he}."),
    ("Πού είναι {n};", "איפה {n_he}?"),
    ("Έχω {n}.", "יש לי {n_he}."),
    ("Χρειάζομαι {n}.", "אני צריך {n_he}."),
    ("Θέλω να {v}.", "אני רוצה {v_he}."),
    ("Μου αρέσει {n}.", "אני אוהב/ת {n_he}."),
    ("Αυτό είναι {adj} {n}.", "זה {n_he} {adj_he}."),
    ("Σήμερα θέλω να {v}.", "היום אני רוצה {v_he}."),
    ("Ψάχνουμε {n}.", "אנחנו מחפשים {n_he}."),
    ("Αγοράζει {n}.", "הוא קונה {n_he}."),
    ("Πόσο κοστίζει {n};", "כמה עולה {n_he}?"),
    ("Το {n} μου είναι εδώ.", "{n_he} שלי כאן."),
    ("Δεν καταλαβαίνω τη λέξη «{n}».", "אני לא מבין/ה את המילה «{n_he}»."),
    ("Μπορώ να {v};", "אפשר {v_he}?"),
    ("Δώστε μου {n}, παρακαλώ.", "תנו לי {n_he}, בבקשה."),
    ("Μετά τη δουλειά θέλω να {v}.", "אחרי העבודה אני רוצה {v_he}."),
    ("Χωρίς {n} είναι δύσκολο.", "בלי {n_he} קשה."),
    ("Παρεμπιπτόντως, πού είναι {n};", "אגב, איפה {n_he}?"),
    ("Πρώτα πρέπει να {v}.", "קודם צריך {v_he}."),
    ("Ορίστε το {n} μου.", "הנה ה{n_he} שלי."),
    ("Αυτό δεν είναι {n}.", "זה לא {n_he}."),
]

TEMPLATES_ADV = [
    ("Το θέμα της συζήτησης είναι {n}.", "נושא השיחה — {n_he}."),
    ("Σήμερα μιλάμε για το θέμα «{n}».", "היום מדובר בנושא «{n_he}»."),
    ("Με ενδιαφέρει το θέμα «{n}».", "מעניין אותי הנושא «{n_he}»."),
    ("Ας εξετάσουμε τη λέξη «{n}».", "בואו נפרק את המילה «{n_he}»."),
    ("Στις ειδήσεις εμφανίζεται συχνά η λέξη «{n}».", "בחדשות לעתים קרובות מופיעה המילה «{n_he}»."),
    ("Για μένα το «{n}» είναι σημαντικό θέμα.", "עבורי «{n_he}» הוא נושא חשוב."),
    ("Χωρίς την έννοια «{n}» είναι δύσκολο να καταλάβεις το κείμενο.", "בלי המושג «{n_he}» קשה להבין את הטקסט."),
    ("Η λέξη-κλειδί εδώ είναι «{n}».", "המילה המרכזית כאן — «{n_he}»."),
    ("Αξίζει να {v} από πριν.", "כדאי {v_he} מראש."),
    ("Σκοπεύω να {v}.", "אני מתכנן/ת {v_he}."),
    ("Τώρα πρέπει να {v}.", "עכשיו צריך {v_he}."),
    ("Ήρθε η ώρα να {v}.", "הגיע הזמן {v_he}."),
    ("Καλύτερα να μην {v} βιαστικά.", "עדיף לא {v_he} בחיפזון."),
    ("Πολλοί προτιμούν να {v}.", "רבים מעדיפים {v_he}."),
    ("Προσπαθώ να {v} κάθε μέρα.", "אני משתדל/ת {v_he} כל יום."),
    ("Αυτό είναι αρκετά {adj} ζήτημα.", "זו שאלה די {adj_he}."),
    ("Χρειαζόμαστε μια {adj} απάντηση.", "אנחנו צריכים תשובה {adj_he}."),
    ("Αυτή είναι μια {adj} προσέγγιση.", "זו גישה די {adj_he}."),
]

def fill_template(tpl_ru, tpl_he, slots):
    return tpl_ru.format(**slots), tpl_he.format(**slots)

def natural_rows_for_lemma(u, rng=None):
    rng = rng or random.Random(hash(u["lemma"]) % 10_000)
    lem, he, pos = u["lemma"], u["he"], u["pos"]
    if pos == "v":
        pool = [
            (f"Αξίζει να {lem} από πριν.", f"כדאי {he} מראש."),
            (f"Σκοπεύω να {lem}.", f"אני מתכנן/ת {he}."),
            (f"Τώρα πρέπει να {lem}.", f"עכשיו צריך {he}."),
            (f"Ήρθε η ώρα να {lem}.", f"הגיע הזמן {he}."),
            (f"Καλύτερα να μην {lem} βιαστικά.", f"עדיף לא {he} בחיפזון."),
            (f"Πολλοί προτιμούν να {lem}.", f"רבים מעדיפים {he}."),
            (f"Προσπαθώ να {lem} κάθε μέρα.", f"אני משתדל/ת {he} כל יום."),
        ]
    elif pos == "adj":
        pool = [
            (f"Αυτό είναι αρκετά {lem} ζήτημα.", f"זו שאלה די {he}."),
            (f"Χρειαζόμαστε μια {lem} απάντηση.", f"אנחנו צריכים תשובה {he}."),
            (f"Αυτή είναι μια {lem} προσέγγιση.", f"זו גישה די {he}."),
            (f"Αυτό είναι {lem} παράδειγμα.", f"זו דוגמה {he}."),
        ]
    elif pos == "adv":
        pool = [
            (f"Ενεργούμε {lem}.", f"אנחנו פועלים {he}."),
            (f"Απάντησε {lem}.", f"הוא ענה {he}."),
            (f"Κάντε το {lem}.", f"עשו את זה {he}."),
        ]
    else:
        pool = [
            (f"Το θέμα της συζήτησης είναι {lem}.", f"נושא השיחה — {he}."),
            (f"Σήμερα μιλάμε για το θέμα «{lem}».", f"היום מדובר בנושא «{he}»."),
            (f"Με ενδιαφέρει το θέμα «{lem}».", f"מעניין אותי הנושא «{he}»."),
            (f"Ας εξετάσουμε τη λέξη «{lem}».", f"בואו נפרק את המילה «{he}»."),
            (f"Στις ειδήσεις εμφανίζεται συχνά η λέξη «{lem}».", f"בחדשות לעתים קרובות מופיעה המילה «{he}»."),
            (f"Για μένα το «{lem}» είναι σημαντικό θέμα.", f"עבורי «{he}» הוא נושא חשוב."),
            (f"Η λέξη-κλειδί εδώ είναι «{lem}».", f"המילה המרכזית כאן — «{he}»."),
        ]
    rng.shuffle(pool)
    return pool[:2]

def generate_lemma_sentences(tracker, cefr=("a1",), theme=None, count=8):
    rng = random.Random(hash((theme, count, tracker.stats()["introduced"])) % 10_000)
    nouns = tracker.pick(40, cefr=cefr, theme=theme, pos="n") or tracker.pick(40, cefr=cefr, pos="n")
    verbs = tracker.pick(30, cefr=cefr, pos="v")
    adjs = tracker.pick(30, cefr=cefr, pos="adj")
    rows = []
    used_local = set()
    levels = set(cefr) if isinstance(cefr, (tuple, list, set)) else {cefr}
    templates = TEMPLATES_ADV if levels & {"b1", "b2", "c1", "c2"} else TEMPLATES_A1
    order = list(range(len(templates)))
    rng.shuffle(order)
    for i in range(count * 4):
        if len(rows) >= count:
            break
        tpl_ru, tpl_he = templates[order[i % len(order)]]
        slots = {}
        if "{n}" in tpl_ru:
            if not nouns: break
            n = nouns[i % len(nouns)]
            if n["lemma"].lower() in used_local and len(nouns) > 1:
                n = nouns[(i + 3) % len(nouns)]
            slots["n"] = n["lemma"]; slots["n_he"] = n["he"]
            used_local.add(n["lemma"].lower())
        if "{v}" in tpl_ru:
            if not verbs: continue
            v = verbs[i % len(verbs)]
            slots["v"] = v["lemma"]; slots["v_he"] = v["he"]
            used_local.add(v["lemma"].lower())
        if "{adj}" in tpl_ru:
            if not adjs: continue
            a = adjs[i % len(adjs)]
            slots["adj"] = a["lemma"]; slots["adj_he"] = a["he"]
            used_local.add(a["lemma"].lower())
        try:
            ru, he = fill_template(tpl_ru, tpl_he, slots)
        except KeyError:
            continue
        rows.append((ru, he))
        tracker.mark_text(ru)
    return rows

if __name__ == "__main__":
    t = LemmaTracker()
    print("bank", t.stats())
