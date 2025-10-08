# _*_ coding: utf-8 _*_
# Author: GC Zhu
# Email: zhugc2016@gmail.com
import ctypes
import os
import platform

from .misc import ET_ReturnCode


class EventDetection:
    """
    Detect fixations and saccades using the I-DT (Identification by Dispersion Threshold) algorithm.
    The I-DT algorithm identifies fixations as groups of consecutive samples where the
    dispersion (sum of x and y ranges) remains below a specified threshold for a minimum duration.

    Please see Salvucci, D. D., & Goldberg, J. H. (2000, November). Identifying fixations and saccades in eye-tracking
    protocols. In Proceedings of the 2000 symposium on Eye tracking research & applications (pp. 71-78).
    """

    def __init__(self):
        """Initialize EventDetection by loading PupilioET.dll depending on platform."""
        if platform.system().lower() == 'windows':
            _current_dir = os.path.abspath(os.path.dirname(__file__))
            _lib_dir = os.path.join(_current_dir, "lib")

            # Add DLL search path (for dependencies)
            os.add_dll_directory(_lib_dir)
            os.environ['PATH'] += ';' + _lib_dir

            # Load DLL
            _dll_path = os.path.join(_lib_dir, 'PupilioET.dll')
            if not os.path.exists(_dll_path):
                raise FileNotFoundError(f"DLL not found: {_dll_path}")

            self._et_native_lib = ctypes.CDLL(_dll_path, winmode=0)
        else:
            raise Exception(f"Not supported platform: {platform.system()}")

        # Define argument and return types
        # int pupil_io_event_detection(const char*, const char*, const char*, int, float)
        self._et_native_lib.pupil_io_event_detection.argtypes = [
            ctypes.c_char_p,  # data_path
            ctypes.c_char_p,  # output_dir
            ctypes.c_char_p,  # which_eye
            ctypes.c_int,  # minimum_duration
            ctypes.c_float  # dispersion_threshold
        ]
        self._et_native_lib.pupil_io_event_detection.restype = ctypes.c_int

    def detect(self, data_path: str, output_dir: str, which_eye: str,
               minimum_duration: int = 30, dispersion_threshold: float = 1.0) -> bool:
        """
        Run event detection on a gaze data CSV file.

        Args:
            data_path (str): Path to the gaze data CSV file.
            output_dir (str): Directory to save detection results.
            which_eye (str): "left", "right", or "bino".
            minimum_duration (int): Minimum fixation duration (>0).
            dispersion_threshold (float): Dispersion threshold (>0).

        Returns:
            bool: True if detection succeeded, otherwise raises an Exception.

        Raises:
            ValueError: For invalid input parameters.
            RuntimeError: For detection errors returned from the DLL.
        """
        # ===== 参数检查 =====
        if not os.path.exists(data_path):
            raise ValueError(f"Input file not found: {data_path}")
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        if which_eye not in ("left", "right", "bino"):
            raise ValueError(f"Invalid which_eye: {which_eye}")
        if minimum_duration <= 0:
            raise ValueError("minimum_duration must be > 0")
        if dispersion_threshold <= 0:
            raise ValueError("dispersion_threshold must be > 0")

        # ===== 调用 C++ DLL =====
        ret = self._et_native_lib.pupil_io_event_detection(
            data_path.encode("gbk"),
            output_dir.encode("gbk"),
            which_eye.encode("gbk"),
            ctypes.c_int(minimum_duration),
            ctypes.c_float(dispersion_threshold)
        )

        # ===== 返回码处理 =====
        if ret == ET_ReturnCode.ET_SUCCESS:
            # print("[Info] Event detection completed successfully.")
            return True
        elif ret == ET_ReturnCode.ET_INVALID_PATH:
            raise RuntimeError("Invalid file or output directory path.")
        elif ret == ET_ReturnCode.ET_INVALID_PARAM:
            raise RuntimeError("Invalid parameter passed to event detection.")
        elif ret == ET_ReturnCode.ET_EXCEPTION:
            raise RuntimeError(f"An internal exception occurred during event detection.")
        else:
            raise RuntimeError(f"Unknown return code: {ret}")
