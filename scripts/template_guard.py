# -*- coding: utf-8 -*-
"""Guard rails for template-generated sentences (Modern Greek).

Root cause of «Χρειάζομαι κόρη.» / «Πόσο κοστίζει γιαγιά;» / «Αυτό είναι
καλός μητέρα.» / «Θέλω να αυξανομαι.» = «אני רוצה לפעול/αυξα» /
«Χρειαζόμαστε μια ταξιδος απάντηση.» = «אנחנו צריכים תשובה נסיעהי»: the old
generators (vocab_bank.generate_lemma_sentences / natural_rows_for_lemma,
called with theme=None) filled open slot frames with *any* unused bank lemma
in its dictionary form — regardless of part of speech, gender, article, case
or the unit's topic — including pseudo-lemmas with placeholder Hebrew, and
padded advanced units with meta sentences that talk *about* a word
(«Ας εξετάσουμε τη λέξη «X».») instead of using it.

This module is the single source of truth for:
  * SAFE_NOUNS     – the only words allowed into a slot (concrete nouns with
                     verified Hebrew gloss, Hebrew gender and the Greek forms
                     with the right article, so agreement is always right)
  * TEMPLATES      – the only slot templates still in use, each limited to
                     the noun categories that make sense in it
  * slot_ok()      – hard rejection rules (POS, placeholders, whitelist)
  * LEGACY_FRAMES / classify_legacy() – detector for old generated items
"""
import re

FUNC_POS = {"conj", "prep", "pron", "adv", "intj", "v", "adj", "num", "phrase", "other"}
PLACEHOLDER_RE = re.compile(r"[0-9A-Za-z]")
# Hebrew side of a bank entry / generated row that is not real Hebrew
HE_PLACEHOLDER_RE = re.compile(r"[0-9A-Za-zА-Яа-яЁёΑ-Ωα-ωά-ώΆ-Ώϊΐϋΰ]|עניין/|לפעול/|קשור ל-")

# lemma -> (hebrew, hebrew gender m/f/p, category, indefinite accusative, definite nominative)
SAFE_NOUNS = {
    # food & drink
    "καφές": ("קפה", "m", "food", "έναν καφέ", "ο καφές"),
    "τσάι": ("תה", "m", "food", "ένα τσάι", "το τσάι"),
    "νερό": ("מים", "p", "food", "ένα νερό", "το νερό"),
    "χυμός": ("מיץ", "m", "food", "έναν χυμό", "ο χυμός"),
    "μπίρα": ("בירה", "f", "food", "μια μπίρα", "η μπίρα"),
    "σαλάτα": ("סלט", "m", "food", "μια σαλάτα", "η σαλάτα"),
    "σούπα": ("מרק", "m", "food", "μια σούπα", "η σούπα"),
    "παγωτό": ("גלידה", "f", "food", "ένα παγωτό", "το παγωτό"),
    "μήλο": ("תפוח", "m", "food", "ένα μήλο", "το μήλο"),
    "μπανάνα": ("בננה", "f", "food", "μια μπανάνα", "η μπανάνα"),
    "πορτοκάλι": ("תפוז", "m", "food", "ένα πορτοκάλι", "το πορτοκάλι"),
    "αυγό": ("ביצה", "f", "food", "ένα αυγό", "το αυγό"),
    "σοκολάτα": ("שוקולד", "m", "food", "μια σοκολάτα", "η σοκολάτα"),
    # household / personal objects
    "κλειδί": ("מפתח", "m", "object", "ένα κλειδί", "το κλειδί"),
    "ομπρέλα": ("מטרייה", "f", "object", "μια ομπρέλα", "η ομπρέλα"),
    "τσάντα": ("תיק", "m", "object", "μια τσάντα", "η τσάντα"),
    "τηλέφωνο": ("טלפון", "m", "object", "ένα τηλέφωνο", "το τηλέφωνο"),
    "κουτάλι": ("כף", "f", "object", "ένα κουτάλι", "το κουτάλι"),
    "πιρούνι": ("מזלג", "m", "object", "ένα πιρούνι", "το πιρούνι"),
    "μαχαίρι": ("סכין", "f", "object", "ένα μαχαίρι", "το μαχαίρι"),
    "πιάτο": ("צלחת", "f", "object", "ένα πιάτο", "το πιάτο"),
    "ποτήρι": ("כוס", "f", "object", "ένα ποτήρι", "το ποτήρι"),
    "πετσέτα": ("מגבת", "f", "object", "μια πετσέτα", "η πετσέτα"),
    "σαπούνι": ("סבון", "m", "object", "ένα σαπούνι", "το σαπούνι"),
    "στυλό": ("עט", "m", "object", "ένα στυλό", "το στυλό"),
    "βιβλίο": ("ספר", "m", "object", "ένα βιβλίο", "το βιβλίο"),
    "τετράδιο": ("מחברת", "f", "object", "ένα τετράδιο", "το τετράδιο"),
    "εισιτήριο": ("כרטיס", "m", "object", "ένα εισιτήριο", "το εισιτήριο"),
    "διαβατήριο": ("דרכון", "m", "object", "ένα διαβατήριο", "το διαβατήριο"),
}

# Slot templates still allowed: (id, greek, hebrew, allowed categories)
TEMPLATES = [
    ("want",  "Θα ήθελα {indef}, παρακαλώ.", "הייתי רוצה {he}, בבקשה.", {"food"}),
    ("give",  "Μου δίνετε {indef};",         "אפשר לקבל {he}?",          {"food", "object"}),
    ("have",  "Έχετε {indef};",              "יש לכם {he}?",             {"food", "object"}),
    ("where", "Πού είναι {defn};",           "איפה ה{he}?",              {"object"}),
]


def norm(s):
    return (s or "").strip().lower().replace("ς", "σ")


_SAFE_N = {norm(k): k for k in SAFE_NOUNS}


def slot_ok(entry, tmpl_id=None):
    """True only if a bank entry may fill a slot of template tmpl_id."""
    lem = entry.get("lemma") or ""
    if not lem or PLACEHOLDER_RE.search(lem):
        return False
    if entry.get("pos") in FUNC_POS:
        return False
    if HE_PLACEHOLDER_RE.search(entry.get("he") or ""):
        return False
    key = _SAFE_N.get(norm(lem))
    if not key:
        return False
    if tmpl_id:
        for tid, _, _, cats in TEMPLATES:
            if tid == tmpl_id:
                return SAFE_NOUNS[key][2] in cats
    return True


def render(tmpl_id, lemma):
    key = _SAFE_N.get(norm(lemma))
    if not key:
        return None
    he, g, cat, indef, defn = SAFE_NOUNS[key]
    for tid, t_el, t_he, cats in TEMPLATES:
        if tid == tmpl_id and cat in cats:
            return t_el.format(indef=indef, defn=defn), t_he.format(he=he)
    return None


def safe_forms():
    out = set()
    for lem in SAFE_NOUNS:
        for t in TEMPLATES:
            r = render(t[0], lem)
            if r:
                out.add(r[0])
    return out


# ---- detector for items produced by the OLD generator -------------------
# Every open frame the old vocab_bank used (TEMPLATES_A1, TEMPLATES_ADV and
# natural_rows_for_lemma).  {x} = slot.
LEGACY_FRAMES = [
    'Αυτό είναι {x} {x}.', 'Αυτό είναι {x}.', 'Πού είναι {x};', 'Έχω {x}.', 'Χρειάζομαι {x}.',
    'Θέλω να {x}.', 'Μου αρέσει {x}.', 'Σήμερα θέλω να {x}.', 'Ψάχνουμε {x}.', 'Αγοράζει {x}.',
    'Πόσο κοστίζει {x};', 'Το {x} μου είναι εδώ.', 'Δεν καταλαβαίνω τη λέξη «{x}».',
    'Μπορώ να {x};', 'Δώστε μου {x}, παρακαλώ.', 'Μετά τη δουλειά θέλω να {x}.',
    'Χωρίς {x} είναι δύσκολο.', 'Παρεμπιπτόντως, πού είναι {x};', 'Πρώτα πρέπει να {x}.',
    'Ορίστε το {x} μου.', 'Αυτό δεν είναι {x}.',
    'Το θέμα της συζήτησης είναι {x}.', 'Σήμερα μιλάμε για το θέμα «{x}».',
    'Με ενδιαφέρει το θέμα «{x}».', 'Ας εξετάσουμε τη λέξη «{x}».',
    'Στις ειδήσεις εμφανίζεται συχνά η λέξη «{x}».', 'Για μένα το «{x}» είναι σημαντικό θέμα.',
    'Χωρίς την έννοια «{x}» είναι δύσκολο να καταλάβεις το κείμενο.', 'Η λέξη-κλειδί εδώ είναι «{x}».',
    'Αξίζει να {x} από πριν.', 'Σκοπεύω να {x}.', 'Τώρα πρέπει να {x}.', 'Ήρθε η ώρα να {x}.',
    'Καλύτερα να μην {x} βιαστικά.', 'Πολλοί προτιμούν να {x}.', 'Προσπαθώ να {x} κάθε μέρα.',
    'Αυτό είναι αρκετά {x} ζήτημα.', 'Χρειαζόμαστε μια {x} απάντηση.', 'Αυτή είναι μια {x} προσέγγιση.',
    'Αυτό είναι {x} παράδειγμα.', 'Ενεργούμε {x}.', 'Απάντησε {x}.', 'Κάντε το {x}.',
]


def _frame_re(f):
    if "{x} {x}" in f:  # adjective + noun frame: capture both words as one slot
        return re.compile("^" + re.escape(f.replace("{x} {x}", "{x}")).replace(re.escape("{x}"), r"(?P<s>\S+ .+?)") + "$")
    return re.compile("^" + re.escape(f).replace(re.escape("{x}"), "(?P<s>.+?)") + "$")


LEGACY_PATTERNS = [(f, _frame_re(f)) for f in LEGACY_FRAMES]
META_WORDS = ("λέξη", "θέμα", "έννοια")
VERB_FRAMES = {f for f in LEGACY_FRAMES if "να {x}" in f or "να μην {x}" in f}
ADJ_FRAMES = {'Αυτό είναι αρκετά {x} ζήτημα.', 'Χρειαζόμαστε μια {x} απάντηση.',
              'Αυτή είναι μια {x} προσέγγιση.', 'Αυτό είναι {x} παράδειγμα.'}
ADV_FRAMES = {'Ενεργούμε {x}.', 'Απάντησε {x}.', 'Κάντε το {x}.'}
# bare noun (no article) where Greek needs one / wrong article
ARTICLE_FRAMES = {'Αυτό είναι {x}.', 'Πού είναι {x};', 'Έχω {x}.', 'Χρειάζομαι {x}.', 'Μου αρέσει {x}.',
                  'Ψάχνουμε {x}.', 'Αγοράζει {x}.', 'Πόσο κοστίζει {x};', 'Δώστε μου {x}, παρακαλώ.',
                  'Χωρίς {x} είναι δύσκολο.', 'Παρεμπιπτόντως, πού είναι {x};', 'Αυτό δεν είναι {x}.',
                  'Το {x} μου είναι εδώ.', 'Ορίστε το {x} μου.'}
ARTICLES = ("ο ", "η ", "το ", "τον ", "την ", "τη ", "οι ", "τα ", "τους ", "τις ", "ένα ", "έναν ", "μια ", "μία ")
NON_OBJECT_THEMES = {"people", "family", "places", "city", "time", "body", "weather", "society", "abstract",
                     "nuance", "mastery", "discourse", "daily", "work"}
# Hebrew built by the same frames: placeholders, gloss fragments, adjective gender clash
HE_BROKEN_RE = re.compile(
    r"\(מושלם\)|עניין/|לפעול/|קשור ל-|[A-Za-zА-Яа-яЁёΑ-Ωα-ωά-ώΆ-Ώϊΐϋΰ]"
    r"|^(זו שאלה די|זו גישה די|אנחנו צריכים תשובה|זו דוגמה) [^ ]*[^התי \.]\.$"
)


def classify_legacy(el, he, bank_by_lemma=None, safe=None):
    """Return (frame, reason) for an old generated row, or None."""
    if safe and el in safe:
        return None
    for f, rx in LEGACY_PATTERNS:
        m = rx.match(el or "")
        if not m:
            continue
        s = m.group("s")
        if (f in ARTICLE_FRAMES or f == 'Αυτό είναι {x} {x}.') and s.startswith(ARTICLES):
            continue  # the old generator never produced articles: a hand-written sentence
        e = (bank_by_lemma or {}).get(norm(s)) or {}
        if any(w in f for w in META_WORDS):
            return f, "meta filler (talks about the word instead of using it)"
        if HE_PLACEHOLDER_RE.search(he or "") or PLACEHOLDER_RE.search(s):
            return f, "placeholder / pseudo-word"
        if HE_BROKEN_RE.search(he or ""):
            return f, "broken Hebrew (gender clash / gloss in slot)"
        if f in VERB_FRAMES and " " not in s:
            return f, "bare dictionary-form verb in a generic frame"
        if f in ADJ_FRAMES or f == 'Αυτό είναι {x} {x}.':
            return f, "adjective in dictionary form (gender/article agreement error)"
        if f in ADV_FRAMES:
            return f, "retired template (off-topic filler)"
        if f in ARTICLE_FRAMES and not s.startswith(ARTICLES) and e.get("theme") in NON_OBJECT_THEMES:
            return f, "person/place/abstract noun in object slot"
        if f in ARTICLE_FRAMES and not s.startswith(ARTICLES):
            return f, "missing article (bare dictionary form in slot)"
        return f, "retired template (off-topic filler)"
    return None
