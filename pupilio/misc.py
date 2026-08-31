# _*_ coding: utf-8 _*_
# Copyright (c) 2024, Hangzhou DeepGaze Science and Technology Co., Ltd
# All Rights Reserved
#
# For use by  Hangzhou DeepGaze Science and Technology Co., Ltd licencees only.
# Redistribution and use in source and binary forms, with or without
# modification, are NOT permitted.
#
# Redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in
# the documentation and/or other materials provided with the distribution.
#
# Neither name of  Hangzhou DeepGaze Science and Technology Co., Ltd nor the name of
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
# This demo shows how to configure the calibration process

# Author: GC Zhu
# Email: zhugc2016@gmail.com

import logging
import math
from enum import Enum, unique
from enum import IntEnum

import numpy as np

logger = logging.getLogger(__name__)


@unique
class StrEnum(str, Enum):
    """
    Enum where members are unique and are also strings
    """

    def _generate_next_value_(name, start, count, last_values):
        return name


class EventType(StrEnum):
    START_FIXATION = "start_fixation"
    END_FIXATION = "end_fixation"
    IN_FIXATION = "in_fixation"
    START_SACCADE = "start_saccade"
    END_SACCADE = "end_saccade"
    IN_SACCADE = "in_saccade"
    START_BLINK = "start_blink"
    END_BLINK = "end_blink"
    IN_BLINK = "in_blink"
    UNKNOWN = "unknown"


class ET_ReturnCode(IntEnum):
    """
    Status codes returned by the native eye tracker library.

    Mirrors ``PupilioReturn`` in ``pupil_io_et.h``; the numeric values are an ABI contract
    with the DLL and must not be renumbered.
    """
    ET_SUCCESS = 0  # Successful, can proceed to the next scenario
    ET_CALI_CONTINUE = 1  # Calibration ongoing, continue with current calibration point
    ET_CALI_NEXT_POINT = 2  # Calibration ongoing, switch to next calibration point
    ET_INVALID_PATH = 3  # A supplied file or directory path is invalid
    ET_INVALID_PARAM = 4  # A supplied argument is out of range or malformed
    ET_ALREADY_SET = 8  # The requested value was already applied; not an error
    ET_FAILED = 9  # Operation failed
    ET_EXCEPTION = 10  # An exception was raised inside the native library


class CalibrationMode(IntEnum):
    """Enum representing calibration modes"""
    TWO_POINTS = 2
    FOUR_POINTS = 4
    FIVE_POINTS = 5


class CameraMode(IntEnum):
    CAMERA_MODE_SYNC_400 = 0
    CAMERA_MODE_SYNC_800 = 1
    CAMERA_MODE_SYNC_1000 = 2
    CAMERA_MODE_SYNC_200 = 3
    CAMERA_MODE_ASYNC_400 = 4


class ActiveEye(IntEnum):
    """Tracking left eye, right eye or both"""
    LEFT_EYE = -1
    RIGHT_EYE = 1
    BINO_EYE = 0


class LocalConfig:
    """
    Class to handle local configuration settings.
    This class loads a JSON configuration file for deep configuration settings.
    """

    def __init__(self):
        """
        Initialize LocalConfig.
        This loads a JSON configuration file and stores it in 'dp_config'.
        """
        self.dp_config = {
            "model_name": "Pupil.IO AIO",
            "screen_width": 1920,
            "screen_height": 1080,
            "physical_screen_width": 34.13,
            "physical_screen_height": 19.32
        }


class Calculator:
    """
    Class to perform calculations related to screen dimensions.
    This class can calculate error metrics based on pixel values and distances.
    """

    def __init__(self, screen_width, screen_height, physical_screen_width, physical_screen_height, *args, **kwargs):
        """
        Initialize Calculate with screen dimensions.

        :param screen_width: Screen width in pixels.
        :param screen_height: Screen height in pixels.
        :param physical_screen_width: Physical screen width in inches.
        :param physical_screen_height: Physical screen height in inches.
        """
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.physical_screen_width = physical_screen_width
        self.physical_screen_height = physical_screen_height

    def error(self, gt_pixel, es_pixel, distance):
        """
        Measure gaze error as a visual angle.

        Converts both points to centimetres on the screen and expresses the distance between
        them as the angle they subtend at the participant's eye, which is the standard way
        to report eye-tracking accuracy independently of screen size and seating distance.

        Args:
            gt_pixel (Sequence[float]): Ground-truth target position ``(x, y)`` in pixels.
            es_pixel (Sequence[float]): Estimated gaze position ``(x, y)`` in pixels.
            distance (float): Viewing distance from eye to screen, in centimetres.

        Returns:
            float: Error in degrees of visual angle.
        """

        gt_pixel = self.px_2_cm(gt_pixel)
        es_pixel = self.px_2_cm(es_pixel)
        # Calculate L2 norm between gt_pixel and es_pixel
        l2_norm = math.sqrt((gt_pixel[0] - es_pixel[0]) ** 2 + (gt_pixel[1] - es_pixel[1]) ** 2)

        visual_angle = 2 * math.degrees(math.atan((l2_norm / (2 * distance))))
        return visual_angle

    def px_2_cm(self, pixel_point):
        """
        Convert a screen position from pixels to centimetres.

        Args:
            pixel_point (Sequence[float]): Position ``(x, y)`` in pixels.

        Returns:
            list[float]: Position ``[x, y]`` in centimetres from the top-left corner.
        """
        point = [0, 0]
        point[0] = pixel_point[0] * self.physical_screen_width / self.screen_width
        point[1] = pixel_point[1] * self.physical_screen_height / self.screen_height
        return point

    def calculate_error_by_sliding_window(self, gt_point, es_points, distances):
        """
        Find the best gaze accuracy achieved during a validation target's presentation.

        Slides a 5-sample window across the recorded gaze positions and keeps the window
        with the lowest mean error. Reporting the best window rather than the overall mean
        keeps a blink or a glance away from the target at the start or end of the
        presentation from dominating the reported accuracy.

        Args:
            gt_point (Sequence[float]): Target position ``(x, y)`` in pixels.
            es_points (Sequence[Sequence[float]]): Recorded gaze positions in pixels.
            distances (Sequence[float]): Viewing distance in centimetres for each sample,
                parallel to ``es_points``.

        Returns:
            dict: With keys ``min_error`` (degrees of visual angle, ``inf`` when it cannot
            be computed), ``min_error_es_point`` (the mean gaze position of the best
            window), and ``gt_point`` (the target, echoed back). Fewer than five samples or
            mismatched inputs yield the ``inf`` result rather than raising.
        """

        min_error = float("inf")
        min_error_es_point = (0, 0)
        try:
            error_list = [self.error(gt_pixel=gt_point, es_pixel=es_points[n],
                                     distance=distances[n]) for n in range(len(es_points))]

            for i in range(len(error_list) - 4):
                error = np.mean(error_list[i:i + 5])
                if min_error > error:
                    min_error = error
                    min_error_es_point = np.mean(es_points[i:i + 5], axis=0)
            return {"min_error": min_error, "min_error_es_point": min_error_es_point, "gt_point": gt_point
                    }
        except Exception as e:
            logger.debug(f"calculate_error_by_sliding_window could not compute an error: {e}")
            return {"min_error": float("inf"), "min_error_es_point": (0, 0), "gt_point": gt_point}


if __name__ == '__main__':
    config = {
        "model_name": "Pupil.IO AIO",
        "screen_width": 1920,
        "screen_height": 1080,
        "physical_screen_width": 34.13,
        "physical_screen_height": 19.32
    }
    cal = Calculator(**config)
    es = [[1, 2], [2, 3], [4, 5], [5, 6], [7, 8],
          [1, 2], [2, 3], [4, 5], [5, 6], [7, 8],
          [1, 2], [2, 3], [4, 5], [5, 6], [7, 8]]
    gt = [0, 0]
    distans = [57, 56.5, 58.5, 58, 57, 57, 56.5, 58.5, 58, 57, 57, 56.5, 58.5, 58, 57]
    print(cal.calculate_error_by_sliding_window(gt, es, distans))
