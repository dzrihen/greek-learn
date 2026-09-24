/* Curriculum loader — merges level data from RL_LEVEL_* globals (supports part files) */
(function (global) {
  "use strict";

  const LEVEL_ORDER = ["A1", "A2", "B1", "B2", "C1", "C2"];
  const UNLOCK_RATIO = 0.92; // require 92% of previous level

  const LEVEL_FILES = (global.RL_LEVEL_FILES) || {
    "A1": [
      "./data/a1-part1.js",
      "./data/a1-part2.js"
    ],
    "A2": [
      "./data/a2-part1.js",
      "./data/a2-part2.js"
    ],
    "B1": [
      "./data/b1-part1.js",
      "./data/b1-part2.js"
    ],
    "B2": [
      "./data/b2-part1.js",
      "./data/b2-part2.js"
    ],
    "C1": [
      "./data/c1-part1.js",
      "./data/c1-part2.js"
    ],
    "C2": [
      "./data/c2-part1.js",
      "./data/c2-part2.js"
    ]
  };

  const loaded = {};
  let levels = [];
  let ready = false;
  const lessonIndex = {};

  function collectFromWindow() {
    levels = [];
    Object.keys(lessonIndex).forEach((k) => delete lessonIndex[k]);
    LEVEL_ORDER.forEach((id) => {
      const obj = global["RL_LEVEL_" + id];
      if (obj) {
        loaded[id] = true;
        levels.push(obj);
        (obj.units || []).forEach((u) => {
          (u.lessons || []).forEach((les) => {
            lessonIndex[les.id] = les;
          });
        });
      }
    });
    // Grammar path (parallel, not CEFR unlock)
    const gram = global.RL_GRAMMAR;
    if (gram) {
      (gram.units || []).forEach((u) => {
        (u.lessons || []).forEach((les) => {
          lessonIndex[les.id] = les;
        });
      });
    }
    ready = levels.length > 0;
  }

  function grammarLessonIds() {
    const gram = global.RL_GRAMMAR;
    if (!gram) return [];
    const ids = [];
    (gram.units || []).forEach((u) => (u.lessons || []).forEach((l) => ids.push(l.id)));
    return ids;
  }

  function getGrammar() {
    return global.RL_GRAMMAR || null;
  }

  function loadScript(src) {
    return new Promise((resolve, reject) => {
      const s = document.createElement("script");
      s.src = src;
      s.async = false;
      s.onload = () => resolve();
      s.onerror = () => reject(new Error("fail " + src));
      document.head.appendChild(s);
    });
  }

  async function ensureLevel(levelId) {
    if (loaded[levelId] || global["RL_LEVEL_" + levelId]) {
      // still may need part2
      const files = LEVEL_FILES[levelId] || [];
      if (files.length > 1 && !loaded[levelId + "_parts"]) {
        for (let i = 1; i < files.length; i++) {
          await loadScript(files[i]);
        }
        loaded[levelId + "_parts"] = true;
      }
      collectFromWindow();
      return;
    }
    const files = LEVEL_FILES[levelId];
    if (!files || !files.length) return;
    for (const src of files) {
      await loadScript(src);
    }
    loaded[levelId + "_parts"] = true;
    collectFromWindow();
  }

  async function ensureAll() {
    for (const id of LEVEL_ORDER) {
      await ensureLevel(id);
    }
  }

  function getLevel(id) {
    return levels.find((l) => l.id === id) || null;
  }

  function lessonIdsForLevel(levelId) {
    const lv = getLevel(levelId);
    if (!lv) return [];
    const ids = [];
    (lv.units || []).forEach((u) => (u.lessons || []).forEach((l) => ids.push(l.id)));
    return ids;
  }

  function totalLessons() {
    return LEVEL_ORDER.reduce((acc, id) => acc + lessonIdsForLevel(id).length, 0);
  }

  function getLesson(id) {
    return lessonIndex[id] || null;
  }

  function isLevelComplete(levelId) {
    const ids = lessonIdsForLevel(levelId);
    if (!ids.length) return false;
    return ids.every((id) => RLProgress.isComplete(id));
  }

  function unlockThreshold(levelId) {
    const ids = lessonIdsForLevel(levelId);
    if (!ids.length) return 0;
    return Math.ceil(ids.length * UNLOCK_RATIO);
  }

  function remainingToUnlockNext(levelId) {
    const next = nextLevelId(levelId);
    if (!next) return 0;
    const ids = lessonIdsForLevel(levelId);
    if (!ids.length) return 0;
    const need = unlockThreshold(levelId);
    const done = RLProgress.countCompleted(ids);
    return Math.max(0, need - done);
  }

  function isLevelUnlocked(levelId) {
    const idx = LEVEL_ORDER.indexOf(levelId);
    if (idx <= 0) return true;
    const prev = LEVEL_ORDER[idx - 1];
    const ids = lessonIdsForLevel(prev);
    if (!ids.length) return true;
    const done = RLProgress.countCompleted(ids);
    return done >= unlockThreshold(prev) || isLevelComplete(prev);
  }

  function nextLevelId(levelId) {
    const idx = LEVEL_ORDER.indexOf(levelId);
    if (idx < 0 || idx >= LEVEL_ORDER.length - 1) return null;
    return LEVEL_ORDER[idx + 1];
  }

  function nextLesson() {
    const cur = RLProgress.get().currentLevel || "A1";
    const order = [cur].concat(LEVEL_ORDER.filter((x) => x !== cur));
    for (const lid of order) {
      if (!isLevelUnlocked(lid) && lid !== "A1") continue;
      const ids = lessonIdsForLevel(lid);
      for (const id of ids) {
        if (!RLProgress.isComplete(id)) return getLesson(id);
      }
    }
    return null;
  }

  /** Unique lemmas seen in completed lessons (approx from exercise RU text). */
  function vocabLearnedCount() {
    const completed = RLProgress.get().completed || {};
    const set = {};
    Object.keys(completed).forEach((lid) => {
      const les = getLesson(lid);
      if (!les) return;
      (les.exercises || []).forEach((ex) => {
        const texts = [];
        if (ex.ru) texts.push(ex.ru);
        if (ex.sentence) texts.push(ex.sentence);
        if (ex.example) texts.push(ex.example);
        (ex.turns || []).forEach((t) => t.ru && texts.push(t.ru));
        (ex.pairs || []).forEach((p) => p.ru && texts.push(p.ru));
        (ex.words || []).forEach((w) => texts.push(w));
        texts.forEach((t) => {
          const toks = String(t).match(/[\u0370-\u03FF\u1F00-\u1FFF\-]+/g) || [];
          toks.forEach((w) => {
            if (w.length >= 2) set[w.toLowerCase()] = true;
          });
        });
      });
    });
    return Object.keys(set).length;
  }

  collectFromWindow();
  const bootPromise = ready
    ? Promise.resolve()
    : ensureAll()
        .then(() => {
          collectFromWindow();
          ready = true;
        })
        .catch((e) => {
          console.error(e);
          collectFromWindow();
          ready = levels.length > 0;
        });

  setTimeout(collectFromWindow, 0);
  setTimeout(collectFromWindow, 100);

  global.RLCurriculum = {
    get levels() {
      return levels;
    },
    get ready() {
      return ready && levels.length > 0;
    },
    bootPromise,
    ensureLevel,
    ensureAll,
    getLevel,
    getLesson,
    lessonIdsForLevel,
    totalLessons,
    isLevelComplete,
    isLevelUnlocked,
    unlockThreshold,
    remainingToUnlockNext,
    nextLevelId,
    nextLesson,
    vocabLearnedCount,
    grammarLessonIds,
    getGrammar,
    UNLOCK_RATIO,
    LEVEL_ORDER,
    _collect: collectFromWindow,
  };
})(window);
