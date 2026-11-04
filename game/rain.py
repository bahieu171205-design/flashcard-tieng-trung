import random

import pygame

from . import ui
from .scene import Scene
from .ui import C, H, W, Button, Particles, Popups, draw_text, rrect

GROUND = H - 150
TOP = 92
TILE_H = 76
HITS_PER_LEVEL = 5


class Tile:
    def __init__(self, word, x, w, vy):
        self.word = word
        self.rect = pygame.Rect(x, TOP - TILE_H, w, TILE_H)
        self.y = float(self.rect.y)
        self.vy = vy
        self.bad = 0.0  # >0: đang nháy đỏ vì bấm sai


class RainScene(Scene):
    def __init__(self, app, title, words, pool, scope, back):
        super().__init__(app)
        self.title, self.words, self.pool, self.scope, self.back = title, words, pool, scope, back
        # chữ "nhiễu" lấy trong cùng bài; bài ít từ thì lấy thêm từ các bài khác
        others = {w.key: w for w in list(words) + list(pool)}
        if len(others) < 10:
            for w in random.sample(app.all_words, 30):
                others.setdefault(w.key, w)
        self.decoys = list(others.values())
        self.btn_back = Button((40, 24, 120, 42), "← Thoát", "ghost", 16)
        self.particles, self.popups = Particles(), Popups()
        self.reset()

    def reset(self):
        self.queue = random.sample(self.words, len(self.words))
        self.total = len(self.queue)
        self.tiles = []
        self.lives, self.score, self.level, self.hits = 3, 0, 1, 0
        self.missed = []
        self.spawn_t = 1.6
        self.banner = ("Bắt đầu!", 1.4)
        self.over = False
        self.target = None
        self.next_target()

    # ---------- logic ----------
    def speed(self):
        return 34 + self.level * 13

    def next_target(self):
        if not self.queue:
            self.target = None
            return self.finish()
        self.target = self.queue.pop()
        self.need_target = True
        self.spawn_t = min(self.spawn_t, 0.5)

    def spawn(self):
        on_screen = {t.word.key for t in self.tiles}
        t = self.target
        if t.key not in on_screen and (self.need_target or random.random() < .4):
            w = t
            self.need_target = False
        else:
            cands = [d for d in self.decoys if d.key not in on_screen and d.vi != t.vi and d.hz != t.hz]
            if not cands:
                return
            w = random.choice(cands)
        tw = max(88, ui.text_width(w.hz, 40) + 40)
        # chọn vị trí không đè lên các ô vừa xuất hiện gần mép trên
        recent = [x.rect for x in self.tiles if x.y < TOP + 2 * TILE_H]
        for _ in range(15):
            x = random.randint(30, W - 30 - tw)
            probe = pygame.Rect(x - 10, 0, tw + 20, 1)
            if not any(probe.left < r.right and r.left < probe.right for r in recent):
                break
        self.tiles.append(Tile(w, x, tw, self.speed() * random.uniform(.85, 1.15)))

    def click(self, pos):
        for tile in reversed(self.tiles):
            if tile.rect.collidepoint(pos) and not tile.bad:
                if tile.word.vi == self.target.vi:
                    self.hit(tile)
                else:
                    self.wrong(tile)
                return

    def hit(self, tile):
        self.tiles.remove(tile)
        self.hits += 1
        gain = 10 * self.level + max(0, int((GROUND - tile.y) / 12))
        self.score += gain
        self.particles.burst(tile.rect.center, C["good"], 22)
        self.popups.add(f"+{gain}  {tile.word.py}", tile.rect.center, C["good"], 22)
        self.app.audio.play("ok")
        self.app.progress.set_known(self.target, True)
        if self.hits % HITS_PER_LEVEL == 0:
            self.level += 1
            self.banner = (f"Cấp {self.level}!", 1.2)
            self.app.audio.play("level")
        self.next_target()

    def wrong(self, tile):
        tile.bad = 0.45
        self.lose_life()
        # cho biết chữ vừa bấm nghĩa là gì
        self.popups.add(f"{tile.word.hz} = {ui.fit(tile.word.vi, 18, 380)}", tile.rect.center, C["bad"], 18, 1.6)
        if self.target not in self.missed:
            self.missed.append(self.target)

    def miss(self):
        t = self.target
        self.popups.add(f"Lỡ mất: {t.hz}  {t.py}", (W // 2, GROUND - 40), C["bad"], 22, 1.8)
        if t not in self.missed:
            self.missed.append(t)
        self.app.progress.set_known(t, False)
        self.lose_life()
        if not self.over:
            self.next_target()

    def lose_life(self):
        self.lives -= 1
        self.app.audio.play("bad")
        if self.lives <= 0:
            self.finish()

    def finish(self):
        if self.over:
            return
        self.over = True
        self.end_wait = 0.9  # để người chơi kịp thấy hiệu ứng cuối rồi mới sang màn kết quả
        app = self.app
        best = app.progress.best_score("rain", self.scope)
        record = app.progress.submit("rain", self.scope, self.score)
        app.save()
        app.audio.play("end")
        from .flashcard import FlashcardScene
        from .result import ResultScene
        replay = lambda: app.go(RainScene(app, self.title, self.words, self.pool, self.scope, self.back))  # noqa: E731
        review = lambda ws: app.go(FlashcardScene(app, "Ôn các từ bị lỡ", ws, self.back))  # noqa: E731
        stats = [("từ bắt được", f"{self.hits}/{self.total}"), ("cấp độ", self.level), ("mạng còn lại", self.lives)]
        heading = "Hết mạng!" if self.lives <= 0 else "Hoàn thành!"
        self.result = ResultScene(app, f"{heading}  ·  Mưa chữ", self.score, best, record, stats, self.missed,
                                  replay, review, self.back)

    # ---------- sự kiện ----------
    def handle(self, e):
        if self.btn_back.clicked(e) or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
            return self.back()
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and not self.over:
            self.click(e.pos)

    def update(self, dt):
        self.particles.update(dt)
        self.popups.update(dt)
        self.banner = (self.banner[0], self.banner[1] - dt)
        if self.over:
            self.end_wait -= dt
            if self.end_wait <= 0:
                self.app.go(self.result)
            return
        self.spawn_t -= dt
        if self.spawn_t <= 0:
            self.spawn()
            self.spawn_t = max(.6, 1.7 - self.level * .12) * random.uniform(.8, 1.2)
        for tile in list(self.tiles):
            if tile.bad:
                tile.bad -= dt
                if tile.bad <= 0:
                    self.tiles.remove(tile)
                continue
            tile.y += tile.vy * dt
            tile.rect.y = int(tile.y)
            if tile.rect.bottom >= GROUND:
                self.tiles.remove(tile)
                self.particles.burst((tile.rect.centerx, GROUND), C["line"], 8, 120)
                if tile.word.key == self.target.key:
                    self.miss()
                    if self.over:
                        return

    # ---------- vẽ ----------
    def draw(self, s):
        # nền: các vạch mờ như giấy kẻ ô viết chữ Hán
        for x in range(40, W, 80):
            pygame.draw.line(s, (240, 233, 220), (x, TOP), (x, GROUND))
        self.btn_back.draw(s)
        draw_text(s, ui.fit(self.title, 18, 300, True), 18, C["ink"], (176, 28), bold=True)
        draw_text(s, f"Còn {len(self.queue) + (1 if self.target else 0)}/{self.total} từ", 15, C["muted"], (176, 52))
        draw_text(s, str(self.score), 34, C["ink"], (W // 2, 42), "center", True)
        draw_text(s, "điểm", 13, C["muted"], (W // 2, 68), "center")
        pill = pygame.Rect(0, 0, 84, 30)
        pill.midleft = (W // 2 + 74, 44)
        rrect(s, C["good_soft"], pill, radius=15)
        draw_text(s, f"Cấp {self.level}", 15, C["good"], pill.center, "center", True)
        ui.hearts(s, W - 40, 44, self.lives)

        mouse = pygame.mouse.get_pos()
        s.set_clip(pygame.Rect(0, TOP, W, GROUND - TOP))  # ô chữ trượt vào từ dưới thanh tiêu đề
        for tile in self.tiles:
            r = tile.rect
            if tile.bad:
                rrect(s, C["bad_soft"], r, radius=14, border=2, border_color=C["bad"], shadow=3)
                draw_text(s, tile.word.hz, 40, C["bad"], r.center, "center")
            else:
                hov = r.collidepoint(mouse)
                rrect(s, C["surface"], r, radius=14, border=2, border_color=C["accent"] if hov else C["line"],
                      shadow=4)
                draw_text(s, tile.word.hz, 40, C["ink"], r.center, "center")
        s.set_clip(None)

        # mặt đất + khung đề bài
        pygame.draw.rect(s, C["surface"], (0, GROUND, W, H - GROUND))
        pygame.draw.line(s, C["accent"], (0, GROUND), (W, GROUND), 3)
        if self.target:
            draw_text(s, "Bấm vào chữ Hán có nghĩa:", 15, C["muted"], (W // 2, GROUND + 16), "midtop")
            ui.draw_wrapped(s, self.target.vi, 30, C["ink"], W // 2, GROUND + 42, W - 200, True, max_lines=2)
        draw_text(s, "Bấm chuột vào chữ đúng  ·  chữ cần tìm chạm đất là mất 1 mạng  ·  Esc: thoát", 13, C["muted"],
                  (W // 2, H - 14), "midbottom")

        self.particles.draw(s)
        self.popups.draw(s)
        text, t = self.banner
        if t > 0:
            b = ui.text(text, 56, C["accent"], True).copy()
            b.set_alpha(int(255 * min(1, t / 0.4)))
            s.blit(b, b.get_rect(center=(W // 2, (TOP + GROUND) // 2)))
