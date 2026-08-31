# _*_ coding: utf-8 _*_
# Tests for pupilio.misc: enums and the accuracy Calculator.

import math

import pytest

from pupilio.misc import (
    ActiveEye,
    CalibrationMode,
    CameraMode,
    Calculator,
    ET_ReturnCode,
    EventType,
    LocalConfig,
)


class TestEnums:
    def test_return_codes_match_native_header(self):
        # These values are an ABI contract with deep_gaze_et.h; changing them
        # silently would misinterpret every native return.
        assert ET_ReturnCode.ET_SUCCESS == 0
        assert ET_ReturnCode.ET_CALI_CONTINUE == 1
        assert ET_ReturnCode.ET_CALI_NEXT_POINT == 2
        assert ET_ReturnCode.ET_INVALID_PATH == 3
        assert ET_ReturnCode.ET_INVALID_PARAM == 4
        assert ET_ReturnCode.ET_FAILED == 9
        assert ET_ReturnCode.ET_EXCEPTION == 10

    def test_calibration_modes_are_their_point_counts(self):
        assert CalibrationMode.TWO_POINTS == 2
        assert CalibrationMode.FOUR_POINTS == 4
        assert CalibrationMode.FIVE_POINTS == 5

    def test_camera_modes_match_native_header(self):
        assert CameraMode.CAMERA_MODE_SYNC_400 == 0
        assert CameraMode.CAMERA_MODE_SYNC_800 == 1
        assert CameraMode.CAMERA_MODE_SYNC_1000 == 2
        assert CameraMode.CAMERA_MODE_SYNC_200 == 3
        assert CameraMode.CAMERA_MODE_ASYNC_400 == 4

    def test_active_eye_matches_native_eye_mode(self):
        assert ActiveEye.LEFT_EYE == -1
        assert ActiveEye.BINO_EYE == 0
        assert ActiveEye.RIGHT_EYE == 1

    def test_event_types_are_strings(self):
        assert EventType.START_FIXATION == "start_fixation"
        assert isinstance(EventType.END_BLINK, str)

    def test_event_type_values_are_unique(self):
        values = [member.value for member in EventType]
        assert len(values) == len(set(values))


class TestLocalConfig:
    def test_defaults_describe_a_1920x1080_screen(self):
        config = LocalConfig().dp_config
        assert config["screen_width"] == 1920
        assert config["screen_height"] == 1080
        assert config["physical_screen_width"] == pytest.approx(34.13)
        assert config["physical_screen_height"] == pytest.approx(19.32)


@pytest.fixture
def calculator():
    return Calculator(
        screen_width=1920,
        screen_height=1080,
        physical_screen_width=34.13,
        physical_screen_height=19.32,
    )


class TestCalculatorPxToCm:
    def test_origin_maps_to_origin(self, calculator):
        assert calculator.px_2_cm([0, 0]) == [0, 0]

    def test_bottom_right_maps_to_physical_size(self, calculator):
        x, y = calculator.px_2_cm([1920, 1080])
        assert x == pytest.approx(34.13)
        assert y == pytest.approx(19.32)

    def test_centre_maps_to_half_the_physical_size(self, calculator):
        x, y = calculator.px_2_cm([960, 540])
        assert x == pytest.approx(34.13 / 2)
        assert y == pytest.approx(19.32 / 2)


class TestCalculatorError:
    def test_no_offset_is_zero_error(self, calculator):
        assert calculator.error([960, 540], [960, 540], 60) == pytest.approx(0.0)

    def test_error_is_symmetric(self, calculator):
        a = calculator.error([100, 100], [200, 200], 60)
        b = calculator.error([200, 200], [100, 100], 60)
        assert a == pytest.approx(b)

    def test_larger_offset_gives_larger_angle(self, calculator):
        near = calculator.error([960, 540], [1000, 540], 60)
        far = calculator.error([960, 540], [1200, 540], 60)
        assert far > near

    def test_greater_viewing_distance_shrinks_the_angle(self, calculator):
        close = calculator.error([960, 540], [1100, 540], 40)
        distant = calculator.error([960, 540], [1100, 540], 80)
        assert distant < close

    def test_matches_hand_computed_visual_angle(self, calculator):
        # 1920 px horizontally spans 34.13 cm, so a 100 px offset is 1.7776 cm.
        offset_cm = 100 * 34.13 / 1920
        expected = 2 * math.degrees(math.atan(offset_cm / (2 * 60)))
        assert calculator.error([0, 0], [100, 0], 60) == pytest.approx(expected)


class TestCalculatorSlidingWindow:
    def test_perfect_gaze_has_near_zero_error(self, calculator):
        gt = [960, 540]
        samples = [[960, 540]] * 10
        distances = [60.0] * 10

        result = calculator.calculate_error_by_sliding_window(gt, samples, distances)

        assert result["min_error"] == pytest.approx(0.0)
        assert result["gt_point"] == gt

    def test_reports_the_best_window_not_the_average(self, calculator):
        # Five accurate samples buried among wildly inaccurate ones: the best
        # window should be found, which is the whole point of the sliding window.
        gt = [960, 540]
        samples = [[0, 0]] * 5 + [[960, 540]] * 5 + [[0, 0]] * 5
        distances = [60.0] * 15

        result = calculator.calculate_error_by_sliding_window(gt, samples, distances)

        assert result["min_error"] == pytest.approx(0.0, abs=1e-6)

    def test_best_point_is_the_mean_of_the_best_window(self, calculator):
        gt = [500, 500]
        samples = [[500, 500], [502, 500], [500, 502], [498, 500], [500, 498]]
        distances = [60.0] * 5

        result = calculator.calculate_error_by_sliding_window(gt, samples, distances)

        assert result["min_error_es_point"][0] == pytest.approx(500.0)
        assert result["min_error_es_point"][1] == pytest.approx(500.0)

    def test_offset_gaze_reports_a_positive_error(self, calculator):
        gt = [960, 540]
        samples = [[1060, 540]] * 6
        distances = [60.0] * 6

        result = calculator.calculate_error_by_sliding_window(gt, samples, distances)

        assert result["min_error"] > 0
        assert result["min_error"] < 90

    @pytest.mark.parametrize("n_samples", [0, 1, 4])
    def test_too_few_samples_returns_infinite_error(self, calculator, n_samples):
        # Fewer than one full window cannot produce an estimate; validation relies
        # on this returning inf rather than raising, so a blink does not crash
        # the calibration routine.
        result = calculator.calculate_error_by_sliding_window(
            [960, 540], [[960, 540]] * n_samples, [60.0] * n_samples
        )

        assert result["min_error"] == float("inf")
        assert result["min_error_es_point"] == (0, 0)

    def test_mismatched_distances_returns_infinite_error(self, calculator):
        result = calculator.calculate_error_by_sliding_window(
            [960, 540], [[960, 540]] * 10, [60.0] * 3
        )

        assert result["min_error"] == float("inf")

    def test_exactly_one_window_is_enough(self, calculator):
        result = calculator.calculate_error_by_sliding_window(
            [960, 540], [[960, 540]] * 5, [60.0] * 5
        )

        assert result["min_error"] == pytest.approx(0.0)
