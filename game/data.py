"""Đọc từ vựng từ vocab.js và lưu tiến độ học vào progress.json."""
import json
import re
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VOCAB_FILE = ROOT / "vocab.js"
PROGRESS_FILE = ROOT / "progress.json"


@dataclass(frozen=True)
class Word:
    bai: int
    hz: str
    py: str
    vi: str
    hv: str
    rieng: bool

    @property
    def key(self):
        return f"{self.bai}|{self.hz}|{self.vi}"


@dataclass
class Lesson:
    bai: int
    ten: str
    words: list


def load_lessons():
    """vocab.js là một mảng JS; đổi sang JSON rồi đọc."""
    src = VOCAB_FILE.read_text(encoding="utf-8")
    src = "\n".join(line for line in src.splitlines() if not line.lstrip().startswith("//"))
    src = src.replace("const LESSONS =", "", 1).strip().rstrip(";")
    src = re.sub(r'([{,]\s*)(bai|ten|tu|rieng)\s*:', r'\1"\2":', src)
    src = re.sub(r",(\s*[\]}])", r"\1", src)
    lessons = []
    for raw in json.loads(src):
        words = [Word(raw["bai"], hz, py, vi, hv, False) for hz, py, vi, hv in raw["tu"]]
        words += [Word(raw["bai"], hz, py, vi, "", True) for hz, py, vi in raw.get("rieng", [])]
        lessons.append(Lesson(raw["bai"], raw["ten"], words))
    return lessons


class Progress:
    def __init__(self):
        self.known = set()
        self.best = {}
        try:
            data = json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
            self.known = set(data.get("known", []))
            self.best = data.get("best", {})
        except (OSError, ValueError):
            pass

    def is_known(self, w):
        return w.key in self.known

    def set_known(self, w, value):
        if value:
            self.known.add(w.key)
        else:
            self.known.discard(w.key)

    def best_score(self, mode, scope):
        return self.best.get(f"{mode}|{scope}", 0)

    def submit(self, mode, scope, score):
        """Lưu điểm; trả về True nếu là kỷ lục mới."""
        k = f"{mode}|{scope}"
        if score > self.best.get(k, 0):
            self.best[k] = score
            return True
        return False

    def reset(self):
        self.known.clear()

    def save(self):
        data = {"known": sorted(self.known), "best": self.best}
        tmp = PROGRESS_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(PROGRESS_FILE)
