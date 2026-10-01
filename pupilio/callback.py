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
# Last updated: 2026/10/01 by Zhiguo Wang

__all__ = ["CalibrationListener"]

class CalibrationListener:
    """
    Hook interface for events raised during a calibration / validation run.

    Subclass and assign an instance to ``config.calibration_listener`` to receive
    notifications when targets are presented. Every method is a no-op by default, so
    subclasses only need to override the hooks they actually care about.

    The built-in UI currently fires :meth:`on_calibration_target_onset`. The
    validation hook is part of the public surface and reserved for tooling that drives
    its own validation loop; it is not invoked by the shipped calibration UI.
    """

    def on_calibration_target_onset(self, point_index: int) -> None:
        """
        Called when a calibration target is presented on the screen.

        Invoked once per target, immediately after the UI advances to it. Override to
        log, timestamp, or trigger a stimulus-locked event.

        Args:
            point_index (int): Zero-based index of the current calibration target.
        """
        # Intentionally a no-op; subclasses override.

    def on_validation_target_onset(self, point_index: int) -> None:
        """
        Called when a validation target is presented on the screen.

        Reserved for tooling that drives its own validation loop. The shipped
        calibration UI does **not** currently fire this hook — overriding it is safe
        but will not receive events from the default validation pass.

        Args:
            point_index (int): Zero-based index of the current validation target.
        """
        # Intentionally a no-op; subclasses override.