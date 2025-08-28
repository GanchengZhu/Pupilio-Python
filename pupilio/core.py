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

# Author: GC Zhu
# Email: zhugc2016@gmail.com

import ctypes
import ipaddress
import logging
import os
import platform
import re
import time
from datetime import datetime
from typing import Callable, Tuple

import cv2
import numpy as np

from .annotation import deprecated
from .default_config import DefaultConfig
from .misc import ET_ReturnCode, CalibrationMode


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
        self._et_native_lib.pupil_io_get_previewer.argtypes = [
            ctypes.POINTER(ctypes.POINTER(ctypes.c_ubyte)),  # img_1
            ctypes.POINTER(ctypes.POINTER(ctypes.c_ubyte)),  # img_2
            np.ctypeslib.ndpointer(dtype=np.float32, ndim=1, flags='C_CONTIGUOUS'),
            np.ctypeslib.ndpointer(dtype=np.float32, ndim=1, flags='C_CONTIGUOUS'),
            np.ctypeslib.ndpointer(dtype=np.float32, ndim=1, flags='C_CONTIGUOUS')
        ]
        self._et_native_lib.pupil_io_previewer_init.argtypes = [ctypes.c_char_p, ctypes.c_int]
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

        self._et_native_lib.pupil_io_set_simulation_mode.argtypes = [ctypes.c_bool]
        self._et_native_lib.pupil_io_set_simulation_mode.restype = ctypes.c_int
        self._et_native_lib.pupil_io_set_kappa_filter.argtypes = [ctypes.c_int]
        self._et_native_lib.pupil_io_set_log.argtypes = [ctypes.c_int, ctypes.c_char_p]
        self._et_native_lib.pupil_io_set_eye_mode.argtypes = [ctypes.c_int]

        self._et_native_lib.pupil_io_set_simulation_mode(self.config.simulation_mode)
        version = self._et_native_lib.pupil_io_get_version()
        print("Native Pupilio Version:", version.decode("gbk"))
        # set tracking eye
        self._et_native_lib.pupil_io_set_eye_mode(self.config.active_eye.value)
        # set filter parameter: look ahead
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
        else:
            self.calibration_points = np.zeros(2 * 2, dtype=np.float32)

        self._et_native_lib.pupil_io_set_cali_mode(self.config.cali_mode, self.calibration_points)
        self.calibration_points = np.reshape(self.calibration_points, (-1, 2))

        # Initialize Pupilio, raise an exception if initialization fails
        if self._et_native_lib.pupil_io_init() != ET_ReturnCode.ET_SUCCESS.value:
            raise Exception("Pupilio init failed, please contact the developer!")

        self._face_pos = np.zeros(3, dtype=np.float32)
        self._pt = np.zeros(11, dtype=np.float32)
        self._pt_l = np.zeros(14, dtype=np.float32)
        self._pt_r = np.zeros(14, dtype=np.float32)

        self._previewer_thread = None
        self._online_event_detection = None

    def previewer_start(self, udp_host: str, udp_port: int):
        """
        Initialize and start the previewer.

        :param udp_host: The UDP host address for receiving the video stream.
        :param udp_port: The UDP port number for receiving the video stream.

        This method first calls pupil_io_previewer_init to initialize the previewer,
        and then calls pupil_io_previewer_start to start the preview.
        """
        try:
            ipaddress.ip_address(udp_host)
        except ValueError:
            raise Exception(f"Invalid IP address: {udp_host}.")
        self._et_native_lib.pupil_io_previewer_init(udp_host.encode('gbk'), udp_port)
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

        return self._et_native_lib.pupil_io_save_data_to(path.encode("gbk"))

    def start_sampling(self) -> int:
        """
        Start eye gaze sampling.

        Returns:
            int: Return code indicating success or failure.
        """
        # Lock to ensure thread safety while modifying sampling status
        res = self._et_native_lib.pupil_io_start_sampling()
        time.sleep(0.05)
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

        # Check if sampling is ongoing
        if self.get_sampling_status():
            # Return failed code if sampling is ongoing
            return ET_ReturnCode.ET_FAILED, self._face_pos
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

    @deprecated("1.1.1")
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
            status, left_eye_sample, right_eye_sample, timestamp, trigger = instance.estimation_lr()
            if status == ET_ReturnCode.ET_SUCCESS:
                print("Gaze estimation successful.")
        """
        timestamp = ctypes.c_longlong()
        status = self._et_native_lib.pupil_io_est_lr(self._pt_l, self._pt_r, ctypes.byref(timestamp))
        trigger = 0
        return status, self._pt_l, self._pt_r, timestamp.value, trigger

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
            trigger: The trigger to set.
        """
        return self._et_native_lib.pupil_io_send_trigger(trigger)

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
        left_img = cv2.cvtColor(left_img, cv2.COLOR_GRAY2BGR)
        right_img = cv2.cvtColor(right_img, cv2.COLOR_GRAY2BGR)

        FRAME_WARNING = (255, 0, 0)  # WARNING FRAME
        FRAME_SUCCESS = (0, 255, 0)  # SUCCESS
        FRAME_COLOR = FRAME_SUCCESS
        FRAME_WIDTH = 8

        imgs = [left_img, right_img]

        eyes_canvas = [[np.ones((IMG_WIDTH - IMG_HEIGHT, IMG_WIDTH // 2, 3), dtype=np.uint8) * 128,
                        np.ones((IMG_WIDTH - IMG_HEIGHT, IMG_WIDTH // 2, 3), dtype=np.uint8) * 128],
                       [np.ones((IMG_WIDTH - IMG_HEIGHT, IMG_WIDTH // 2, 3), dtype=np.uint8) * 128,
                        np.ones((IMG_WIDTH - IMG_HEIGHT, IMG_WIDTH // 2, 3), dtype=np.uint8) * 128]
                       ]

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

                if w==0 or h==0: # empty eye-patch when tracking monocularly
                    patch = img[0:96,0:96]
                else:
                    patch = img[y1:y2, x1:x2]  # clip the eye patch

                # pupil center and glint coordinates
                pupil_x, pupil_y = pupil_center_list[img_idx][patch_idx]
                glint_x, glint_y = glint_center_list[img_idx][patch_idx]

                if not (x1 <= pupil_x < x2 and y1 <= pupil_y < y2):
                    if not (patch_mask_index==patch_idx):
                        FRAME_COLOR = FRAME_WARNING
                    # print(f"Invalid pupil center at img {img_idx}, rect {patch_idx}: ({pupil_x}, {pupil_y})")
                    pupil_x, pupil_y = None, None  # invalid pupil center
                else:
                    pupil_x, pupil_y = int(pupil_x - x1), int(pupil_y - y1)

                if not (x1 <= glint_x < x2 and y1 <= glint_y < y2):
                    if not (patch_mask_index==patch_idx):
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
                if w==0 or h==0:
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
                if not rect_idx==patch_mask_index:
                    eyes_canvas[canvas_idx][rect_idx][start_y:start_y + new_h, start_x:start_x + new_w] = resized_patch


        for idx in range(2):
            original_img = imgs[idx]
            eye1_canvas, eye2_canvas = eyes_canvas[idx]
            cv2.rectangle(eye1_canvas, (0, 0), (eye1_canvas.shape[1] - 1, eye1_canvas.shape[0] - 1), FRAME_COLOR, 2)
            cv2.rectangle(eye2_canvas, (0, 0), (eye2_canvas.shape[1] - 1, eye2_canvas.shape[0] - 1), FRAME_COLOR, 2)

            cv2.rectangle(original_img, (0, 0), (original_img.shape[1] - 1, original_img.shape[0] - 1), FRAME_COLOR,
                          FRAME_WIDTH)

            preview_imgs[idx, 0:IMG_HEIGHT, 0:IMG_WIDTH, :] = original_img

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
        IMG_HEIGHT, IMG_WIDTH = 1024, 1280  # Dimensions of the preview images

        # Initialize arrays for preview images, eye bounds, pupil centers, and CR centers
        preview_left_img = np.zeros((IMG_HEIGHT, IMG_WIDTH), dtype=np.uint8)  # Left preview image
        preview_right_img = np.zeros((IMG_HEIGHT, IMG_WIDTH), dtype=np.uint8)  # Right preview image
        # preview_imgs = np.zeros((2, IMG_HEIGHT, IMG_WIDTH), dtype=np.uint8)  # Combined preview images
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
