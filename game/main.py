import os

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame  # noqa: E402

from . import ui  # noqa: E402
from .audio import Audio  # noqa: E402
from .data import Progress, load_lessons  # noqa: E402


class App:
    def __init__(self, screen):
        self.screen = screen
        self.lessons = load_lessons()
        self.all_words = [w for l in self.lessons for w in l.words]
        self.progress = Progress()
        self.audio = Audio()
        self.settings = {"rieng": True, "reverse": False}
        self.scene = None
        self.running = True

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
