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
# A callback listener for calibration manipulation

# Author: GC Zhu
# Email: zhugc2016@gmail.com

class CalibrationListener:
    """
    A listener class to handle events during a calibration process. This class defines
    methods that can be overridden to perform specific actions when calibration or
    validation targets are presented during gaze calibration.

    Attributes:
        None

    Methods:
        __init__(): Initializes the listener instance.
        on_calibration_target_onset(point_index): Called when a calibration target is presented.
        on_validation_target_onset(point_index): Called when a validation target is presented.
    """

    def __init__(self):
        """
        Initializes the CalibrationListener instance.

        This method can be used to set up any initial state or parameters required for the listener.
        By default, it does nothing.
        """
        pass

    def on_calibration_target_onset(self, point_index):
        """
        This method is called when a calibration target is presented on the screen.

        Args:
            point_index (int): The index of the current calibration target. This can be used
            to identify the target's position or other characteristics specific to the calibration
            process.

        This method can be overridden to define actions that should occur when a calibration target
        is shown (e.g., logging, updating UI, or triggering an event).
        """
        pass

    def on_validation_target_onset(self, point_index):
        """
        This method is called when a validation target is presented on the screen.

        Args:
            point_index (int): The index of the current validation target. Similar to the calibration
            target, this can be used to identify the target's position or other properties related to
            the validation process.

        This method can be overridden to define actions that should occur when a validation target
        is shown (e.g., logging, updating UI, or triggering an event).
        """
        pass
