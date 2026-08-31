# _*_ coding: utf-8 _*_
# Tests for the CalibrationListener hook interface.

from pupilio.callback import CalibrationListener


class TestCalibrationListener:
    def test_default_hooks_are_no_ops(self):
        # CalibrationUI calls these unconditionally, so the base implementation
        # must tolerate being called without being overridden.
        listener = CalibrationListener()

        assert listener.on_calibration_target_onset(0) is None
        assert listener.on_validation_target_onset(0) is None

    def test_subclass_hooks_receive_the_point_index(self):
        class RecordingListener(CalibrationListener):
            def __init__(self):
                super().__init__()
                self.calibration_points = []
                self.validation_points = []

            def on_calibration_target_onset(self, point_index):
                self.calibration_points.append(point_index)

            def on_validation_target_onset(self, point_index):
                self.validation_points.append(point_index)

        listener = RecordingListener()
        for index in range(3):
            listener.on_calibration_target_onset(index)
        listener.on_validation_target_onset(4)

        assert listener.calibration_points == [0, 1, 2]
        assert listener.validation_points == [4]

    def test_is_the_documented_extension_point(self):
        class Listener(CalibrationListener):
            pass

        assert isinstance(Listener(), CalibrationListener)
