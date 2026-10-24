/* Hebrew transliteration helper (copied from js/engine.js for stories/chat) */
(function (global) {
// --- Hebrew transliteration for whole sentences (rule-based, Greek) ---
  function heFinals(s) {
    return s.replace(/מ$/, "ם").replace(/נ$/, "ן").replace(/פ$/, "ף").replace(/צ$/, "ץ").replace(/\uE001/g, "פ");
  }
  function wordToHe(w) {
    // keep diaeresis as marker "¨" after vowel, strip other accents
    let s = w.toLowerCase().normalize("NFD").replace(/\u0308/g, "¨").replace(/[\u0301\u0300\u0342]/g, "´").replace(/[\u0300-\u036f]/g, "").replace(/ς/g, "σ");
    const VOW = "αεηιουω";
    const FRONT = /^(ε|η|ι|υ|αι|ει|οι)/;
    const VOICELESS = "θκξπστφχψ";
    let out = "";
    let i = 0;
    const isStart = () => out === "";
    while (i < s.length) {
      const c = s[i], n = s[i + 1] || "", di = s[i + 2] === "¨" || n === "¨";
      const rest = s.slice(i);
      const atEnd = (k) => s.slice(i + k).replace(/[´¨]/g, "") === "";
      // vowel digraphs
      if (!di && (rest.startsWith("αυ") || rest.startsWith("ευ"))) {
        const nx = s.slice(i + 2).replace(/^[´¨]+/, "")[0] || "";
        const f = !nx || VOICELESS.includes(nx);
        out += (isStart() ? "א" : "") + (f ? (atEnd(2) ? "ף" : "\uE001") : "ב");
        i += 2; continue;
      }
      if (!di && rest.startsWith("ου")) { out += isStart() ? "או" : "ו"; i += 2; continue; }
      if (!di && rest.startsWith("αι")) { out += isStart() ? "א" : atEnd(2) ? "ה" : ""; i += 2; continue; }
      if (!di && (rest.startsWith("ει") || rest.startsWith("οι") || rest.startsWith("υι"))) { out += isStart() ? "אי" : "י"; i += 2; continue; }
      if (c === "¨" || c === "´") { i++; continue; }
      if (c === "α" || c === "ε") {
        const nxt = s.slice(i + 1).replace(/^[´¨]+/, "")[0] || "";
        const prevV = /[יו]$/.test(out) && VOW.includes(s.slice(0, i).replace(/[´¨]/g, "").slice(-1));
        out += isStart() ? "א" : atEnd(1) ? "ה" : (prevV || VOW.includes(nxt)) ? "א" : "";
        i++; continue;
      }
      if (c === "ο" || c === "ω") { out += isStart() ? "או" : "ו"; i++; continue; }
      if (c === "ι" || c === "η" || c === "υ") { out += isStart() ? "אי" : "י"; i++; continue; }
      // consonant clusters
      if (rest.startsWith("μπ")) { out += isStart() ? "ב" : "מב"; i += 2; continue; }
      if (rest.startsWith("ντ")) { out += isStart() ? "ד" : "נד"; i += 2; continue; }
      if (rest.startsWith("γκ")) { out += isStart() ? "ג" : "נג"; i += 2; continue; }
      if (rest.startsWith("γγ")) { out += "נג"; i += 2; continue; }
      if (rest.startsWith("γχ")) { out += "נח"; i += 2; continue; }
      if (rest.startsWith("τσ")) { out += "צ"; i += 2; continue; }
      if (rest.startsWith("τζ")) { out += "ג׳"; i += 2; continue; }
      if (c === "γ" && /^(ει|οι|ι|η|υ)´?/.test(s.slice(i + 1).replace(/´/g, ""))) { out += "י"; const r = s.slice(i + 1); i += 1 + (/^(ει|οι)/.test(r) ? 2 : 1); while (s[i] === "´" || s[i] === "¨") i++; continue; }
      if (c === "γ") { out += FRONT.test(s.slice(i + 1)) ? "י" : "ג"; i++; continue; }
      const M = { β:"ב",δ:"ד",ζ:"ז",θ:"ת",κ:"ק",λ:"ל",μ:"מ",ν:"נ",ξ:"קס",π:"\uE001",ρ:"ר",σ:"ס",τ:"ט",φ:"פ",χ:"ח",ψ:"\uE001ס" };
      if (M[c] != null) { out += M[c]; i++; continue; }
      if (VOW.includes(c)) { i++; continue; }
      out += c; i++;
    }
    return heFinals(out);
  }
  function sentenceHeTranslit(text) {
    return String(text || "").replace(/;/g, "?").split(/\s+/).map(function (tok) {
      const m = tok.match(/^([^\p{L}]*)([\p{L}\p{M}-]+)([^\p{L}]*)$/u);
      if (!m) return tok.replace(/[^?!,.…]/g, "");
      return m[2].split("-").map(wordToHe).join("־") + m[3].replace(/[^?!,]/g, "");
    }).filter(Boolean).join(" ");
  }

  
  global.RLHeTl = function (text) { return sentenceHeTranslit(text); };
})(window);
