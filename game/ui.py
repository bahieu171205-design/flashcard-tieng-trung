import math
import os

import pygame

W, H = 1180, 780

# màu lấy từ file PDF từ vựng Boya: navy #1F3A5F và 5 màu thanh điệu
C = {
    "bg": (243, 246, 250),
    "surface": (255, 255, 255),
    "ink": (31, 36, 48),
    "muted": (85, 101, 122),
    "line": (223, 230, 239),
    "shadow": (221, 228, 238),
    "accent": (31, 58, 95),
    "accent_dark": (21, 41, 68),
    "accent_soft": (227, 234, 244),
    "tint": (236, 242, 250),  # nền nhạt cho các bài trong phạm vi đang chọn
    "good": (22, 128, 60),
    "good_soft": (220, 241, 227),
    "bad": (214, 40, 57),
    "bad_soft": (251, 227, 229),
    "gold": (184, 115, 10),
    "gold_soft": (252, 239, 214),
    "white": (255, 255, 255),
}
# thanh 1–4 và thanh nhẹ (0)
TONE = {1: (214, 40, 57), 2: (180, 83, 9), 3: (22, 128, 60), 4: (43, 95, 217), 0: (107, 107, 107)}

# Chữ Hán: Hiragino Sans GB; chữ Latin/tiếng Việt/pinyin: SF (font hệ thống).
_LATIN = ["/System/Library/Fonts/SFNS.ttf", "/Library/Fonts/Arial Unicode.ttf"]
_CJK = ["/System/Library/Fonts/Hiragino Sans GB.ttc", "/System/Library/Fonts/STHeiti Medium.ttc",
        "/Library/Fonts/Arial Unicode.ttf"]


def _first(paths):
    return next((p for p in paths if os.path.exists(p)), None)


LATIN_PATH, CJK_PATH = _first(_LATIN), _first(_CJK)
_fonts = {}
_text_cache = {}


class _FaceFont:
    """Một mặt chữ trong file .ttc (vd Hiragino W6), dùng như pygame.font.Font."""

    def __init__(self, path, size, index):
        import pygame.freetype
        pygame.freetype.init()
        self.f = pygame.freetype.Font(path, size, font_index=index)
        self.f.origin = True
        self.asc = self.f.get_sized_ascender()
        self.desc = -self.f.get_sized_descender()

    def get_ascent(self):
        return self.asc

    def render(self, s, _aa, color):
        w = int(sum(m[4] for m in self.f.get_metrics(s) if m)) + 2
        surf = pygame.Surface((max(1, w), self.asc + self.desc), pygame.SRCALPHA)
        self.f.render_to(surf, (0, self.asc), s, color)
        return surf


def font(kind, size, bold=False):
    k = (kind, size, bold)
    if k not in _fonts:
        if kind == "cjk":
            # pygame tô đậm giả làm dính nét chữ Hán, nên dùng mặt chữ đậm thật W6 của Hiragino
            if bold and CJK_PATH.endswith("Hiragino Sans GB.ttc"):
                _fonts[k] = _FaceFont(CJK_PATH, size, 2)
            else:
                _fonts[k] = pygame.font.Font(CJK_PATH, size)
        else:
            f = pygame.font.Font(LATIN_PATH, size)
            f.bold = bold
            _fonts[k] = f
    return _fonts[k]


def is_cjk(ch):
    o = ord(ch)
    return 0x2E80 <= o <= 0x9FFF or 0xF900 <= o <= 0xFAFF or 0xFF00 <= o <= 0xFFEF


def _runs(text):
    runs = []
    for ch in text:
        kind = "cjk" if is_cjk(ch) else "latin"
        if runs and runs[-1][0] == kind:
            runs[-1][1] += ch
        else:
            runs.append([kind, ch])
    return runs


def text(s, size, color, bold=False):
    """Render chuỗi có thể lẫn chữ Hán và chữ Latin, căn chung đường chân chữ."""
    k = (s, size, color, bold)
    surf = _text_cache.get(k)
    if surf is not None:
        return surf
    parts = [(font(kind, size, bold), run) for kind, run in _runs(s)] or [(font("latin", size, bold), "")]
    rendered = [(f, f.render(run, True, color)) for f, run in parts]
    asc = max(f.get_ascent() for f, _ in rendered)
    h = max(asc - f.get_ascent() + r.get_height() for f, r in rendered)
    surf = pygame.Surface((sum(r.get_width() for _, r in rendered), h), pygame.SRCALPHA)
    x = 0
    for f, r in rendered:
        surf.blit(r, (x, asc - f.get_ascent()))
        x += r.get_width()
    if len(_text_cache) > 4000:
        _text_cache.clear()
    _text_cache[k] = surf
    return surf


def pinyin(py, size, bold=False, color=None):
    """Pinyin tô màu theo thanh điệu từng âm tiết (giống sách); phần không phải pinyin dùng `color`."""
    from .pinyin import tone_runs
    k = ("py", py, size, bold, color)
    surf = _text_cache.get(k)
    if surf is None:
        parts = [text(s, size, TONE[t] if t is not None else (color or C["ink"]), bold) for s, t in tone_runs(py)]
        surf = pygame.Surface((sum(p.get_width() for p in parts), max(p.get_height() for p in parts)), pygame.SRCALPHA)
        x = 0
        for p in parts:
            surf.blit(p, (x, 0))
            x += p.get_width()
        _text_cache[k] = surf
    return surf


def draw_pinyin(surf, py, size, pos, anchor="topleft", bold=False):
    t = pinyin(py, size, bold)
    r = t.get_rect(**{anchor: pos})
    surf.blit(t, r)
    return r


def draw_text(surf, s, size, color, pos, anchor="topleft", bold=False):
    t = text(s, size, color, bold)
    r = t.get_rect(**{anchor: pos})
    if anchor in ("center", "midleft", "midright") and s and all(is_cjk(ch) for ch in s):
        # font chữ Hán có khoảng trống dưới lớn: căn giữa theo nét chữ thật
        bb = t.get_bounding_rect()
        if bb.h:
            r.y = pos[1] - bb.centery
    surf.blit(t, r)
    return r


def text_width(s, size, bold=False):
    return text(s, size, (0, 0, 0), bold).get_width()


def wrap(s, size, max_w, bold=False):
    """Ngắt dòng theo từ; từ quá dài (vd chữ Hán liền) thì ngắt theo ký tự."""
    lines, cur = [], ""
    for word in s.split(" "):
        cand = (cur + " " + word).strip()
        if text_width(cand, size, bold) <= max_w:
            cur = cand
            continue
        if cur:
            lines.append(cur)
        cur = ""
        for ch in word:
            if text_width(cur + ch, size, bold) > max_w and cur:
                lines.append(cur)
                cur = ""
            cur += ch
    if cur:
        lines.append(cur)
    return lines or [""]


def draw_wrapped(surf, s, size, color, center_x, top, max_w, bold=False, line_gap=4, max_lines=None):
    lines = wrap(s, size, max_w, bold)
    if max_lines and len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = fit(lines[-1] + "…", size, max_w, bold)
    y = top
    for line in lines:
        r = draw_text(surf, line, size, color, (center_x, y), "midtop", bold)
        y = r.bottom + line_gap
    return y


def wrapped_height(s, size, max_w, bold=False, line_gap=4):
    lines = wrap(s, size, max_w, bold)
    return sum(text(l, size, (0, 0, 0), bold).get_height() for l in lines) + line_gap * (len(lines) - 1)


def fit(s, size, max_w, bold=False):
    """Cắt chuỗi kèm dấu … cho vừa bề rộng."""
    if text_width(s, size, bold) <= max_w:
        return s
    while s and text_width(s + "…", size, bold) > max_w:
        s = s[:-1]
    return s + "…"


def fit_size(s, start, max_w, min_size=16, bold=False):
    size = start
    while size > min_size and text_width(s, size, bold) > max_w:
        size -= 4
    return size


def rrect(surf, color, rect, radius=14, border=0, border_color=None, shadow=0):
    rect = pygame.Rect(rect)
    if shadow:
        pygame.draw.rect(surf, C["shadow"], rect.move(0, shadow), border_radius=radius)
    pygame.draw.rect(surf, color, rect, border_radius=radius)
    if border:
        pygame.draw.rect(surf, border_color or C["line"], rect, border, border_radius=radius)


def bar(surf, rect, frac, color, bg=None):
    rect = pygame.Rect(rect)
    pygame.draw.rect(surf, bg or C["line"], rect, border_radius=rect.h // 2)
    if frac > 0:
        r = rect.copy()
        r.w = max(r.h, int(rect.w * min(1, frac)))
        pygame.draw.rect(surf, color, r, border_radius=rect.h // 2)


def heart(surf, center, size, color):
    x, y = center
    r = size * .28
    pygame.draw.circle(surf, color, (x - r, y - r * .4), r)
    pygame.draw.circle(surf, color, (x + r, y - r * .4), r)
    pygame.draw.polygon(surf, color, [(x - 2 * r, y - r * .2), (x + 2 * r, y - r * .2), (x, y + size * .5)])


def hearts(surf, right, cy, lives, total=3):
    for i in range(total):
        cx = right - 18 - (total - 1 - i) * 34
        heart(surf, (cx, cy), 26, C["bad"] if i < lives else C["line"])


def check_icon(surf, center, color, s=1.0):
    x, y = center
    pygame.draw.lines(surf, color, False, [(x - 7 * s, y), (x - 2 * s, y + 5 * s), (x + 8 * s, y - 6 * s)], max(2, int(3 * s)))


STYLES = {
    "default": (C["surface"], C["ink"], C["line"], (238, 243, 249)),
    "primary": (C["accent"], C["white"], C["accent"], C["accent_dark"]),
    "good": (C["good_soft"], C["good"], C["good_soft"], (204, 234, 214)),
    "bad": (C["bad_soft"], C["bad"], C["bad_soft"], (246, 210, 214)),
    "ghost": (C["bg"], C["ink"], C["line"], C["surface"]),
}


class PressTracker:
    """Nhấn chuột trên vùng nào thì vùng đó 'lún' xuống; thả chuột vẫn trong vùng mới tính là bấm
    (kéo ra ngoài rồi thả để hủy)."""

    def __init__(self):
        self.armed = False

    def clicked(self, e, rect):
        if getattr(e, "button", 1) != 1:
            return False
        if e.type == pygame.MOUSEBUTTONDOWN:
            self.armed = rect.collidepoint(e.pos)
        elif e.type == pygame.MOUSEBUTTONUP:
            hit = self.armed and rect.collidepoint(e.pos)
            self.armed = False
            return hit
        return False


class Button:
    def __init__(self, rect, label, style="default", size=18, bold=True, enabled=True, hint=None):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.style = style
        self.size = size
        self.bold = bold
        self.enabled = enabled
        self.hint = hint  # chữ nhỏ ở góc, vd phím tắt
        self.press = PressTracker()

    def hovered(self):
        return self.enabled and self.rect.collidepoint(pygame.mouse.get_pos())

    def pressed(self):
        return self.enabled and self.press.armed and self.hovered()

    def clicked(self, e):
        return self.enabled and self.press.clicked(e, self.rect)

    def draw(self, surf):
        bg, fg, border, hover_bg = STYLES[self.style]
        r = self.rect.copy()
        shadow = 2 if self.enabled else 0
        if self.pressed():
            # đang nhấn: nút lún xuống, mất bóng
            bg = hover_bg
            r = r.move(0, 2).inflate(-4, -2)
            shadow = 0
        elif self.hovered():
            bg = hover_bg
            r.y -= 1
        if not self.enabled:
            bg, fg = C["bg"], C["line"]
        rrect(surf, bg, r, radius=12, border=1, border_color=border, shadow=shadow)
        draw_text(surf, fit(self.label, self.size, r.w - 20, self.bold), self.size, fg, r.center, "center", self.bold)
        if self.hint:
            draw_text(surf, self.hint, 12, fg if self.style != "default" else C["muted"], (r.right - 9, r.bottom - 6), "bottomright")


class Toggle(Button):
    """Nút dạng 'viên thuốc' có trạng thái bật/tắt."""

    def __init__(self, rect, label, on=False, size=15):
        super().__init__(rect, label, size=size, bold=False)
        self.on = on

    def draw(self, surf):
        r = self.rect.move(0, 2).inflate(-4, -2) if self.pressed() else self.rect
        bg = C["accent_soft"] if self.on else (C["surface"] if not self.hovered() else (238, 243, 249))
        rrect(surf, bg, r, radius=r.h // 2, border=1, border_color=C["accent"] if self.on else C["line"])
        draw_text(surf, self.label, self.size, C["accent"] if self.on else C["ink"], r.center, "center", self.on)


class Particles:
    def __init__(self):
        self.items = []

    def burst(self, pos, color, n=18, speed=260):
        import random
        for _ in range(n):
            a = random.uniform(0, math.tau)
            v = random.uniform(.3, 1) * speed
            self.items.append([pos[0], pos[1], math.cos(a) * v, math.sin(a) * v - 80, random.uniform(.4, .8), color])

    def update(self, dt):
        for p in self.items:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[3] += 500 * dt
            p[4] -= dt
        self.items = [p for p in self.items if p[4] > 0]

    def draw(self, surf):
        for x, y, _, _, life, color in self.items:
            pygame.draw.circle(surf, color, (int(x), int(y)), max(1, int(6 * life)))


class Popups:
    """Chữ nổi lên rồi mờ dần (điểm cộng, thông báo)."""

    def __init__(self):
        self.items = []

    def add(self, s, pos, color, size=22, life=1.0):
        self.items.append([s, list(pos), color, size, life, life])

    def update(self, dt):
        for p in self.items:
            p[1][1] -= 40 * dt
            p[4] -= dt
        self.items = [p for p in self.items if p[4] > 0]

    def draw(self, surf):
        for s, pos, color, size, life, total in self.items:
            t = text(s, size, color, True).copy()
            t.set_alpha(int(255 * min(1, life / total * 2)))
            surf.blit(t, t.get_rect(center=pos))
