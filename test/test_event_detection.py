# _*_ coding: utf-8 _*_
# Tests for EventDetection argument validation.
#
# These cover the checks that run before the native library is called, so they
# assert on behaviour the Python layer owns.

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


class TestDetectValidation:
    def test_missing_input_file_is_rejected(self, detector, tmp_path):
        with pytest.raises(ValueError, match="not found"):
            detector.detect(
                data_path=str(tmp_path / "does_not_exist.csv"),
                output_dir=str(tmp_path),
                which_eye="left",
            )

    @pytest.mark.parametrize("which_eye", ["both", "LEFT", "", "binocular", None])
    def test_unknown_eye_is_rejected(self, detector, data_file, tmp_path, which_eye):
        with pytest.raises(ValueError, match="which_eye"):
            detector.detect(
                data_path=data_file,
                output_dir=str(tmp_path),
                which_eye=which_eye,
            )

    @pytest.mark.parametrize("which_eye", ["left", "right", "bino"])
    def test_documented_eyes_pass_validation(self, detector, data_file, tmp_path, which_eye):
        # The native call may still fail on this stub CSV; what matters here is
        # that validation does not reject a documented value.
        try:
            detector.detect(
                data_path=data_file,
                output_dir=str(tmp_path),
                which_eye=which_eye,
            )
        except RuntimeError:
            pass
        except ValueError as exc:  # pragma: no cover - would be a validation bug
            pytest.fail(f"'{which_eye}' should be accepted, but raised: {exc}")

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
        output_dir = tmp_path / "new" / "nested"

        try:
            detector.detect(
                data_path=data_file,
                output_dir=str(output_dir),
                which_eye="left",
            )
        except RuntimeError:
            pass

        assert output_dir.is_dir()
