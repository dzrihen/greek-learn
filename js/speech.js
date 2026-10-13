/* Speech: cached MP3/OGG when available, else Web Speech TTS (el-GR) */
(function (global) {
  "use strict";

  let preferredVoice = null;
  let voicesReady = false;
  let userGesture = false;
  let audioManifest = null; // { hash: "audio/....mp3" }
  let manifestPromise = null;
  let currentAudio = null;
  let playGen = 0; // bumps on every new request / stop → stale continuations abort

  function markGesture() {
    userGesture = true;
  }
  if (typeof document !== "undefined") {
    ["pointerdown", "keydown", "touchstart"].forEach((ev) => {
      document.addEventListener(ev, markGesture, { once: true, capture: true });
    });
  }

  function scoreVoice(v) {
    const name = v.name || "";
    const lang = (v.lang || "").toLowerCase();
    let s = 0;
    if (lang === "el-gr") s += 20;
    else if (lang.startsWith("el")) s += 12;
    if (/google|microsoft|neural|enhanced|premium|natural/i.test(name)) s += 8;
    if (/athina|nestor|stefanos|melina|afroditi|greek/i.test(name)) s += 6;
    if (/female|woman|женщин/i.test(name)) s += 2;
    if (/male|nestor|stefanos/i.test(name)) s -= 1;
    if (/compact|online \(natural\) compact/i.test(name)) s -= 2;
    return s;
  }

  function pickVoice() {
    if (typeof speechSynthesis === "undefined") return;
    const voices = speechSynthesis.getVoices() || [];
    const ru = voices.filter(
      (v) => (v.lang || "").toLowerCase().startsWith("el") || /greek|ελλην|ellin/i.test(v.name || "")
    );
    ru.sort((a, b) => scoreVoice(b) - scoreVoice(a));
    preferredVoice = ru[0] || null;
    voicesReady = true;
  }

  if (typeof speechSynthesis !== "undefined") {
    pickVoice();
    speechSynthesis.onvoiceschanged = pickVoice;
  }

  function learnerRate() {
    try {
      const s = (global.RLProgress && RLProgress.get().settings) || {};
      if (s.speechRate === "normal") return 1.0;
      return 0.9;
    } catch (e) {
      return 0.9;
    }
  }

  /** Stable short hash for audio lookup (djb2 hex). */
  function textHash(text) {
    const s = String(text || "").trim();
    let h = 5381;
    for (let i = 0; i < s.length; i++) {
      h = ((h << 5) + h) ^ s.charCodeAt(i);
      h = h >>> 0;
    }
    return h.toString(16);
  }

  function loadManifest() {
    if (audioManifest) return Promise.resolve(audioManifest);
    if (manifestPromise) return manifestPromise;
    if (global.RL_AUDIO_MANIFEST) {
      audioManifest = global.RL_AUDIO_MANIFEST;
      return Promise.resolve(audioManifest);
    }
    manifestPromise = fetch("./audio/manifest.json")
      .then((r) => (r.ok ? r.json() : {}))
      .then((j) => {
        audioManifest = j || {};
        return audioManifest;
      })
      .catch(() => {
        audioManifest = {};
        return audioManifest;
      });
    return manifestPromise;
  }

  function soundEnabled() {
    try {
      return !global.RLProgress || RLProgress.get().settings.sound !== false;
    } catch (e) {
      return true;
    }
  }

  function playFile(url, rate, gen) {
    return new Promise((resolve) => {
      try {
        if (gen != null && gen !== playGen) return resolve({ ok: false, source: "file", cancelled: true });
        haltOutput();
        const a = new Audio(url);
        currentAudio = a;
        a.playbackRate = rate != null ? rate : learnerRate();
        let settled = false;
        const done = (ok) => {
          if (settled) return;
          settled = true;
          if (!ok) {
            // make sure a late-loading clip can never start after we fall back to TTS
            try { a.onended = null; a.onerror = null; a.oncanplay = null; a.pause(); a.removeAttribute("src"); a.load(); } catch (e) {}
          }
          if (currentAudio === a) currentAudio = null;
          resolve({ ok: !!ok, source: "file", cancelled: gen != null && gen !== playGen });
        };
        a.onended = () => done(true);
        a.onerror = () => done(false);
        const p = a.play();
        if (p && p.then) {
          p.catch(() => done(false));
        }
        // Slow mobile networks: give the clip time to load before giving up.
        setTimeout(() => {
          if (!settled && a.paused && (a.error || a.readyState < 2)) done(false);
        }, 6000);
      } catch (e) {
        resolve({ ok: false, source: "file" });
      }
    });
  }

  function speakTts(text, opts, gen) {
    if (!text || typeof speechSynthesis === "undefined") {
      return Promise.resolve({ ok: false, source: "tts" });
    }
    opts = opts || {};
    return new Promise((resolve) => {
      try {
        if (gen != null && gen !== playGen) return resolve({ ok: false, source: "tts", cancelled: true });
        speechSynthesis.cancel();
        const u = new SpeechSynthesisUtterance(String(text));
        u.lang = "el-GR";
        u.rate = opts.rate != null ? opts.rate : learnerRate();
        u.pitch = opts.pitch != null ? opts.pitch : 1;
        if (preferredVoice) u.voice = preferredVoice;
        let settled = false;
        const done = (ok) => {
          if (settled) return;
          settled = true;
          resolve({ ok: !!ok, source: "tts" });
        };
        u.onend = () => done(true);
        u.onerror = () => done(false);
        speechSynthesis.speak(u);
        setTimeout(() => {
          if (!settled && !speechSynthesis.speaking && !speechSynthesis.pending) {
            done(false);
          }
        }, 700);
      } catch (e) {
        resolve({ ok: false, source: "tts" });
      }
    });
  }

  function speak(text, opts) {
    opts = opts || {};
    if (!text) return Promise.resolve({ ok: false });
    if (!soundEnabled() && !opts.force) return Promise.resolve({ ok: false });

    const rate = opts.rate != null ? opts.rate : learnerRate();
    const hash = textHash(text);
    const idKey = opts.audioId || null;
    const gen = ++playGen;
    haltOutput();

    return loadManifest().then((man) => {
      if (gen !== playGen) return { ok: false, cancelled: true };
      const path =
        (idKey && man[idKey]) ||
        man[hash] ||
        man[String(text).trim()] ||
        null;
      if (path) {
        const url = path.startsWith("http") || path.startsWith("./") || path.startsWith("/")
          ? path
          : "./" + path;
        return playFile(url, rate, gen).then((r) => {
          if (r && r.ok) return r;
          if (gen !== playGen || (r && r.cancelled)) return { ok: false, cancelled: true };
          return speakTts(text, opts, gen);
        });
      }
      return speakTts(text, opts, gen);
    });
  }

  function autoPlay(text, opts) {
    if (!text) return Promise.resolve({ ok: false, blocked: false });
    if (!soundEnabled()) return Promise.resolve({ ok: false, blocked: false });
    return speak(text, opts).then((r) => ({
      ok: !!(r && r.ok),
      blocked: !(r && r.ok) && !userGesture,
      needsGesture: !userGesture,
      source: r && r.source,
    }));
  }

  function haltOutput() {
    try {
      if (currentAudio) {
        currentAudio.onended = null;
        currentAudio.onerror = null;
        currentAudio.pause();
        currentAudio = null;
      }
    } catch (e) {}
    try {
      if (typeof speechSynthesis !== "undefined") speechSynthesis.cancel();
    } catch (e) {}
  }

  function stop() {
    playGen++;
    try {
      if (currentAudio) {
        currentAudio.pause();
        currentAudio = null;
      }
    } catch (e) {}
    try {
      if (typeof speechSynthesis !== "undefined") speechSynthesis.cancel();
    } catch (e) {}
  }

  function sleep(ms) {
    return new Promise((r) => setTimeout(r, ms));
  }

  function seqStale(r) {
    return !!(r && r.cancelled);
  }

  async function speakTurns(texts, gapMs, opts) {
    const list = (texts || []).map((t) => String(t || "").trim()).filter(Boolean);
    const gap = gapMs == null ? 420 : gapMs;
    for (let i = 0; i < list.length; i++) {
      const r = await speak(list[i], opts);
      if (r && r.cancelled) return; // something else started playing → abandon the sequence
      const g = playGen;
      if (i < list.length - 1 && gap > 0) await sleep(gap);
      if (playGen !== g) return;
    }
  }

  const Rec =
    global.SpeechRecognition || global.webkitSpeechRecognition || null;

  function canRecognize() {
    return !!Rec;
  }

  function recognizeOnce(timeoutMs) {
    return new Promise((resolve) => {
      if (!Rec) {
        resolve({ ok: false, reason: "unsupported", transcript: "" });
        return;
      }
      let done = false;
      const finish = (result) => {
        if (done) return;
        done = true;
        try {
          r.stop();
        } catch (e) {}
        resolve(result);
      };
      const r = new Rec();
      r.lang = "el-GR";
      r.interimResults = false;
      r.maxAlternatives = 3;
      r.onresult = (ev) => {
        const alts = [];
        for (let i = 0; i < ev.results[0].length; i++) {
          alts.push(ev.results[0][i].transcript);
        }
        finish({ ok: true, transcript: alts[0] || "", alternatives: alts });
      };
      r.onerror = () => finish({ ok: false, reason: "error", transcript: "" });
      r.onend = () => finish({ ok: false, reason: "ended", transcript: "" });
      try {
        r.start();
      } catch (e) {
        finish({ ok: false, reason: "start_failed", transcript: "" });
      }
      setTimeout(() => finish({ ok: false, reason: "timeout", transcript: "" }), timeoutMs || 6000);
    });
  }

  function normalizeRu(s) {
    return String(s || "")
      .toLowerCase()
      .normalize("NFD")
      .replace(/[̀-ͯ]/g, "")
      .replace(/ς/g, "σ")
      .replace(/[^Ͱ-Ͽἀ-῿\s]/g, "")
      .replace(/\s+/g, " ")
      .trim();
  }

  function looseMatch(heard, expected) {
    const a = normalizeRu(heard);
    const b = normalizeRu(expected);
    if (!a || !b) return false;
    if (a === b) return true;
    if (a.includes(b) || b.includes(a)) return true;
    const ta = new Set(a.split(" "));
    const tb = b.split(" ");
    const hit = tb.filter((t) => ta.has(t)).length;
    return hit >= Math.ceil(tb.length * 0.6);
  }

  // prefetch manifest
  loadManifest();

  global.RLSpeech = {
    speak,
    speakSlow: (t, o) => speak(t, Object.assign({}, o, { rate: 0.65 })),
    autoPlay,
    speakTurns,
    stop,
    canRecognize,
    recognizeOnce,
    normalizeRu,
    looseMatch,
    textHash,
    loadManifest,
    voicesReady: () => voicesReady,
    preferredVoiceName: () => (preferredVoice && preferredVoice.name) || null,
    hasUserGesture: () => userGesture,
    getRate: learnerRate,
  };

  /* Central audio guard: identical play requests within 600ms are collapsed into one
     (protects against autoplay + tap / double render / double listeners). Each new
     distinct request already cancels the previous clip + TTS inside speak(). */
  (function () {
    const S = global.RLSpeech;
    if (!S || S.__guarded) return;
    S.__guarded = true;
    const DEDUPE_MS = 600;
    let last = { key: "", t: 0, p: null };
    const stats = (global.__RL_AUDIO_STATS = global.__RL_AUDIO_STATS || { requests: 0, deduped: 0 });
    function guard(kind, text, run) {
      const key = kind + "|" + (Array.isArray(text) ? text.join("\u0001") : String(text || "").trim());
      const now = Date.now();
      stats.requests++;
      if (last.p && last.key === key && now - last.t < DEDUPE_MS) {
        stats.deduped++;
        return last.p;
      }
      const p = Promise.resolve(run());
      last = { key: key, t: now, p: p };
      return p;
    }
    const raw = { speak: S.speak, autoPlay: S.autoPlay, speakSlow: S.speakSlow, speakTurns: S.speakTurns, stop: S.stop };
    S.speak = function (text, opts) {
      const k = "n" + (opts && opts.rate != null ? ":" + opts.rate : "") + (opts && opts.audioId ? ":" + opts.audioId : "");
      return guard(k, text, () => raw.speak(text, opts));
    };
    S.autoPlay = function (text, opts) {
      // shares the "n" key with speak(): autoplay + immediate replay tap = one playback
      const k = "n" + (opts && opts.rate != null ? ":" + opts.rate : "");
      let viaAuto = false;
      const p = guard(k, text, () => { viaAuto = true; return raw.autoPlay(text, opts); });
      if (viaAuto) return p;
      return p.then((r) => (r && "blocked" in r ? r : { ok: !!(r && r.ok), blocked: false, source: r && r.source }));
    };
    if (raw.speakSlow) S.speakSlow = function (text, opts) { return guard("slow", text, () => raw.speakSlow(text, opts)); };
    S.speakTurns = function (texts, gap, opts) { return guard("turns", texts, () => raw.speakTurns(texts, gap, opts)); };
    S.stop = function () { last = { key: "", t: 0, p: null }; return raw.stop(); };
  })();
})(window);
