# _*_ coding: utf-8 _*_
# Copyright (c) 2024, Hangzhou Deep Gaze Sci & Tech Ltd
# All Rights Reserved
#
# For use by  Hangzhou Deep Gaze Sci & Tech Ltd licencees only.
# Redistribution and use in source and binary forms, with or without
# modification, are NOT permitted.
#
# Redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in
# the documentation and/or other materials provided with the distribution.
#
# Neither name of  Hangzhou Deep Gaze Sci & Tech Ltd nor the name of
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
from __future__ import annotations

import ctypes
import ipaddress
import logging
import os
import platform
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Tuple

import cv2
import numpy as np

from .annotation import deprecated
from .default_config import DefaultConfig
from .misc import ET_ReturnCode, CalibrationMode


# Author: GC Zhu
# Email: zhugc2016@gmail.com


class Pupilio:
    """Class for interacting with the eye tracker dynamic link library (DLL).
        A pythonic wrapper for Pupilio library."""

    def __init__(self, config=None):
        """
        Initialize the Pupilio class.
        Load the appropriate DLL based on the platform (Windows or other).
        Set return types and argument types for DLL functions.
        Initialize various attributes and start the sampling thread.
        """

        """
        usage 1:
        config = DefaultConfig()
        config.look_ahead = 2
        pi = Pupilio(config=config)

        usage 2:
        pi = Pupilio()
        """

        if config is None:
            self.config = DefaultConfig()
        else:
            self.config = config

        # Determine the platform and load the appropriate DLL
        if platform.system().lower() == 'windows':
            _current_dir = os.path.abspath(os.path.dirname(__file__))
            _lib_dir = os.path.join(_current_dir, "lib")
            os.add_dll_directory(_lib_dir)
            os.environ['PATH'] = os.environ['PATH'] + ';' + _lib_dir
            # dll
            if self.config.simulation_mode:
                _dll_path = os.path.join(_lib_dir, 'DummyPupilioET.dll')
            else:
                _dll_path = os.path.join(_lib_dir, 'PupilioET.dll')
            self._et_native_lib = ctypes.CDLL(_dll_path, winmode=0)

        else:
            logging.warning("Not supported platform: %s" % platform.system())

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

        # Set argument types
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
            ctypes.POINTER(ctypes.POINTER(ctypes.c_ubyte)),  # img_1
            ctypes.POINTER(ctypes.POINTER(ctypes.c_ubyte)),  # img_2
            np.ctypeslib.ndpointer(dtype=np.float32, ndim=1, flags='C_CONTIGUOUS'),
            np.ctypeslib.ndpointer(dtype=np.float32, ndim=1, flags='C_CONTIGUOUS'),
            np.ctypeslib.ndpointer(dtype=np.float32, ndim=1, flags='C_CONTIGUOUS')
        ]
        self._et_native_lib.pupil_io_previewer_init.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_bool]
        self._et_native_lib.pupil_io_send_trigger.argtypes = [ctypes.c_int]
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
            ctypes.POINTER(ctypes.c_int),  # int* mode
            ctypes.POINTER(ctypes.c_int),  # int* left_roi（指向4个int的数组）
            ctypes.POINTER(ctypes.c_int)  # int* right_roi（同上）
        ]

        self._et_native_lib.pupil_io_est_full.restype = ctypes.c_int
        self._et_native_lib.pupil_io_est_full.argtypes = [
            ctypes.POINTER(ctypes.c_float),  # float* pt
            ctypes.POINTER(ctypes.c_longlong)  # long long* timestamp
        ]

        # ---------- 绑定 pupil_io_set_camera_mode ----------
        # 原型: PupilioReturn pupil_io_set_camera_mode(int* mode)
        self._et_native_lib.pupil_io_set_camera_mode.restype = ctypes.c_int
        self._et_native_lib.pupil_io_set_camera_mode.argtypes = [
            ctypes.POINTER(ctypes.c_int)  # int* mode
        ]

        version = self._et_native_lib.pupil_io_get_version()
        print("Native Pupilio Version:", version.decode("gbk"))
        # set tracking eye
        self._et_native_lib.pupil_io_set_eye_mode(self.config.active_eye.value)

        # set filter parameter: look ahead
        if not (isinstance(self.config.look_ahead, int) and (0 < self.config.look_ahead <= 4)):
            raise ValueError("Parameter `look_ahead` must be between 0 and 4 and integer")

        self._et_native_lib.pupil_io_set_look_ahead(self.config.look_ahead)
        # set enable kappa verify
        self._et_native_lib.pupil_io_set_kappa_filter(self.config.enable_kappa_verification)
        # config logger
        os.makedirs(self.config.log_directory, exist_ok=True)
        self._et_native_lib.pupil_io_set_log(self.config.enable_debug_logging, self.config.log_directory.encode("gbk"))

        # set calibration mode
        if self.config.cali_mode == CalibrationMode.TWO_POINTS:
            self.calibration_points = np.zeros(2 * 2, dtype=np.float32)
        elif self.config.cali_mode == CalibrationMode.FIVE_POINTS:
            self.calibration_points = np.zeros(2 * 5, dtype=np.float32)
        elif self.config.cali_mode == CalibrationMode.FOUR_POINTS:
            self.calibration_points = np.zeros(2 * 4, dtype=np.float32)
        else:
            self.calibration_points = np.zeros(2 * 2, dtype=np.float32)

        self._et_native_lib.pupil_io_set_cali_mode(self.config.cali_mode, self.calibration_points)
        self.calibration_points = np.reshape(self.calibration_points, (-1, 2))

        support_sampling_rate = self.query_support_samping_rate()
        if not self.config.sampling_rate:
            self.config.sampling_rate = support_sampling_rate[-1]
        else:
            if self.config.sampling_rate not in support_sampling_rate:
                raise Exception("Do not support this sampling rate: %s" % self.config.sampling_rate)

        if self.config.sampling_rate == 200:
            self.set_camera_mode(3)
        else:
            self.set_camera_mode(0)

        # Initialize Pupilio, raise an exception if initialization fails
        if self._et_native_lib.pupil_io_init() != ET_ReturnCode.ET_SUCCESS.value:
            raise Exception("Pupilio init failed, please contact the developer!")

        mode, left_roi, right_roi = self.get_camera_mode()

        self.max_sampling_rate = 200
        if mode == 1:
            self.max_sampling_rate = 800
        elif mode == 2:
            self.max_sampling_rate = 1000
        elif mode == 3:
            self.max_sampling_rate = 200
        elif mode == 4 or mode[0] == 0:
            self.max_sampling_rate = 400

        self.LEFT_IMG_WIDTH: int = int(left_roi[2])
        self.LEFT_IMG_HEIGHT: int = int(left_roi[3])

        self.RIGHT_IMG_WIDTH: int = int(right_roi[2])
        self.RIGHT_IMG_HEIGHT: int = int(right_roi[3])

        self._face_pos = np.zeros(3, dtype=np.float32)
        self._pt = np.zeros(11, dtype=np.float32)
        self._pt_l = np.zeros(14, dtype=np.float32)
        self._pt_r = np.zeros(14, dtype=np.float32)
        self._pt_bino = np.zeros(10, dtype=np.float32)

        self._previewer_thread = None
        self._online_event_detection = None

        # 用PathLib吧，在本文件对应的./asset/smiling-face.png
        avatar_path = Path(__file__).parent / 'asset' / 'smiling-face.png'
        self.face_avatar_raw = cv2.imread(str(avatar_path), cv2.IMREAD_UNCHANGED)

    def query_support_samping_rate(self):
        """
        Query the list of supported sampling (frame) rates for the current camera mode.

        This method retrieves the active camera mode via `get_camera_mode()` and returns
        a list of available sampling rates (in Hz) that are supported under that mode.
        The supported rates vary depending on the hardware capabilities and the current
        configuration.

        Returns:
            list[int]: A list of integer sampling rates (e.g., [200, 400, 800]) supported
                       by the current camera mode. The list is determined as follows
                       based on the `mode` value obtained from `get_camera_mode()`:

                       - mode == 1  : supports [200, 400, 800]   (max 800)
                       - mode == 2  : supports [200, 400, 800, 1000] (max 1000)
                       - mode == 3  : supports [200]             (max 200)
                       - mode == 0 or 4 : supports [200, 400]    (max 400)

        Note:
            The current implementation treats `mode == 4` and `mode == 0` identically.
            However, the line `elif mode == 4 or mode[0] == 0:` appears to contain an
            error – `mode` is an integer, so `mode[0]` will raise a `TypeError`. The
            intended condition is likely `mode == 4 or mode == 0`. The docstring
            reflects the logical intent as written in the code.

        Raises:
            Exception: Propagated from `get_camera_mode()` if the underlying C call fails.

        See Also:
            get_camera_mode : Retrieves the current camera mode and ROI geometries.
        """
        mode, left_roi, right_roi = self.get_camera_mode()

        max_sampling_rate = 200
        if mode == 1:
            max_sampling_rate = 800
            return [200, 400, 800]
        elif mode == 2:
            max_sampling_rate = 1000
            return [200, 400, 800, 1000]
        elif mode == 3:
            max_sampling_rate = 200
            return [200]
        elif mode == 4 or mode[0] == 0:  # BUG: mode is int, mode[0] is invalid
            max_sampling_rate = 400
            return [200, 400]

    def set_camera_mode(self, mode_value):
        """
        Set the camera frame rate mode.

        This function sets the camera mode (only for sync_400 devices that also support
        sync_200). It must be called **before** `deep_gaze_init()` – the library reads
        the configuration file and applies the mode during initialization.

        The mode is written into the `dp_camera_tunning.bin` at runtime; the camera is
        opened with the chosen setting and cannot be reconfigured after initialization.

        Args:
            mode_value (int): Target mode. Only the following values are accepted:
                - CAMERA_MODE_SYNC_400 (0) : native 400 fps
                - CAMERA_MODE_SYNC_200 (3) : down‑sampled 200 fps (ROI 1024×1024,
                  exposure 2500 µs, identical to native 200 devices)

        Raises:
            Exception: If the underlying C function returns a code other than ET_SUCCESS.
                This can happen if `mode_value` is invalid, the device is not a
                sync_400 device, or the call fails internally.

        Returns:
            None
        """
        mode = ctypes.c_int(mode_value)
        ret = self._et_native_lib.pupil_io_set_camera_mode(ctypes.byref(mode))
        if ret != ET_ReturnCode.ET_SUCCESS:
            raise Exception(f"pupil_io_set_camera_mode failed with code {ret}")

    def get_camera_mode(self):
        """
        Query the currently active camera frame rate mode and ROI geometry.

        This function retrieves the runtime mode and the ROI rectangles for the left
        and right cameras. The values are determined by the `dp_camera_tunning.bin`
        file and are the single source of truth – clients should **not** hard‑code
        ROI dimensions or offsets.

        Call this function **after** `deep_gaze_init()` has succeeded. The returned
        ROI information can be used to allocate preview buffers and layout the image
        rectangles on the UI.

        Args:
            None

        Returns:
            tuple: A 3‑element tuple containing:
                - mode (int): The current camera mode (see CameraMode.h for values).
                - left_roi (numpy.ndarray): 4‑element int32 array [x, y, w, h] for the
                  left camera ROI in the full sensor coordinate system (1280×1024).
                  These values define both the ROI buffer size (w×h) and the paste
                  position (x,y) on the canvas.
                - right_roi (numpy.ndarray): 4‑element int32 array [x, y, w, h] for
                  the right camera ROI, with the same definition as `left_roi`.

        Raises:
            Exception: If the underlying C function returns a code other than ET_SUCCESS.
                This typically indicates that the function was called before
                `deep_gaze_init()` or that the DLL is not properly initialized.

        Notes:
            - The `mode` parameter in the C++ signature is an output pointer; here it is
              returned as the first element of the tuple.
            - Both `left_roi` and `right_roi` are allocated as NumPy arrays and passed
              by pointer to the DLL.
        """
        mode = np.zeros(1, dtype=np.int32)  # 单个 int32
        left_roi = np.zeros(4, dtype=np.int32)  # 长度4的 int32 数组
        right_roi = np.zeros(4, dtype=np.int32)
        ret = self._et_native_lib.pupil_io_get_camera_mode(
            mode.ctypes.data_as(ctypes.POINTER(ctypes.c_int)),
            left_roi.ctypes.data_as(ctypes.POINTER(ctypes.c_int)),
            right_roi.ctypes.data_as(ctypes.POINTER(ctypes.c_int))
        )
        if ret != ET_ReturnCode.ET_SUCCESS:
            raise Exception(f"pupil_io_set_camera_mode failed with code {ret}")
        return mode[0], left_roi, right_roi

    def previewer_start(self, udp_host: str, udp_port: int, draw_preview_annotations: bool = True):
        """
        Initialize and start the previewer.

        :param udp_host: The UDP host address for receiving the video stream.
        :param udp_port: The UDP port number for receiving the video stream.
        :param draw_preview_annotations: Whether to eye boxes, glints, and eye pupils.

        This method first calls pupil_io_previewer_init to initialize the previewer,
        and then calls pupil_io_previewer_start to start the preview.
        """
        try:
            ipaddress.ip_address(udp_host)
        except ValueError:
            raise Exception(f"Invalid IP address: {udp_host}.")
        self._et_native_lib.pupil_io_previewer_init(udp_host.encode('gbk'), udp_port, draw_preview_annotations)
        self._et_native_lib.pupil_io_previewer_start()

    def previewer_stop(self):
        """
        Stop the previewer.

        This method calls pupil_io_previewer_stop to cease receiving and processing
        the video stream.
        """
        self._et_native_lib.pupil_io_previewer_stop()

    def create_session(self, session_name: str) -> int:
        """
        Creates a new session and sets up related directories, log files, and the logger.

        Args:
            session_name: The name of the session, used to define log files and a temporary folder
            for real-time storage of eye-tracking data.
            It is recommended to make the session_name unique, so data can be recovered from the
            temporary folder in case of loss. The session_name must only contain letters, digits,
            or underscores without any special characters.

        Returns:
            int: ET_ReturnCode indicating the success or failure of session creation.

        Notes:
            1. The temporary folder is located at `/Pupilio/{session_name}_{time}` in the user's home directory.
            2. If storage space runs out, you can delete this temporary folder to free up space.
        """
        self._session_name = session_name

        # List of reserved names for Windows
        reserved_names = {
            "CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
            "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"
        }

        pattern = r'^[a-zA-Z0-9_+\-()]+$'
        available_session = bool(re.fullmatch(pattern, session_name) and (session_name.upper() not in reserved_names))
        if not available_session:
            raise Exception(
                f"Session name '{session_name}' is invalid. Ensure it follows these rules:\n"
                f"1. Only includes letters (A-Z, a-z), digits (0-9), underscores (_), hyphens (-), plus signs (+), and parentheses ().\n"
                f"2. Does not include any of the following prohibited characters: < > : \" / \\ | ? *.\n"
                f"3. Does not match any of the following reserved names: {', '.join(reserved_names)}."
            )

        current_time = datetime.now()
        formatted_current_time = current_time.strftime("%Y%m%d%H%M%S")
        self._session_name += f"_{formatted_current_time}"
        return self._et_native_lib.pupil_io_create_session(self._session_name.encode('gbk'))

    def save_data(self, path: str) -> int:
        """
        Save sampled data to a file.

        Args:
            path (str): The path to save the data file.

        Returns:
            int: Return code indicating success or failure.
        """
        # Check if the directory exists and is writable
        directory = os.path.dirname(path)

        if directory and (not os.path.exists(directory)):
            raise Exception("The directory of data file not exist.")

        if directory and not os.access(directory, os.W_OK):
            raise Exception("The directory of data file is not writeable.")
            # sys.exit(1)  # Exit the program with an error status

        if self._et_native_lib.pupil_io_save_data_to(path.encode("gbk")) == ET_ReturnCode.ET_SUCCESS:
            return ET_ReturnCode.ET_SUCCESS
        else:
            raise Exception(f"Failed to save data at path: {path}.")

    def start_sampling(self) -> int:
        """
        Start eye gaze sampling.

        Returns:
            int: Return code indicating success or failure.
        """
        # Lock to ensure thread safety while modifying sampling status
        res = self._et_native_lib.pupil_io_start_sampling()
        time.sleep(0.05)
        if res == ET_ReturnCode.ET_FAILED:
            raise Exception("You have called `start_sampling` function or something went wrong.")
        return res

    def get_sampling_status(self) -> bool:
        """
        Check the status of sampling from the pupil IO.

        Returns:
        bool: True if sampling is active, False otherwise.
        """
        # Create a c_bool variable to hold the status
        status = ctypes.c_bool()

        # Create a pointer to the c_bool variable
        status_pointer = ctypes.byref(status)

        # Call the function from the C library
        self._et_native_lib.pupil_io_sampling_status(status_pointer)

        # Return the value of the status
        return status.value

    def stop_sampling(self) -> int:
        """
        Stop eye gaze sampling.

        Returns:
            int: Return code indicating success or failure.
        """
        res = self._et_native_lib.pupil_io_stop_sampling()
        time.sleep(0.1)
        if res == ET_ReturnCode.ET_FAILED:
            raise Exception("There is no sampling running.")
        return res

    def face_position(self) -> Tuple[int, np.ndarray]:
        """
        Get the current face position.

        Returns:
            tuple: A tuple containing the result code and numpy array of face position coordinates.
                   - If sampling is ongoing, returns ET_FAILED and an empty list.
                   - If successful, returns ET_SUCCESS and the face position coordinates.
        """
        # Create a ctypes array to store face position
        # Call DLL function to get face position
        ret = self._et_native_lib.pupil_io_face_pos(self._face_pos)
        # Return result code and face position coordinates
        return ret, self._face_pos

    def calibration(self, cali_point_id: int) -> int:
        """Perform calibration

        Args:
            cali_point_id (int): ID of the calibration point, 0 for the first calibration point,
                                 1 for the second, and so on.

        Returns:
            int: Result of the calibration, can be checked against ET_ReturnCode enum.
        """
        if self.get_sampling_status():
            return ET_ReturnCode.ET_FAILED
        return self._et_native_lib.pupil_io_cali(cali_point_id)

    @deprecated("1.1.1", "Please use function `estimate_gaze`")
    def estimation(self) -> Tuple[int, np.ndarray, int, int]:
        """
        Estimate the gaze state and position.

        Returns:
            tuple[int, np.ndarray, int, int]: A tuple containing ET_ReturnCode,
            eye position data, timestamp, and trigger.
        """
        timestamp = ctypes.c_longlong()
        status = self._et_native_lib.pupil_io_gaze_est(self._pt.ctypes, ctypes.byref(timestamp))
        trigger = 0
        return status, self._pt, timestamp.value, trigger

    @deprecated("1.4.0", "Please use function `estimate_gaze`")
    def estimation_lr(self) -> Tuple[int, np.ndarray, np.ndarray, int, int]:
        """
        Estimate the gaze state and position for left and right eyes.

        This function calls the native pupil estimation library to obtain the
        estimated gaze points for both the left and right eyes, as well as the
        timestamp of the estimation. The function returns the status of the
        operation, the gaze points for the left and right eyes, the timestamp,
        and an additional trigger value.

        Returns:
            Tuple[int, np.ndarray, np.ndarray, int, int]:
                - int: Status code, where `ET_ReturnCode.ET_SUCCESS` indicates success.
                - np.ndarray: Estimated gaze point for the left eye. Contains 14 elements.
                    left_eye_sample[0]:left eye gaze position x (0~1920)
                    left_eye_sample[1]:left eye gaze position y (0~1920)
                    left_eye_sample[2]:left eye pupil diameter (0~10) (mm)
                    left_eye_sample[3]:left eye pupil position x
                    left_eye_sample[4]:left eye pupil position y
                    left_eye_sample[5]:left eye pupil position z
                    left_eye_sample[6]:left eye visual angle in spherical: theta
                    left_eye_sample[7]:left eye visual angle in spherical: phi
                    left_eye_sample[8]:left eye visual angle in vector: x
                    left_eye_sample[9]:left eye visual angle in vector: y
                    left_eye_sample[10]:left eye visual angle in vector: z
                    left_eye_sample[11]:left eye pix per degree x
                    left_eye_sample[12]:left eye pix per degree y
                    left_eye_sample[13]:left eye valid (0:invalid 1:valid)
                - np.ndarray: Estimated gaze point for the right eye. Contains 14 elements.
                    right_eye_sample[0]:right eye gaze position x (0~1920)
                    right_eye_sample[1]:right eye gaze position y (0~1920)
                    right_eye_sample[2]:right eye pupil diameter (0~10) (mm)
                    right_eye_sample[3]:right eye pupil position x
                    right_eye_sample[4]:right eye pupil position y
                    right_eye_sample[5]:right eye pupil position z
                    right_eye_sample[6]:right eye visual angle in spherical: theta
                    right_eye_sample[7]:right eye visual angle in spherical: phi
                    right_eye_sample[8]:right eye visual angle in vector: x
                    right_eye_sample[9]:right eye visual angle in vector: y
                    right_eye_sample[10]:right eye visual angle in vector: z
                    right_eye_sample[11]:right eye pix per degree x
                    right_eye_sample[12]:right eye pix per degree y
                    right_eye_sample[13]:right eye valid (0:invalid 1:valid)
                - int: Timestamp of the estimation (in milliseconds).
                - int: Trigger value, initialized to 0.
        Example:
            status, left_eye_sample, right_eye_sample, bino_eye_sample, timestamp, trigger = instance.estimation_lr()
            if status == ET_ReturnCode.ET_SUCCESS:
                print("Gaze estimation successful.")
        """
        timestamp = ctypes.c_longlong()
        status = self._et_native_lib.pupil_io_est_lr(self._pt_l, self._pt_r, ctypes.byref(timestamp))
        trigger = 0
        return status, self._pt_l, self._pt_r, timestamp.value, trigger

    def estimate_gaze(self) -> Tuple[int, np.ndarray, np.ndarray, np.ndarray, int, int]:
        """
        Estimate the gaze state and position for left, right, and bino eyes.

        This function calls the native pupil estimation library to obtain the
        estimated gaze points for both the left and right eyes, as well as the
        timestamp of the estimation. The function returns the status of the
        operation, the gaze points for the left and right eyes, the timestamp,
        and an additional trigger value.

        Returns:
            Tuple[int, np.ndarray, np.ndarray, int, int]:
                - int: Status code, where `ET_ReturnCode.ET_SUCCESS` indicates success.
                - np.ndarray: Estimated gaze point for the left eye. Contains 14 elements.
                    left_eye_sample[0]:left eye gaze position x (0~1920)
                    left_eye_sample[1]:left eye gaze position y (0~1920)
                    left_eye_sample[2]:left eye pupil diameter (0~10) (mm)
                    left_eye_sample[3]:left eye pupil position x
                    left_eye_sample[4]:left eye pupil position y
                    left_eye_sample[5]:left eye pupil position z
                    left_eye_sample[6]:left eye visual angle in spherical: theta
                    left_eye_sample[7]:left eye visual angle in spherical: phi
                    left_eye_sample[8]:left eye visual angle in vector: x
                    left_eye_sample[9]:left eye visual angle in vector: y
                    left_eye_sample[10]:left eye visual angle in vector: z
                    left_eye_sample[11]:left eye pix per degree x
                    left_eye_sample[12]:left eye pix per degree y
                    left_eye_sample[13]:left eye valid (0:invalid 1:valid)
                - np.ndarray: Estimated gaze point for the right eye. Contains 14 elements.
                    right_eye_sample[0]:right eye gaze position x (0~1920)
                    right_eye_sample[1]:right eye gaze position y (0~1920)
                    right_eye_sample[2]:right eye pupil diameter (0~10) (mm)
                    right_eye_sample[3]:right eye pupil position x
                    right_eye_sample[4]:right eye pupil position y
                    right_eye_sample[5]:right eye pupil position z
                    right_eye_sample[6]:right eye visual angle in spherical: theta
                    right_eye_sample[7]:right eye visual angle in spherical: phi
                    right_eye_sample[8]:right eye visual angle in vector: x
                    right_eye_sample[9]:right eye visual angle in vector: y
                    right_eye_sample[10]:right eye visual angle in vector: z
                    right_eye_sample[11]:right eye pix per degree x
                    right_eye_sample[12]:right eye pix per degree y
                    right_eye_sample[13]:right eye valid (0:invalid 1:valid)
                 - np.ndarray: Estimated gaze point for the bino eye. Contains 9 elements.
                    bino_eye_sample[0]: bino eye gaze position x (0~1920)
                    bino_eye_sample[1]: bino eye gaze position y (0~1920)
                    bino_eye_sample[2]: nil
                    bino_eye_sample[3]: nil
                    bino_eye_sample[4]: nil
                    bino_eye_sample[5]: nil
                    bino_eye_sample[6]: nil
                    bino_eye_sample[7]: nil
                    bino_eye_sample[8]: nil
                    bino_eye_sample[9]: nil
                - int: Timestamp of the estimation (in milliseconds).
                - int: Trigger value, initialized to 0.
        Example:
            status, left_eye_sample, right_eye_sample, bino_eye_sample, timestamp, trigger = instance.estimation_lr()
            if status == ET_ReturnCode.ET_SUCCESS:
                print("Gaze estimation successful.")
        """
        timestamp = ctypes.c_longlong()
        status = self._et_native_lib.pupil_io_estimate_gaze(self._pt_l, self._pt_r, self._pt_bino,
                                                            ctypes.byref(timestamp))
        trigger = 0
        return status, self._pt_l, self._pt_r, self._pt_bino, timestamp.value, trigger

    def release(self) -> int:
        """
        Release the resources used by the eye tracker.

        Returns:
            int: ET_ReturnCode.ET_SUCCESS if successful.
        """
        # logging.info("release deep gaze")
        return_code = self._et_native_lib.pupil_io_release()

        # if platform.system().lower() == 'windows':
        #     kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        #     free_library = kernel32.FreeLibrary
        #     free_library.argtypes = [ctypes.c_void_p]
        #     if free_library(self._et_native_lib._handle):
        #         logging.info("native library unload successfully.")
        #     else:
        #         logging.info("failed to unload native library.")
        # else:
        #     logging.warning("Not supported platform: %s" % platform.system())
        return return_code

    def set_trigger(self, trigger: int) -> int:
        """
        Set the trigger.

        Args:
            trigger: The trigger to set. Range: 1 - 65535
        """
        if not isinstance(trigger, int):
            raise TypeError("Trigger must be an integer.")

        if trigger < 1 or trigger > 65535:
            raise ValueError("Trigger must be between 1 and 65535")

        if self._et_native_lib.pupil_io_send_trigger(trigger) == ET_ReturnCode.ET_SUCCESS:
            return ET_ReturnCode.ET_SUCCESS
        else:
            raise Exception("Please don't call `set_trigger` function too frequently.")

    def set_filter_enable(self, status: bool) -> int:
        """
        Enable or disable the filter.

        Args:
            status (bool): True to enable the filter, False to disable.
        """
        return self._et_native_lib.pupil_io_set_filter_enable(status)

    def get_current_gaze(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Retrieve the current gaze values for the left eye, right eye, and binocular gaze.

        Example:
            left, right, bino = pupil_io.get_current_gaze()
            left_valid = left[0]
            right_valid = right[0]
            bino_valid = bino[0]
            left_coordinate_x, left_coordinate_y = left[1], left[2]
            right_coordinate_x, right_coordinate_y = right[1], right[2]
            bino_coordinate_x, bino_coordinate_y = bino[1], bino[2]
        Returns:
            np.ndarray: A Tuple containing the left gaze, right gaze, and binocular gaze as floats.
        """
        # Create NumPy float arrays to hold the gaze values
        left_gaze = np.zeros(3, dtype=np.float32)
        right_gaze = np.zeros(3, dtype=np.float32)
        bino_gaze = np.zeros(3, dtype=np.float32)

        # Call the C function
        self._et_native_lib.pupil_io_get_current_gaze(
            left_gaze,  # Pointer to left gaze
            right_gaze,  # Pointer to right gaze
            bino_gaze  # Pointer to binocular gaze
        )
        # Return the gaze values as a NumPy array
        return left_gaze, right_gaze, bino_gaze

    def calibration_draw(self, screen=None, validate=False, bg_color=(255, 255, 255), hands_free=False):
        """
        Draw the indicator of the face distance and the eyebrow center position.
        Draw the calibration UI.
        Args:
            screen: The screen to draw on. You can choose pygame window or psychopy window
            validate (bool): Whether to validate the calibration result.
            bg_color (tuple): Background color, specific parameter for pygame
            hands_free (bool): Whether to hands free
        """
        from pygame import Surface
        screen_type = ""
        if screen is None:
            try:
                import pygame
                from pygame.locals import FULLSCREEN, HWSURFACE
                pygame.init()
                scn_width, scn_height = (1920, 1080)
                screen = pygame.display.set_mode((scn_width, scn_height), FULLSCREEN | HWSURFACE)
                screen_type = 'pygame'
            except:
                print("The parameter passed is None, creating a new pygame screen.")
                raise Exception("pygame screen can't be created.")
        elif isinstance(screen, Surface):
            screen_type = 'pygame'
        else:
            from psychopy.visual import Window
            if isinstance(screen, Window):
                screen_type = 'psychopy'

        if screen_type == "":
            raise Exception("Screen cannot be None. Please pass pygame window or psychopy window instance")

        if screen_type == 'pygame':
            from .graphics_pygame import CalibrationUI
        else:
            from .graphics import CalibrationUI

        if not hands_free:
            CalibrationUI(pupil_io=self, screen=screen).draw(validate=validate, bg_color=bg_color)
        else:
            CalibrationUI(pupil_io=self, screen=screen).draw_hands_free(validate=validate, bg_color=bg_color)


        # if screen is None:
        #     # 创建默认的 PyGame 全屏窗口
        #     import pygame
        #     from pygame.locals import FULLSCREEN, HWSURFACE
        #     pygame.init()
        #     screen = pygame.display.set_mode((1920, 1080), FULLSCREEN | HWSURFACE)
        #
        #     # 导入统一的校准 UI（内部会根据 screen 类型自动选择后端）
        # from .cali_graphics import CalibrationUI
        # ui = CalibrationUI(pupil_io=self, screen=screen, bg_color=bg_color)
        #
        # if not hands_free:
        #     ui.draw(validate=validate, bg_color=bg_color)
        # else:
        #     ui.draw_hands_free(validate=validate, bg_color=bg_color)

    @deprecated("1.1.2")
    def subscribe_sample(self, subscriber_func: Callable, args=(), kwargs=None):
        """
        Subscribe a function to receive eye tracking samples.

            'sample' is an instance of dict. The format is as follows:

            sample = {
                "trigger": trigger,
                "status": status,
                "left_eye_sample": left_eye_sample,
                "right_eye_sample": right_eye_sample,
                "timestamp": timestamp
            }

            'left_eye_sample' is an instance of list, which contains 14 elements as follows:
                left_eye_sample[0]:left eye gaze position x (0~1920)
                left_eye_sample[1]:left eye gaze position y (0~1920)
                left_eye_sample[2]:left eye pupil diameter (0~10) (mm)
                left_eye_sample[3]:left eye pupil position x
                left_eye_sample[4]:left eye pupil position y
                left_eye_sample[5]:left eye pupil position z
                left_eye_sample[6]:left eye visual angle in spherical: theta
                left_eye_sample[7]:left eye visual angle in spherical: phi
                left_eye_sample[8]:left eye visual angle in vector: x
                left_eye_sample[9]:left eye visual angle in vector: y
                left_eye_sample[10]:left eye visual angle in vector: z
                left_eye_sample[11]:left eye pix per degree x
                left_eye_sample[12]:left eye pix per degree y
                left_eye_sample[13]:left eye valid (0:invalid 1:valid)
            'right_eye_sample' is an instance of list, which contains 14 elements as follows:
                right_eye_sample[0]:right eye gaze position x (0~1920)
                right_eye_sample[1]:right eye gaze position y (0~1920)
                right_eye_sample[2]:right eye pupil diameter (0~10) (mm)
                right_eye_sample[3]:right eye pupil position x
                right_eye_sample[4]:right eye pupil position y
                right_eye_sample[5]:right eye pupil position z
                right_eye_sample[6]:right eye visual angle in spherical: theta
                right_eye_sample[7]:right eye visual angle in spherical: phi
                right_eye_sample[8]:right eye visual angle in vector: x
                right_eye_sample[9]:right eye visual angle in vector: y
                right_eye_sample[10]:right eye visual angle in vector: z
                right_eye_sample[11]:right eye pix per degree x
                right_eye_sample[12]:right eye pix per degree y
                right_eye_sample[13]:right eye valid (0:invalid 1:valid)

        Args:
            subscriber_func (Callable): The function to be called when a new eye tracking sample is available.
            args (tuple): Optional positional arguments to pass to the subscriber function.
            kwargs (dict): Optional keyword arguments to pass to the subscriber function.

        Raises:
            Exception: If `subscriber_func` is not Callable.
        """
        if kwargs is None:
            kwargs = {}

    @deprecated("1.1.2")
    def unsubscribe_sample(self, subscriber_func: Callable, args=(), kwargs=None):
        """
        Unsubscribe a function from receiving eye tracking samples.

        Args:
            subscriber_func (Callable): The function to be removed from subscribers.
            args (tuple): Positional arguments used for subscription (should match what was used during subscription).
            kwargs (dict): Keyword arguments used for subscription (should match what was used during subscription).

        Raises:
            Exception: If `subscriber_func` is not Callable.
        """
        if kwargs is None:
            kwargs = {}

    @deprecated("1.1.2")
    def subscribe_event(self, *args):
        """
        Subscribe a function to receive eye tracking sample.

        Raises:
            Exception: If any of the args are not Callable.
        """

        # self._online_event_detection.subscribe(*args)
        pass

    @deprecated("1.1.2")
    def unsubscribe_event(self, *args):
        """
        Unsubscribe functions from receiving eye tracking sample.
        """

        # self._online_event_detection.unsubscribe(*args)
        pass

    def clear_cache(self) -> int:
        """Clear the cache."""
        return self._et_native_lib.pupil_io_clear_cache()

    @deprecated("1.1.2")
    @property
    def sample_subscriber_lock(self):
        return None

    @deprecated("1.1.2")
    @property
    def sample_subscribers(self):
        return None

    def _process_images(self, left_img: np.ndarray, right_img: np.ndarray, eye_rects: np.ndarray,
                        pupil_centers: np.ndarray, glint_centers: np.ndarray) -> np.ndarray:

        IMG_HEIGHT, IMG_WIDTH = 1024, 1280  # Dimensions of the preview images
        _left_img = cv2.cvtColor(left_img, cv2.COLOR_GRAY2BGR)
        _right_img = cv2.cvtColor(right_img, cv2.COLOR_GRAY2BGR)

        FRAME_WARNING = (255, 0, 0)  # WARNING FRAME
        FRAME_SUCCESS = (0, 255, 0)  # SUCCESS
        FRAME_COLOR = FRAME_SUCCESS
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

        # figure out which eye to mask for drawing purposes
        if self.config.active_eye in [-1, 'left']:
            patch_mask_index = 1
        elif self.config.active_eye in [1, 'right']:
            patch_mask_index = 0
        else:
            patch_mask_index = -1

        # clip eye_patches
        eye_patches = []
        for img_idx, img in enumerate(imgs):  # enumerate left and right images
            patches = []
            img_h, img_w, _ = img.shape  # get image size
            for patch_idx, rect in enumerate(rects[img_idx]):
                # Ensure eye rect is valid
                x1, y1, w, h = map(int, rect)
                x2, y2 = x1 + w, y1 + h
                if x1 < 0 or y1 < 0 or x2 > img_w or y2 > img_h or x1 > x2 or y1 > y2:
                    # print(f"Invalid rect at img {img_idx}, rect {patch_idx}: {rect}")
                    FRAME_COLOR = FRAME_WARNING
                    continue  # skip invalid frame

                if w == 0 or h == 0:  # empty eye-patch when tracking monocularly
                    patch = img[0:96, 0:96]
                else:
                    patch = img[y1:y2, x1:x2]  # clip the eye patch

                # pupil center and glint coordinates
                pupil_x, pupil_y = pupil_center_list[img_idx][patch_idx]
                glint_x, glint_y = glint_center_list[img_idx][patch_idx]

                if not (x1 <= pupil_x < x2 and y1 <= pupil_y < y2):
                    if not (patch_mask_index == patch_idx):
                        FRAME_COLOR = FRAME_WARNING
                    # print(f"Invalid pupil center at img {img_idx}, rect {patch_idx}: ({pupil_x}, {pupil_y})")
                    pupil_x, pupil_y = None, None  # invalid pupil center
                else:
                    pupil_x, pupil_y = int(pupil_x - x1), int(pupil_y - y1)

                if not (x1 <= glint_x < x2 and y1 <= glint_y < y2):
                    if not (patch_mask_index == patch_idx):
                        FRAME_COLOR = FRAME_WARNING
                    # print(f"Invalid glint center at img {img_idx}, rect {patch_idx}: ({glint_x}, {glint_y})")
                    glint_x, glint_y = None, None  # invalid glint
                else:
                    glint_x, glint_y = int(glint_x - x1), int(glint_y - y1)

                # draw pupil center
                if pupil_x is not None and pupil_y is not None:
                    cv2.circle(patch, (pupil_x, pupil_y), 5, (0, 0, 255), -1)
                # draw glint
                if glint_x is not None and glint_y is not None:
                    cv2.circle(patch, (glint_x, glint_y), 3, (0, 255, 0), -1)

                # draw rect on image
                if w == 0 or h == 0:
                    pass
                else:
                    cv2.rectangle(patch, (0, 0), (patch.shape[1] - 1, patch.shape[0] - 1), FRAME_COLOR, 6)

                patches.append(patch)
            eye_patches.append(patches)

        margin = 10
        for canvas_idx, canvases in enumerate(eyes_canvas):
            for rect_idx, canvas in enumerate(canvases):
                if canvas_idx >= len(eye_patches) or rect_idx >= len(eye_patches[canvas_idx]):
                    continue  # skip invalid patch
                patch = eye_patches[canvas_idx][rect_idx]
                patch_h, patch_w, _ = patch.shape
                canvas_h, canvas_w, _ = canvas.shape

                # calculate scale
                scale = min((canvas_w - 2 * margin) / patch_w, (canvas_h - 2 * margin) / patch_h)
                new_w, new_h = int(patch_w * scale), int(patch_h * scale)

                # resize eye_patch
                resized_patch = cv2.resize(patch, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

                # calculate patch center
                start_x = (canvas_w - new_w) // 2
                start_y = (canvas_h - new_h) // 2

                # draw scaled patch on canvas
                if not rect_idx == patch_mask_index:
                    eyes_canvas[canvas_idx][rect_idx][start_y:start_y + new_h, start_x:start_x + new_w] = resized_patch

        for idx in range(2):
            original_img = imgs[idx]
            eye1_canvas, eye2_canvas = eyes_canvas[idx]
            cv2.rectangle(eye1_canvas, (0, 0), (eye1_canvas.shape[1] - 1, eye1_canvas.shape[0] - 1), FRAME_COLOR, 2)
            cv2.rectangle(eye2_canvas, (0, 0), (eye2_canvas.shape[1] - 1, eye2_canvas.shape[0] - 1), FRAME_COLOR, 2)

            # cv2.rectangle(original_img, (0, 0), (original_img.shape[1] - 1, original_img.shape[0] - 1), FRAME_COLOR,
            #               FRAME_WIDTH)

            # if self.sampling_rate == 200 or not return_ava:
            #
            # else:
            #     img = np.ones((IMG_HEIGHT, IMG_WIDTH, 3), dtype=np.uint8) * 128
            #     self._draw_avatar_face(img,
            #                            rects[idx][0],
            #                            rects[idx][1],
            #                             pupil_center_list[idx][0],
            #                             pupil_center_list[idx][1],
            #                            (43, 49), (83, 51))
            #     preview_imgs[idx, 0:IMG_HEIGHT, 0:IMG_WIDTH, :] = img

            h, w = original_img.shape[:2]
            start_y = (IMG_HEIGHT - h) // 2
            start_x = (IMG_WIDTH - w) // 2
            preview_imgs[idx, start_y:start_y + h, start_x:start_x + w, :] = original_img

            # if self.config.sampling_rate == 400:
            #     RECT_YELLOW = (0, 255, 255)
            #     if idx == 0:
            #         rect = (320, 385, 960, 420)
            #     else:
            #         rect = (0, 356, 960, 420)
            #     pt1 = (rect[0], rect[1])
            #     pt2 = (rect[0] + rect[2], rect[1] + rect[3])
            #     cv2.rectangle(preview_imgs[idx], pt1, pt2, RECT_YELLOW, 2)

            cv2.rectangle(preview_imgs[idx], (0, 0), (IMG_WIDTH - 1, IMG_HEIGHT - 1), FRAME_COLOR,
                          FRAME_WIDTH)
            canvas_h, canvas_w, _ = eye1_canvas.shape
            target_h, target_w = canvas_h, canvas_w
            # Merge two eye patches
            combined_canvas = np.zeros((target_h, 2 * target_w, 3), dtype=np.uint8)
            combined_canvas[:, 0:target_w, :] = eye1_canvas
            combined_canvas[:, target_w:2 * target_w, :] = eye2_canvas
            preview_imgs[idx, IMG_HEIGHT:IMG_HEIGHT + target_h, 0:2 * target_w, :] = combined_canvas
        return preview_imgs

    def get_preview_images(self):
        """
        Retrieves preview images and related eye-tracking data, including eye bounds, pupil centers,
        and corneal reflection (CR) centers, from the native eye-tracking library.

        Returns:
            numpy.ndarray: A 3D array containing the left and right grayscale preview images.
        """

        # if self.max_sampling_rate == 200:
        #     # Initialize arrays for preview images, eye bounds, pupil centers, and CR centers
        #     IMG_HEIGHT, IMG_WIDTH = 1024, 1280  # Dimensions of the preview images
        #     preview_left_img = np.zeros((IMG_HEIGHT, IMG_WIDTH), dtype=np.uint8)
        #     preview_right_img = np.zeros((IMG_HEIGHT, IMG_WIDTH), dtype=np.uint8)
        # else:
        #     preview_left_img = np.zeros((self.LEFT_IMG_HEIGHT, self.LEFT_IMG_WIDTH), dtype=np.uint8)
        #     preview_right_img = np.zeros((self.RIGHT_IMG_HEIGHT, self.RIGHT_IMG_WIDTH), dtype=np.uint8)

        IMG_HEIGHT, IMG_WIDTH = 1024, 1280  # Dimensions of the preview images
        preview_left_img = np.zeros((IMG_HEIGHT, IMG_WIDTH), dtype=np.uint8)
        preview_right_img = np.zeros((IMG_HEIGHT, IMG_WIDTH), dtype=np.uint8)
        eye_rects = np.zeros(4 * 4, dtype=np.float32)  # Array for eye bounding boxes (4 coordinates per eye)
        pupil_centers = np.zeros(4 * 2, dtype=np.float32)  # Array for pupil centers (x, y for each pupil)
        glint_centers = np.zeros(4 * 2, dtype=np.float32)  # Array for CR centers (x, y for each CR)

        # Get C pointers to the data in the numpy arrays
        left_img_ptr = preview_left_img.ctypes.data_as(ctypes.POINTER(ctypes.c_ubyte))
        right_img_ptr = preview_right_img.ctypes.data_as(ctypes.POINTER(ctypes.c_ubyte))

        # Call the native eye-tracking library to retrieve data
        self._et_native_lib.pupil_io_get_previewer(ctypes.pointer(left_img_ptr),
                                                   ctypes.pointer(right_img_ptr),
                                                   eye_rects, pupil_centers,
                                                   glint_centers)

        # Copy data from native library back into the numpy arrays
        ctypes.memmove(preview_left_img.ctypes.data, left_img_ptr, preview_left_img.nbytes)
        ctypes.memmove(preview_right_img.ctypes.data, right_img_ptr, preview_right_img.nbytes)

        preview_imgs = self._process_images(preview_left_img, preview_right_img, eye_rects, pupil_centers,
                                            glint_centers)
        return preview_imgs

    def _recalibration(self) -> int:
        """
        Recalibration function
        """
        return self._et_native_lib.pupil_io_recalibrate()

    def _draw_avatar_face(self,
                          img: np.ndarray,
                          eye_rect_a: tuple | np.ndarray,  # (x, y, w, h)
                          eye_rect_b: tuple | np.ndarray,
                          pupil_a: tuple | np.ndarray,  # (x, y)
                          pupil_b: tuple | np.ndarray,
                          avatar_pupil_left: tuple,  # 头像左瞳孔 (x, y)
                          avatar_pupil_right: tuple) -> None:
        """
        将人脸头像通过瞳孔对齐绘制到图像上。
        参数:
            img: 目标图像 (H, W, 3) uint8, 就地修改
            eye_rect_a/b: 检测到的左右眼矩形 (x, y, w, h)
            pupil_a/b: 检测到的瞳孔坐标 (x, y)
            avatar_bgr: 头像彩色图
            avatar_alpha: 头像 alpha 蒙版 (0-255)
            avatar_pupil_left/right: 头像素材中左右瞳孔坐标 (x, y)
        """
        # 有效性检查
        valid_a = eye_rect_a[2] > 0 and eye_rect_a[3] > 0
        valid_b = eye_rect_b[2] > 0 and eye_rect_b[3] > 0
        if not valid_a or not valid_b:
            return

        if self.face_avatar_raw.ndim == 3 and self.face_avatar_raw.shape[2] == 4:
            # 四通道：分离 BGR 和 Alpha
            avatar_bgr = self.face_avatar_raw[:, :, :3]
            avatar_alpha = self.face_avatar_raw[:, :, 3]
        elif self.face_avatar_raw.ndim == 3 and self.face_avatar_raw.shape[2] == 3:
            # 三通道：直接当作 BGR，Alpha 全 255
            avatar_bgr = self.face_avatar_raw
            avatar_alpha = np.full(self.face_avatar_raw.shape[:2], 255, dtype=np.uint8)
        else:
            # 单通道灰度：转为 BGR，Alpha 全 255
            avatar_bgr = cv2.cvtColor(self.face_avatar_raw, cv2.COLOR_GRAY2BGR)
            avatar_alpha = np.full(self.face_avatar_raw.shape[:2], 255, dtype=np.uint8)
        # 头像存在性检查 (若没有 alpha 则返回)
        if avatar_bgr is None or avatar_alpha is None:
            return

        # 源瞳孔与目标瞳孔按 x 排序，保证左右一致
        s0 = np.float32(avatar_pupil_left)
        s1 = np.float32(avatar_pupil_right)
        if s0[0] > s1[0]:
            s0, s1 = s1, s0

        d0 = np.float32(pupil_a)
        d1 = np.float32(pupil_b)
        if d0[0] > d1[0]:
            d0, d1 = d1, d0

        # 相似变换矩阵 M = [[a, -b, tx], [b, a, ty]]
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

        # 计算变换后头像四角的包围盒
        fh, fw = avatar_bgr.shape[:2]
        corners = np.float32([[0, 0],
                              [fw, 0],
                              [fw, fh],
                              [0, fh]])
        warped_corners = cv2.transform(corners.reshape(1, -1, 2), M).reshape(-1, 2)

        minx = np.min(warped_corners[:, 0])
        maxx = np.max(warped_corners[:, 0])
        miny = np.min(warped_corners[:, 1])
        maxy = np.max(warped_corners[:, 1])

        bb_x = int(np.floor(minx))
        bb_y = int(np.floor(miny))
        bb_w = int(np.ceil(maxx)) - bb_x
        bb_h = int(np.ceil(maxy)) - bb_y

        # 裁剪到图像范围内
        bb_x = max(0, bb_x)
        bb_y = max(0, bb_y)
        bb_w = min(bb_w, img.shape[1] - bb_x)
        bb_h = min(bb_h, img.shape[0] - bb_y)
        if bb_w <= 0 or bb_h <= 0:
            return

        # 平移矩阵到包围盒局部坐标
        M_roi = M.copy()
        M_roi[0, 2] -= bb_x
        M_roi[1, 2] -= bb_y

        # 仿射变换彩色图和 alpha
        warped_bgr = cv2.warpAffine(avatar_bgr, M_roi, (bb_w, bb_h),
                                    flags=cv2.INTER_LINEAR,
                                    borderMode=cv2.BORDER_CONSTANT,
                                    borderValue=(0, 0, 0))
        warped_alpha = cv2.warpAffine(avatar_alpha, M_roi, (bb_w, bb_h),
                                      flags=cv2.INTER_LINEAR,
                                      borderMode=cv2.BORDER_CONSTANT,
                                      borderValue=0)

        # Alpha 混合: roi = roi*(1-α) + face*α
        alpha_f = warped_alpha.astype(np.float32) / 255.0
        alpha3 = np.dstack([alpha_f] * 3)

        roi = img[bb_y:bb_y + bb_h, bb_x:bb_x + bb_w]  # 视图
        roi_f = roi.astype(np.float32)
        face_f = warped_bgr.astype(np.float32)

        blended = roi_f * (1.0 - alpha3) + face_f * alpha3
        np.clip(blended, 0, 255, out=blended)
        roi[:] = blended.astype(np.uint8)
