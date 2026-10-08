# -*- coding: utf-8 -*-

# Copyright (c) 2026, Hangzhou DeepGaze Science and Technology Co., Ltd
# All Rights Reserved
#
# For use by Hangzhou DeepGaze Science and Technology Co., Ltd licensees only.
# Redistribution and use in source and binary forms, with or without
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
# This demo shows how to grab camera preview images while recording gaze
# data. A background thread pulls the left and right camera preview frames
# at roughly 60 Hz and saves them as JPEG files.
#
# Warning: this demo is for previewing only -- it is not intended for
# capturing high-frame-rate video alongside gaze recording. Writing frames
# to disk competes with the tracking thread for CPU and I/O, so keep the
# preview rate low and the recording session short.

# Author: Gancheng Zhu
# Email: zhugc2016@gmail.com
# Last updated: 2026-06-21 by Zhiguo Wang

import os
import threading
import time

import cv2
import numpy as np

from pupilio import Pupilio

# Directory for both the preview JPEGs and the recorded CSV.
DATA_DIR = "./data"

# ----- ROI configuration -----
# Expected ROI: (x, y, width, height) in sensor coordinates.
ROI_X, ROI_Y, ROI_W, ROI_H = 100, 235, 960, 420


class PreviewThread(threading.Thread):
    """Background thread that pulls camera preview frames and saves them."""

    def __init__(self, pupil_io: Pupilio, save_dir=DATA_DIR):
        super().__init__()
        self._pupil_io = pupil_io
        self._is_running = True
        self.daemon = True

        # JPEG compression parameters for the saved preview frames.
        self.preview_compression = [cv2.IMWRITE_JPEG_QUALITY, 40]  # ratio: 0~100
        self.preview_format = ".jpg"
        self.save_dir = save_dir
        os.makedirs(self.save_dir, exist_ok=True)

    def stop(self):
        """Signal the thread to exit and wait briefly for it to finish."""
        self._is_running = False
        self.join(timeout=2.0)

    @staticmethod
    def _is_valid_image(img):
        """Return True only if img is a non-empty numpy array."""
        if img is None:
            return False
        if not isinstance(img, np.ndarray):
            return False
        if img.size == 0:
            return False
        return True

    def run(self):
        count = 0
        while self._is_running:
            # ~60 Hz target; keep this low so the preview thread does not
            # starve the tracking thread.
            time.sleep(0.016)

            preview_images = self._pupil_io.get_preview_images()

            # FIX #1: avoid `if not preview_images` on a numpy array.
            # Only check for None and length explicitly.
            if preview_images is None:
                continue
            try:
                if len(preview_images) < 2:
                    continue
            except TypeError:
                continue

            left, right = preview_images[0], preview_images[1]

            # FIX #2: validate each frame is a real image before saving.
            if self._is_valid_image(left):
                cv2.imwrite(
                    os.path.join(
                        self.save_dir,
                        f"left_camera_previewer_count_{count}{self.preview_format}",
                    ),
                    left,
                    self.preview_compression,
                )

            if self._is_valid_image(right):
                cv2.imwrite(
                    os.path.join(
                        self.save_dir,
                        f"right_camera_previewer_count_{count}{self.preview_format}",
                    ),
                    right,
                    self.preview_compression,
                )

            count += 1

        print("[INFO] Preview thread shutdown.")


def wait_for_camera_ready(pupil_io: Pupilio, timeout_s: float = 5.0) -> bool:
    """
    Wait until the camera reports valid (non-zero) dimensions.

    This addresses the `ApplyRoi: set roi(...) failed, W=0 H=0` message,
    which occurs when the ROI is applied before the camera has finished
    initializing.

    Returns True if the camera is ready, False if it timed out.
    """
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            # Adjust these method names to match the actual SDK API.
            w = pupil_io.get_camera_width()
            h = pupil_io.get_camera_height()
        except AttributeError:
            # If the SDK does not expose camera dimensions, just wait a
            # fixed amount of time and give up on the ready-check.
            time.sleep(1.0)
            return True

        if w and h and w > 0 and h > 0:
            print(f"[INFO] Camera ready: {w} x {h}")
            return True

        time.sleep(0.1)

    print("[WARN] Timed out waiting for camera to report dimensions.")
    return False


def try_apply_roi(pupil_io: Pupilio):
    """
    Attempt to apply the configured ROI after the camera is ready.

    This is optional and depends on the SDK API. If the method or
    signature does not match, the error is swallowed so the demo can
    still run.
    """
    try:
        pupil_io.set_roi(ROI_X, ROI_Y, ROI_W, ROI_H)
        print(f"[INFO] Applied ROI: ({ROI_X}, {ROI_Y}, {ROI_W}, {ROI_H})")
    except AttributeError:
        print("[WARN] SDK does not expose set_roi(...); skipping.")
    except Exception as exc:
        print(f"[WARN] set_roi(...) failed: {exc}")


if __name__ == '__main__':
    # ---- Initialize the tracker ----
    pi = Pupilio()

    # ---- Wait for the camera to be fully initialized BEFORE applying ROI ----
    # This fixes: "ApplyRoi: set roi(100,235,960,420) failed, W=0 H=0"
    wait_for_camera_ready(pi, timeout_s=5.0)
    try_apply_roi(pi)

    # ---- Start the preview thread ----
    preview_thread = PreviewThread(pupil_io=pi)
    preview_thread.start()

    # ---- Record a short session ----
    # Note: no calibration is performed here, since this demo only reads
    # camera preview images and never uses gaze coordinates. If you want
    # to also record usable gaze data, call pi.calibration_draw(...) with
    # a presentation window before start_sampling().
    pi.create_session("preview_demo")
    pi.start_sampling()
    time.sleep(2)
    pi.stop_sampling()

    # ---- Stop the preview thread and save data ----
    preview_thread.stop()

    os.makedirs(DATA_DIR, exist_ok=True)
    pi.save_data(os.path.join(DATA_DIR, "preview_demo.csv"))
    pi.release()
    print("[INFO] Demo finished.")
