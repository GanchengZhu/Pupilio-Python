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
# This demo shows how to configure the calibration process

# Author: GC Zhu
# Email: zhugc2016@gmail.com

import copy
import logging
import math
import threading  # Importing the threading module for creating locks
from collections import deque
from enum import Enum, unique
from enum import IntEnum

import numpy as np


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
    """Enum representing return codes from the eye tracker"""
    ET_SUCCESS = 0  # Successful, can proceed to the next scenario
    ET_CALI_CONTINUE = 1  # Calibration ongoing, continue with current calibration point
    ET_CALI_NEXT_POINT = 2  # Calibration ongoing, switch to next calibration point
    ET_INVALID_PATH = 3
    ET_INVALID_PARAM = 4
    ET_FAILED = 9  # Operation failed
    ET_EXCEPTION = 10


class CalibrationMode(IntEnum):
    """Enum representing calibration modes"""
    TWO_POINTS = 2
    FIVE_POINTS = 5


class ActiveEye(IntEnum):
    """Tracking left eye, right eye or both"""
    LEFT_EYE = -1
    RIGHT_EYE = 1
    BINO_EYE = 0


class TriggerHandler:
    def __init__(self):
        """
        Initializes the MarkerHandle class.
        - self.trigger: Holds the current trigger value (initially None). The trigger value is less
            than 256 and larger than 0. 0 is default value and user can set the trigger as 0.
        - self.triggerUpdated: Flag to indicate if the trigger has been updated (initially False).
        - self.lock: A lock object for ensuring thread safety.
        """
        self.trigger: int = 0
        self.triggerUpdated = False
        self.lock = threading.Lock()  # Create a lock object for thread safety

    def set(self, trigger: int):
        """
        Method to set the marker value.
        :param trigger: The new marker value to be set.
        """
        with self.lock:  # Acquire the lock to ensure thread safety
            logging.info("send trigger to eye tracker with the value {}".format(trigger))
            self.trigger = trigger  # Update the marker with the provided value
            if self.triggerUpdated:
                logging.warning("trigger already exists, don't send trigger frequently")
            else:
                self.triggerUpdated = True  # Set the flag to indicate that the marker has been updated

    def get(self):
        """
        Method to get the current marker value.
        :return: The current marker value or -1 if the marker is not updated.
        """
        with self.lock:  # Acquire the lock to ensure thread safety
            if self.triggerUpdated:  # Check if the marker has been updated
                self.triggerUpdated = False  # Reset the flag after reading the marker value
                logging.info("retrieve trigger with the value {}".format(self.trigger))
                return self.trigger  # Return the current marker value
            else:
                return 0  # Return 0 if the marker is not updated since the last read


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
        Calculate the error between ground truth pixel and estimated pixel.

        :param gt_pixel: Ground truth pixel value.
        :param es_pixel: Estimated pixel value.
        :param distance: Distance between the pixels.
        :return: Error value calculated based on the provided formula.
        """

        gt_pixel = self.px_2_cm(gt_pixel)
        es_pixel = self.px_2_cm(es_pixel)
        # Calculate L2 norm between gt_pixel and es_pixel
        l2_norm = math.sqrt((gt_pixel[0] - es_pixel[0]) ** 2 + (gt_pixel[1] - es_pixel[1]) ** 2)

        visual_angle = 2 * math.degrees(math.atan((l2_norm / (2 * distance))))
        return visual_angle

    def px_2_cm(self, pixel_point):
        point = [0, 0]
        point[0] = pixel_point[0] * self.physical_screen_width / self.screen_width
        point[1] = pixel_point[1] * self.physical_screen_height / self.screen_height
        return point

    """
     if (null == errorList || errorList.size() < 5) {
                continue;
            } else {
                for (int j = 0; j < errorList.size() - 4; j++) {
                    float error = (errorList.get(j) + errorList.get(j + 1) + errorList.get(j + 2)
                            + errorList.get(j + 3) + errorList.get(j + 4)) / 5;
                    if (minError > error) {
                        minError = error;
                        Log.i(TAG, "update min error");
                    }
                }
            }
    """

    def calculate_error_by_sliding_window(self, gt_point, es_points, distances):
        """
        Calculate the error between ground truth pixel and estimated pixel.
        :param gt_point: Ground truth pixel value.
        :param es_points: Points of estimated pixel value, array-like.
        :param distances: Distance list between the pixels.

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
            print(f"[Error] calculate_error_by_sliding_window: {e}")
            return {"min_error": float("inf"), "min_error_es_point": (0, 0), "gt_point": gt_point}

class Queue:
    def __init__(self, cache_size=2):
        self._cache_size = cache_size
        self.items = deque(maxlen=cache_size)

    def __getitem__(self, idx):
        if isinstance(idx, slice):
            new_queue = copy.deepcopy(self)
            new_queue.items = list(new_queue.items)[idx]
            return new_queue
        else:
            return self.items[idx]

    def empty(self):
        return len(self.items) == 0

    def enqueue(self, item):
        self.items.append(item)

    def dequeue(self):
        if not self.empty():
            return self.items.popleft()
        else:
            raise IndexError("dequeue from empty queue")

    def size(self):
        return len(self.items)

    def peek(self):
        if not self.empty():
            return self.items[0]
        else:
            raise IndexError("peek from empty queue")

    def tail(self):
        if not self.empty():
            return self.items[-1]
        else:
            raise IndexError("peek from empty queue")

    def full(self):
        return len(self.items) == self._cache_size

    def __str__(self):
        return '[' + ', '.join(map(str, self.items)) + ']'


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
