# _*_ coding: utf-8 _*_
# Tests for EventDetection argument validation.
#
# These cover the checks that run before the native library is called, so they
# assert on behaviour the Python layer owns.
#
# NOTE: The exact validation contract (which values are accepted, what
# exception types are raised, whether the output directory is created before or
# after the native call) is defined in pupilio/event_detection.py. If that
# module changes its validation, these tests must change with it. The
# ``test_event_detection_imports_cleanly`` test exists so an import-time break
# (e.g. a renamed symbol in pupilio.misc) surfaces as one clear failure rather
# than as an opaque error in every fixture-dependent test.

import pytest
from conftest import windows_only

pytestmark = windows_only


@pytest.fixture
def detector():
    from pupilio.event_detection import EventDetection

    return EventDetection()


@pytest.fixture
def data_file(tmp_path):
    path = tmp_path / "gaze.csv"
    path.write_text("timestamp,x,y\n0,100,100\n", encoding="utf-8")
    return str(path)


class TestImports:
    def test_event_detection_imports_cleanly(self):
        # Guards against a symbol rename in pupilio.misc (e.g. StrEnum ->
        # _StrEnum) breaking the module at import time. Without this, the
        # fixture used by every other test in the file is the first thing to
        # fail, and the error is reported against the wrong test.
        import pupilio.event_detection  # noqa: F401

        from pupilio.event_detection import EventDetection

        assert EventDetection is not None


class TestDetectValidation:
    def test_missing_input_file_is_rejected(self, detector, tmp_path):
        with pytest.raises(ValueError, match="not found"):
            detector.detect(
                data_path=str(tmp_path / "does_not_exist.csv"),
                output_dir=str(tmp_path),
                which_eye="left",
            )

    @pytest.mark.parametrize("which_eye", ["both", "LEFT", "", "binocular"])
    def test_unknown_eye_string_is_rejected(self, detector, data_file, tmp_path, which_eye):
        with pytest.raises(ValueError, match="which_eye"):
            detector.detect(
                data_path=data_file,
                output_dir=str(tmp_path),
                which_eye=which_eye,
            )

    def test_none_eye_is_rejected(self, detector, data_file, tmp_path):
        # Separated from the string cases because a validator that calls
        # .lower() / .strip() on its argument would raise AttributeError for
        # None before any membership check runs. Either ValueError (clean
        # rejection) or TypeError (attribute error surfaced) is acceptable —
        # what matters is that the call does not silently succeed.
        with pytest.raises((ValueError, TypeError)):
            detector.detect(
                data_path=data_file,
                output_dir=str(tmp_path),
                which_eye=None,
            )

    @pytest.mark.parametrize("which_eye", ["left", "right", "bino"])
    def test_documented_eyes_pass_validation(self, detector, data_file, tmp_path, which_eye):
        # The native call may still fail on this stub CSV. What this test cares
        # about is that validation does not reject a documented value. We treat
        # any non-validation exception as "validation passed, native failed" —
        # but we explicitly check the failure is not a validation error that
        # happened to be wrapped in a runtime exception.
        try:
            detector.detect(
                data_path=data_file,
                output_dir=str(tmp_path),
                which_eye=which_eye,
            )
        except ValueError as exc:
            pytest.fail(f"'{which_eye}' should be accepted, but raised: {exc}")
        except Exception as exc:
            # Native-side failure. Confirm the message isn't a validation error.
            message = str(exc).lower()
            assert "which_eye" not in message, (
                f"'{which_eye}' was rejected, but the error was raised as "
                f"{type(exc).__name__} instead of ValueError: {exc}"
            )

    @pytest.mark.parametrize("duration", [0, -1, -100])
    def test_non_positive_duration_is_rejected(self, detector, data_file, tmp_path, duration):
        with pytest.raises(ValueError, match="minimum_duration"):
            detector.detect(
                data_path=data_file,
                output_dir=str(tmp_path),
                which_eye="left",
                minimum_duration=duration,
            )

    @pytest.mark.parametrize("threshold", [0, -0.5, -10.0])
    def test_non_positive_dispersion_is_rejected(self, detector, data_file, tmp_path, threshold):
        with pytest.raises(ValueError, match="dispersion_threshold"):
            detector.detect(
                data_path=data_file,
                output_dir=str(tmp_path),
                which_eye="left",
                dispersion_threshold=threshold,
            )

    def test_missing_output_directory_is_created(self, detector, data_file, tmp_path):
        # Unlike the input path, a missing output directory is created rather
        # than rejected, so results can be written to a fresh folder per run.
        #
        # Caveat: this asserts that mkdir happens before whatever step fails on
        # the stub CSV. If the implementation moves mkdir after the native call,
        # this test will need to change with it.
        output_dir = tmp_path / "new" / "nested"

        try:
            detector.detect(
                data_path=data_file,
                output_dir=str(output_dir),
                which_eye="left",
            )
        except Exception:
            # Native failure is expected with the stub CSV; we only care about
            # the mkdir side effect.
            pass

        assert output_dir.is_dir()
