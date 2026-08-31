# _*_ coding: utf-8 _*_
# Tests for the CalibrationUI state machine.
#
# Drawing goes to a recording test double rather than a real window, so the
# phase transitions can be driven deterministically without a display.

import numpy as np
import pytest

from conftest import windows_only
from pupilio.misc import ET_ReturnCode
from pupilio.ui_backend import UIBackend

pytestmark = windows_only


class FakeUIBackend(UIBackend):
    """
    Records draw calls and replays a scripted sequence of user actions.

    The simulation DLL reports ET_CALI_CONTINUE forever, so calibration never
    ends on its own. `max_frames` bounds the draw loop and sets `capped`, letting
    tests assert whether the routine exited by itself or had to be cut off.
    """

    def __init__(self, actions=(), screen_size=(1920, 1080), max_frames=200):
        super().__init__(win=None)
        self.actions = list(actions)
        self.screen_size = screen_size
        self.max_frames = max_frames
        self.capped = False
        self.calls = []
        self.frames = 0

    def _record(self, name, *args):
        self.calls.append((name, args))

    def draw_circle(self, x, y, radius, color, line_width=0):
        self._record("draw_circle", x, y, radius, color, line_width)

    def draw_line(self, sx, sy, ex, ey, color, line_width):
        self._record("draw_line", sx, sy, ex, ey, color, line_width)

    def draw_image(self, img_path, rect):
        self._record("draw_image", img_path, rect)

    def draw_texture(self, img, rect):
        self._record("draw_texture", rect)

    def draw_rect(self, rect, color, line_width):
        self._record("draw_rect", rect, color, line_width)

    def draw_text(self, text, font_name, font_size, text_color, rect, align="center"):
        self._record("draw_text", text)

    def get_screen_size(self):
        return self.screen_size

    def before_draw(self, bg_color):
        self.frames += 1
        self._record("before_draw", bg_color)

    def after_draw(self):
        self._record("after_draw")

    def check_action(self):
        if self.actions:
            return self.actions.pop(0)
        if self.frames >= self.max_frames:
            self.capped = True
            return "quit"
        return None

    def clear_events(self):
        self._record("clear_events")

    def texts(self):
        return [args[0] for name, args in self.calls if name == "draw_text"]

    def names(self):
        return [name for name, _ in self.calls]


@pytest.fixture
def make_ui(pupil_io):
    from pupilio.cali_graphics import CalibrationUI

    created = []

    def factory(actions=(), max_frames=200):
        backend = FakeUIBackend(actions=actions, max_frames=max_frames)
        ui = CalibrationUI(pupil_io=pupil_io, ui_backend=backend)
        created.append(ui)
        return ui, backend

    return factory


class TestInitialisation:
    def test_starts_in_the_head_adjustment_phase(self, make_ui):
        ui, _ = make_ui()

        assert ui._phase_adjust_position is True
        assert ui._phase_calibration is False
        assert ui._phase_validation is False
        assert ui._exit is False

    def test_validation_uses_five_targets(self, make_ui):
        ui, _ = make_ui()

        assert len(ui._validation_points) == 5
        assert len(ui._calibration_drawing_list) == 5

    def test_central_target_is_validated_last(self, make_ui):
        # The peripheral targets are shuffled so participants cannot anticipate
        # them, but the centre is always appended last.
        ui, backend = make_ui()
        width, height = backend.screen_size

        assert ui._validation_points[-1] == [width // 2, height // 2]

    def test_validation_targets_are_within_the_screen(self, make_ui):
        ui, backend = make_ui()
        width, height = backend.screen_size

        for x, y in ui._validation_points:
            assert 0 <= x <= width
            assert 0 <= y <= height

    def test_sample_stores_start_empty(self, make_ui):
        ui, _ = make_ui()

        assert ui._validation_left_sample_store == [[] for _ in range(5)]
        assert ui._validation_right_sample_store == [[] for _ in range(5)]


class TestPhaseTransitions:
    def test_quit_exits_immediately(self, make_ui):
        ui, backend = make_ui(actions=["quit"])

        ui.draw(validate=False)

        assert ui._exit is True
        assert backend.frames == 1

    def test_continue_advances_from_adjustment_to_the_prompt(self, make_ui):
        ui, backend = make_ui(actions=["continue", "quit"])

        ui.draw(validate=False)

        assert ui._phase_adjust_position is False
        assert backend.texts()  # the calibration prompt was shown

    def test_reaches_the_calibration_phase_and_draws_targets(self, make_ui):
        # continue -> leave adjustment, continue -> begin calibration. The
        # simulation tracker never signals completion, so the frame cap ends it.
        ui, backend = make_ui(actions=["continue", "continue"])

        ui.draw(validate=False)

        assert ui._phase_calibration is True
        assert "draw_image" in backend.names()

    def test_every_frame_is_bracketed_by_before_and_after_draw(self, make_ui):
        ui, backend = make_ui(actions=["continue", "continue"], max_frames=20)

        ui.draw(validate=False)

        names = [name for name in backend.names() if name in ("before_draw", "after_draw")]
        assert names.count("before_draw") == names.count("after_draw")
        assert names[0] == "before_draw"
        assert names[-1] == "after_draw"

    def test_background_colour_is_forwarded_each_frame(self, make_ui):
        ui, backend = make_ui(actions=["quit"])

        ui.draw(validate=False, bg_color=(12, 34, 56))

        assert ("before_draw", ((12, 34, 56),)) in backend.calls

    def test_calibration_listener_is_notified(self, make_ui, pupil_io):
        from pupilio.callback import CalibrationListener

        class RecordingListener(CalibrationListener):
            def __init__(self):
                super().__init__()
                self.seen = []

            def on_calibration_target_onset(self, point_index):
                self.seen.append(point_index)

        listener = RecordingListener()
        original = pupil_io.config.calibration_listener
        pupil_io.config.calibration_listener = listener
        try:
            ui, _ = make_ui(actions=["continue", "continue"])
            ui.draw(validate=False)
        finally:
            pupil_io.config.calibration_listener = original

        assert listener.seen  # at least the first target was announced


class TestHandsFree:
    def test_hands_free_flag_survives_initialisation(self, make_ui):
        # Regression test: initialize_variables used to clear this flag after
        # draw_hands_free set it, so hands-free mode never actually engaged.
        ui, _ = make_ui(actions=["quit"])

        ui.draw_hands_free(validate=False)

        assert ui._hands_free is True

    def test_manual_draw_leaves_hands_free_off(self, make_ui):
        ui, _ = make_ui(actions=["quit"])

        ui.draw(validate=False)

        assert ui._hands_free is False

    def test_good_head_position_advances_once_the_countdown_expires(self, make_ui, pupil_io):
        # A well-positioned face plus an elapsed countdown is what lets a
        # hands-free participant progress without touching an input device.
        ui, _ = make_ui()
        ui._hands_free = True
        ui._hands_free_adjust_head_wait_time = 0
        pupil_io.face_position = lambda: (0, np.array([172.08, 110.0, -500.0], dtype=np.float32))

        ui._draw_adjust_position()

        assert ui._phase_adjust_position is False
        assert ui._calibration_preparing is True

    def test_poor_head_position_does_not_advance(self, make_ui, pupil_io):
        ui, _ = make_ui()
        ui._hands_free = True
        ui._hands_free_adjust_head_wait_time = 0
        # Far too close to the tracker, outside the safe depth range.
        pupil_io.face_position = lambda: (0, np.array([172.08, 110.0, -100.0], dtype=np.float32))

        ui._draw_adjust_position()

        assert ui._phase_adjust_position is True

    def test_drifting_out_of_position_restarts_the_countdown(self, make_ui, pupil_io):
        ui, _ = make_ui()
        ui._hands_free = True
        ui._hands_free_start_timestamp = 12345.0
        pupil_io.face_position = lambda: (0, np.array([172.08, 110.0, -100.0], dtype=np.float32))

        ui._draw_adjust_position()

        assert ui._hands_free_start_timestamp == 0


class TestRendering:
    def test_head_adjustment_draws_the_boundary_and_target_zone(self, make_ui):
        ui, backend = make_ui(actions=["quit"])

        ui.draw(validate=False)

        assert "draw_rect" in backend.names()
        assert "draw_circle" in backend.names()

    def test_face_preview_is_drawn_when_enabled(self, make_ui, pupil_io):
        pupil_io.config.face_previewing = 1
        ui, backend = make_ui(actions=["quit"])

        ui.draw(validate=False)

        assert "draw_texture" in backend.names()

    def test_face_preview_is_skipped_when_disabled(self, make_ui, pupil_io):
        original = pupil_io.config.face_previewing
        pupil_io.config.face_previewing = 0
        try:
            ui, backend = make_ui(actions=["quit"])
            ui.draw(validate=False)
        finally:
            pupil_io.config.face_previewing = original

        assert "draw_texture" not in backend.names()


class TestSoundHelpers:
    def test_sound_failures_do_not_propagate(self, make_ui):
        # Audio is a cue, not a requirement; a broken mixer must not abort a run.
        ui, _ = make_ui()

        class BrokenSound:
            def play(self):
                raise RuntimeError("no audio device")

            def stop(self):
                raise RuntimeError("no audio device")

        ui.play_sound(BrokenSound())
        ui.stop_sound(BrokenSound())


class TestInputBuffering:
    """
    Buffered input must be dropped before any screen that waits for a response,
    otherwise a key pressed during the previous phase dismisses it instantly.
    """

    def test_input_is_cleared_before_the_first_screen(self, make_ui):
        ui, backend = make_ui(actions=["quit"])

        ui.draw(validate=False)

        assert "clear_events" in backend.names()

    def test_input_is_cleared_when_leaving_head_adjustment(self, make_ui):
        ui, backend = make_ui(actions=["continue", "quit"])

        ui.draw(validate=False)

        # Once at startup, once on entering the calibration prompt.
        assert backend.names().count("clear_events") >= 2


class TestCalibrationFailure:
    """
    A rejected calibration (typically failed kappa verification) should let the
    participant retry or accept it, rather than silently continuing.
    """

    @pytest.fixture
    def failing_ui(self, make_ui, pupil_io):
        ui, backend = make_ui(actions=["continue", "continue"], max_frames=10)
        pupil_io.calibration = lambda point_id: ET_ReturnCode.ET_FAILED.value
        return ui, backend

    def test_failure_shows_the_retry_prompt(self, failing_ui, pupil_io):
        pupil_io.config.enable_kappa_verification = 1
        ui, backend = failing_ui

        ui.draw(validate=False)

        assert ui._phase_calibration_failed is True
        assert any(
            pupil_io.config.instruction_calibration_failed in text for text in backend.texts()
        )

    def test_prompt_offers_both_retry_and_continue(self, failing_ui, pupil_io):
        pupil_io.config.enable_kappa_verification = 1
        ui, backend = failing_ui

        ui.draw(validate=False)

        shown = "\n".join(backend.texts())
        assert pupil_io.config.instruction_recalibration in shown
        assert pupil_io.config.instruction_calibration_over in shown

    def test_input_is_cleared_before_the_prompt(self, failing_ui, pupil_io):
        pupil_io.config.enable_kappa_verification = 1
        ui, backend = failing_ui

        ui.draw(validate=False)

        assert "clear_events" in backend.names()

    def test_continue_accepts_the_failed_calibration(self, make_ui, pupil_io):
        pupil_io.config.enable_kappa_verification = 1
        pupil_io.calibration = lambda point_id: ET_ReturnCode.ET_FAILED.value
        ui, backend = make_ui(actions=["continue", "continue", "continue"], max_frames=10)

        ui.draw(validate=False)

        assert ui._exit is True
        assert ui._phase_calibration_failed is False

    def test_no_prompt_when_kappa_verification_is_disabled(self, make_ui, pupil_io):
        # The prompt reports a kappa failure, so it is meaningless when kappa
        # verification was switched off in the first place.
        pupil_io.config.enable_kappa_verification = 0
        pupil_io.calibration = lambda point_id: ET_ReturnCode.ET_FAILED.value
        ui, backend = make_ui(actions=["continue", "continue"], max_frames=10)

        ui.draw(validate=False)

        assert ui._phase_calibration_failed is False
        assert ui._exit is True

    def test_no_prompt_in_hands_free_mode(self, make_ui, pupil_io):
        # Nobody can answer a prompt in hands-free mode, so it must not block.
        pupil_io.config.enable_kappa_verification = 1
        pupil_io.calibration = lambda point_id: ET_ReturnCode.ET_FAILED.value
        ui, backend = make_ui(max_frames=10)

        ui.draw_hands_free(validate=False)

        assert ui._phase_calibration_failed is False


class TestValidationScoring:
    def test_targets_with_too_few_samples_are_repeated(self, make_ui):
        ui, _ = make_ui()
        ui._calibration_drawing_list = []

        ui._repeat_calibration_point()

        # Nothing was collected, so every target needs another attempt.
        assert len(ui._calibration_drawing_list) == 5

    def test_accurate_targets_are_not_repeated(self, make_ui):
        ui, _ = make_ui()
        ui._calibration_drawing_list = []

        for index, point in enumerate(ui._validation_points):
            samples = [[float(point[0]), float(point[1])] for _ in range(10)]
            distances = [60.0] * 10
            ui._validation_left_sample_store[index] = list(samples)
            ui._validation_right_sample_store[index] = list(samples)
            ui._validation_left_eye_distance_store[index] = list(distances)
            ui._validation_right_eye_distance_store[index] = list(distances)

        ui._repeat_calibration_point()

        assert ui._calibration_drawing_list == []
        assert ui._n_validation == 2

    def test_repeated_targets_have_their_samples_cleared(self, make_ui):
        ui, _ = make_ui()
        ui._calibration_drawing_list = []
        # Plenty of samples, but far from the target, so accuracy fails.
        ui._validation_left_sample_store[0] = [[0.0, 0.0]] * 10
        ui._validation_left_eye_distance_store[0] = [60.0] * 10

        ui._repeat_calibration_point()

        assert 0 in ui._calibration_drawing_list
        assert ui._validation_left_sample_store[0] == []
