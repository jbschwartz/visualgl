from typing import List, Optional

import glfw

from visualgl.settings import settings
from visualgl.timer import Timer
from visualgl.window import InputHandler, Window
from visualgl.window.exceptions import WindowError

from .bindings import Bindings
from .renderer import Renderer
from .settings import settings
from .utils import glfw_detail_error


class Application:
    """The main visualgl application."""

    def __init__(self, name: str):
        self.name = name

        self.bindings = Bindings(settings.bindings)
        self.input_handlers: List[InputHandler] = []

        self.renderer = Renderer()
        self.windows: List[Window] = []

        if not glfw.init():
            raise WindowError(glfw_detail_error("GLFW initialization failed"))

    @property
    def should_close(self):
        """Return True if the application should close."""
        return all(glfw.window_should_close(window.glfw_window) for window in self.windows)

    def create_window(self, **kwargs) -> Window:
        """Create a new window for the application."""
        window = Window(kwargs.get("name", self.name), **kwargs)

        self.input_handlers.append(InputHandler(window, self.bindings))
        self.windows.append(window)

        return window

    def run(self, fps_limit: Optional[int] = None) -> None:
        """Run the main event loop.

        If `fps_limit` is provided, the loop will execute no faster than the provide value.
        """
        # If the user did not create any windows explicitly, create a default window.
        if len(self.windows) == 0:
            self.create_window()

        period = (1 / fps_limit) if fps_limit else 0

        update = Timer()
        frame = Timer(period=period)

        self.renderer.start()
        for window in self.windows:
            for viewport in window.layout.viewports:
                viewport.on_start()

        while not self.should_close:
            with update:
                for window in self.windows:
                    for viewport in window.layout.viewports:
                        viewport.on_update(update.time_since_last)

            with frame:
                if frame.ready:
                    for window in self.windows:
                        glfw.make_context_current(window.glfw_window)

                        self.renderer.frame()
                        self.renderer.draw(window)

                        glfw.swap_buffers(window.glfw_window)

            glfw.poll_events()
