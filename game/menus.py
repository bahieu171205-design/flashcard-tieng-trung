"""Màn hình chính (30 bài), màn chọn chế độ chơi và danh sách từ."""
import pygame

from . import ui
from .scene import Scene
from .ui import C, H, W, Button, PressTracker, Toggle, draw_text, fit, rrect


class HomeScene(Scene):
    COLS, GAP, TOP, TILE_H = 6, 14, 214, 98

    def __init__(self, app):
        super().__init__(app)
        self.confirm_reset = 0
        self.btn_unknown = Button((40, 116, 262, 46), "Ôn tất cả từ chưa thuộc", "primary")
        self.btn_mix = Button((314, 116, 200, 46), "Trộn cả 30 bài")
        self.btn_reset = Button((W - 40 - 230, 116, 230, 46), "Xóa tiến độ", "ghost", size=16)
        tw = (W - 80 - self.GAP * (self.COLS - 1)) // self.COLS
        self.tiles = []
        for i, lesson in enumerate(app.lessons):
            col, row = i % self.COLS, i // self.COLS
            rect = pygame.Rect(40 + col * (tw + self.GAP), self.TOP + row * (self.TILE_H + self.GAP), tw, self.TILE_H)
            self.tiles.append((lesson, rect))
        self.tile_press = [PressTracker() for _ in self.tiles]

    def handle(self, e):
        app = self.app
        if self.btn_unknown.clicked(e):
            words = [w for w in app.all_words if not app.progress.is_known(w)]
            app.go(ModeScene(app, "Từ chưa thuộc · cả 30 bài", words, "unknown", app.all_words))
        elif self.btn_mix.clicked(e):
            app.go(ModeScene(app, "Cả 30 bài", app.all_words, "all", app.all_words))
        elif self.btn_reset.clicked(e):
            if self.confirm_reset > 0:
                app.progress.reset()
                app.save()
                self.confirm_reset = 0
            else:
                self.confirm_reset = 3
        elif e.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            for (lesson, rect), press in zip(self.tiles, self.tile_press):
                if press.clicked(e, rect):
                    app.audio.play("click")
                    return app.go(ModeScene(app, f"Bài {lesson.bai} · {lesson.ten}", lesson.words,
                                            f"bai{lesson.bai}", lesson.words))

    def update(self, dt):
        self.confirm_reset = max(0, self.confirm_reset - dt)
        self.btn_reset.label = "Bấm lần nữa để xóa" if self.confirm_reset else "Xóa tiến độ"
        self.btn_reset.style = "bad" if self.confirm_reset else "ghost"

    def draw(self, s):
        app = self.app
        rrect(s, C["accent"], (40, 30, 58, 58), radius=14)
        draw_text(s, "学", 36, C["white"], (69, 60), "center", True)
        draw_text(s, "Flashcard Tiếng Trung", 30, C["ink"], (114, 28), bold=True)
        draw_text(s, "Boya 博雅汉语 · Sơ cấp I · 30 bài", 16, C["muted"], (114, 68))

        total = len(app.all_words)
        known = sum(app.progress.is_known(w) for w in app.all_words)
        x = W - 40
        for label, val, color in (("chưa thuộc", total - known, C["accent"]), ("đã thuộc", known, C["good"]),
                                  ("tổng số từ", total, C["ink"])):
            r = pygame.Rect(0, 28, 128, 62)
            r.right = x
            rrect(s, C["surface"], r, radius=12, border=1)
            draw_text(s, str(val), 24, color, (r.x + 14, r.y + 8), bold=True)
            draw_text(s, label, 13, C["muted"], (r.x + 14, r.y + 38))
            x = r.x - 10

        self.btn_unknown.enabled = known < total
        for b in (self.btn_unknown, self.btn_mix, self.btn_reset):
            b.draw(s)
        draw_text(s, "Chọn bài học", 18, C["ink"], (40, 182), bold=True)

        mouse = pygame.mouse.get_pos()
        for (lesson, rect), press in zip(self.tiles, self.tile_press):
            n = len(lesson.words)
            k = sum(app.progress.is_known(w) for w in lesson.words)
            hov = rect.collidepoint(mouse)
            down = hov and press.armed
            done = n and k == n
            r = rect.inflate(-8, -6) if down else rect.move(0, -3) if hov else rect
            border = C["accent"] if hov else C["good"] if done else C["line"]
            rrect(s, C["surface"], r, radius=14, border=2 if (hov or done) else 1, border_color=border,
                  shadow=0 if down else 4 if hov else 2)
            draw_text(s, f"Bài {lesson.bai}", 14, C["muted"], (r.x + 14, r.y + 11))
            draw_text(s, fit(lesson.ten, 19, r.w - 28, True), 19, C["ink"], (r.x + 14, r.y + 33), bold=True)
            draw_text(s, f"{k}/{n} từ đã thuộc", 13, C["muted"], (r.x + 14, r.bottom - 36))
            ui.bar(s, (r.x + 14, r.bottom - 15, r.w - 28, 6), k / n if n else 0, C["good"])
            if done:
                ui.check_icon(s, (r.right - 20, r.y + 20), C["good"])


MODES = [
    ("flash", "卡", "Lật thẻ", "Lật thẻ để học, tự đánh dấu từ nào đã thuộc, từ nào chưa.", "accent"),
    ("quiz", "问", "Trắc nghiệm", "Chọn nghĩa đúng trong 4 đáp án. 3 mạng, đếm giờ, cộng điểm combo.", "gold"),
    ("rain", "雨", "Mưa chữ", "Chữ Hán rơi xuống — bấm đúng chữ mang nghĩa ở dưới trước khi chạm đất.", "good"),
    ("list", "表", "Danh sách từ", "Xem toàn bộ từ của bài: chữ Hán, pinyin, Hán Việt và nghĩa.", "muted"),
]


class ModeScene(Scene):
    def __init__(self, app, title, words, scope, pool):
        super().__init__(app)
        self.title, self.all, self.scope, self.pool = title, words, scope, pool
        self.btn_back = Button((40, 28, 130, 42), "← Trở về", "ghost", 16)
        self.has_rieng = any(w.rieng for w in words)
        self.t_rieng = Toggle((40, 176, 170, 36), "Gồm tên riêng", app.settings["rieng"])
        dx = 222 if self.has_rieng else 40
        self.t_dir = Toggle((dx, 176, 220, 36), "", app.settings["reverse"])
        cw = (W - 80 - 3 * 20) // 4
        self.cards = [(m, pygame.Rect(40 + i * (cw + 20), 244, cw, 330)) for i, m in enumerate(MODES)]
        self.card_press = [PressTracker() for _ in self.cards]

    def words(self):
        return [w for w in self.all if self.app.settings["rieng"] or not w.rieng]

    def start(self, mode):
        from .flashcard import FlashcardScene
        from .quiz import QuizScene
        from .rain import RainScene
        app, ws = self.app, self.words()
        back = lambda: app.go(self)  # noqa: E731
        app.audio.play("click")
        if mode == "flash":
            app.go(FlashcardScene(app, self.title, ws, back))
        elif mode == "quiz":
            app.go(QuizScene(app, self.title, ws, self.pool, self.scope, back))
        elif mode == "rain":
            app.go(RainScene(app, self.title, ws, self.pool, self.scope, back))
        else:
            app.go(ListScene(app, self.title, ws, back))

    def handle(self, e):
        if self.btn_back.clicked(e) or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
            self.app.go(HomeScene(self.app))
        elif self.has_rieng and self.t_rieng.clicked(e):
            self.app.settings["rieng"] = self.t_rieng.on = not self.t_rieng.on
        elif self.t_dir.clicked(e):
            self.app.settings["reverse"] = self.t_dir.on = not self.t_dir.on
        elif e.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP) and self.words():
            for ((mode, *_), rect), press in zip(self.cards, self.card_press):
                if press.clicked(e, rect):
                    return self.start(mode)

    def draw(self, s):
        app = self.app
        ws = self.words()
        self.btn_back.draw(s)
        draw_text(s, fit(self.title, 30, W - 80, True), 30, C["ink"], (40, 90), bold=True)
        k = sum(app.progress.is_known(w) for w in ws)
        draw_text(s, f"{len(ws)} từ · {k} đã thuộc · {len(ws) - k} chưa thuộc", 16, C["muted"], (40, 136))
        if self.has_rieng:
            self.t_rieng.draw(s)
        self.t_dir.label = "Hỏi: Việt → Hán" if self.t_dir.on else "Hỏi: Hán → Việt"
        self.t_dir.draw(s)

        mouse = pygame.mouse.get_pos()
        for ((mode, icon, name, desc, col), rect), press in zip(self.cards, self.card_press):
            hov = bool(ws) and rect.collidepoint(mouse)
            down = hov and press.armed
            r = rect.inflate(-10, -10) if down else rect.move(0, -4) if hov else rect
            rrect(s, C["surface"], r, radius=18, border=2 if hov else 1,
                  border_color=C[col] if hov else C["line"], shadow=0 if down else 5 if hov else 2)
            pygame.draw.circle(s, C[col], (r.centerx, r.y + 72), 42)
            draw_text(s, icon, 40, C["white"], (r.centerx, r.y + 73), "center", True)
            draw_text(s, name, 23, C["ink"], (r.centerx, r.y + 132), "midtop", True)
            ui.draw_wrapped(s, desc, 15, C["muted"], r.centerx, r.y + 172, r.w - 44)
            if mode in ("quiz", "rain"):
                best = app.progress.best_score(mode, self.scope)
                draw_text(s, f"Kỷ lục: {best}" if best else "Chưa có kỷ lục", 15,
                          C["gold"] if best else C["muted"], (r.centerx, r.bottom - 26), "center", True)
            elif mode == "flash":
                draw_text(s, f"{k}/{len(ws)} đã thuộc", 15, C["good"], (r.centerx, r.bottom - 26), "center", True)
        if not ws:
            # không có từ nào: phủ mờ các thẻ để thấy rõ là không bấm được
            for _, rect in self.cards:
                veil = pygame.Surface(rect.size, pygame.SRCALPHA)
                pygame.draw.rect(veil, (*C["bg"], 170), veil.get_rect(), border_radius=18)
                s.blit(veil, rect)
            draw_text(s, "Không còn từ nào ở đây — bạn đã thuộc hết!", 18, C["good"], (W // 2, 620), "center", True)
        draw_text(s, "Trong lúc chơi, nhấn Esc để quay lại màn này.", 14, C["muted"], (W // 2, H - 34), "center")


class ListScene(Scene):
    ROW = 58
    AREA = pygame.Rect(40, 136, W - 80, H - 136 - 28)
    COLS = (("Chữ Hán", 18), ("Pinyin", 250), ("Hán Việt", 470), ("Nghĩa", 660))

    def __init__(self, app, title, words, back):
        super().__init__(app)
        self.title, self.words, self.back = title, words, back
        self.btn_back = Button((40, 28, 130, 42), "← Trở về", "ghost", 16)
        self.scroll = 0

    def max_scroll(self):
        return max(0, len(self.words) * self.ROW - (self.AREA.h - 44))

    def handle(self, e):
        if self.btn_back.clicked(e) or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
            self.back()
        elif e.type == pygame.MOUSEWHEEL:
            self.scroll = min(self.max_scroll(), max(0, self.scroll - e.y * 40))
        elif e.type == pygame.KEYDOWN and e.key in (pygame.K_DOWN, pygame.K_UP, pygame.K_PAGEDOWN, pygame.K_PAGEUP):
            step = {pygame.K_DOWN: 58, pygame.K_UP: -58, pygame.K_PAGEDOWN: 400, pygame.K_PAGEUP: -400}[e.key]
            self.scroll = min(self.max_scroll(), max(0, self.scroll + step))

    def draw(self, s):
        self.btn_back.draw(s)
        draw_text(s, fit(self.title, 26, W - 260, True), 26, C["ink"], (190, 34), bold=True)
        draw_text(s, f"{len(self.words)} từ · cuộn chuột để xem thêm", 15,
                  C["muted"], (40, 100))
        a = self.AREA
        rrect(s, C["surface"], a, radius=14, border=1)
        for label, x in self.COLS:
            draw_text(s, label, 14, C["muted"], (a.x + x, a.y + 14), bold=True)
        pygame.draw.line(s, C["line"], (a.x, a.y + 44), (a.right - 1, a.y + 44))
        body = pygame.Rect(a.x + 1, a.y + 45, a.w - 2, a.h - 46)
        s.set_clip(body)
        first = self.scroll // self.ROW
        mouse = pygame.mouse.get_pos()
        for i in range(first, min(len(self.words), first + body.h // self.ROW + 2)):
            w = self.words[i]
            y = body.y + i * self.ROW - self.scroll
            row = pygame.Rect(body.x, y, body.w, self.ROW)
            if row.collidepoint(mouse) and body.collidepoint(mouse):
                pygame.draw.rect(s, (250, 245, 236), row)
            cy = y + self.ROW // 2
            draw_text(s, fit(w.hz, 28, 220), 28, C["ink"], (a.x + 18, cy), "midleft")
            draw_text(s, fit(w.py, 18, 205), 18, C["accent"], (a.x + 250, cy), "midleft")
            draw_text(s, fit(w.hv or "tên riêng", 16, 180), 16, C["muted"], (a.x + 470, cy), "midleft")
            draw_text(s, fit(w.vi, 17, a.w - 660 - 60), 17, C["ink"], (a.x + 660, cy), "midleft")
            if self.app.progress.is_known(w):
                ui.check_icon(s, (a.right - 30, cy), C["good"])
            pygame.draw.line(s, C["line"], (row.x + 12, row.bottom - 1), (row.right - 12, row.bottom - 1))
        s.set_clip(None)
        if self.max_scroll():
            track_h = body.h - 8
            thumb_h = max(40, track_h * body.h // (len(self.words) * self.ROW))
            ty = body.y + 4 + (track_h - thumb_h) * self.scroll // self.max_scroll()
            pygame.draw.rect(s, C["line"], (a.right - 9, ty, 5, thumb_h), border_radius=3)
