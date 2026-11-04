import pygame

from . import ui
from .scene import Scene
from .ui import C, H, W, Button, PressTracker, Toggle, draw_text, fit, rrect


class HomeScene(Scene):
    COLS, GAP, TOP, TILE_H = 6, 14, 214, 92
    RANGE_BOX = pygame.Rect(40, 108, W - 80, 62)
    # ô chọn "Học từ [− Bài a +] đến [− Bài b +]": vị trí x của nút − mỗi ô
    STEP_X = (126, 346)

    def __init__(self, app):
        super().__init__(app)
        self.confirm_reset = 0
        # nút đổi sách/tập ngay dưới tên app
        self.book_label = f"{app.vol.book} · {app.vol.ten}"
        self.book_btn = pygame.Rect(114, 66, ui.text_width(self.book_label, 15, True) + 46, 30)
        self.book_press = PressTracker()
        cy = self.RANGE_BOX.centery
        self.steps = []  # (nút −, ô số, nút +) cho "từ" và "đến"
        for x in self.STEP_X:
            self.steps.append((Button((x, cy - 20, 40, 40), "−", size=20),
                               pygame.Rect(x + 44, cy - 20, 76, 40),
                               Button((x + 124, cy - 20, 40, 40), "+", size=20)))
        right = self.RANGE_BOX.right - 12
        self.btn_unknown = Button((right - 250, cy - 23, 250, 46), "", size=16)
        self.btn_mix = Button((right - 250 - 12 - 200, cy - 23, 200, 46), "", "primary", size=16)
        self.btn_reset = Button((W - 40 - 210, H - 40, 210, 34), "Xóa tiến độ tập này", "ghost", size=14)
        # lưới bài: 6 cột, chiều cao ô co lại nếu tập có nhiều bài hơn
        tw = (W - 80 - self.GAP * (self.COLS - 1)) // self.COLS
        rows = -(-len(app.lessons) // self.COLS)
        th = min(self.TILE_H, (H - 50 - self.TOP - self.GAP * (rows - 1)) // rows)
        self.tiles = []
        for i, lesson in enumerate(app.lessons):
            col, row = i % self.COLS, i // self.COLS
            rect = pygame.Rect(40 + col * (tw + self.GAP), self.TOP + row * (th + self.GAP), tw, th)
            self.tiles.append((lesson, rect))
        self.tile_press = [PressTracker() for _ in self.tiles]

    # ---------- phạm vi bài (theo số bài của sách) ----------
    def range_words(self):
        a, b = self.app.range
        return [w for l in self.app.lessons if a <= l.bai <= b for w in l.words]

    def set_range(self, which, value):
        """which = 0: 'từ bài', 1: 'đến bài'. Luôn giữ từ ≤ đến."""
        rng, lessons = self.app.range, self.app.lessons
        rng[which] = max(lessons[0].bai, min(lessons[-1].bai, value))
        if rng[0] > rng[1]:
            rng[1 - which] = rng[which]
        self.app.save()

    def handle(self, e):
        app = self.app
        a, b = app.range
        span = f"bài {a}" if a == b else f"bài {a}–{b}"
        if self.book_press.clicked(e, self.book_btn):
            app.audio.play("click")
            return app.go(BookScene(app))
        for which, (minus, box, plus) in enumerate(self.steps):
            if minus.clicked(e):
                return self.set_range(which, app.range[which] - 1)
            if plus.clicked(e):
                return self.set_range(which, app.range[which] + 1)
            if e.type == pygame.MOUSEWHEEL and box.inflate(88, 0).collidepoint(pygame.mouse.get_pos()):
                return self.set_range(which, app.range[which] + (1 if e.y > 0 else -1))
        if self.btn_unknown.clicked(e):
            ws = self.range_words()
            app.go(ModeScene(app, f"Từ chưa thuộc · {span}", [w for w in ws if not app.progress.is_known(w)],
                             f"unknown{a}-{b}", ws))
        elif self.btn_mix.clicked(e):
            if a == b:
                l = next(x for x in app.lessons if x.bai == a)
                app.go(ModeScene(app, f"Bài {l.bai} · {l.ten}", l.words, f"bai{l.bai}", l.words))
            else:
                ws = self.range_words()
                app.go(ModeScene(app, f"Trộn {span}", ws, f"range{a}-{b}", ws))
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
        self.btn_reset.label = "Bấm lần nữa để xóa" if self.confirm_reset else "Xóa tiến độ tập này"
        self.btn_reset.style = "bad" if self.confirm_reset else "ghost"

    def draw(self, s):
        app = self.app
        rrect(s, C["accent"], (40, 30, 58, 58), radius=14)
        draw_text(s, "学", 36, C["white"], (69, 60), "center", True)
        draw_text(s, "Flashcard Tiếng Trung", 30, C["ink"], (114, 28), bold=True)
        # nút đổi sách/tập (dạng viên thuốc có mũi tên ⌄)
        bb = self.book_btn
        hov = bb.collidepoint(pygame.mouse.get_pos())
        r = bb.inflate(-4, -2) if hov and self.book_press.armed else bb
        rrect(s, C["surface"], r, radius=r.h // 2, border=1, border_color=C["accent"] if hov else C["line"])
        draw_text(s, self.book_label, 15, C["ink"] if hov else C["muted"], (r.x + 14, r.centery), "midleft", True)
        cx, cy = r.right - 18, r.centery - 2
        pygame.draw.lines(s, C["muted"], False, [(cx - 5, cy - 2), (cx, cy + 3), (cx + 5, cy - 2)], 2)

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

        # ô chọn phạm vi bài
        a, b = app.range
        lo, hi = app.lessons[0].bai, app.lessons[-1].bai
        box = self.RANGE_BOX
        rrect(s, C["surface"], box, radius=16, border=1, shadow=2)
        draw_text(s, "Học từ", 16, C["ink"], (box.x + 16, box.centery), "midleft", True)
        draw_text(s, "đến", 16, C["ink"], (self.STEP_X[1] - 14, box.centery), "midright", True)
        for which, (minus, vbox, plus) in enumerate(self.steps):
            val = (a, b)[which]
            minus.enabled, plus.enabled = val > lo, val < hi
            rrect(s, C["bg"], vbox, radius=10, border=1)
            draw_text(s, f"Bài {val}", 17, C["ink"], vbox.center, "center", True)
            minus.draw(s)
            plus.draw(s)
        ws = self.range_words()
        unk = sum(not app.progress.is_known(w) for w in ws)
        draw_text(s, f"{len(ws)} từ", 15, C["muted"], (self.STEP_X[1] + 182, box.centery), "midleft")
        self.btn_mix.label = f"Học bài {a}" if a == b else f"Trộn bài {a}–{b}"
        self.btn_unknown.label = f"Ôn từ chưa thuộc ({unk})" if unk else "Đã thuộc hết phạm vi này"
        self.btn_unknown.enabled = unk > 0
        for btn in (self.btn_mix, self.btn_unknown, self.btn_reset):
            btn.draw(s)
        draw_text(s, "Chọn bài học", 18, C["ink"], (40, 184), bold=True)

        full = a == lo and b == hi
        mouse = pygame.mouse.get_pos()
        for (lesson, rect), press in zip(self.tiles, self.tile_press):
            n = len(lesson.words)
            k = sum(app.progress.is_known(w) for w in lesson.words)
            hov = rect.collidepoint(mouse)
            down = hov and press.armed
            done = n and k == n
            # tô nền các bài trong phạm vi (khi đã thu hẹp phạm vi)
            bg = C["tint"] if not full and a <= lesson.bai <= b else C["surface"]
            r = rect.inflate(-8, -6) if down else rect.move(0, -3) if hov else rect
            border = C["accent"] if hov else C["good"] if done else C["line"]
            rrect(s, bg, r, radius=14, border=2 if (hov or done) else 1, border_color=border,
                  shadow=0 if down else 4 if hov else 2)
            draw_text(s, f"Bài {lesson.bai}", 14, C["muted"], (r.x + 14, r.y + 9))
            draw_text(s, fit(lesson.ten, 19, r.w - 28, True), 19, C["ink"], (r.x + 14, r.y + 30), bold=True)
            draw_text(s, f"{k}/{n} từ đã thuộc", 13, C["muted"], (r.x + 14, r.bottom - 34))
            ui.bar(s, (r.x + 14, r.bottom - 14, r.w - 28, 6), k / n if n else 0, C["good"])
            if done:
                ui.check_icon(s, (r.right - 20, r.y + 20), C["good"])


class BookScene(Scene):
    CARD_W, CARD_H, GAP = 268, 150, 16

    def __init__(self, app):
        super().__init__(app)
        self.btn_back = Button((40, 28, 130, 42), "← Trở về", "ghost", 16)
        # nhóm các tập theo sách, mỗi sách một hàng thẻ
        self.cards = []  # (tập, ô)
        self.headings = []  # (tên sách, y)
        y = 100
        books = []
        for v in app.volumes:
            if not books or books[-1][0] != v.book:
                books.append((v.book, []))
            books[-1][1].append(v)
        per_row = (W - 80 + self.GAP) // (self.CARD_W + self.GAP)
        for book, vols in books:
            self.headings.append((book, y))
            y += 34
            for i, v in enumerate(vols):
                x = 40 + (i % per_row) * (self.CARD_W + self.GAP)
                row_y = y + (i // per_row) * (self.CARD_H + self.GAP)
                self.cards.append((v, pygame.Rect(x, row_y, self.CARD_W, self.CARD_H)))
            y += (-(-len(vols) // per_row)) * (self.CARD_H + self.GAP) + 14
        self.note_y = y + 6
        self.presses = [PressTracker() for _ in self.cards]

    def handle(self, e):
        app = self.app
        if self.btn_back.clicked(e) or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
            return app.go(HomeScene(app))
        for (v, rect), press in zip(self.cards, self.presses):
            if press.clicked(e, rect):
                app.audio.play("click")
                app.use_volume(v.id)
                app.save()
                return app.go(HomeScene(app))

    def draw(self, s):
        app = self.app
        self.btn_back.draw(s)
        draw_text(s, "Chọn sách và tập", 24, C["ink"], (190, 36), bold=True)
        for book, y in self.headings:
            draw_text(s, book, 18, C["ink"], (40, y), bold=True)
        mouse = pygame.mouse.get_pos()
        for (v, rect), press in zip(self.cards, self.presses):
            ws = v.words
            k = sum(app.progress.is_known(w) for w in ws)
            cur = v.id == app.vol.id
            hov = rect.collidepoint(mouse)
            r = rect.inflate(-8, -6) if hov and press.armed else rect.move(0, -3) if hov else rect
            border = C["good"] if cur else C["accent"] if hov else C["line"]
            rrect(s, C["surface"], r, radius=16, border=2 if (cur or hov) else 1, border_color=border, shadow=3)
            draw_text(s, v.ten, 22, C["ink"], (r.x + 18, r.y + 16), bold=True)
            if cur:
                pill = pygame.Rect(0, r.y + 14, 92, 26)
                pill.right = r.right - 14
                rrect(s, C["good_soft"], pill, radius=13)
                draw_text(s, "Đang học", 13, C["good"], pill.center, "center", True)
            if v.goc:
                draw_text(s, v.goc, 16, C["muted"], (r.x + 18, r.y + 50))
            draw_text(s, f"{len(v.lessons)} bài · {len(ws)} từ", 15, C["muted"], (r.x + 18, r.y + 78))
            ui.bar(s, (r.x + 18, r.y + 106, r.w - 36, 6), k / len(ws) if ws else 0, C["good"])
            draw_text(s, f"{k} từ đã thuộc", 14, C["muted"], (r.x + 18, r.y + 120))
        draw_text(s, "Muốn học tập khác hoặc sách khác? Gửi file từ vựng (PDF, Excel, ảnh…) để thêm vào app.",
                  14, C["muted"], (40, self.note_y))


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
                pygame.draw.rect(s, (240, 244, 250), row)
            cy = y + self.ROW // 2
            draw_text(s, fit(w.hz, 28, 220), 28, C["ink"], (a.x + 18, cy), "midleft")
            ui.draw_pinyin(s, w.py, 18, (a.x + 250, cy), "midleft")
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
