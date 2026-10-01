# _*_ coding: utf-8 _*_
# Manual smoke script: cycle through supported languages and render the
# legend / tips strings CalibrationUI would draw, without a real tracker.
#
# Run directly:  python language_gui_test.py
# Press Space to advance to the next locale; Escape or window-close to exit.
#
# This is NOT a pytest test. It exists so a developer can eyeball each
# translation in a real window. The automated coverage lives in the
# test_default_config.py::TestInstructionLanguage suite.

import os
import sys

import pygame

# Add the repository root to sys.path so `import pupilio` resolves when this
# script is run from anywhere inside the checkout.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pupilio.default_config import DefaultConfig
from pupilio.ui_backend import PyGameUIBackend
from pupilio.cali_graphics import CalibrationUI


class LanguageFixture:
    """
    Minimal stand-in for a real ``Pupilio`` instance.

    ``CalibrationUI`` only touches a handful of attributes for the two draw
    helpers this script uses, so we provide exactly those rather than
    subclassing Pupilio (which would try to load the native DLL).

    The name is deliberately not ``DummyPupilIO`` — it would imply the object
    can be passed to the full calibration flow, which it cannot.
    """

    def __init__(self):
        self.config = DefaultConfig()
        self.calibration_points = [[0.1, 0.1], [0.9, 0.1], [0.9, 0.9], [0.1, 0.9]]
        self._session_name = "language_gui_test"

    def _recalibration(self):
        """No-op; CalibrationUI.draw calls this before starting."""


LANGUAGES = ['en-US', 'zh-CN', 'zh-HK', 'fr-FR', 'es-ES', 'jp-JP', 'ko-KR']


def main():
    pygame.init()
    try:
        screen = pygame.display.set_mode((1920, 1080), pygame.RESIZABLE)
        pygame.display.set_caption("Language GUI Test")

        fixture = LanguageFixture()
        ui_backend = PyGameUIBackend(screen)
        cali_ui = CalibrationUI(fixture, ui_backend)

        current_lang_idx = 0
        running = True

        while running:
            lang = LANGUAGES[current_lang_idx]

            # Validates and assigns atomically; a bad code raises before _lang
            # is touched, so a typo in LANGUAGES surfaces immediately rather
            # than silently rendering the previous locale.
            fixture.config.instruction_language(lang)

            # Re-read screen size each frame so RESIZABLE actually works.
            cali_ui._screen_width, cali_ui._screen_height = ui_backend.get_screen_size()

            ui_backend.before_draw((255, 255, 255))
            cali_ui._draw_recali_and_continue_tips()
            cali_ui._draw_legend()
            ui_backend.draw_text(
                f"Current Language: {lang} (Press Space to switch)",
                "Arial", 30, (0, 0, 0), (10, 10, 800, 40), "left",
            )
            ui_backend.after_draw()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        current_lang_idx = (current_lang_idx + 1) % len(LANGUAGES)
                    elif event.key == pygame.K_ESCAPE:
                        running = False
    finally:
        # Ensures the display and mixer are torn down even if the loop raises.
        pygame.quit()


if __name__ == "__main__":
    main()
