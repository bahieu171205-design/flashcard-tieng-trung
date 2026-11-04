import math
import random

import pygame

from . import ui
from .scene import Scene
from .ui import C, H, W, Button, Toggle, draw_text, rrect

CARD = pygame.Rect(0, 0, 780, 400)
CARD.center = (W // 2, 340)
FLIP_TIME = 0.3
LEAVE_TIME = 0.2   # thẻ trượt ra
ENTER_TIME = 0.2   # thẻ mới hiện vào


def stack(surf, items, center_x, center_y, gap=10):
    """Vẽ các surface chồng dọc, căn giữa theo cả hai chiều."""
    total = sum(i.get_height() for i in items) + gap * (len(items) - 1)
    y = center_y - total // 2
    for i in items:
        surf.blit(i, i.get_rect(midtop=(center_x, y)))
        y += i.get_height() + gap


def wrapped_lines(s, size, color, max_w, bold=False, max_lines=3):
    lines = ui.wrap(s, size, max_w, bold)[:max_lines]
    return [ui.text(l, size, color, bold) for l in lines]


class FlashcardScene(Scene):
    def __init__(self, app, title, words, back):
        super().__init__(app)
        self.title, self.back = title, back
        self.btn_back = Button((40, 28, 130, 42), "← Trở về", "ghost", 16)
        self.t_shuffle = Toggle((W - 40 - 120, 32, 120, 34), "Trộn thẻ")
        by = CARD.bottom + 36
        self.btn_prev = Button((CARD.x, by, 70, 60), "←", size=22)
        self.btn_bad = Button((CARD.x + 84, by, 296, 60), "Chưa thuộc", "bad", size=19, hint="1")
        self.btn_good = Button((CARD.right - 84 - 296, by, 296, 60), "Đã thuộc", "good", size=19, hint="2")
        self.btn_next = Button((CARD.right - 70, by, 70, 60), "→", size=22)
        self.end_btns = []
        self.start(words)

    # ---------- trạng thái ----------
    def start(self, words):
        self.source = list(words)
        self.deck = list(words)
        if self.t_shuffle.on:
            random.shuffle(self.deck)
        self.i = 0
        self.flipped = False
        self.anim = 1.0
        self.wrong = []
        self.faces = {}
        self.done = not self.deck
        self.leaving = None  # [hướng, màu viền hoặc None, thời gian] khi thẻ đang trượt ra
        self.enter = 1.0     # 0→1: thẻ mới hiện dần vào

    @property
    def cur(self):
        return self.deck[self.i] if self.i < len(self.deck) else None

    def flip(self):
        if self.done or self.leaving:
            return
        self.flipped = not self.flipped
        self.anim = 0.0

    def move(self, d):
        n = self.i + d
        if 0 <= n <= len(self.deck):
            self.i, self.flipped, self.anim, self.enter = n, False, 1.0, 0.0
            if n == len(self.deck):
                self.finish()

    def leave(self, d, tone=None):
        """Thẻ trượt ra trong LEAVE_TIME rồi mới sang thẻ khác; trong lúc đó bỏ qua thao tác."""
        if not self.leaving and 0 <= self.i + d <= len(self.deck):
            self.leaving = [d, tone, 0.0]

    def mark(self, known):
        w = self.cur
        if not w or self.leaving:
            return
        self.app.progress.set_known(w, known)
        self.faces.clear()
        if known:
            self.wrong = [x for x in self.wrong if x.key != w.key]
            self.app.audio.play("ok")
        elif w not in self.wrong:
            self.wrong.append(w)
            self.app.audio.play("click")
        self.app.save()
        self.leave(1, "good" if known else "bad")

    def finish(self):
        self.done = True
        self.app.audio.play("end")
        cx = W // 2
        self.end_btns = []
        if self.wrong:
            self.end_btns.append((Button((cx - 330, 470, 210, 54), "Ôn lại từ chưa thuộc", "primary", 16),
                                  lambda: self.start(self.wrong)))
        self.end_btns.append((Button((cx - 105, 470, 210, 54), "Ôn lại cả bộ", size=16), lambda: self.start(self.source)))
        self.end_btns.append((Button((cx + 120, 470, 210, 54), "Trở về", "ghost", 16), self.back))

    # ---------- sự kiện ----------
    def handle(self, e):
        if self.btn_back.clicked(e) or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
            return self.back()
        if self.t_shuffle.clicked(e):
            self.t_shuffle.on = not self.t_shuffle.on
            return self.start(self.source)
        if self.done:
            for b, fn in self.end_btns:
                if b.clicked(e):
                    return fn()
            if e.type == pygame.KEYDOWN and e.key in (pygame.K_RETURN, pygame.K_SPACE) and self.end_btns:
                self.end_btns[0][1]()
            return
        if e.type == pygame.KEYDOWN:
            k = e.key
            if k in (pygame.K_SPACE, pygame.K_UP, pygame.K_DOWN, pygame.K_RETURN):
                self.flip()
            elif k == pygame.K_RIGHT:
                self.leave(1)
            elif k == pygame.K_LEFT:
                self.leave(-1)
            elif k in (pygame.K_1, pygame.K_KP1):
                self.mark(False)
            elif k in (pygame.K_2, pygame.K_KP2):
                self.mark(True)
        elif self.btn_prev.clicked(e):
            self.leave(-1)
        elif self.btn_next.clicked(e):
            self.leave(1)
        elif self.btn_bad.clicked(e):
            self.mark(False)
        elif self.btn_good.clicked(e):
            self.mark(True)
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and CARD.collidepoint(e.pos):
            self.flip()

    def update(self, dt):
        self.anim = min(1.0, self.anim + dt / FLIP_TIME)
        self.enter = min(1.0, self.enter + dt / ENTER_TIME)
        if self.leaving:
            self.leaving[2] += dt
            if self.leaving[2] >= LEAVE_TIME:
                d = self.leaving[0]
                self.leaving = None
                self.move(d)

    # ---------- vẽ ----------
    def face(self, w, back_side):
        reverse = self.app.settings["reverse"]
        known = self.app.progress.is_known(w)
        k = (w.key, back_side, reverse, known)
        if k in self.faces:
            return self.faces[k]
        s = pygame.Surface(CARD.size, pygame.SRCALPHA)
        rrect(s, C["surface"], s.get_rect(), radius=24, border=1)
        draw_text(s, f"Bài {w.bai}" + (" · Tên riêng" if w.rieng else ""), 14, C["muted"], (24, 18))
        if known:
            pill = pygame.Rect(0, 14, 96, 28)
            pill.right = CARD.w - 18
            rrect(s, C["good_soft"], pill, radius=14)
            draw_text(s, "Đã thuộc", 14, C["good"], pill.center, "center", True)
        cx, cy = CARD.w // 2, CARD.h // 2
        if not back_side:
            if reverse:
                stack(s, wrapped_lines(w.vi, 40, C["ink"], CARD.w - 120, True), cx, cy - 10)
            else:
                size = ui.fit_size(w.hz, 150, CARD.w - 100, 48)
                draw_text(s, w.hz, size, C["ink"], (cx, cy - 8), "center")
            draw_text(s, "Bấm vào thẻ hoặc nhấn Space để lật", 14, C["muted"], (cx, CARD.h - 20), "midbottom")
        else:
            items = [ui.text(w.hz, ui.fit_size(w.hz, 96, CARD.w - 160, 40), C["ink"]),
                     ui.pinyin(w.py, 32, True)]
            items += wrapped_lines(w.vi, 27, C["ink"], CARD.w - 140, max_lines=2)
            if w.hv:
                items.append(ui.text(f"Hán Việt: {w.hv}", 17, C["muted"]))
            stack(s, items, cx, cy, gap=12)
        self.faces[k] = s
        return s

    def draw(self, s):
        self.btn_back.draw(s)
        draw_text(s, ui.fit(self.title, 22, W - 520, True), 22, C["ink"], (190, 38), bold=True)
        n = len(self.deck)
        draw_text(s, f"{min(self.i + 1, n)}/{n}", 18, C["muted"], (W - 180, 49), "midright", True)
        self.t_shuffle.draw(s)
        ui.bar(s, (40, 92, W - 80, 6), self.i / n if n else 1, C["accent"])

        if self.done:
            return self.draw_end(s)

        w = self.cur
        p = self.anim
        # nửa đầu: mặt cũ co lại; nửa sau: mặt mới giãn ra
        side = self.flipped if p >= 0.5 else not self.flipped
        scale = abs(math.cos(p * math.pi)) if p < 1 else 1
        face = self.face(w, side)
        cw = max(2, int(CARD.w * scale))
        r = pygame.Rect(0, 0, cw, CARD.h)
        r.center = CARD.center
        img = face if cw == CARD.w else pygame.transform.smoothscale(face, (cw, CARD.h))
        alpha = 255
        if self.leaving:
            # chuyển thẻ: trượt sang ngang; đánh dấu: bay lên với viền xanh (thuộc) / đỏ (chưa thuộc)
            d, tone, t = self.leaving
            q = min(1.0, t / LEAVE_TIME) ** 2
            r = r.move(0, -int(110 * q)) if tone else r.move(-d * int(320 * q), 0)
            alpha = int(255 * (1 - q))
            if tone:
                img = img.copy()
                pygame.draw.rect(img, C[tone], img.get_rect(), 5, border_radius=24)
        elif self.enter < 1:
            # thẻ mới hiện dần, hơi phóng từ 96% lên 100%
            q = 1 - (1 - self.enter) ** 3
            k = .96 + .04 * q
            img = pygame.transform.smoothscale(img, (int(r.w * k), int(r.h * k)))
            r = img.get_rect(center=CARD.center)
            alpha = int(255 * q)
        if alpha >= 255:
            pygame.draw.rect(s, C["shadow"], r.move(0, 5), border_radius=24)
        else:
            img = img.copy() if img is face else img
            img.set_alpha(alpha)
        s.blit(img, r)

        self.btn_prev.enabled = self.i > 0
        for b in (self.btn_prev, self.btn_bad, self.btn_good, self.btn_next):
            b.draw(s)
        draw_text(s, "Space lật thẻ  ·  ← → chuyển thẻ  ·  1 chưa thuộc  ·  2 đã thuộc  ·  Esc trở về",
                  14, C["muted"], (W // 2, H - 30), "center")

    def draw_end(self, s):
        panel = pygame.Rect(0, 0, 760, 400)
        panel.center = (W // 2, 380)
        rrect(s, C["surface"], panel, radius=24, border=1, shadow=5)
        draw_text(s, "Xong lượt ôn!", 36, C["ink"], (W // 2, panel.y + 60), "center", True)
        n, bad = len(self.deck), len(self.wrong)
        msg = (f"{n - bad}/{n} từ đã thuộc · còn {bad} từ cần ôn lại" if bad
               else f"Bạn đã thuộc cả {n} từ. Giỏi lắm!" if n else "Không có từ nào để ôn.")
        draw_text(s, msg, 19, C["muted"], (W // 2, panel.y + 110), "center")
        if bad:
            chips = "   ".join(f"{w.hz}" for w in self.wrong[:12]) + ("  …" if bad > 12 else "")
            draw_text(s, ui.fit(chips, 26, panel.w - 80), 26, C["bad"], (W // 2, panel.y + 170), "center")
        for b, _ in self.end_btns:
            b.draw(s)
