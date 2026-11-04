import os

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame  # noqa: E402

from . import ui  # noqa: E402
from .audio import Audio  # noqa: E402
from .data import Progress, load_volumes  # noqa: E402


class App:
    def __init__(self, screen):
        self.screen = screen
        self.volumes = load_volumes()
        self.progress = Progress()
        self.use_volume(self.progress.vol)
        self.audio = Audio()
        self.settings = {"reverse": False}
        self.scene = None
        self.running = True

    def use_volume(self, vol_id):
        """Chọn tập đang học: bài, từ, phạm vi bài và kỷ lục đều theo tập này."""
        self.vol = next((v for v in self.volumes if v.id == vol_id), self.volumes[0])
        self.lessons = self.vol.lessons
        self.all_words = self.vol.words
        self.progress.vol = self.vol.id
        lo, hi = self.lessons[0].bai, self.lessons[-1].bai
        a, b = self.progress.ranges.get(self.vol.id, [lo, hi])
        a = max(lo, min(hi, int(a)))
        self.progress.ranges[self.vol.id] = [a, max(a, min(hi, int(b)))]

    @property
    def range(self):
        """[từ bài, đến bài] của tập đang học (sửa trực tiếp danh sách này)."""
        return self.progress.ranges[self.vol.id]

    def go(self, scene):
        self.scene = scene

    def save(self):
        try:
            self.progress.save()
        except OSError:
            pass

    def run(self):
        from .menus import HomeScene
        self.go(HomeScene(self))
        clock = pygame.time.Clock()
        while self.running:
            dt = min(clock.tick(60) / 1000, 0.05)
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    self.running = False
                else:
                    self.scene.handle(e)
            self.scene.update(dt)
            self.screen.fill(ui.C["bg"])
            self.scene.draw(self.screen)
            pygame.display.flip()
        self.save()


def _icon():
    s = pygame.Surface((64, 64), pygame.SRCALPHA)
    ui.rrect(s, ui.C["accent"], (0, 0, 64, 64), radius=14)
    ui.draw_text(s, "学", 42, ui.C["white"], (32, 33), "center", True)
    return s


def main():
    pygame.init()
    pygame.display.set_caption("Flashcard Tiếng Trung")
    pygame.display.set_icon(_icon())
    screen = pygame.display.set_mode((ui.W, ui.H))
    App(screen).run()
    pygame.quit()
