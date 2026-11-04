"""Hiệu ứng âm thanh ngắn, tự tổng hợp (không cần file âm thanh)."""
import array
import math

import pygame


class Audio:
    def __init__(self):
        self.sounds = {}
        try:
            pygame.mixer.init(44100, -16, 1, 512)
            freq, _, channels = pygame.mixer.get_init()
            self.sounds = {
                "ok": self._tone([(660, .07), (990, .12)], freq, channels),
                "bad": self._tone([(220, .09), (165, .16)], freq, channels, wave="square", vol=.18),
                "click": self._tone([(1200, .025)], freq, channels, vol=.15),
                "level": self._tone([(523, .08), (659, .08), (784, .08), (1047, .18)], freq, channels),
                "end": self._tone([(784, .1), (659, .1), (523, .22)], freq, channels),
            }
        except pygame.error:
            pass  # không có thiết bị âm thanh: chạy im lặng

    @staticmethod
    def _tone(notes, freq, channels, wave="sine", vol=.3):
        buf = array.array("h")
        for hz, dur in notes:
            n = int(freq * dur)
            for i in range(n):
                t = i / freq
                env = min(1, i / (freq * .005)) * (1 - i / n) ** 1.5
                v = math.sin(2 * math.pi * hz * t)
                if wave == "square":
                    v = 1 if v >= 0 else -1
                s = int(32767 * vol * env * v)
                buf.extend([s] * channels)
        return pygame.mixer.Sound(buffer=buf.tobytes())

    def play(self, name):
        s = self.sounds.get(name)
        if s:
            s.play()
