# _*_ coding: utf-8 _*_
# Integration tests driving a real Pupilio against the simulation DLL.
#
# These exercise the ctypes bindings end to end, which is where signature and
# return-type mistakes actually surface.

import warnings

import numpy as np
import pytest

from conftest import windows_only
from pupilio.misc import ActiveEye, CalibrationMode, CameraMode, ET_ReturnCode

pytestmark = windows_only


class TestConstruction:
    def test_reports_the_camera_mode_and_roi(self, pupil_io):
        assert pupil_io._camera_mode in list(CameraMode)
        assert len(pupil_io.left_roi) == 4
        assert len(pupil_io.right_roi) == 4

    def test_image_dimensions_follow_the_roi(self, pupil_io):
        assert pupil_io.LEFT_IMG_WIDTH == int(pupil_io.left_roi[2])
        assert pupil_io.LEFT_IMG_HEIGHT == int(pupil_io.left_roi[3])
        assert pupil_io.RIGHT_IMG_WIDTH == int(pupil_io.right_roi[2])
        assert pupil_io.RIGHT_IMG_HEIGHT == int(pupil_io.right_roi[3])

    def test_sampling_rate_is_resolved_to_a_supported_value(self, pupil_io):
        assert pupil_io.config.sampling_rate in pupil_io.query_support_samping_rate()

    def test_calibration_points_match_the_configured_mode(self, simulation_config):
        from pupilio import Pupilio

        simulation_config.cali_mode = CalibrationMode.FIVE_POINTS
        tracker = Pupilio(config=simulation_config)
        try:
            assert tracker.calibration_points.shape == (5, 2)
        finally:
            tracker.release()

    def test_look_ahead_outside_the_valid_range_is_rejected(self, simulation_config):
        from pupilio import Pupilio

        simulation_config.look_ahead = 99
        with pytest.raises(ValueError, match="look_ahead"):
            Pupilio(config=simulation_config)


class TestCameraMode:
    def test_supported_rates_are_ascending_and_non_empty(self, pupil_io):
        rates = pupil_io.query_support_samping_rate()

        assert rates
        assert rates == sorted(rates)
        assert 200 in rates

    def test_get_camera_mode_agrees_with_the_cached_mode(self, pupil_io):
        mode, left_roi, right_roi = pupil_io.get_camera_mode()

        assert mode == pupil_io._camera_mode
        assert np.array_equal(left_roi, pupil_io.left_roi)
        assert np.array_equal(right_roi, pupil_io.right_roi)


class TestSessionLifecycle:
    def test_create_session_succeeds(self, pupil_io):
        assert pupil_io.create_session("test_session") == ET_ReturnCode.ET_SUCCESS

    def test_session_name_is_timestamped_for_uniqueness(self, pupil_io):
        pupil_io.create_session("my_session")

        assert pupil_io._session_name.startswith("my_session_")
        assert pupil_io._session_name != "my_session"

    @pytest.mark.parametrize("name", ["with space", "with/slash", "with:colon", "with*star", "bad?name"])
    def test_invalid_session_names_are_rejected(self, pupil_io, name):
        with pytest.raises(Exception, match="invalid"):
            pupil_io.create_session(name)

    @pytest.mark.parametrize("name", ["CON", "PRN", "NUL", "COM1", "LPT1", "com1"])
    def test_windows_reserved_names_are_rejected(self, pupil_io, name):
        # These cannot be used as file names on Windows, and the session name
        # becomes a directory name.
        with pytest.raises(Exception, match="invalid"):
            pupil_io.create_session(name)

    @pytest.mark.parametrize("name", ["session1", "my_session", "test-run", "run+1", "trial(1)"])
    def test_documented_name_characters_are_accepted(self, pupil_io, name):
        assert pupil_io.create_session(name) == ET_ReturnCode.ET_SUCCESS


class TestSampling:
    def test_not_sampling_before_start(self, pupil_io):
        assert pupil_io.get_sampling_status() is False

    def test_start_then_stop(self, pupil_io):
        pupil_io.create_session("sampling_test")

        pupil_io.start_sampling()
        assert pupil_io.get_sampling_status() is True

        pupil_io.stop_sampling()
        assert pupil_io.get_sampling_status() is False

    def test_stopping_when_idle_raises(self, pupil_io):
        # Regression test: the native call dereferences a null sampling thread
        # here, which crashed the interpreter instead of raising.
        with pytest.raises(RuntimeError, match="no sampling running"):
            pupil_io.stop_sampling()

    def test_starting_twice_raises(self, pupil_io):
        pupil_io.create_session("double_start")
        pupil_io.start_sampling()
        try:
            with pytest.raises(RuntimeError, match="already running"):
                pupil_io.start_sampling()
        finally:
            pupil_io.stop_sampling()

    def test_calibration_is_refused_while_sampling(self, pupil_io):
        # Calibrating mid-recording would corrupt the recording, so the guard
        # matters.
        pupil_io.create_session("cali_guard")
        pupil_io.start_sampling()
        try:
            assert pupil_io.calibration(0) == ET_ReturnCode.ET_FAILED
        finally:
            pupil_io.stop_sampling()


class TestEstimation:
    def test_face_position_returns_three_coordinates(self, pupil_io):
        status, position = pupil_io.face_position()

        assert status in list(ET_ReturnCode)
        assert position.shape == (3,)
        assert position.dtype == np.float32

    def test_estimate_gaze_returns_the_documented_shapes(self, pupil_io):
        status, left, right, bino, timestamp, trigger = pupil_io.estimate_gaze()

        assert status in list(ET_ReturnCode)
        assert left.shape == (14,)
        assert right.shape == (14,)
        assert bino.shape == (10,)
        assert isinstance(timestamp, int)
        assert trigger == 0

    def test_estimation_lr_returns_the_documented_shapes(self, pupil_io):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            status, left, right, timestamp, trigger = pupil_io.estimation_lr()

        assert status in list(ET_ReturnCode)
        assert left.shape == (14,)
        assert right.shape == (14,)

    def test_estimation_binds_an_exported_symbol(self, pupil_io):
        # Regression test: this used to call pupil_io_gaze_est, which the DLL
        # does not export, so every call raised AttributeError.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            status, pt, timestamp, trigger = pupil_io.estimation()

        assert status in list(ET_ReturnCode)
        assert pt.shape == (11,)

    def test_get_current_gaze_returns_three_arrays(self, pupil_io):
        left, right, bino = pupil_io.get_current_gaze()

        for gaze in (left, right, bino):
            assert gaze.shape == (3,)
            assert gaze.dtype == np.float32


class TestTrigger:
    @pytest.mark.parametrize("trigger", [1, 100, 65535])
    def test_valid_triggers_are_accepted(self, pupil_io, trigger):
        pupil_io.create_session("trigger_test")
        pupil_io.start_sampling()
        try:
            assert pupil_io.set_trigger(trigger) == ET_ReturnCode.ET_SUCCESS
        finally:
            pupil_io.stop_sampling()

    @pytest.mark.parametrize("trigger", [0, -1, 65536, 100000])
    def test_out_of_range_triggers_are_rejected(self, pupil_io, trigger):
        with pytest.raises(ValueError, match="between 1 and 65535"):
            pupil_io.set_trigger(trigger)

    @pytest.mark.parametrize("trigger", ["1", 1.5, None])
    def test_non_integer_triggers_are_rejected(self, pupil_io, trigger):
        with pytest.raises(TypeError, match="integer"):
            pupil_io.set_trigger(trigger)


class TestDataOutput:
    def test_save_data_writes_a_file(self, pupil_io, tmp_path):
        pupil_io.create_session("save_test")
        pupil_io.start_sampling()
        pupil_io.stop_sampling()

        target = tmp_path / "gaze_data.csv"
        assert pupil_io.save_data(str(target)) == ET_ReturnCode.ET_SUCCESS
        assert target.exists()

    def test_saving_into_a_missing_directory_raises(self, pupil_io, tmp_path):
        with pytest.raises(Exception, match="not exist"):
            pupil_io.save_data(str(tmp_path / "missing" / "data.csv"))

    def test_clear_cache_returns_a_known_status(self, pupil_io):
        pupil_io.create_session("clear_test")
        assert pupil_io.clear_cache() in list(ET_ReturnCode)


class TestFilterAndPreview:
    @pytest.mark.parametrize("status", [True, False])
    def test_filter_can_be_toggled(self, pupil_io, status):
        assert pupil_io.set_filter_enable(status) in list(ET_ReturnCode)

    def test_preview_images_have_the_documented_shape(self, pupil_io):
        images = pupil_io.get_preview_images()

        assert images.shape == (2, 1280, 1280, 3)
        assert images.dtype == np.uint8

    def test_previewer_rejects_a_malformed_host(self, pupil_io):
        with pytest.raises(Exception, match="Invalid IP address"):
            pupil_io.previewer_start("not-an-ip", 5000)


class TestDeprecatedApi:
    def test_subscribe_sample_warns(self, pupil_io):
        with pytest.warns(DeprecationWarning):
            pupil_io.subscribe_sample(lambda sample: None)

    def test_unsubscribe_sample_warns(self, pupil_io):
        with pytest.warns(DeprecationWarning):
            pupil_io.unsubscribe_sample(lambda sample: None)

    def test_subscribe_event_warns(self, pupil_io):
        with pytest.warns(DeprecationWarning):
            pupil_io.subscribe_event(lambda event: None)

    def test_unsubscribe_event_warns(self, pupil_io):
        with pytest.warns(DeprecationWarning):
            pupil_io.unsubscribe_event(lambda event: None)

    @pytest.mark.parametrize("name", ["sample_subscriber_lock", "sample_subscribers"])
    def test_removed_properties_read_as_none(self, pupil_io, name):
        # Regression test: with @deprecated stacked above @property these
        # returned a bound method instead of the property value.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            assert getattr(pupil_io, name) is None


class TestActiveEyeModes:
    @pytest.mark.parametrize(
        "eye", [ActiveEye.LEFT_EYE, ActiveEye.RIGHT_EYE, ActiveEye.BINO_EYE]
    )
    def test_each_eye_mode_initialises(self, simulation_config, eye):
        from pupilio import Pupilio

        simulation_config.active_eye = eye
        tracker = Pupilio(config=simulation_config)
        try:
            assert tracker.config.active_eye == eye
        finally:
            tracker.release()
