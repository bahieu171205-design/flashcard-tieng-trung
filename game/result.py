import pygame

from . import ui
from .scene import Scene
from .ui import C, W, Button, draw_text, rrect


class ResultScene(Scene):
    def __init__(self, app, heading, score, best, is_record, stats, wrong, replay, review, back):
        super().__init__(app)
        self.heading, self.score, self.best, self.is_record = heading, score, best, is_record
        self.stats, self.wrong = stats, wrong
        self.panel = pygame.Rect(0, 0, 860, 660)
        self.panel.center = (W // 2, 400)
        by = self.panel.bottom - 84
        self.buttons = [(Button((0, by, 200, 56), "Chơi lại", "primary", 18, hint="Enter"), replay)]
        if wrong:
            self.buttons.append((Button((0, by, 240, 56), "Lật thẻ các từ sai", size=17), lambda: review(wrong)))
        self.buttons.append((Button((0, by, 210, 56), "Chọn chế độ khác", "ghost", 17), back))
        total = sum(b.rect.w for b, _ in self.buttons) + 16 * (len(self.buttons) - 1)
        x = W // 2 - total // 2
        for b, _ in self.buttons:
            b.rect.x = x
            x += b.rect.w + 16
        self.t = 0

    def handle(self, e):
        if e.type == pygame.KEYDOWN:
            if e.key in (pygame.K_RETURN, pygame.K_SPACE):
                return self.buttons[0][1]()
            if e.key == pygame.K_ESCAPE:
                return self.buttons[-1][1]()
        for b, fn in self.buttons:
            if b.clicked(e):
                return fn()

    def update(self, dt):
        self.t += dt

    def draw(self, s):
        p = self.panel
        rrect(s, C["surface"], p, radius=26, border=1, shadow=6)
        cx = p.centerx
        draw_text(s, self.heading, 34, C["ink"], (cx, p.y + 50), "center", True)
        # điểm đếm dần lên trong 0.8 giây đầu
        shown = int(self.score * min(1, self.t / 0.8))
        draw_text(s, str(shown), 76, C["accent"], (cx, p.y + 132), "center", True)
        if self.is_record and self.score:
            pill = pygame.Rect(0, 0, 170, 34)
            pill.center = (cx, p.y + 195)
            rrect(s, C["gold_soft"], pill, radius=17)
            draw_text(s, "Kỷ lục mới!", 17, C["gold"], pill.center, "center", True)
        else:
            draw_text(s, f"Kỷ lục: {self.best}", 17, C["muted"], (cx, p.y + 195), "center")

        bw = 180
        x = cx - (len(self.stats) * bw + (len(self.stats) - 1) * 14) // 2
        for label, val in self.stats:
            r = pygame.Rect(x, p.y + 230, bw, 74)
            rrect(s, C["bg"], r, radius=14)
            draw_text(s, str(val), 26, C["ink"], (r.centerx, r.y + 26), "center", True)
            draw_text(s, label, 14, C["muted"], (r.centerx, r.y + 56), "center")
            x += bw + 14

        top = p.y + 330
        if self.wrong:
            draw_text(s, f"Từ cần ôn lại ({len(self.wrong)})", 18, C["ink"], (p.x + 50, top), bold=True)
            col_w = (p.w - 100 - 20) // 2
            for i, w in enumerate(self.wrong[:10]):
                x = p.x + 50 + (i % 2) * (col_w + 20)
                y = top + 36 + (i // 2) * 40
                hz = draw_text(s, w.hz, 22, C["bad"], (x, y))
                py = ui.draw_pinyin(s, w.py, 16, (hz.right + 10, hz.centery), "midleft")
                draw_text(s, ui.fit(w.vi, 16, x + col_w - py.right - 12), 16, C["ink"], (py.right + 10, hz.centery), "midleft")
            if len(self.wrong) > 10:
                draw_text(s, f"… và {len(self.wrong) - 10} từ nữa", 15, C["muted"], (cx, top + 240), "center")
        else:
            draw_text(s, "Không sai câu nào. Tuyệt vời!", 20, C["good"], (cx, top + 80), "center", True)
        for b, _ in self.buttons:
            b.draw(s)
