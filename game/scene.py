class Scene:
    """Một màn hình của game. App gọi handle → update → draw mỗi khung hình."""

    def __init__(self, app):
        self.app = app

    def handle(self, e):
        pass

    def update(self, dt):
        pass

    def draw(self, surf):
        pass
