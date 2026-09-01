import sys
import pygame
import os

# Add parent dir to path to import pupilio
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pupilio.default_config import DefaultConfig
from pupilio.ui_backend import PyGameUIBackend
from pupilio.cali_graphics import CalibrationUI

class DummyPupilIO:
    def __init__(self):
        self.config = DefaultConfig()
        self.calibration_points = [[0.1, 0.1], [0.9, 0.1], [0.9, 0.9], [0.1, 0.9]]
        self._session_name = "test"

    def _recalibration(self):
        pass

def main():
    pygame.init()
    screen = pygame.display.set_mode((1920, 1080), pygame.RESIZABLE)
    pygame.display.set_caption("Language GUI Test")

    pupil = DummyPupilIO()
    ui_backend = PyGameUIBackend(screen)
    cali_ui = CalibrationUI(pupil, ui_backend)

    languages = ['en-US', 'zh-CN', 'zh-HK', 'fr-FR', 'es-ES', 'jp-JP', 'ko-KR']
    current_lang_idx = 0

    running = True
    while running:
        lang = languages[current_lang_idx]
        pupil.config.instruction_language(lang)
        cali_ui.config = pupil.config
        
        ui_backend.before_draw((255, 255, 255))
        
        cali_ui._screen_width, cali_ui._screen_height = ui_backend.get_screen_size()
        cali_ui._draw_recali_and_continue_tips()
        cali_ui._draw_legend()
        
        # Display current language
        ui_backend.draw_text(f"Current Language: {lang} (Press Space to switch)", "Arial", 30, (0,0,0), (10, 10, 800, 40), "left")

        ui_backend.after_draw()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    current_lang_idx = (current_lang_idx + 1) % len(languages)
                elif event.key == pygame.K_ESCAPE:
                    running = False

    pygame.quit()

if __name__ == "__main__":
    main()
