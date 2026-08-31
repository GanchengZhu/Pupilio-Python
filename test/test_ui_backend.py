# _*_ coding: utf-8 _*_
# Tests for the UIBackend abstraction and its concrete implementations.

import numpy as np
import pytest

from pupilio.ui_backend import UIBackend


class TestUIBackendContract:
    """The base class must refuse to draw, so a partial backend fails loudly."""

    @pytest.fixture
    def backend(self):
        return UIBackend(win=None)

    @pytest.mark.parametrize(
        "method, args",
        [
            ("draw_circle", (0, 0, 10, (255, 0, 0))),
            ("draw_line", (0, 0, 10, 10, (255, 0, 0), 1)),
            ("draw_image", ("path.png", (0, 0, 10, 10))),
            ("draw_texture", (np.zeros((4, 4, 3), dtype=np.uint8), (0, 0, 10, 10))),
            ("draw_rect", ((0, 0, 10, 10), (255, 0, 0), 1)),
            ("draw_text", ("hi", "Arial", 12, (0, 0, 0), (0, 0, 10, 10))),
            ("get_screen_size", ()),
            ("before_draw", ((255, 255, 255),)),
            ("after_draw", ()),
            ("check_action", ()),
            ("clear_events", ()),
        ],
    )
    def test_every_drawing_operation_must_be_overridden(self, backend, method, args):
        with pytest.raises(NotImplementedError):
            getattr(backend, method)(*args)

    def test_stores_the_window(self):
        sentinel = object()
        assert UIBackend(win=sentinel).win is sentinel


class TestPyGameUIBackend:
    @pytest.fixture
    def backend(self, pygame_screen):
        from pupilio.ui_backend import PyGameUIBackend

        return PyGameUIBackend(pygame_screen)

    def test_reports_the_surface_size(self, backend):
        assert backend.get_screen_size() == (800, 600)

    def test_frame_can_be_started_and_presented(self, backend):
        backend.before_draw((255, 255, 255))
        backend.after_draw()

    def test_background_colour_is_applied(self, backend, pygame_screen):
        backend.before_draw((255, 0, 0))
        assert pygame_screen.get_at((10, 10))[:3] == (255, 0, 0)

    @pytest.mark.parametrize("line_width", [0, 1, 6])
    def test_draw_circle(self, backend, line_width):
        backend.draw_circle(400, 300, 50, (0, 255, 0), line_width)

    def test_draw_line(self, backend):
        backend.draw_line(0, 0, 800, 600, (0, 0, 0), 2)

    @pytest.mark.parametrize("line_width", [0, 1, 6])
    def test_draw_rect(self, backend, line_width):
        backend.draw_rect((100, 100, 200, 150), (255, 0, 0), line_width)

    @pytest.mark.parametrize("align", ["center", "left", "right"])
    def test_draw_text_alignments(self, backend, align):
        backend.draw_text("Pupilio", "Arial", 24, (0, 0, 0), (100, 100, 400, 40), align)

    def test_draw_text_falls_back_when_the_font_is_missing(self, backend):
        # Calibration must still render if the configured font is unavailable.
        backend.draw_text("x", "NoSuchFontExists12345", 20, (0, 0, 0), (0, 0, 100, 40))

    def test_draw_texture_from_an_array(self, backend):
        image = np.random.randint(0, 255, (64, 64, 3), dtype=np.uint8)
        backend.draw_texture(image, (10, 10, 128, 128))

    def test_draw_texture_scales_to_the_target_rect(self, backend):
        image = np.zeros((32, 16, 3), dtype=np.uint8)
        backend.draw_texture(image, (0, 0, 200, 100))

    def test_draw_image_caches_by_path(self, backend):
        from pupilio.default_config import DefaultConfig

        target = DefaultConfig().cali_target_img
        backend.draw_image(target, (100, 100, 60, 60))
        backend.draw_image(target, (200, 200, 30, 30))

        assert list(backend._image_cache) == [target]

    def test_no_action_reported_when_nothing_is_pressed(self, backend):
        import pygame

        pygame.event.clear()
        assert backend.check_action() is None

    @pytest.mark.parametrize(
        "key, expected",
        [("K_RETURN", "continue"), ("K_r", "recali"), ("K_q", "quit"), ("K_ESCAPE", "quit")],
    )
    def test_keyboard_actions(self, backend, key, expected):
        import pygame

        pygame.event.clear()
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=getattr(pygame, key)))
        assert backend.check_action() == expected

    @pytest.mark.parametrize("button, expected", [(1, "continue"), (3, "recali")])
    def test_mouse_actions(self, backend, button, expected):
        import pygame

        pygame.event.clear()
        pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, button=button))
        assert backend.check_action() == expected

    def test_quit_event_is_honoured(self, backend):
        import pygame

        pygame.event.clear()
        pygame.event.post(pygame.event.Event(pygame.QUIT))
        assert backend.check_action() == "quit"

    def test_unrelated_keys_are_ignored(self, backend):
        import pygame

        pygame.event.clear()
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a))
        assert backend.check_action() is None

    def test_clear_events_drops_buffered_input(self, backend):
        # A key pressed during a previous phase must not dismiss the next screen.
        import pygame

        pygame.event.clear()
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))

        backend.clear_events()

        assert backend.check_action() is None


class TestPsychoPyUIBackend:
    """PsychoPy is an optional, display-hungry dependency, so coverage is light."""

    def test_pixel_to_psychopy_coordinate_centres_the_origin(self):
        pytest.importorskip("psychopy")
        from pupilio.ui_backend import PsychoPyUIBackend

        class FakeWindow:
            size = (1920, 1080)

        class FakeBackend:
            win = FakeWindow()
            pixel_to_psychopy_coordinate = PsychoPyUIBackend.pixel_to_psychopy_coordinate

        backend = FakeBackend()

        assert backend.pixel_to_psychopy_coordinate(960, 540) == (0, 0)
        assert backend.pixel_to_psychopy_coordinate(0, 0) == (-960, 540)
        assert backend.pixel_to_psychopy_coordinate(1920, 1080) == (960, -540)
