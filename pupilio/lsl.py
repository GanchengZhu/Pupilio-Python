# _*_ coding: utf-8 _*_
# Copyright (c) 2026, Hangzhou DeepGaze Science and Technology Co., Ltd
# All Rights Reserved
#
# DESCRIPTION:
# LabStreamingLayer (LSL) integration for Pupilio Eye Tracker SDK.
# Supports real-time streaming of continuous gaze data and discrete marker events.

from __future__ import annotations

import logging
import threading
import time
from typing import Any, List, Optional, Tuple, TYPE_CHECKING
import numpy as np

if TYPE_CHECKING:
    from .core import Pupilio

logger = logging.getLogger(__name__)

# -------------------------------------------------------------------------
# Channel Specifications
# -------------------------------------------------------------------------

# Standard 12-channel layout (recommended for general research & EEG co-registration)
STANDARD_GAZE_CHANNELS: List[dict] = [
    {"label": "bino_gaze_x", "eye": "both", "type": "GazePosition", "unit": "pixels"},
    {"label": "bino_gaze_y", "eye": "both", "type": "GazePosition", "unit": "pixels"},
    {"label": "bino_valid", "eye": "both", "type": "Confidence", "unit": "binary"},
    {"label": "left_gaze_x", "eye": "left", "type": "GazePosition", "unit": "pixels"},
    {"label": "left_gaze_y", "eye": "left", "type": "GazePosition", "unit": "pixels"},
    {"label": "left_pupil_dia", "eye": "left", "type": "PupilDiameter", "unit": "mm"},
    {"label": "left_valid", "eye": "left", "type": "Confidence", "unit": "binary"},
    {"label": "right_gaze_x", "eye": "right", "type": "GazePosition", "unit": "pixels"},
    {"label": "right_gaze_y", "eye": "right", "type": "GazePosition", "unit": "pixels"},
    {"label": "right_pupil_dia", "eye": "right", "type": "PupilDiameter", "unit": "mm"},
    {"label": "right_valid", "eye": "right", "type": "Confidence", "unit": "binary"},
    {"label": "trigger", "eye": "none", "type": "TriggerCode", "unit": "integer"},
]

# Full 39-channel layout (38 full estimation parameters + 1 trigger channel)
FULL_GAZE_CHANNELS: List[dict] = [
    # Left eye (14)
    {"label": "left_gaze_x", "eye": "left", "type": "GazePosition", "unit": "pixels"},
    {"label": "left_gaze_y", "eye": "left", "type": "GazePosition", "unit": "pixels"},
    {"label": "left_pupil_dia", "eye": "left", "type": "PupilDiameter", "unit": "mm"},
    {"label": "left_pupil_pos_x", "eye": "left", "type": "PupilPosition", "unit": "mm"},
    {"label": "left_pupil_pos_y", "eye": "left", "type": "PupilPosition", "unit": "mm"},
    {"label": "left_pupil_pos_z", "eye": "left", "type": "PupilPosition", "unit": "mm"},
    {"label": "left_visual_angle_theta", "eye": "left", "type": "VisualAngle", "unit": "radians"},
    {"label": "left_visual_angle_phi", "eye": "left", "type": "VisualAngle", "unit": "radians"},
    {"label": "left_visual_vector_x", "eye": "left", "type": "VisualVector", "unit": "vector"},
    {"label": "left_visual_vector_y", "eye": "left", "type": "VisualVector", "unit": "vector"},
    {"label": "left_visual_vector_z", "eye": "left", "type": "VisualVector", "unit": "vector"},
    {"label": "left_pix_per_degree_x", "eye": "left", "type": "Resolution", "unit": "pixels/deg"},
    {"label": "left_pix_per_degree_y", "eye": "left", "type": "Resolution", "unit": "pixels/deg"},
    {"label": "left_valid", "eye": "left", "type": "Confidence", "unit": "binary"},
    # Right eye (14)
    {"label": "right_gaze_x", "eye": "right", "type": "GazePosition", "unit": "pixels"},
    {"label": "right_gaze_y", "eye": "right", "type": "GazePosition", "unit": "pixels"},
    {"label": "right_pupil_dia", "eye": "right", "type": "PupilDiameter", "unit": "mm"},
    {"label": "right_pupil_pos_x", "eye": "right", "type": "PupilPosition", "unit": "mm"},
    {"label": "right_pupil_pos_y", "eye": "right", "type": "PupilPosition", "unit": "mm"},
    {"label": "right_pupil_pos_z", "eye": "right", "type": "PupilPosition", "unit": "mm"},
    {"label": "right_visual_angle_theta", "eye": "right", "type": "VisualAngle", "unit": "radians"},
    {"label": "right_visual_angle_phi", "eye": "right", "type": "VisualAngle", "unit": "radians"},
    {"label": "right_visual_vector_x", "eye": "right", "type": "VisualVector", "unit": "vector"},
    {"label": "right_visual_vector_y", "eye": "right", "type": "VisualVector", "unit": "vector"},
    {"label": "right_visual_vector_z", "eye": "right", "type": "VisualVector", "unit": "vector"},
    {"label": "right_pix_per_degree_x", "eye": "right", "type": "Resolution", "unit": "pixels/deg"},
    {"label": "right_pix_per_degree_y", "eye": "right", "type": "Resolution", "unit": "pixels/deg"},
    {"label": "right_valid", "eye": "right", "type": "Confidence", "unit": "binary"},
    # Binocular fused (10)
    {"label": "bino_gaze_x", "eye": "both", "type": "GazePosition", "unit": "pixels"},
    {"label": "bino_gaze_y", "eye": "both", "type": "GazePosition", "unit": "pixels"},
    {"label": "bino_valid", "eye": "both", "type": "Confidence", "unit": "binary"},
    {"label": "bino_reserved_3", "eye": "both", "type": "Reserved", "unit": "unknown"},
    {"label": "bino_reserved_4", "eye": "both", "type": "Reserved", "unit": "unknown"},
    {"label": "bino_reserved_5", "eye": "both", "type": "Reserved", "unit": "unknown"},
    {"label": "bino_reserved_6", "eye": "both", "type": "Reserved", "unit": "unknown"},
    {"label": "bino_reserved_7", "eye": "both", "type": "Reserved", "unit": "unknown"},
    {"label": "bino_reserved_8", "eye": "both", "type": "Reserved", "unit": "unknown"},
    {"label": "bino_reserved_9", "eye": "both", "type": "Reserved", "unit": "unknown"},
    # Trigger channel (1)
    {"label": "trigger", "eye": "none", "type": "TriggerCode", "unit": "integer"},
]


def check_pylsl_available():
    """
    Check if pylsl is installed and importable.

    Returns:
        module: The imported pylsl module.

    Raises:
        ImportError: If pylsl is not installed, providing friendly installation instructions.
    """
    try:
        import pylsl
        return pylsl
    except ImportError as exc:
        raise ImportError(
            "LabStreamingLayer (LSL) support requires the 'pylsl' library. "
            "Please install it using: pip install pylsl"
        ) from exc


class ClockSync:
    """
    Clock synchronizer between hardware camera exposure timestamps (in ms)
    and pylsl.local_clock() (in seconds).
    """

    def __init__(self):
        self._offset: Optional[float] = None
        self._last_lsl_time: float = 0.0

    def reset(self):
        self._offset = None
        self._last_lsl_time = 0.0

    def get_lsl_time(self, hw_timestamp_ms: int, current_local_clock: float) -> float:
        """
        Convert hardware timestamp to an aligned LSL timestamp.

        Args:
            hw_timestamp_ms (int): Hardware exposure timestamp in milliseconds.
            current_local_clock (float): Result of pylsl.local_clock().

        Returns:
            float: Synchronized LSL timestamp in seconds.
        """
        if hw_timestamp_ms <= 0:
            # Fallback to local clock when hardware timestamp is not available
            return current_local_clock

        hw_seconds = hw_timestamp_ms / 1000.0
        if self._offset is None:
            self._offset = current_local_clock - hw_seconds

        calculated_lsl_time = hw_seconds + self._offset

        # Ensure monotonicity: timestamps should not go backwards
        if calculated_lsl_time < self._last_lsl_time:
            calculated_lsl_time = self._last_lsl_time

        self._last_lsl_time = calculated_lsl_time
        return calculated_lsl_time


class LSLWorkerThread(threading.Thread):
    """
    Background worker thread that samples gaze data from Pupilio
    and pushes it to LSL outlets without blocking the main rendering/experiment thread.
    """

    def __init__(self, lsl_manager: "LSLManager"):
        super().__init__(name="Pupilio-LSL-Worker", daemon=True)
        self.lsl_manager = lsl_manager
        self._running = False
        self._stop_event = threading.Event()

    def run(self):
        self._running = True
        self._stop_event.clear()

        pylsl = check_pylsl_available()
        pupil_io = self.lsl_manager.pupil_io
        gaze_outlet = self.lsl_manager.gaze_outlet
        stream_mode = self.lsl_manager.stream_mode
        clock_sync = self.lsl_manager.clock_sync

        sampling_rate = self.lsl_manager.nominal_srate
        # Sleep interval: slightly faster than sampling interval to poll new frames promptly
        sleep_interval = 1.0 / (sampling_rate * 2.0) if sampling_rate > 0 else 0.002

        last_timestamp = -1

        logger.info(f"LSL worker thread started (mode={stream_mode}, rate={sampling_rate}Hz).")

        while not self._stop_event.is_set():
            try:
                # Estimate gaze from Pupilio
                status, pt_l, pt_r, pt_bino, timestamp, _ = pupil_io.estimate_gaze()

                # Only push if this is a new frame or timestamp is valid
                if timestamp != last_timestamp or timestamp <= 0:
                    last_timestamp = timestamp

                    now_clock = pylsl.local_clock()
                    lsl_time = clock_sync.get_lsl_time(timestamp, now_clock)

                    # Retrieve and consume active trigger code for this sample
                    current_trigger = self.lsl_manager.consume_active_trigger()

                    if stream_mode == "standard":
                        # 12 channels:
                        # 0: bino_x, 1: bino_y, 2: bino_valid,
                        # 3: left_x, 4: left_y, 5: left_pupil, 6: left_valid,
                        # 7: right_x, 8: right_y, 9: right_pupil, 10: right_valid,
                        # 11: trigger
                        sample = [
                            float(pt_bino[0]), float(pt_bino[1]), float(pt_bino[2]),
                            float(pt_l[0]), float(pt_l[1]), float(pt_l[2]), float(pt_l[13]),
                            float(pt_r[0]), float(pt_r[1]), float(pt_r[2]), float(pt_r[13]),
                            float(current_trigger)
                        ]
                    else:
                        # 39 channels: full 38 items + trigger
                        full_38 = np.concatenate([pt_l, pt_r, pt_bino]).astype(float).tolist()
                        sample = full_38 + [float(current_trigger)]

                    if gaze_outlet is not None:
                        gaze_outlet.push_sample(sample, lsl_time)

                time.sleep(sleep_interval)

            except Exception as e:
                if not self._stop_event.is_set():
                    logger.warning(f"Error in LSL streaming worker: {e}")
                time.sleep(0.01)

        self._running = False
        logger.info("LSL worker thread stopped.")

    def stop(self):
        self._stop_event.set()


class LSLManager:
    """
    High-level manager for LabStreamingLayer (LSL) integration in Pupilio SDK.
    Manages Gaze and Marker StreamInfo, StreamOutlets, and background streaming.
    """

    def __init__(
        self,
        pupil_io: "Pupilio",
        gaze_stream_name: str = "Pupilio_Gaze",
        marker_stream_name: str = "Pupilio_Markers",
        stream_mode: str = "standard",
    ):
        """
        Initialize the LSL manager.

        Args:
            pupil_io (Pupilio): The parent Pupilio eye tracker instance.
            gaze_stream_name (str): Name of the continuous gaze stream. Default "Pupilio_Gaze".
            marker_stream_name (str): Name of the discrete marker stream. Default "Pupilio_Markers".
            stream_mode (str): "standard" (12 channels) or "full" (39 channels). Default "standard".
        """
        self.pylsl = check_pylsl_available()
        self.pupil_io = pupil_io
        self.gaze_stream_name = gaze_stream_name
        self.marker_stream_name = marker_stream_name
        self.stream_mode = stream_mode.lower()

        if self.stream_mode not in ("standard", "full"):
            raise ValueError(f"Invalid stream_mode '{stream_mode}'. Must be 'standard' or 'full'.")

        self.nominal_srate = float(getattr(pupil_io.config, "sampling_rate", 200) or 200)

        self.gaze_info: Optional[Any] = None
        self.marker_info: Optional[Any] = None
        self.gaze_outlet: Optional[Any] = None
        self.marker_outlet: Optional[Any] = None

        self.clock_sync = ClockSync()
        self.worker_thread: Optional[LSLWorkerThread] = None

        self._trigger_lock = threading.Lock()
        self._active_trigger: int = 0

        self._init_outlets()

    def _init_outlets(self):
        """Create StreamInfo and StreamOutlet instances with detailed XML metadata."""
        pylsl = self.pylsl

        # 1. Gaze Stream
        channels_spec = STANDARD_GAZE_CHANNELS if self.stream_mode == "standard" else FULL_GAZE_CHANNELS
        channel_count = len(channels_spec)
        source_id = f"pupilio_{self.stream_mode}_{int(self.nominal_srate)}hz"

        self.gaze_info = pylsl.StreamInfo(
            name=self.gaze_stream_name,
            type="Gaze",
            channel_count=channel_count,
            nominal_srate=self.nominal_srate,
            channel_format=pylsl.cf_float32,
            source_id=source_id,
        )

        # Populate XML description
        desc = self.gaze_info.desc()
        channels_xml = desc.append_child("channels")
        for ch in channels_spec:
            ch_node = channels_xml.append_child("channel")
            ch_node.append_child_value("label", ch["label"])
            ch_node.append_child_value("eye", ch["eye"])
            ch_node.append_child_value("type", ch["type"])
            ch_node.append_child_value("unit", ch["unit"])

        hardware_xml = desc.append_child("hardware")
        hardware_xml.append_child_value("manufacturer", "Hangzhou DeepGaze Science and Technology Co., Ltd")
        hardware_xml.append_child_value("model", "Pupil.IO AIO")
        hardware_xml.append_child_value("stream_mode", self.stream_mode)
        hardware_xml.append_child_value("nominal_rate", str(self.nominal_srate))

        display_xml = desc.append_child("display")
        display_xml.append_child_value("resolution_x", "1920")
        display_xml.append_child_value("resolution_y", "1080")

        self.gaze_outlet = pylsl.StreamOutlet(self.gaze_info)

        # 2. Marker Stream (for discrete triggers / string annotations)
        marker_source_id = f"pupilio_markers_{self.marker_stream_name}"
        self.marker_info = pylsl.StreamInfo(
            name=self.marker_stream_name,
            type="Markers",
            channel_count=1,
            nominal_srate=pylsl.IRREGULAR_RATE,
            channel_format=pylsl.cf_string,
            source_id=marker_source_id,
        )
        self.marker_outlet = pylsl.StreamOutlet(self.marker_info)

        logger.info(
            f"LSL Outlets created: Gaze='{self.gaze_stream_name}' ({channel_count} channels), "
            f"Markers='{self.marker_stream_name}'."
        )

    def start(self):
        """Start the background streaming worker thread."""
        if self.worker_thread is not None and self.worker_thread.is_alive():
            logger.warning("LSL streaming is already running.")
            return

        self.clock_sync.reset()
        self.worker_thread = LSLWorkerThread(self)
        self.worker_thread.start()
        logger.info("LSL streaming started successfully.")

    def stop(self):
        """Stop the background streaming worker thread."""
        if self.worker_thread is not None:
            self.worker_thread.stop()
            self.worker_thread.join(timeout=2.0)
            self.worker_thread = None
            logger.info("LSL streaming stopped.")

    @property
    def is_running(self) -> bool:
        """Report whether the LSL streaming worker is currently active."""
        return self.worker_thread is not None and self.worker_thread.is_alive()

    def push_trigger(self, trigger_code: int):
        """
        Record a trigger integer code.
        The trigger code will be broadcast to the discrete Marker stream immediately
        and injected into the continuous gaze stream's trigger channel on the next sample.

        Args:
            trigger_code (int): Trigger integer code (1-65535).
        """
        with self._trigger_lock:
            self._active_trigger = trigger_code

        # Also push immediately to the discrete marker stream
        if self.marker_outlet is not None:
            now_clock = self.pylsl.local_clock()
            self.marker_outlet.push_sample([str(trigger_code)], now_clock)

    def push_marker(self, marker_text: str):
        """
        Broadcast a custom semantic string marker to the discrete Marker stream.

        Args:
            marker_text (str): Marker string annotation (e.g. 'STIM_ONSET', 'TRIAL_START').
        """
        if self.marker_outlet is not None:
            now_clock = self.pylsl.local_clock()
            self.marker_outlet.push_sample([str(marker_text)], now_clock)

    def consume_active_trigger(self) -> int:
        """
        Retrieve and consume the active trigger code for the current sample frame.
        Once read, resets to 0 (pulse behavior).

        Returns:
            int: The active trigger code, or 0 if none.
        """
        with self._trigger_lock:
            val = self._active_trigger
            self._active_trigger = 0
            return val

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


# Alias PupilioLSLOutlet to LSLManager for user familiarity
PupilioLSLOutlet = LSLManager
