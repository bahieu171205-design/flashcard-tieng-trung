import json
import re
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VOCAB_FILE = ROOT / "vocab.js"
PROGRESS_FILE = ROOT / "progress.json"
# tiến độ lưu trước khi có chức năng chọn sách/tập đều thuộc tập này
OLD_VOL = "boya-sc1"


@dataclass(frozen=True)
class Word:
    vol: str
    bai: int
    hz: str
    py: str
    vi: str
    hv: str
    rieng: bool

    @property
    def key(self):
        return f"{self.vol}|{self.bai}|{self.hz}|{self.vi}"


@dataclass
class Lesson:
    bai: int
    ten: str
    words: list


@dataclass
class Volume:
    id: str
    book: str
    ten: str
    goc: str
    lessons: list = field(default_factory=list)

    @property
    def words(self):
        return [w for l in self.lessons for w in l.words]


def load_volumes():
    """vocab.js là `const BOOKS = [...]` với khóa có ngoặc kép, nên đọc được như JSON."""
    src = VOCAB_FILE.read_text(encoding="utf-8")
    src = "\n".join(line for line in src.splitlines() if not line.lstrip().startswith("//"))
    src = src.replace("const BOOKS =", "", 1).strip().rstrip(";")
    src = re.sub(r",(\s*[\]}])", r"\1", src)  # phòng khi sửa tay để thừa dấu phẩy cuối
    volumes = []
    for book in json.loads(src):
        for t in book["taps"]:
            v = Volume(t["id"], book["ten"], t["ten"], t.get("goc", ""))
            for raw in t["lessons"]:
                words = [Word(v.id, raw["bai"], hz, py, vi, hv, False) for hz, py, vi, hv in raw["tu"]]
                words += [Word(v.id, raw["bai"], hz, py, vi, "", True) for hz, py, vi in raw.get("rieng", [])]
                v.lessons.append(Lesson(raw["bai"], raw["ten"], words))
            volumes.append(v)
    return volumes


class Progress:
    def __init__(self):
        self.known = set()
        self.best = {}
        self.ranges = {}  # id tập -> [từ bài, đến bài]
        self.vol = OLD_VOL  # tập đang học
        try:
            data = json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        # chuyển dữ liệu kiểu cũ (chỉ có 1 tập) sang tập OLD_VOL
        self.known = {f"{OLD_VOL}|{k}" if re.match(r"\d+\|", k) else k for k in data.get("known", [])}
        for k, v in data.get("best", {}).items():
            mode, _, scope = k.partition("|")
            self.best[k if ":" in scope else f"{mode}|{OLD_VOL}:{scope}"] = v
        self.ranges = data.get("ranges", {})
        if "range" in data and OLD_VOL not in self.ranges:
            self.ranges[OLD_VOL] = list(data["range"])
        self.vol = data.get("vol", OLD_VOL)

    def is_known(self, w):
        return w.key in self.known

    def set_known(self, w, value):
        if value:
            self.known.add(w.key)
        else:
            self.known.discard(w.key)

    def best_score(self, mode, scope):
        return self.best.get(f"{mode}|{self.vol}:{scope}", 0)

    def submit(self, mode, scope, score):
        """Lưu điểm; trả về True nếu là kỷ lục mới."""
        k = f"{mode}|{self.vol}:{scope}"
        if score > self.best.get(k, 0):
            self.best[k] = score
            return True
        return False

    def reset(self):
        """Xóa tiến độ của tập đang học."""
        self.known = {k for k in self.known if not k.startswith(f"{self.vol}|")}

    def save(self):
        data = {"known": sorted(self.known), "best": self.best, "ranges": self.ranges, "vol": self.vol}
        tmp = PROGRESS_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(PROGRESS_FILE)
