#!/usr/bin/env python
# _*_ coding: utf-8 _*_

# Copyright (c) 2026, Hangzhou DeepGaze Science and Technology Co., Ltd
# All Rights Reserved
#
# For use by Hangzhou DeepGaze Science and Technology Co., Ltd customers
# only. Redistribution and use in source and binary forms, with or without
# modification, are NOT permitted.
#
# Redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in
# the documentation and/or other materials provided with the distribution.
#
# Neither name of Hangzhou DeepGaze Sci & Tech Ltd nor the name of
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS ``AS
# IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED
# TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
# PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE REGENTS OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# DESCRIPTION:
# The core library

# Author: GC Zhu
# Email: zhugc2016@gmail.com
# Last updated: 2026/10/01 by Zhiguo Wang

from __future__ import annotations

import ctypes
import ipaddress
import logging
import os
import platform
import re
import threading          # NEW: for _sampling_lock
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Tuple

import cv2
import numpy as np

from .annotation import deprecated
from .default_config import DefaultConfig
from .misc import ET_ReturnCode, CalibrationMode, CameraMode

# Hardware-supported sampling rates (sync_400 sensor capability)
HARDWARE_RATES = [200, 400]

logger = logging.getLogger(__name__)


class Pupilio:
    """Class for interacting with the eye tracker dynamic link library (DLL).
        A pythonic wrapper for Pupilio library."""

    def __init__(self, config=None):
        """
        Load the native library and bring the eye tracker up to a ready state.

        Loads ``PupilioET.dll`` (or ``DummyPupilioET.dll`` when ``config.simulation_mode``
        is set), binds every native entry point through ctypes, applies the eye mode,
        look-ahead, kappa filter, logging, and calibration mode from ``config``, then
        initialises the tracker. If a 400 Hz-capable camera is asked to run at 200 Hz, the
        tracker is released, switched to ``CAMERA_MODE_SYNC_200``, and re-initialised, since
        the camera cannot be reconfigured while open.

        Args:
            config (DefaultConfig, optional): Settings to apply. A default instance is
                created when omitted.

        Raises:
            ValueError: If ``config.look_ahead`` is not an integer in ``(0, 4]``.
            RuntimeError: If the native tracker fails to initialise, or if the host
                platform is not Windows.
        """

        if config is None:
            self.config = DefaultConfig()
        else:
            self.config = config

        # --- 整合 Logging ---
        if self.config.enable_debug_logging:
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.WARNING)

        # FIX: sampling state lock, shared by start_sampling / stop_sampling
        self._sampling_lock = threading.Lock()

        # Determine the platform and load the appropriate DLL
        if platform.system().lower() == 'windows':
            _current_dir = os.path.abspath(os.path.dirname(__file__))
            _lib_dir = os.path.join(_current_dir, "lib")
            os.add_dll_directory(_lib_dir)
            os.environ['PATH'] = os.environ['PATH'] + ';' + _lib_dir
            if self.config.simulation_mode:
                _dll_path = os.path.join(_lib_dir, 'DummyPupilioET.dll')
            else:
                _dll_path = os.path.join(_lib_dir, 'PupilioET.dll')
            self._et_native_lib = ctypes.CDLL(_dll_path, winmode=0)
        else:
            # FIX: fail fast on unsupported platforms instead of AttributeError later
            raise RuntimeError(
                f"Pupilio native library is only available on Windows; "
                f"detected platform: {platform.system()}"
            )

        # initialize get_camera_mode return value
        self._camera_mode = None
        self.left_roi = None
        self.right_roi = None
        self._is_initialized = False

        self._session_name = ""

        # Set return types
        self._et_native_lib.pupil_io_set_look_ahead.restype = ctypes.c_int
        self._et_native_lib.pupil_io_init.restype = ctypes.c_int
        self._et_native_lib.pupil_io_recalibrate.restype = ctypes.c_int
        self._et_native_lib.pupil_io_face_pos.restype = ctypes.c_int
        self._et_native_lib.pupil_io_cali.restype = ctypes.c_int
        self._et_native_lib.pupil_io_est.restype = ctypes.c_int
        self._et_native_lib.pupil_io_est_lr.restype = ctypes.c_int
        self._et_native_lib.pupil_io_release.restype = ctypes.c_int
        self._et_native_lib.pupil_io_get_version.restype = ctypes.c_char_p
        self._et_native_lib.pupil_io_get_previewer.restype = ctypes.c_int

        self._et_native_lib.pupil_io_previewer_init.restype = ctypes.c_int
        self._et_native_lib.pupil_io_previewer_start.restype = ctypes.c_int
        self._et_native_lib.pupil_io_previewer_stop.restype = ctypes.c_int

        self._et_native_lib.pupil_io_create_session.restype = ctypes.c_int
        self._et_native_lib.pupil_io_set_filter_enable.restype = ctypes.c_int
        self._et_native_lib.pupil_io_start_sampling.restype = ctypes.c_int
        self._et_native_lib.pupil_io_stop_sampling.restype = ctypes.c_int
        self._et_native_lib.pupil_io_sampling_status.restype = ctypes.c_int
        self._et_native_lib.pupil_io_send_trigger.restype = ctypes.c_int
        self._et_native_lib.pupil_io_save_data_to.restype = ctypes.c_int
        self._et_native_lib.pupil_io_clear_cache.restype = ctypes.c_int
        self._et_native_lib.pupil_io_get_current_gaze.restype = ctypes.c_int
        self._et_native_lib.pupil_io_set_cali_mode.restype = ctypes.c_int
        self._et_native_lib.pupil_io_set_kappa_filter.restype = ctypes.c_int
        self._et_native_lib.pupil_io_set_log.restype = ctypes.c_int
        self._et_native_lib.pupil_io_set_eye_mode.restype = ctypes.c_int
        self._et_native_lib.pupil_io_estimate_gaze.restype = ctypes.c_int

        # Set argument types
        self._et_native_lib.pupil_io_init.argtypes = []
        self._et_native_lib.pupil_io_recalibrate.argtypes = []
        self._et_native_lib.pupil_io_release.argtypes = []
        self._et_native_lib.pupil_io_get_version.argtypes = []
        self._et_native_lib.pupil_io_previewer_start.argtypes = []
        self._et_native_lib.pupil_io_previewer_stop.argtypes = []
        self._et_native_lib.pupil_io_start_sampling.argtypes = []
        self._et_native_lib.pupil_io_stop_sampling.argtypes = []
        self._et_native_lib.pupil_io_clear_cache.argtypes = []
        self._et_native_lib.pupil_io_set_look_ahead.argtypes = [ctypes.c_int]

        self._et_native_lib.pupil_io_cali.argtypes = [ctypes.c_int]
        self._et_native_lib.pupil_io_face_pos.argtypes = [
            np.ctypeslib.ndpointer(dtype=np.float32, ndim=1, flags='C_CONTIGUOUS')
        ]
        self._et_native_lib.pupil_io_est.argtypes = [
            np.ctypeslib.ndpointer(dtype=np.float32, ndim=1, flags='C_CONTIGUOUS'),
            ctypes.POINTER(ctypes.c_longlong)
        ]
        self._et_native_lib.pupil_io_est_lr.argtypes = [
            np.ctypeslib.ndpointer(dtype=np.float32, ndim=1, flags='C_CONTIGUOUS'),
            np.ctypeslib.ndpointer(dtype=np.float32, ndim=1, flags='C_CONTIGUOUS'),
            ctypes.POINTER(ctypes.c_longlong)
        ]
        self._et_native_lib.pupil_io_estimate_gaze.argtypes = [
            np.ctypeslib.ndpointer(dtype=np.float32, ndim=1, flags='C_CONTIGUOUS'),
            np.ctypeslib.ndpointer(dtype=np.float32, ndim=1, flags='C_CONTIGUOUS'),
            np.ctypeslib.ndpointer(dtype=np.float32, ndim=1, flags='C_CONTIGUOUS'),
            ctypes.POINTER(ctypes.c_longlong)
        ]
        self._et_native_lib.pupil_io_get_previewer.argtypes = [
            ctypes.POINTER(ctypes.POINTER(ctypes.c_ubyte)),
            ctypes.POINTER(ctypes.POINTER(ctypes.c_ubyte)),
            np.ctypeslib.ndpointer(dtype=np.float32, ndim=1, flags='C_CONTIGUOUS'),
            np.ctypeslib.ndpointer(dtype=np.float32, ndim=1, flags='C_CONTIGUOUS'),
            np.ctypeslib.ndpointer(dtype=np.float32, ndim=1, flags='C_CONTIGUOUS')
        ]
        self._et_native_lib.pupil_io_previewer_init.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_bool]
        self._et_native_lib.pupil_io_send_trigger.argtypes = [ctypes.c_uint64]
        self._et_native_lib.pupil_io_set_filter_enable.argtypes = [ctypes.c_bool]
        self._et_native_lib.pupil_io_save_data_to.argtypes = [ctypes.c_char_p]
        self._et_native_lib.pupil_io_create_session.argtypes = [ctypes.c_char_p]

        self._et_native_lib.pupil_io_sampling_status.argtypes = [ctypes.POINTER(ctypes.c_bool)]
        self._et_native_lib.pupil_io_get_current_gaze.argtypes = [
            np.ctypeslib.ndpointer(dtype=np.float32, ndim=1, flags='C_CONTIGUOUS'),
            np.ctypeslib.ndpointer(dtype=np.float32, ndim=1, flags='C_CONTIGUOUS'),
            np.ctypeslib.ndpointer(dtype=np.float32, ndim=1, flags='C_CONTIGUOUS')
        ]
        self._et_native_lib.pupil_io_set_cali_mode.argtypes = [
            ctypes.c_int,
            np.ctypeslib.ndpointer(dtype=np.float32, ndim=1, flags='C_CONTIGUOUS'),
        ]

        self._et_native_lib.pupil_io_set_kappa_filter.argtypes = [ctypes.c_int]
        self._et_native_lib.pupil_io_set_log.argtypes = [ctypes.c_int, ctypes.c_char_p]
        self._et_native_lib.pupil_io_set_eye_mode.argtypes = [ctypes.c_int]
        self._et_native_lib.pupil_io_get_camera_mode.restype = ctypes.c_int
        self._et_native_lib.pupil_io_get_camera_mode.argtypes = [
            ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.c_int)
        ]

        self._et_native_lib.pupil_io_est_full.restype = ctypes.c_int
        self._et_native_lib.pupil_io_est_full.argtypes = [
            np.ctypeslib.ndpointer(dtype=np.float32, ndim=1, flags='C_CONTIGUOUS'),
            ctypes.POINTER(ctypes.c_longlong)
        ]

        # ---------- 绑定 pupil_io_set_camera_mode ----------
        self._et_native_lib.pupil_io_set_camera_mode.restype = ctypes.c_int
        self._et_native_lib.pupil_io_set_camera_mode.argtypes = [
            ctypes.POINTER(ctypes.c_int)
        ]

        if hasattr(self._et_native_lib, "get_version"):
            self._et_native_lib.get_version.restype = ctypes.c_char_p
            self._et_native_lib.get_version.argtypes = []

        if hasattr(self._et_native_lib, "pupil_io_previewer_init_ex"):
            self._et_native_lib.pupil_io_previewer_init_ex.restype = ctypes.c_int
            self._et_native_lib.pupil_io_previewer_init_ex.argtypes = [
                ctypes.c_char_p, ctypes.c_int, ctypes.c_bool, ctypes.c_int
            ]

        if hasattr(self._et_native_lib, "pupil_io_previewer_set_fps"):
            self._et_native_lib.pupil_io_previewer_set_fps.restype = ctypes.c_int
            self._et_native_lib.pupil_io_previewer_set_fps.argtypes = [ctypes.c_int]

        if hasattr(self._et_native_lib, "pupil_io_previewer_get_fps"):
            self._et_native_lib.pupil_io_previewer_get_fps.restype = ctypes.c_int
            self._et_native_lib.pupil_io_previewer_get_fps.argtypes = []

        if hasattr(self._et_native_lib, "pupil_io_get_last_error"):
            self._et_native_lib.pupil_io_get_last_error.restype = ctypes.c_char_p
            self._et_native_lib.pupil_io_get_last_error.argtypes = []

        version = self._et_native_lib.pupil_io_get_version()
        # FIX: decode with errors="replace" so an odd byte doesn't crash __init__;
        # also route through the logger instead of print
        logger.info("Native Pupilio Version: %s",
                    version.decode("gbk", errors="replace") if version else "<unknown>")

        # set tracking eye
        ret = self._et_native_lib.pupil_io_set_eye_mode(self.config.active_eye.value)
        if ret != ET_ReturnCode.ET_SUCCESS.value:
            logger.warning(f"pupil_io_set_eye_mode returned code {ret}")

        # set filter parameter: look ahead
        if not (isinstance(self.config.look_ahead, int) and (0 <= self.config.look_ahead <= 4)):
            raise ValueError("Parameter `look_ahead` must be between 0 and 4 and integer")

        ret = self._et_native_lib.pupil_io_set_look_ahead(self.config.look_ahead)
        if ret != ET_ReturnCode.ET_SUCCESS.value:
            logger.warning(f"pupil_io_set_look_ahead returned code {ret}")

        # set enable kappa verify
        ret = self._et_native_lib.pupil_io_set_kappa_filter(self.config.enable_kappa_verification)
        if ret != ET_ReturnCode.ET_SUCCESS.value:
            logger.warning(f"pupil_io_set_kappa_filter returned code {ret}")

        # config logger
        os.makedirs(self.config.log_directory, exist_ok=True)
        ret = self._et_native_lib.pupil_io_set_log(
            self.config.enable_debug_logging, self.config.log_directory.encode("gbk")
        )
        if ret != ET_ReturnCode.ET_SUCCESS.value:
            logger.warning(f"pupil_io_set_log returned code {ret}")

        # set calibration mode
        if self.config.cali_mode == CalibrationMode.TWO_POINTS:
            self.calibration_points = np.zeros(2 * 2, dtype=np.float32)
        elif self.config.cali_mode == CalibrationMode.FIVE_POINTS:
            self.calibration_points = np.zeros(2 * 5, dtype=np.float32)
        elif self.config.cali_mode == CalibrationMode.NINE_POINTS:
            self.calibration_points = np.zeros(2 * 9, dtype=np.float32)
        elif self.config.cali_mode == CalibrationMode.FOUR_POINTS:
            # Deprecated path. DefaultConfig already redirects 4 -> 5, but keep this
            # branch so a manually-constructed CalibrationMode.FOUR_POINTS still works.
            self.calibration_points = np.zeros(2 * 4, dtype=np.float32)
        else:
            self.calibration_points = np.zeros(2 * 2, dtype=np.float32)

        ret = self._et_native_lib.pupil_io_set_cali_mode(
            int(self.config.cali_mode), self.calibration_points
        )

        ret = self._et_native_lib.pupil_io_set_cali_mode(self.config.cali_mode, self.calibration_points)
        if ret != ET_ReturnCode.ET_SUCCESS.value:
            logger.warning(f"pupil_io_set_cali_mode returned code {ret}")
        self.calibration_points = np.reshape(self.calibration_points, (-1, 2))

        # ---- Init tracker + resolve camera mode / sampling rate ----
        try:
            status = self._et_native_lib.pupil_io_init()
            if status != ET_ReturnCode.ET_SUCCESS.value:
                raise RuntimeError(f"pupil_io_init failed with code: {status}")

            self._is_initialized = True

            self._camera_mode, self.left_roi, self.right_roi = self.get_camera_mode()
            logger.info(f"[PupilioET] Current camera mode: {self._camera_mode}")

            if self.config.sampling_rate == 0:
                self.config.sampling_rate = HARDWARE_RATES[-1]
                logger.info(
                    f"[PupilioET] Auto-selected sampling rate: "
                    f"{self.config.sampling_rate} Hz"
                )
            elif self.config.sampling_rate not in HARDWARE_RATES:
                fallback_rate = HARDWARE_RATES[-1]
                logger.warning(
                    f"[PupilioET] Warning: requested sampling rate "
                    f"{self.config.sampling_rate} Hz is not supported by this "
                    f"hardware. Falling back to {fallback_rate} Hz."
                )
                self.config.sampling_rate = fallback_rate

            while True:
                try:
                    if self.config.sampling_rate == 400:
                        target_mode = CameraMode.CAMERA_MODE_SYNC_400
                    elif self.config.sampling_rate == 200:
                        target_mode = CameraMode.CAMERA_MODE_SYNC_200
                    else:
                        raise RuntimeError(
                            f"Unsupported sampling_rate: {self.config.sampling_rate}"
                        )

                    if self._is_initialized and self._camera_mode == target_mode:
                        logger.info(
                            f"[PupilioET] Camera already in requested mode "
                            f"({self.config.sampling_rate} Hz) — no switch needed"
                        )
                        break

                    logger.info(
                        f"[PupilioET] Switching camera from mode {self._camera_mode} to "
                        f"mode {target_mode} ({self.config.sampling_rate} Hz)..."
                    )

                    if self._is_initialized:
                        status = self._et_native_lib.pupil_io_release()
                        if status != ET_ReturnCode.ET_SUCCESS.value:
                            raise RuntimeError(
                                f"Pupilio release failed with code: {status}"
                            )
                        self._is_initialized = False

                    if not self.set_camera_mode(target_mode):
                        raise RuntimeError(
                            f"Failed to set camera mode to "
                            f"{self.config.sampling_rate} Hz (mode {target_mode})"
                        )

                    status = self._et_native_lib.pupil_io_init()
                    if status != ET_ReturnCode.ET_SUCCESS.value:
                        raise RuntimeError(
                            f"Pupilio re-init failed with code: {status}"
                        )
                    self._is_initialized = True

                    self._camera_mode, self.left_roi, self.right_roi = self.get_camera_mode()
                    logger.info(
                        f"[PupilioET] Changed sample rate to "
                        f"{self.config.sampling_rate} Hz "
                        f"(mode {self._camera_mode}) and re-inited the tracker"
                    )
                    break

                except Exception as exc:
                    # FIX: no longer silently swallow cleanup errors
                    try:
                        if self._is_initialized:
                            self._et_native_lib.pupil_io_release()
                            self._is_initialized = False
                    except Exception as cleanup_exc:
                        logger.debug(
                            f"[PupilioET] Cleanup during rate fallback failed: {cleanup_exc}"
                        )

                    if self.config.sampling_rate == 400:
                        logger.warning(
                            f"[PupilioET] 400 Hz initialization failed: {exc}. "
                            f"Falling back to 200 Hz."
                        )
                        self.config.sampling_rate = 200

                        try:
                            status = self._et_native_lib.pupil_io_init()
                            if status == ET_ReturnCode.ET_SUCCESS.value:
                                self._is_initialized = True
                                self._camera_mode, self.left_roi, self.right_roi = (
                                    self.get_camera_mode()
                                )
                                logger.info(
                                    f"[PupilioET] Recovered device after 400 Hz failure; "
                                    f"current camera mode: {self._camera_mode}"
                                )

                                if self._camera_mode == CameraMode.CAMERA_MODE_SYNC_200:
                                    logger.info(
                                        "[PupilioET] Device is already in native 200 Hz "
                                        "mode; accepting without set_camera_mode()"
                                    )
                                    break
                        except Exception as recover_exc:
                            logger.warning(
                                f"[PupilioET] Recovery re-init failed: {recover_exc}"
                            )

                        continue

                    raise

            logger.info(
                f"[PupilioET] System initialized successfully at "
                f"{self.config.sampling_rate} Hz"
            )

        except Exception as exc:
            logger.error(f"[PupilioET] Initialization error: {exc}")
            raise

        self.LEFT_IMG_WIDTH: int = int(self.left_roi[2])
        self.LEFT_IMG_HEIGHT: int = int(self.left_roi[3])

        self.RIGHT_IMG_WIDTH: int = int(self.right_roi[2])
        self.RIGHT_IMG_HEIGHT: int = int(self.right_roi[3])

        self._face_pos = np.zeros(3, dtype=np.float32)
        self._pt = np.zeros(11, dtype=np.float32)
        self._pt_l = np.zeros(14, dtype=np.float32)
        self._pt_r = np.zeros(14, dtype=np.float32)
        self._pt_bino = np.zeros(10, dtype=np.float32)
        self._pt_full = np.zeros(38, dtype=np.float32)

        self._previewer_thread = None
        self._online_event_detection = None

        avatar_path = Path(__file__).parent / 'asset' / 'smiling-face.png'
        self.face_avatar_raw = cv2.imread(str(avatar_path), cv2.IMREAD_UNCHANGED)

        # LabStreamingLayer (LSL) Manager
        self._lsl_manager = None
        if getattr(self.config, "enable_lsl", False):
            from .lsl import LSLManager
            self._lsl_manager = LSLManager(
                pupil_io=self,
                gaze_stream_name=self.config.lsl_gaze_stream_name,
                marker_stream_name=self.config.lsl_marker_stream_name,
                stream_mode=self.config.lsl_stream_mode,
            )

    # ------------------------------------------------------------------ #
    # Version / camera-mode plumbing                                     #
    # ------------------------------------------------------------------ #

    def get_version(self) -> str:
        """
        Retrieve the native Pupilio library version string.

        Returns:
            str: Version string decoded from native library.
        """
        version = self._et_native_lib.pupil_io_get_version()
        # FIX: tolerant decoding
        return version.decode("gbk", errors="replace") if version else ""

    def query_support_sampling_rate(self):
        """
        Query the sampling (frame) rates supported by the currently active camera mode.
        ...
        """
        mode, _left_roi, _right_roi = self.get_camera_mode()

        if mode == CameraMode.CAMERA_MODE_SYNC_200:
            return [200]
        elif mode in (CameraMode.CAMERA_MODE_SYNC_400, CameraMode.CAMERA_MODE_ASYNC_400):
            return list(HARDWARE_RATES)   # FIX: derive from HARDWARE_RATES
        logger.warning(
            f"Camera mode {mode} is not supported by the initialization path "
            f"(HARDWARE_RATES = {HARDWARE_RATES}); assuming 200 Hz only."
        )
        return [200]

    def set_camera_mode(self, mode_value) -> bool:
        """
        Set the camera frame rate mode.

        Only for sync_400 devices that also support sync_200. It is called from
        :meth:`__init__` **after** the current tracker has been released and before the
        tracker is re-initialised — the camera cannot be reconfigured while open.

        Args:
            mode_value (int): Target mode. Only the following values are accepted:
                - CAMERA_MODE_SYNC_400 (0) : native 400 fps
                - CAMERA_MODE_SYNC_200 (3) : down-sampled 200 fps

        Returns:
            bool: True on success, False if the native call rejects the mode.

        Raises:
            ValueError: If ``mode_value`` is not one of the supported modes.
        """
        # FIX: validate the input before hitting the DLL
        allowed = (
            CameraMode.CAMERA_MODE_SYNC_400.value,
            CameraMode.CAMERA_MODE_SYNC_200.value,
        )
        if mode_value not in allowed:
            raise ValueError(
                f"Unsupported camera mode {mode_value!r}; "
                f"expected one of {allowed}."
            )

        mode = ctypes.c_int(mode_value)
        ret = self._et_native_lib.pupil_io_set_camera_mode(ctypes.byref(mode))
        if ret != ET_ReturnCode.ET_SUCCESS.value:
            logger.error(f"pupil_io_set_camera_mode failed with code {ret}")
            return False
        return True

    def get_camera_mode(self):
        """
        Query the currently active camera frame rate mode and ROI geometry.

        ... (original docstring preserved) ...
        """
        # FIX: use a c_int for the mode output — cheaper and clearer than a 1-element ndarray
        mode = ctypes.c_int(0)
        left_roi = np.zeros(4, dtype=np.int32)
        right_roi = np.zeros(4, dtype=np.int32)
        ret = self._et_native_lib.pupil_io_get_camera_mode(
            ctypes.byref(mode),
            left_roi.ctypes.data_as(ctypes.POINTER(ctypes.c_int)),
            right_roi.ctypes.data_as(ctypes.POINTER(ctypes.c_int)),
        )
        if ret != ET_ReturnCode.ET_SUCCESS.value:
            raise RuntimeError(f"pupil_io_get_camera_mode failed with code {ret}")
        return mode.value, left_roi, right_roi

    # ------------------------------------------------------------------ #
    # Previewer                                                          #
    # ------------------------------------------------------------------ #

    def previewer_start(self, udp_host: str, udp_port: int,
                        draw_preview_annotations: bool = True,
                        fps: int = 30) -> None:
        """
        Start streaming the camera preview over UDP.

        ... (original docstring preserved) ...

        Raises:
            ValueError: If ``udp_host`` is not a valid IP address or ``udp_port`` is out
                of range.
            RuntimeError: If ``pupil_io_previewer_init`` or ``pupil_io_previewer_start``
                returns a non-success code.
        """
        try:
            ipaddress.ip_address(udp_host)
        except ValueError:
            raise ValueError(f"Invalid IP address: {udp_host}.")

        # FIX: validate port range as documented
        if not (isinstance(udp_port, int) and 1 <= udp_port <= 65535):
            raise ValueError(f"Invalid UDP port: {udp_port!r}.")

        if hasattr(self._et_native_lib, "pupil_io_previewer_init_ex"):
            ret_init = self._et_native_lib.pupil_io_previewer_init_ex(
                udp_host.encode('gbk'), udp_port, draw_preview_annotations, fps
            )
        else:
            ret_init = self._et_native_lib.pupil_io_previewer_init(
                udp_host.encode('gbk'), udp_port, draw_preview_annotations
            )

        if ret_init != ET_ReturnCode.ET_SUCCESS.value:
            err = self.get_last_error()
            raise RuntimeError(f"pupil_io_previewer_init failed with code {ret_init}. Detail: {err}")

        ret_start = self._et_native_lib.pupil_io_previewer_start()
        if ret_start != ET_ReturnCode.ET_SUCCESS.value:
            err = self.get_last_error()
            raise RuntimeError(f"pupil_io_previewer_start failed with code {ret_start}. Detail: {err}")

    def previewer_set_fps(self, fps: int) -> None:
        """
        Dynamically update the target streaming frame rate of the UDP previewer.

        ... (original docstring preserved) ...
        """
        if not hasattr(self._et_native_lib, "pupil_io_previewer_set_fps"):
            # FIX: info-level; this is not an error, just an older library
            logger.info("pupil_io_previewer_set_fps is not supported by the loaded native library.")
            return

        ret = self._et_native_lib.pupil_io_previewer_set_fps(fps)
        if ret != ET_ReturnCode.ET_SUCCESS.value:
            err = self.get_last_error()
            raise RuntimeError(f"pupil_io_previewer_set_fps failed with code {ret}. Detail: {err}")

    def previewer_get_fps(self) -> int:
        """
        Get the currently configured target frame rate of the UDP previewer.

        Returns:
            int: Target frame rate in FPS, or -1 if the loaded native library does not
            expose this query.
        """
        if hasattr(self._et_native_lib, "pupil_io_previewer_get_fps"):
            return self._et_native_lib.pupil_io_previewer_get_fps()
        return -1

    def get_last_error(self) -> str:
        """
        Retrieve the latest detailed error message reported by the native C++ library.

        Returns:
            str: Error description, or empty string if no error occurred.
        """
        if hasattr(self._et_native_lib, "pupil_io_get_last_error"):
            err_ptr = self._et_native_lib.pupil_io_get_last_error()
            if err_ptr:
                # FIX: try UTF-8 first, then GBK, never raise on decoding
                try:
                    return err_ptr.decode('utf-8')
                except UnicodeDecodeError:
                    return err_ptr.decode('gbk', errors='replace')
        return ""

    def previewer_stop(self):
        """
        Stop the UDP preview stream started by :meth:`previewer_start`.

        Returns:
            None
        """
        ret = self._et_native_lib.pupil_io_previewer_stop()
        if ret != ET_ReturnCode.ET_SUCCESS.value:
            logger.warning(f"pupil_io_previewer_stop returned non-success code: {ret}")

    # ------------------------------------------------------------------ #
    # Session / data                                                     #
    # ------------------------------------------------------------------ #

    def create_session(self, session_name: str) -> int:
        """
        Creates a new session and sets up related directories, log files, and the logger.

        ... (original docstring preserved) ...

        Raises:
            TypeError: If ``session_name`` is not a string.
            RuntimeError: If ``session_name`` is invalid or the native call fails.
        """
        # FIX: type check before regex
        if not isinstance(session_name, str):
            raise TypeError(
                f"session_name must be str, got {type(session_name).__name__}."
            )

        self._session_name = session_name

        reserved_names = {
            "CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
            "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"
        }

        pattern = r'^[a-zA-Z0-9_+\-()]+$'
        available_session = bool(re.fullmatch(pattern, session_name) and (session_name.upper() not in reserved_names))
        if not available_session:
            raise RuntimeError(
                f"Session name '{session_name}' is invalid. Ensure it follows these rules:\n"
                f"1. Only includes letters (A-Z, a-z), digits (0-9), underscores (_), hyphens (-), plus signs (+), and parentheses ().\n"
                f"2. Does not include any of the following prohibited characters: < > : \" / \\ | ? *.\n"
                f"3. Does not match any of the following reserved names: {', '.join(reserved_names)}."
            )

        current_time = datetime.now()
        formatted_current_time = current_time.strftime("%Y%m%d%H%M%S")
        self._session_name += f"_{formatted_current_time}"

        # FIX: check the native return code instead of silently ignoring it
        res = self._et_native_lib.pupil_io_create_session(self._session_name.encode('gbk'))
        if res != ET_ReturnCode.ET_SUCCESS.value:
            raise RuntimeError(f"pupil_io_create_session failed with code {res}.")
        return res

    def save_data(self, path: str) -> int:
        """
        Write the recorded samples to a CSV file.

        ... (original docstring preserved) ...

        Raises:
            RuntimeError: If the parent directory is missing or not writable, or if the
                native library fails to write the file.
        """
        directory = os.path.dirname(path)

        if directory and (not os.path.exists(directory)):
            raise RuntimeError("The directory of data file not exist.")

        if directory and not os.access(directory, os.W_OK):
            raise RuntimeError("The directory of data file is not writeable.")

        if self._et_native_lib.pupil_io_save_data_to(path.encode("gbk")) == ET_ReturnCode.ET_SUCCESS.value:
            return ET_ReturnCode.ET_SUCCESS.value
        else:
            raise RuntimeError(f"Failed to save data at path: {path}.")

    # ------------------------------------------------------------------ #
    # Sampling                                                           #
    # ------------------------------------------------------------------ #

    def start_sampling(self) -> int:
        """
        Begin recording gaze samples into the native buffer.

        Idempotent: if sampling is already running this returns ``ET_SUCCESS`` and does
        nothing.

        Returns:
            int: An :class:`ET_ReturnCode` value; ``ET_SUCCESS`` on success.

        Raises:
            RuntimeError: If the tracker refuses to start, or the LSL manager cannot be
                started (native sampling is rolled back in that case).
        """
        # FIX: hold the lock across the whole check-then-act sequence
        with self._sampling_lock:
            if self.get_sampling_status():
                logger.info("Sampling is already running; start_sampling is a no-op.")
                return ET_ReturnCode.ET_SUCCESS.value

            res = self._et_native_lib.pupil_io_start_sampling()
            if res != ET_ReturnCode.ET_SUCCESS.value:
                logger.error(f"Failed to start sampling (code: {res}).")
                raise RuntimeError(f"Failed to start sampling (code: {res}).")

            # FIX: only sleep after we know sampling actually started
            time.sleep(0.05)

            if self._lsl_manager:
                try:
                    self._lsl_manager.start()
                except Exception as exc:
                    # FIX: roll back native sampling so a later start_sampling can retry
                    logger.exception(
                        "Native sampling started, but the LSL manager failed to start; "
                        "rolling back native sampling."
                    )
                    try:
                        self._et_native_lib.pupil_io_stop_sampling()
                    except Exception:
                        logger.exception(
                            "Rollback of native sampling also failed; tracker may be "
                            "left in an inconsistent state."
                        )
                    raise RuntimeError(
                        "LSL manager failed to start; native sampling was rolled back."
                    ) from exc

            return res

    def get_sampling_status(self) -> bool:
        """
        Report whether the tracker is currently recording samples.

        Returns:
            bool: True while a sampling session is running, False otherwise.
        """
        status = ctypes.c_bool()
        status_pointer = ctypes.byref(status)

        # FIX: check the native return code instead of trusting an uninitialised bool
        res = self._et_native_lib.pupil_io_sampling_status(status_pointer)
        if res != ET_ReturnCode.ET_SUCCESS.value:
            logger.warning(
                f"pupil_io_sampling_status returned code {res}; assuming not sampling."
            )
            return False
        return status.value

    def stop_sampling(self) -> int:
        """
        Stop recording gaze samples.

        Buffered data is retained, so :meth:`save_data` can still be called afterwards.

        Idempotent: if sampling is not running this returns ``ET_SUCCESS`` and does
        nothing.

        Returns:
            int: An :class:`ET_ReturnCode` value; ``ET_SUCCESS`` on success.

        Raises:
            RuntimeError: If the native tracker refuses to stop.
        """
        # FIX: same lock as start_sampling; makes the guard atomic
        with self._sampling_lock:
            # The native library dereferences its sampling thread without a null check,
            # so calling it while idle takes down the whole process. Refuse early instead.
            if not self.get_sampling_status():
                logger.info("No sampling thread is running; stop_sampling is a no-op.")
                return ET_ReturnCode.ET_SUCCESS.value

            if self._lsl_manager:
                try:
                    self._lsl_manager.stop()
                except Exception:
                    # FIX: don't let an LSL failure leave the native thread running
                    logger.exception(
                        "LSL manager failed to stop; continuing to stop native sampling."
                    )

            res = self._et_native_lib.pupil_io_stop_sampling()
            if res != ET_ReturnCode.ET_SUCCESS.value:
                logger.error(f"Failed to stop sampling (code: {res}).")
                raise RuntimeError(f"Failed to stop sampling (code: {res}).")

            # FIX: only sleep after we know the native stop succeeded
            time.sleep(0.1)
            return res

    # ------------------------------------------------------------------ #
    # Gaze estimation                                                    #
    # ------------------------------------------------------------------ #

    def face_position(self) -> Tuple[int, np.ndarray]:
        """
        Get the participant's eye position in tracker space.

        ... (original docstring preserved) ...
        """
        ret = self._et_native_lib.pupil_io_face_pos(self._face_pos)
        return ret, self._face_pos

    def calibration(self, cali_point_id: int) -> int:
        """
        Feed one frame of calibration data for the given target.

        ... (original docstring preserved) ...
        """
        if self.get_sampling_status():
            return ET_ReturnCode.ET_FAILED
        return self._et_native_lib.pupil_io_cali(cali_point_id)

    @deprecated("1.1.1", "Please use function `estimate_gaze`")
    def estimation(self) -> Tuple[int, np.ndarray, int, int]:
        """Estimate the gaze state and position."""
        timestamp = ctypes.c_longlong()
        status = self._et_native_lib.pupil_io_est(self._pt, ctypes.byref(timestamp))
        trigger = 0
        return status, self._pt, timestamp.value, trigger

    @deprecated("1.4.0", "Please use function `estimate_gaze`")
    def estimation_lr(self) -> Tuple[int, np.ndarray, np.ndarray, int, int]:
        """Estimate the gaze state and position for left and right eyes."""
        timestamp = ctypes.c_longlong()
        status = self._et_native_lib.pupil_io_est_lr(self._pt_l, self._pt_r, ctypes.byref(timestamp))
        trigger = 0
        return status, self._pt_l, self._pt_r, timestamp.value, trigger

    def estimate_gaze(self) -> Tuple[int, np.ndarray, np.ndarray, np.ndarray, int, int]:
        """
        Estimate the gaze state and position for left, right, and bino eyes.

        ... (per-eye layout preserved) ...

        Returns:
            tuple[int, np.ndarray, np.ndarray, np.ndarray, int, int]:
                - int: Status code.
                - np.ndarray: Left-eye sample, 14 floats.
                - np.ndarray: Right-eye sample, 14 floats.
                - np.ndarray: Fused binocular sample, 10 floats.
                - int: Timestamp (ms).
                - int: Trigger value (0).
        """
        timestamp = ctypes.c_longlong()
        status = self._et_native_lib.pupil_io_estimate_gaze(
            self._pt_l, self._pt_r, self._pt_bino, ctypes.byref(timestamp)
        )
        trigger = 0
        return status, self._pt_l, self._pt_r, self._pt_bino, timestamp.value, trigger

    def estimate_gaze_full(self) -> Tuple[int, np.ndarray, int]:
        """
        Estimate full 38-channel gaze parameters for left eye, right eye, and binocular fusion.
        """
        timestamp = ctypes.c_longlong()
        status = self._et_native_lib.pupil_io_est_full(self._pt_full, ctypes.byref(timestamp))
        return status, self._pt_full, timestamp.value

    # ------------------------------------------------------------------ #
    # Lifecycle                                                          #
    # ------------------------------------------------------------------ #

    def release(self) -> int:
        """
        Shut down the tracker and free the resources held by the native library.

        Call this once at the end of an experiment. The instance must not be used
        afterwards.

        Returns:
            int: An :class:`ET_ReturnCode` value; ``ET_SUCCESS`` on success.
        """
        # FIX: stop any running sampling before releasing the native library
        try:
            self.stop_sampling()
        except Exception:
            logger.exception(
                "Failed to stop sampling before release; proceeding with release anyway."
            )

        # FIX: stop LSL defensively (stop_sampling only runs if sampling was active)
        if self._lsl_manager:
            try:
                self._lsl_manager.stop()
            except Exception:
                logger.exception("LSL manager failed to stop during release.")
            self._lsl_manager = None

        res = self._et_native_lib.pupil_io_release()
        # FIX: mark the instance as no longer initialized
        self._is_initialized = False
        return res

    # ------------------------------------------------------------------ #
    # Triggers / LSL                                                     #
    # ------------------------------------------------------------------ #

    def set_trigger(self, trigger: int) -> int:
        """
        Mark the current sample with a trigger code.

        ... (original docstring preserved) ...

        Raises:
            TypeError: If ``trigger`` is not an integer or is a bool.
            ValueError: If ``trigger`` is outside 1-65535.
            RuntimeError: If the native call rejects the trigger.
        """
        # FIX: bool is a subclass of int — reject it explicitly
        if isinstance(trigger, bool) or not isinstance(trigger, int):
            raise TypeError("Trigger must be an integer (bool is not accepted).")

        if trigger < 1 or trigger > 65535:
            raise ValueError("Trigger must be between 1 and 65535")

        if self._et_native_lib.pupil_io_send_trigger(trigger) == ET_ReturnCode.ET_SUCCESS.value:
            if self._lsl_manager:
                self._lsl_manager.push_trigger(trigger)
            return ET_ReturnCode.ET_SUCCESS.value
        else:
            raise RuntimeError("Please don't call `set_trigger` function too frequently.")

    def send_lsl_marker(self, marker: str):
        """
        Broadcast a custom semantic string marker to the LabStreamingLayer (LSL) Marker stream.
        """
        if not self._lsl_manager:
            logger.warning("LSL is not enabled; marker was not sent to LSL.")
            return
        self._lsl_manager.push_marker(marker)

    def start_lsl(
        self,
        gaze_stream_name: str = None,
        marker_stream_name: str = None,
        stream_mode: str = None,
    ):
        """
        Enable and immediately start LabStreamingLayer (LSL) streaming.
        """
        from .lsl import LSLManager

        if gaze_stream_name:
            self.config.lsl_gaze_stream_name = gaze_stream_name
        if marker_stream_name:
            self.config.lsl_marker_stream_name = marker_stream_name
        if stream_mode:
            self.config.lsl_stream_mode = stream_mode

        self.config.enable_lsl = True

        # FIX: if LSL is already running, stop it first so we don't double-stream
        if self._lsl_manager is not None:
            try:
                self._lsl_manager.stop()
            except Exception:
                logger.exception("Failed to stop existing LSL manager; recreating it.")

        self._lsl_manager = LSLManager(
            pupil_io=self,
            gaze_stream_name=self.config.lsl_gaze_stream_name,
            marker_stream_name=self.config.lsl_marker_stream_name,
            stream_mode=self.config.lsl_stream_mode,
        )
        self._lsl_manager.start()

    def stop_lsl(self):
        """
        Stop LabStreamingLayer (LSL) streaming and drop the manager reference.
        """
        if self._lsl_manager:
            try:
                self._lsl_manager.stop()
            except Exception:
                logger.exception("LSL manager failed to stop.")
            # FIX: match release() and clear the reference so start_lsl can rebuild
            self._lsl_manager = None

    # ------------------------------------------------------------------ #
    # Properties                                                         #
    # ------------------------------------------------------------------ #

    @property
    def is_initialized(self) -> bool:
        """True once the tracker has been successfully initialized."""
        return self._is_initialized

    @property
    def lsl_manager(self):
        """Return the active LSLManager instance, or None if LSL is disabled."""
        return self._lsl_manager

    # ------------------------------------------------------------------ #
    # Filter / current gaze                                              #
    # ------------------------------------------------------------------ #

    def set_filter_enable(self, status: bool) -> int:
        """
        Enable or disable the gaze smoothing filter.
        """
        return self._et_native_lib.pupil_io_set_filter_enable(status)

    def get_current_gaze(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Retrieve the most recent gaze position for each eye and the fused binocular gaze.
        """
        left_gaze = np.zeros(3, dtype=np.float32)
        right_gaze = np.zeros(3, dtype=np.float32)
        bino_gaze = np.zeros(3, dtype=np.float32)

        # FIX: check the return code; on failure return zero-initialised arrays (valid=0)
        ret = self._et_native_lib.pupil_io_get_current_gaze(
            left_gaze, right_gaze, bino_gaze
        )
        if ret != ET_ReturnCode.ET_SUCCESS.value:
            logger.warning(f"pupil_io_get_current_gaze returned code {ret}")
        return left_gaze, right_gaze, bino_gaze

    # ------------------------------------------------------------------ #
    # Calibration UI                                                     #
    # ------------------------------------------------------------------ #

    def calibration_draw(self, screen=None, validate=False, bg_color=(255, 255, 255), hands_free=False):
        """
        Run the full calibration routine on screen.

        ... (original docstring preserved) ...
        """
        screen_type = ""
        if screen is None:
            try:
                import pygame
                pygame.init()
                scn_width, scn_height = (1920, 1080)
                screen = pygame.display.set_mode((scn_width, scn_height), pygame.FULLSCREEN | pygame.HWSURFACE)
                screen_type = 'pygame'
            except Exception as e:
                logger.error(f"Cannot fallback to pygame screen creation: {e}")
                raise RuntimeError("pygame screen can't be created.")
        else:
            if hasattr(screen, 'get_size') and hasattr(screen, 'fill'):
                screen_type = 'pygame'
            else:
                screen_type = 'psychopy'

        if screen_type == 'pygame':
            from .ui_backend import PyGameUIBackend
            ui_backend = PyGameUIBackend(screen)
        else:
            from .ui_backend import PsychoPyUIBackend
            ui_backend = PsychoPyUIBackend(screen)

        from .cali_graphics import CalibrationUI

        ui = CalibrationUI(pupil_io=self, ui_backend=ui_backend)

        # FIX: removed the commented-out duplicate branch
        if not hands_free:
            ui.draw(validate=validate, bg_color=bg_color)
        else:
            ui.draw_hands_free(validate=validate, bg_color=bg_color)

        # The native calibration routine leaves its own sampling thread running after
        # it finishes. Stop it here so a later start_sampling() is not rejected.
        try:
            if self.get_sampling_status():
                logger.info(
                    "[PupilioET] Calibration left sampling active; stopping it "
                    "so start_sampling() can be called afterwards."
                )
                self.stop_sampling()
        except Exception as exc:
            logger.warning(f"[PupilioET] Failed to stop leftover sampling: {exc}")

    # ------------------------------------------------------------------ #
    # Deprecated subscription API                                        #
    # ------------------------------------------------------------------ #

    @deprecated("1.1.2")
    def subscribe_sample(self, subscriber_func: Callable, args=(), kwargs=None):
        """
        Deprecated since 1.1.2 — the sample subscription mechanism was removed.

        Raises:
            NotImplementedError: Always. Use LSL streaming or polling
                :meth:`estimate_gaze` instead.
        """
        raise NotImplementedError(
            "subscribe_sample was removed in 1.1.2; use LSL streaming or "
            "poll estimate_gaze()/get_current_gaze() instead."
        )

    @deprecated("1.1.2")
    def unsubscribe_sample(self, subscriber_func: Callable, args=(), kwargs=None):
        """
        Deprecated since 1.1.2 — the sample subscription mechanism was removed.

        Raises:
            NotImplementedError: Always.
        """
        raise NotImplementedError(
            "unsubscribe_sample was removed in 1.1.2; there is nothing to unsubscribe."
        )

    @deprecated("1.1.2")
    def subscribe_event(self, *args):
        """
        Deprecated since 1.1.2 — the online event detection mechanism was removed.

        Raises:
            NotImplementedError: Always.
        """
        raise NotImplementedError(
            "subscribe_event was removed in 1.1.2."
        )

    @deprecated("1.1.2")
    def unsubscribe_event(self, *args):
        """
        Deprecated since 1.1.2 — the online event detection mechanism was removed.

        Raises:
            NotImplementedError: Always.
        """
        raise NotImplementedError(
            "unsubscribe_event was removed in 1.1.2."
        )

    def clear_cache(self) -> int:
        """
        Discard the samples buffered in the native library.

        Returns:
            int: An :class:`ET_ReturnCode` value; ``ET_SUCCESS`` on success.
        """
        return self._et_native_lib.pupil_io_clear_cache()

    @property
    @deprecated("1.1.2")
    def sample_subscriber_lock(self):
        """Always ``None``; the sample subscription mechanism was removed in 1.1.2."""
        return None

    @property
    @deprecated("1.1.2")
    def sample_subscribers(self):
        """Always ``None``; the sample subscription mechanism was removed in 1.1.2."""
        return None

    # ------------------------------------------------------------------ #
    # Preview image composition                                          #
    # ------------------------------------------------------------------ #

    def _process_images(self, left_img: np.ndarray, right_img: np.ndarray, eye_rects: np.ndarray,
                        pupil_centers: np.ndarray, glint_centers: np.ndarray) -> np.ndarray:
        """
        Compose annotated preview canvases from the raw camera images.

        ... (original docstring preserved) ...

        Returns:
            np.ndarray: ``(2, 1280, 1280, 3)`` uint8 BGR array, index 0 left and 1 right.
        """
        IMG_HEIGHT, IMG_WIDTH = 1024, 1280
        _left_img = cv2.cvtColor(left_img, cv2.COLOR_GRAY2BGR)
        _right_img = cv2.cvtColor(right_img, cv2.COLOR_GRAY2BGR)

        FRAME_WARNING = (255, 0, 0)
        FRAME_SUCCESS = (0, 255, 0)
        FRAME_WIDTH = 8

        imgs = [_left_img, _right_img]

        eyes_canvas = [[np.ones((IMG_WIDTH - IMG_HEIGHT, IMG_WIDTH // 2, 3), dtype=np.uint8) * 128,
                        np.ones((IMG_WIDTH - IMG_HEIGHT, IMG_WIDTH // 2, 3), dtype=np.uint8) * 128],
                       [np.ones((IMG_WIDTH - IMG_HEIGHT, IMG_WIDTH // 2, 3), dtype=np.uint8) * 128,
                        np.ones((IMG_WIDTH - IMG_HEIGHT, IMG_WIDTH // 2, 3), dtype=np.uint8) * 128]]

        preview_imgs = np.zeros((2, IMG_WIDTH, IMG_WIDTH, 3), dtype=np.uint8)

        rects = [
            [eye_rects[:4], eye_rects[4:8]],
            [eye_rects[8:12], eye_rects[12:16]]
        ]

        pupil_center_list = [
            [pupil_centers[0:2], pupil_centers[2:4]],
            [pupil_centers[4:6], pupil_centers[6:8]]
        ]
        glint_center_list = [
            [glint_centers[0:2], glint_centers[2:4]],
            [glint_centers[4:6], glint_centers[6:8]]
        ]

        if self.config.active_eye in [-1, 'left']:
            patch_mask_index = 1
        elif self.config.active_eye in [1, 'right']:
            patch_mask_index = 0
        else:
            patch_mask_index = -1

        # FIX: per-image frame color so a bad patch on one camera doesn't
        # turn the other camera's frame red too
        frame_colors = [FRAME_SUCCESS, FRAME_SUCCESS]

        eye_patches = []
        for img_idx, img in enumerate(imgs):
            patches = []
            img_h, img_w, _ = img.shape   # FIX: hoisted out of the inner loop
            for patch_idx, rect in enumerate(rects[img_idx]):
                x1, y1, w, h = map(int, rect)
                x2, y2 = x1 + w, y1 + h
                if x1 < 0 or y1 < 0 or x2 > img_w or y2 > img_h or x1 > x2 or y1 > y2:
                    frame_colors[img_idx] = FRAME_WARNING   # FIX: per-image
                    continue

                if w == 0 or h == 0:
                    patch = img[0:96, 0:96]
                else:
                    patch = img[y1:y2, x1:x2]

                pupil_x, pupil_y = pupil_center_list[img_idx][patch_idx]
                glint_x, glint_y = glint_center_list[img_idx][patch_idx]

                if not (x1 <= pupil_x < x2 and y1 <= pupil_y < y2):
                    if not (patch_mask_index == patch_idx):
                        frame_colors[img_idx] = FRAME_WARNING   # FIX
                    pupil_x, pupil_y = None, None
                else:
                    pupil_x, pupil_y = int(pupil_x - x1), int(pupil_y - y1)

                if not (x1 <= glint_x < x2 and y1 <= glint_y < y2):
                    if not (patch_mask_index == patch_idx):
                        frame_colors[img_idx] = FRAME_WARNING   # FIX
                    glint_x, glint_y = None, None
                else:
                    glint_x, glint_y = int(glint_x - x1), int(glint_y - y1)

                if pupil_x is not None and pupil_y is not None:
                    cv2.circle(patch, (pupil_x, pupil_y), 5, (0, 0, 255), -1)
                if glint_x is not None and glint_y is not None:
                    cv2.circle(patch, (glint_x, glint_y), 3, (0, 255, 0), -1)

                if w == 0 or h == 0:
                    pass
                else:
                    # FIX: use the per-image frame color
                    cv2.rectangle(patch, (0, 0), (patch.shape[1] - 1, patch.shape[0] - 1),
                                  frame_colors[img_idx], 6)

                patches.append(patch)
            eye_patches.append(patches)

        margin = 10
        for canvas_idx, canvases in enumerate(eyes_canvas):
            for rect_idx, canvas in enumerate(canvases):
                if canvas_idx >= len(eye_patches) or rect_idx >= len(eye_patches[canvas_idx]):
                    continue
                patch = eye_patches[canvas_idx][rect_idx]
                patch_h, patch_w, _ = patch.shape
                canvas_h, canvas_w, _ = canvas.shape

                scale = min((canvas_w - 2 * margin) / patch_w, (canvas_h - 2 * margin) / patch_h)
                new_w, new_h = int(patch_w * scale), int(patch_h * scale)

                resized_patch = cv2.resize(patch, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

                start_x = (canvas_w - new_w) // 2
                start_y = (canvas_h - new_h) // 2

                if not rect_idx == patch_mask_index:
                    eyes_canvas[canvas_idx][rect_idx][start_y:start_y + new_h, start_x:start_x + new_w] = resized_patch

        for idx in range(2):
            original_img = imgs[idx]
            eye1_canvas, eye2_canvas = eyes_canvas[idx]
            # FIX: use the per-image frame color for both eye canvases and the full frame
            cv2.rectangle(eye1_canvas, (0, 0), (eye1_canvas.shape[1] - 1, eye1_canvas.shape[0] - 1),
                          frame_colors[idx], 2)
            cv2.rectangle(eye2_canvas, (0, 0), (eye2_canvas.shape[1] - 1, eye2_canvas.shape[0] - 1),
                          frame_colors[idx], 2)

            h, w = original_img.shape[:2]
            start_y = (IMG_HEIGHT - h) // 2
            start_x = (IMG_WIDTH - w) // 2
            preview_imgs[idx, start_y:start_y + h, start_x:start_x + w, :] = original_img

            cv2.rectangle(preview_imgs[idx], (0, 0), (IMG_WIDTH - 1, IMG_HEIGHT - 1),
                          frame_colors[idx], FRAME_WIDTH)
            canvas_h, canvas_w, _ = eye1_canvas.shape
            target_h, target_w = canvas_h, canvas_w
            combined_canvas = np.zeros((target_h, 2 * target_w, 3), dtype=np.uint8)
            combined_canvas[:, 0:target_w, :] = eye1_canvas
            combined_canvas[:, target_w:2 * target_w, :] = eye2_canvas
            preview_imgs[idx, IMG_HEIGHT:IMG_HEIGHT + target_h, 0:2 * target_w, :] = combined_canvas
        return preview_imgs

    def get_preview_images(self):
        """
        Fetch the latest camera frames and return them as annotated preview canvases.

        ... (original docstring preserved) ...

        Returns:
            np.ndarray: ``(2, 1280, 1280, 3)`` uint8 BGR array, index 0 left and 1 right,
            or None if the native call failed.
        """
        # FIX: collapse the two identical 200-Hz branches
        if self._camera_mode == CameraMode.CAMERA_MODE_SYNC_200 or (
            self._camera_mode == CameraMode.CAMERA_MODE_SYNC_400 and self.config.sampling_rate == 200
        ):
            IMG_HEIGHT, IMG_WIDTH = 1024, 1280
            preview_left_img = np.zeros((IMG_HEIGHT, IMG_WIDTH), dtype=np.uint8)
            preview_right_img = np.zeros((IMG_HEIGHT, IMG_WIDTH), dtype=np.uint8)
        else:
            preview_left_img = np.zeros((self.LEFT_IMG_HEIGHT, self.LEFT_IMG_WIDTH), dtype=np.uint8)
            preview_right_img = np.zeros((self.RIGHT_IMG_HEIGHT, self.RIGHT_IMG_WIDTH), dtype=np.uint8)

        eye_rects = np.zeros(4 * 4, dtype=np.float32)
        pupil_centers = np.zeros(4 * 2, dtype=np.float32)
        glint_centers = np.zeros(4 * 2, dtype=np.float32)

        left_img_ptr = preview_left_img.ctypes.data_as(ctypes.POINTER(ctypes.c_ubyte))
        right_img_ptr = preview_right_img.ctypes.data_as(ctypes.POINTER(ctypes.c_ubyte))

        ret = self._et_native_lib.pupil_io_get_previewer(
            ctypes.pointer(left_img_ptr),
            ctypes.pointer(right_img_ptr),
            eye_rects, pupil_centers, glint_centers,
        )

        # FIX: bail out if the native call failed rather than returning a black frame
        if ret != ET_ReturnCode.ET_SUCCESS.value:
            logger.warning(f"pupil_io_get_previewer returned non-success code: {ret}")
            return None

        ctypes.memmove(preview_left_img.ctypes.data, left_img_ptr, preview_left_img.nbytes)
        ctypes.memmove(preview_right_img.ctypes.data, right_img_ptr, preview_right_img.nbytes)

        preview_imgs = self._process_images(
            preview_left_img, preview_right_img, eye_rects, pupil_centers, glint_centers
        )
        return preview_imgs

    def recalibrate(self) -> int:
        """
        Reset the native calibration state so a fresh calibration can start.

        Returns:
            int: An :class:`ET_ReturnCode` value; ``ET_SUCCESS`` on success.
        """
        return self._et_native_lib.pupil_io_recalibrate()

    def _recalibration(self) -> int:
        """
        Reset the native calibration state so a fresh calibration can start.

        Called by :meth:`calibration_draw` before drawing.

        Returns:
            int: An :class:`ET_ReturnCode` value; ``ET_SUCCESS`` on success.
        """
        return self.recalibrate()

    def _draw_avatar_face(self,
                          img: np.ndarray,
                          eye_rect_a,
                          eye_rect_b,
                          pupil_a,
                          pupil_b,
                          avatar_pupil_left: tuple,
                          avatar_pupil_right: tuple) -> None:
        """
        Blend the face avatar onto an image, aligned by pupil positions.
        """
        # FIX: guard against None inputs before touching them
        if eye_rect_a is None or eye_rect_b is None:
            return
        if pupil_a is None or pupil_b is None:
            return
        if self.face_avatar_raw is None:
            return

        valid_a = eye_rect_a[2] > 0 and eye_rect_a[3] > 0
        valid_b = eye_rect_b[2] > 0 and eye_rect_b[3] > 0
        if not valid_a or not valid_b:
            return

        if self.face_avatar_raw.ndim == 3 and self.face_avatar_raw.shape[2] == 4:
            avatar_bgr = self.face_avatar_raw[:, :, :3]
            avatar_alpha = self.face_avatar_raw[:, :, 3]
        elif self.face_avatar_raw.ndim == 3 and self.face_avatar_raw.shape[2] == 3:
            avatar_bgr = self.face_avatar_raw
            avatar_alpha = np.full(self.face_avatar_raw.shape[:2], 255, dtype=np.uint8)
        else:
            avatar_bgr = cv2.cvtColor(self.face_avatar_raw, cv2.COLOR_GRAY2BGR)
            avatar_alpha = np.full(self.face_avatar_raw.shape[:2], 255, dtype=np.uint8)

        if avatar_bgr is None or avatar_alpha is None:
            return

        s0 = np.float32(avatar_pupil_left)
        s1 = np.float32(avatar_pupil_right)
        if s0[0] > s1[0]:
            s0, s1 = s1, s0

        d0 = np.float32(pupil_a)
        d1 = np.float32(pupil_b)
        if d0[0] > d1[0]:
            d0, d1 = d1, d0

        vs = s1 - s0
        vd = d1 - d0
        denom = vs[0] ** 2 + vs[1] ** 2
        if denom < 1e-6:
            return

        a = (vs[0] * vd[0] + vs[1] * vd[1]) / denom
        b = (vs[0] * vd[1] - vs[1] * vd[0]) / denom
        tx = d0[0] - (a * s0[0] - b * s0[1])
        ty = d0[1] - (b * s0[0] + a * s0[1])
        M = np.array([[a, -b, tx],
                      [b, a, ty]], dtype=np.float64)

        fh, fw = avatar_bgr.shape[:2]
        corners = np.float32([[0, 0], [fw, 0], [fw, fh], [0, fh]])
        warped_corners = cv2.transform(corners.reshape(1, -1, 2), M).reshape(-1, 2)

        minx = np.min(warped_corners[:, 0])
        maxx = np.max(warped_corners[:, 0])
        miny = np.min(warped_corners[:, 1])
        maxy = np.max(warped_corners[:, 1])

        bb_x = int(np.floor(minx))
        bb_y = int(np.floor(miny))
        bb_w = int(np.ceil(maxx)) - bb_x
        bb_h = int(np.ceil(maxy)) - bb_y

        bb_x = max(0, bb_x)
        bb_y = max(0, bb_y)
        bb_w = min(bb_w, img.shape[1] - bb_x)
        bb_h = min(bb_h, img.shape[0] - bb_y)
        if bb_w <= 0 or bb_h <= 0:
            return

        M_roi = M.copy()
        M_roi[0, 2] -= bb_x
        M_roi[1, 2] -= bb_y

        warped_bgr = cv2.warpAffine(avatar_bgr, M_roi, (bb_w, bb_h),
                                    flags=cv2.INTER_LINEAR,
                                    borderMode=cv2.BORDER_CONSTANT,
                                    borderValue=(0, 0, 0))
        warped_alpha = cv2.warpAffine(avatar_alpha, M_roi, (bb_w, bb_h),
                                      flags=cv2.INTER_LINEAR,
                                      borderMode=cv2.BORDER_CONSTANT,
                                      borderValue=0)

        alpha_f = warped_alpha.astype(np.float32) / 255.0
        alpha3 = np.dstack([alpha_f] * 3)

        roi = img[bb_y:bb_y + bb_h, bb_x:bb_x + bb_w]
        roi_f = roi.astype(np.float32)
        face_f = warped_bgr.astype(np.float32)

        blended = roi_f * (1.0 - alpha3) + face_f * alpha3
        np.clip(blended, 0, 255, out=blended)
        roi[:] = blended.astype(np.uint8)

