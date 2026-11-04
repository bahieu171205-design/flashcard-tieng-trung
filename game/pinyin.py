import json
import re
import unicodedata
from functools import lru_cache

from .data import ROOT

_src = (ROOT / "syllables.js").read_text(encoding="utf-8")
SYLLABLES = frozenset(json.loads(re.search(r"\[.*\]", _src, re.S).group(0)))

_MARK_TONE = {"̄": 1, "́": 2, "̌": 3, "̀": 4}
_LETTER = re.compile(r"[A-Za-zÀ-ɏ̀-ͯ]+")


def _plain(ch):
    """Một chữ cái pinyin -> (chữ thường không dấu, thanh điệu 0-4)."""
    tone = 0
    out = []
    for c in unicodedata.normalize("NFD", ch):
        if c in _MARK_TONE:
            tone = _MARK_TONE[c]
        else:
            out.append(c)
    base = unicodedata.normalize("NFC", "".join(out)).lower()
    return ("ü" if base == "v" else base), tone


def _mark_index(s):
    """Vị trí nguyên âm mang dấu thanh theo quy tắc: a/e trước, 'ou' dấu ở o, còn lại nguyên âm cuối."""
    for v in "ae":
        if v in s:
            return s.index(v)
    if "ou" in s:
        return s.index("o")
    vowels = [i for i, c in enumerate(s) if c in "iouü"]
    return vowels[-1] if vowels else -1


def _valid(base, tones, i, j):
    s = "".join(base[i:j])
    if s not in SYLLABLES:
        if not (s.endswith("r") and len(s) > 1 and s[:-1] in SYLLABLES):  # 儿 hóa: nǎr, wánr…
            return False
        s = s[:-1]
    marked = [k for k in range(i, j) if tones[k]]
    if len(marked) > 1:
        return False
    return not marked or marked[0] - i == _mark_index(s)


@lru_cache(maxsize=4096)
def _split_word(word):
    """Tách một cụm chữ cái liền nhau thành [(chuỗi gốc, thanh)], hoặc None nếu không tách được."""
    pairs = [_plain(c) for c in word]
    base = [p[0] for p in pairs]
    tones = [p[1] for p in pairs]
    n = len(word)
    best = [None] * (n + 1)  # best[i] = (số âm tiết, vị trí cắt) cho phần word[i:]
    best[n] = (0, n)
    for i in range(n - 1, -1, -1):
        for j in range(n, i, -1):  # ưu tiên âm tiết dài
            if best[j] is not None and _valid(base, tones, i, j):
                cand = (best[j][0] + 1, j)
                if best[i] is None or cand[0] < best[i][0]:
                    best[i] = cand
    if best[0] is None:
        return None
    out, i = [], 0
    while i < n:
        j = best[i][1]
        out.append((word[i:j], max(tones[i:j])))
        i = j
    return out


def tone_runs(py):
    """Chia chuỗi pinyin thành [(đoạn chữ, thanh)], thanh 0 = thanh nhẹ, None = không phải pinyin (dấu câu, 'OK'…)."""
    py = unicodedata.normalize("NFC", py)
    runs, pos = [], 0
    for m in _LETTER.finditer(py):
        if m.start() > pos:
            runs.append((py[pos:m.start()], None))
        parts = _split_word(m.group(0))
        runs.extend(parts if parts else [(m.group(0), None)])
        pos = m.end()
    if pos < len(py):
        runs.append((py[pos:], None))
    return runs
