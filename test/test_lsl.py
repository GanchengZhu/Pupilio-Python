# _*_ coding: utf-8 _*_
# Copyright (c) 2026, Hangzhou DeepGaze Science and Technology Co., Ltd
# All Rights Reserved
#
# DESCRIPTION:
# Unit and integration tests for LabStreamingLayer (LSL) integration in Pupilio SDK.

import time
import pytest
import pylsl
from pupilio import Pupilio, DefaultConfig, ET_ReturnCode
from pupilio.lsl import (
    STANDARD_GAZE_CHANNELS,
    FULL_GAZE_CHANNELS,
    ClockSync,
    LSLManager,
)


class TestLSLChannelSpecifications:
    def test_standard_channels_count_and_structure(self):
        assert len(STANDARD_GAZE_CHANNELS) == 12
        assert STANDARD_GAZE_CHANNELS[0]["label"] == "bino_gaze_x"
        assert STANDARD_GAZE_CHANNELS[1]["label"] == "bino_gaze_y"
        assert STANDARD_GAZE_CHANNELS[2]["label"] == "bino_valid"
        assert STANDARD_GAZE_CHANNELS[3]["label"] == "left_gaze_x"
        assert STANDARD_GAZE_CHANNELS[4]["label"] == "left_gaze_y"
        assert STANDARD_GAZE_CHANNELS[5]["label"] == "left_pupil_dia"
        assert STANDARD_GAZE_CHANNELS[6]["label"] == "left_valid"
        assert STANDARD_GAZE_CHANNELS[7]["label"] == "right_gaze_x"
        assert STANDARD_GAZE_CHANNELS[8]["label"] == "right_gaze_y"
        assert STANDARD_GAZE_CHANNELS[9]["label"] == "right_pupil_dia"
        assert STANDARD_GAZE_CHANNELS[10]["label"] == "right_valid"
        assert STANDARD_GAZE_CHANNELS[11]["label"] == "trigger"

    def test_full_channels_count_and_structure(self):
        assert len(FULL_GAZE_CHANNELS) == 39
        assert FULL_GAZE_CHANNELS[0]["label"] == "left_gaze_x"
        assert FULL_GAZE_CHANNELS[13]["label"] == "left_valid"
        assert FULL_GAZE_CHANNELS[14]["label"] == "right_gaze_x"
        assert FULL_GAZE_CHANNELS[27]["label"] == "right_valid"
        assert FULL_GAZE_CHANNELS[28]["label"] == "bino_gaze_x"
        assert FULL_GAZE_CHANNELS[38]["label"] == "trigger"


class TestClockSync:
    def test_clock_sync_monotonicity_and_offset(self):
        sync = ClockSync()
        t0_clock = 1000.0
        hw_t0 = 50000  # 50 sec

        # First sample establishes offset
        lsl_t0 = sync.get_lsl_time(hw_t0, t0_clock)
        assert abs(lsl_t0 - t0_clock) < 1e-4

        # Subsequent sample: +10 ms hardware time
        hw_t1 = 50010
        lsl_t1 = sync.get_lsl_time(hw_t1, t0_clock + 0.0105)
        assert abs(lsl_t1 - (t0_clock + 0.010)) < 1e-4
        assert lsl_t1 >= lsl_t0

    def test_clock_sync_fallback_on_zero_timestamp(self):
        sync = ClockSync()
        t = sync.get_lsl_time(0, 123.456)
        assert t == 123.456


class TestLSLStreamingSimulation:
    def test_config_lsl_mode_validation(self):
        config = DefaultConfig()
        config.lsl_stream_mode = "standard"
        assert config.lsl_stream_mode == "standard"
        config.lsl_stream_mode = "full"
        assert config.lsl_stream_mode == "full"

        with pytest.raises(ValueError, match="Invalid lsl_stream_mode"):
            config.lsl_stream_mode = "invalid_mode"

    def test_lsl_standard_stream_reception(self):
        # Unique stream names to prevent conflict with other tests/devices on network
        gaze_name = f"Test_Pupilio_Gaze_Std_{int(time.time())}"
        marker_name = f"Test_Pupilio_Markers_Std_{int(time.time())}"

        config = DefaultConfig()
        config.simulation_mode = True
        config.enable_lsl = True
        config.lsl_stream_mode = "standard"
        config.lsl_gaze_stream_name = gaze_name
        config.lsl_marker_stream_name = marker_name

        pupil_io = Pupilio(config=config)
        pupil_io.create_session("lsl_sim_std_session")

        try:
            assert pupil_io.lsl_manager is not None
            assert pupil_io.lsl_manager.gaze_info.channel_count() == 12

            # Start sampling (which starts LSL worker)
            pupil_io.start_sampling()
            time.sleep(0.1)

            # Resolve gaze stream via LSL
            gaze_streams = pylsl.resolve_byprop("name", gaze_name, timeout=3.0)
            assert len(gaze_streams) > 0, f"Could not find LSL stream '{gaze_name}'"

            inlet = pylsl.StreamInlet(gaze_streams[0])
            sample, timestamp = inlet.pull_sample(timeout=2.0)
            assert sample is not None
            assert len(sample) == 12
            assert timestamp > 0

            # Resolve marker stream
            marker_streams = pylsl.resolve_byprop("name", marker_name, timeout=3.0)
            assert len(marker_streams) > 0, f"Could not find LSL stream '{marker_name}'"
            marker_inlet = pylsl.StreamInlet(marker_streams[0])
            marker_inlet.open_stream(timeout=2.0)
            time.sleep(0.3)  # Allow TCP connection handshake to establish

            # Send trigger
            pupil_io.set_trigger(42)

            # Check that discrete marker received the trigger string
            marker_sample, marker_ts = marker_inlet.pull_sample(timeout=2.0)
            assert marker_sample is not None
            assert marker_sample[0] == "42"

            # Send custom string marker
            pupil_io.send_lsl_marker("TEST_STIMULUS_ON")
            annot_sample, _ = marker_inlet.pull_sample(timeout=2.0)
            assert annot_sample is not None
            assert annot_sample[0] == "TEST_STIMULUS_ON"

        finally:
            if 'inlet' in locals():
                inlet.close_stream()
            if 'marker_inlet' in locals():
                marker_inlet.close_stream()
            pupil_io.stop_sampling()
            pupil_io.release()

    def test_lsl_full_stream_reception(self):
        gaze_name = f"Test_Pupilio_Gaze_Full_{int(time.time())}"
        marker_name = f"Test_Pupilio_Markers_Full_{int(time.time())}"

        config = DefaultConfig()
        config.simulation_mode = True
        config.enable_lsl = True
        config.lsl_stream_mode = "full"
        config.lsl_gaze_stream_name = gaze_name
        config.lsl_marker_stream_name = marker_name

        pupil_io = Pupilio(config=config)
        pupil_io.create_session("lsl_sim_full_session")

        try:
            assert pupil_io.lsl_manager is not None
            assert pupil_io.lsl_manager.gaze_info.channel_count() == 39

            pupil_io.start_sampling()
            time.sleep(0.1)

            gaze_streams = pylsl.resolve_byprop("name", gaze_name, timeout=3.0)
            assert len(gaze_streams) > 0

            inlet = pylsl.StreamInlet(gaze_streams[0])
            sample, timestamp = inlet.pull_sample(timeout=2.0)
            assert sample is not None
            assert len(sample) == 39
            assert timestamp > 0

        finally:
            if 'inlet' in locals():
                inlet.close_stream()
            pupil_io.stop_sampling()
            pupil_io.release()
