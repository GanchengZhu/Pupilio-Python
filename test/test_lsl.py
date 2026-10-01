# _*_ coding: utf-8 _*_
# Copyright (c) 2026, Hangzhou DeepGaze Science and Technology Co., Ltd
# All Rights Reserved
#
# DESCRIPTION:
# Unit and integration tests for LabStreamingLayer (LSL) integration in Pupilio SDK.

import time

import pylsl
import pytest

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

            # The 39-field ordering is the most fragile part of the LSL spec;
            # verify the advertised channel labels match what the docstring and
            # channel-spec list claim, not just the count.
            info = inlet.info()
            channel = info.desc().child("channels").child("channel")
            labels = []
            for _ in range(info.channel_count()):
                labels.append(channel.child_value("label"))
                channel = channel.next_sibling()

            assert labels[0] == "left_gaze_x"
            assert labels[13] == "left_valid"
            assert labels[14] == "right_gaze_x"
            assert labels[27] == "right_valid"
            assert labels[28] == "bino_gaze_x"
            assert labels[38] == "trigger"

        finally:
            if 'inlet' in locals():
                inlet.close_stream()
            pupil_io.stop_sampling()
            pupil_io.release()


class TestSamplingIdempotency:
    """
    Pins the idempotent start/stop semantics.

    ``stop_sampling`` used to raise when no session was running, and
    ``start_sampling`` used to raise when one was already active. Both are now
    no-ops that return ``ET_SUCCESS``. The tests here fail loudly if either
    reverts, so a caller relying on the new contract is not surprised by a
    runtime error in production.
    """

    @pytest.fixture
    def pupil_io(self):
        config = DefaultConfig()
        config.simulation_mode = True
        tracker = Pupilio(config=config)
        try:
            yield tracker
        finally:
            tracker.release()

    def test_stop_without_start_is_a_noop(self, pupil_io):
        # The native call would dereference a null sampling thread if it ran.
        # The guard must short-circuit and return success rather than raising.
        assert pupil_io.stop_sampling() == ET_ReturnCode.ET_SUCCESS

    def test_double_start_is_a_noop(self, pupil_io):
        pupil_io.create_session("idempotent_start")
        pupil_io.start_sampling()
        try:
            assert pupil_io.start_sampling() == ET_ReturnCode.ET_SUCCESS
            assert pupil_io.get_sampling_status() is True
        finally:
            pupil_io.stop_sampling()

    def test_double_stop_is_a_noop(self, pupil_io):
        pupil_io.create_session("idempotent_stop")
        pupil_io.start_sampling()
        pupil_io.stop_sampling()
        assert pupil_io.stop_sampling() == ET_ReturnCode.ET_SUCCESS


class TestLSLManagerLifecycle:
    """
    Pins the thread-safe start/stop contract of ``LSLManager``.

    The two methods are now serialized by an internal lock and are safe to call
    twice. A second ``start()`` must not spawn a duplicate worker (which would
    double every sample in the recorded stream), and a second ``stop()`` must
    not raise. These tests exercise both.
    """

    @pytest.fixture
    def manager(self):
        config = DefaultConfig()
        config.simulation_mode = True
        config.enable_lsl = True
        config.lsl_stream_mode = "standard"
        config.lsl_gaze_stream_name = f"Test_Lifecycle_{int(time.time())}"
        config.lsl_marker_stream_name = f"Test_Lifecycle_Markers_{int(time.time())}"

        tracker = Pupilio(config=config)
        try:
            yield tracker.lsl_manager
        finally:
            tracker.release()

    def test_double_start_does_not_spawn_two_workers(self, manager):
        manager.start()
        first = manager.worker_thread
        manager.start()
        # Same thread object; the second start is a no-op.
        assert manager.worker_thread is first
        manager.stop()

    def test_stop_is_idempotent(self, manager):
        manager.start()
        manager.stop()
        # Stopping twice must not raise, and the worker reference must be
        # cleared after a successful join.
        manager.stop()
        assert manager.worker_thread is None

    def test_is_running_reflects_lifecycle(self, manager):
        assert manager.is_running is False
        manager.start()
        assert manager.is_running is True
        manager.stop()
        assert manager.is_running is False

