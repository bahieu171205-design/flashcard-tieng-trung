"""Chế độ trắc nghiệm: 4 đáp án, 3 mạng, đếm giờ, combo."""
import math
import random

import pygame

from . import ui
from .scene import Scene
from .ui import C, H, W, Button, Particles, Popups, draw_text, rrect

Q_TIME = 12.0
QCARD = pygame.Rect(0, 0, 760, 240)
QCARD.midtop = (W // 2, 106)
OPT_W, OPT_H, OPT_GAP = 372, 108, 16


class QuizScene(Scene):
    def __init__(self, app, title, words, pool, scope, back):
        super().__init__(app)
        self.title, self.words, self.scope, self.back = title, words, scope, back
        self.pool = pool if len({w.vi for w in pool}) >= 8 else app.all_words
        self.reverse = app.settings["reverse"]
        self.btn_back = Button((40, 28, 120, 42), "← Thoát", "ghost", 16)
        self.particles, self.popups = Particles(), Popups()
        self.opt_rects = []
        x0 = W // 2 - OPT_W - OPT_GAP // 2
        y0 = QCARD.bottom + 42
        for i in range(4):
            self.opt_rects.append(pygame.Rect(x0 + (i % 2) * (OPT_W + OPT_GAP), y0 + (i // 2) * (OPT_H + OPT_GAP),
                                              OPT_W, OPT_H))
        self.reset()

    def reset(self):
        self.deck = random.sample(self.words, len(self.words))
        self.idx = -1
        self.lives, self.score, self.combo, self.best_combo, self.correct = 3, 0, 0, 0, 0
        self.wrong = []
        self.fx_t = 0  # thời gian kể từ lúc trả lời, dùng cho hiệu ứng đáp án
        self.next_question()

    # ---------- logic ----------
    def distractors(self, q):
        key = (lambda w: w.hz) if self.reverse else (lambda w: w.vi)
        seen, out = {key(q)}, []
        for src in (self.pool, self.app.all_words):
            cands = [w for w in src if w.hz != q.hz and w.vi != q.vi]
            random.shuffle(cands)
            for w in cands:
                if key(w) not in seen:
                    seen.add(key(w))
                    out.append(w)
                    if len(out) == 3:
                        return out
        return out

    def next_question(self):
        self.idx += 1
        if self.idx >= len(self.deck) or self.lives <= 0:
            return self.finish()
        self.q = self.deck[self.idx]
        self.options = [self.q] + self.distractors(self.q)
        random.shuffle(self.options)
        self.answered = None
        self.timer = Q_TIME
        self.wait = 0

    def answer(self, i):
        if self.answered is not None or i >= len(self.options):
            return
        self.answered = i
        self.fx_t = 0
        q = self.q
        audio = self.app.audio
        if i >= 0 and self.options[i] is q:
            self.combo += 1
            self.best_combo = max(self.best_combo, self.combo)
            self.correct += 1
            gain = 100 + 20 * (self.combo - 1) + int(self.timer * 5)
            self.score += gain
            self.popups.add(f"+{gain}", (W // 2, 74), C["good"], 24)
            self.particles.burst(self.opt_rects[i].center, C["good"])
            audio.play("ok")
            self.app.progress.set_known(q, True)
            self.wait = 1.2
        else:
            self.combo = 0
            self.lives -= 1
            self.wrong.append(q)
            audio.play("bad")
            self.app.progress.set_known(q, False)
            self.wait = 2.2

    def finish(self):
        app = self.app
        app.save()
        best = app.progress.best_score("quiz", self.scope)
        record = app.progress.submit("quiz", self.scope, self.score)
        app.save()
        app.audio.play("end")
        answered = self.correct + len(self.wrong)
        from .flashcard import FlashcardScene
        from .result import ResultScene
        replay = lambda: app.go(QuizScene(app, self.title, self.words, self.pool, self.scope, self.back))  # noqa: E731
        review = lambda ws: app.go(FlashcardScene(app, "Ôn các từ sai", ws, self.back))  # noqa: E731
        stats = [("câu đúng", f"{self.correct}/{answered}"),
                 ("combo cao nhất", self.best_combo),
                 ("độ chính xác", f"{round(100 * self.correct / max(1, answered))}%")]
        heading = "Hết mạng!" if self.lives <= 0 else "Hoàn thành!"
        app.go(ResultScene(app, f"{heading}  ·  Trắc nghiệm", self.score, best, record, stats, self.wrong,
                           replay, review, self.back))

    # ---------- sự kiện ----------
    def handle(self, e):
        if self.btn_back.clicked(e) or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
            return self.back()
        if e.type == pygame.KEYDOWN:
            keys = {pygame.K_1: 0, pygame.K_2: 1, pygame.K_3: 2, pygame.K_4: 3,
                    pygame.K_KP1: 0, pygame.K_KP2: 1, pygame.K_KP3: 2, pygame.K_KP4: 3}
            if e.key in keys:
                self.answer(keys[e.key])
            elif e.key in (pygame.K_SPACE, pygame.K_RETURN) and self.answered is not None:
                self.next_question()
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            if self.answered is None:
                for i, r in enumerate(self.opt_rects[:len(self.options)]):
                    if r.collidepoint(e.pos):
                        return self.answer(i)
            elif any(r.collidepoint(e.pos) for r in self.opt_rects):
                return self.next_question()

    def update(self, dt):
        if self.answered is None:
            self.timer -= dt
            if self.timer <= 0:
                self.timer = 0
                self.answer(-1)
        else:
            self.wait -= dt
            if self.wait <= 0:
                self.next_question()
        self.fx_t += dt
        self.particles.update(dt)
        self.popups.update(dt)

    # ---------- vẽ ----------
    def draw(self, s):
        self.btn_back.draw(s)
        draw_text(s, ui.fit(self.title, 18, 330, True), 18, C["ink"], (176, 34), bold=True)
        draw_text(s, f"Câu {min(self.idx + 1, len(self.deck))}/{len(self.deck)}", 15, C["muted"], (176, 58))
        draw_text(s, f"{self.score}", 34, C["ink"], (W // 2, 46), "center", True)
        draw_text(s, "điểm", 13, C["muted"], (W // 2, 72), "center")
        if self.combo >= 2:
            pill = pygame.Rect(0, 0, 108, 30)
            pill.midleft = (W // 2 + 70, 46)
            rrect(s, C["gold_soft"], pill, radius=15)
            draw_text(s, f"Combo x{self.combo}", 15, C["gold"], pill.center, "center", True)
        ui.hearts(s, W - 40, 48, self.lives)

        # thẻ câu hỏi
        card = QCARD
        rrect(s, C["surface"], card, radius=24, border=1, shadow=4)
        q, done = self.q, self.answered is not None
        if not self.reverse:
            size = ui.fit_size(q.hz, 104 if not done else 80, card.w - 120, 40)
            hz = draw_text(s, q.hz, size, C["ink"], (card.centerx, card.y + (card.h // 2 - 10 if not done else 82)),
                           "center")
            if done:
                py = draw_text(s, q.py, 28, C["accent"], (card.centerx, hz.bottom + 8), "midtop", True)
                if q.hv:
                    draw_text(s, f"Hán Việt: {q.hv}", 16, C["muted"], (card.centerx, py.bottom + 8), "midtop")
            else:
                draw_text(s, "Nghĩa của từ này là gì?", 15, C["muted"], (card.centerx, card.bottom - 16), "midbottom")
        else:
            top = card.y + (34 if done else 70)
            y = ui.draw_wrapped(s, q.vi, 32, C["ink"], card.centerx, top, card.w - 100, True, max_lines=2)
            if done:
                hz = draw_text(s, q.hz, 54, C["ink"], (card.centerx, y + 8), "midtop")
                draw_text(s, q.py, 24, C["accent"], (card.centerx, hz.bottom + 4), "midtop", True)
            else:
                draw_text(s, "Chọn chữ Hán đúng", 15, C["muted"], (card.centerx, card.bottom - 16), "midbottom")

        # thanh thời gian
        frac = self.timer / Q_TIME
        col = C["good"] if frac > .5 else C["gold"] if frac > .25 else C["bad"]
        ui.bar(s, (QCARD.x, QCARD.bottom + 16, QCARD.w, 10), frac, col)

        # 4 đáp án
        mouse = pygame.mouse.get_pos()
        t = self.fx_t
        for i, (w, r) in enumerate(zip(self.options, self.opt_rects)):
            bg, border, fg = C["surface"], C["line"], C["ink"]
            if done:
                if w is q:
                    bg, border, fg = C["good_soft"], C["good"], C["good"]
                    if i == self.answered:
                        # chọn đúng: nảy lên 5% rồi về
                        k = math.sin(math.pi * min(1, t / 0.3)) * .05
                        r = r.inflate(int(r.w * k), int(r.h * k))
                    elif t < 1.2:
                        # chọn sai: đáp án đúng nhấp nháy viền để mắt tìm tới
                        glow = r.inflate(14, 14)
                        if math.sin(t * math.tau / 0.6) > 0:
                            rrect(s, C["good_soft"], glow, radius=20)
                elif i == self.answered:
                    bg, border, fg = C["bad_soft"], C["bad"], C["bad"]
                    # đáp án sai vừa chọn rung, biên độ giảm dần
                    amp = 10 * max(0, 1 - t / 0.45)
                    r = r.move(int(math.sin(t * 45) * amp), 0)
                else:
                    fg = C["muted"]
            elif r.collidepoint(mouse):
                down = pygame.mouse.get_pressed()[0]
                r = r.move(0, 2).inflate(-4, -2) if down else r.move(0, -2)
                border = C["accent"]
            rrect(s, bg, r, radius=16, border=2, border_color=border, shadow=3)
            badge = pygame.Rect(r.x + 14, r.y + 14, 28, 28)
            rrect(s, C["bg"], badge, radius=8)
            draw_text(s, str(i + 1), 15, C["muted"], badge.center, "center", True)
            if self.reverse:
                draw_text(s, w.hz, ui.fit_size(w.hz, 44, r.w - 100, 24), fg, r.center, "center")
            else:
                h = ui.wrapped_height(w.vi, 21, r.w - 90, True)
                ui.draw_wrapped(s, w.vi, 21, fg, r.centerx + 10, r.centery - min(h, 80) // 2, r.w - 90, True,
                                max_lines=3)
            if done and w is not q and i == self.answered:
                # cho biết từ mình vừa chọn là gì
                draw_text(s, f"{w.hz} · {w.py}" if not self.reverse else ui.fit(w.vi, 13, r.w - 30),
                          13, C["bad"], (r.centerx, r.bottom - 8), "midbottom")

        hint = "Space: câu tiếp" if done else "Phím 1–4 để chọn"
        draw_text(s, f"{hint}  ·  Esc: thoát", 14, C["muted"], (W // 2, H - 26), "center")
        self.particles.draw(s)
        self.popups.draw(s)
