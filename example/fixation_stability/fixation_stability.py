#!/usr/bin/env python
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
# Neither name of Hangzhou Deep Gaze Sci & Tech Ltd nor the name of
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
# Demonstration of the estimate_gaze() method, showing left and right eye
# gaze cursors separately with L and R labels.
#
# Cursor design:
#   - Left  eye: hollow red  circle, labelled "L"
#   - Right eye: hollow blue circle, labelled "R"
# Each cursor is drawn only when that eye reports a valid, finite sample
# within screen bounds.
#
# Author: Gancheng Zhu
# Last updated: 6/21/2026 by Zhiguo Wang

import os
import math
import pygame
from pygame.locals import FULLSCREEN, HWSURFACE, QUIT, KEYDOWN, K_ESCAPE, K_q

from pupilio import Pupilio, DefaultConfig
from pupilio.misc import ActiveEye

# Display dimensions (standard 1920x1080 fullscreen)
SCREEN_WIDTH, SCREEN_HEIGHT = (1920, 1080)
BACKGROUND_COLOR = (128, 128, 128)  # Gray background

# Visual parameters for the fixation cross
CROSS_SIZE = 20
CROSS_LINE_WIDTH = 7
CROSS_COLOR = (0, 255, 0)

# Gaze cursor settings
GAZE_CURSOR_RADIUS = 50
GAZE_CURSOR_LINE_WIDTH = 5
LABEL_FONT_SIZE = 32
LEFT_EYE_COLOR = (255, 0, 0)    # red
RIGHT_EYE_COLOR = (0, 0, 255)   # blue
LABEL_COLOR = (255, 255, 255)   # white

# Initialize Pygame and create a fullscreen window
pygame.init()
win = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), FULLSCREEN | HWSURFACE)
pygame.mouse.set_visible(False)  # Hide the system mouse cursor

# Font for the L / R labels, created once and reused every frame
label_font = pygame.font.SysFont('Arial', LABEL_FONT_SIZE, bold=True)

# Configure the eye tracker
config = DefaultConfig()
config.face_previewing = 1                      # show face image during calibration
config.look_ahead = 4                           # heuristic filter: 4 flanking samples
config.sampling_rate = 400                      # acquisition rate in Hz
config.cali_mode = 2                            # 2-point calibration (quickest)
config.active_eye = ActiveEye.BINO_EYE          # binocular; see pupilio.misc.ActiveEye
config.simulation_mode = 0                      # 0 = real hardware, 1 = simulate

# Initialize the tracker object
pupil_io = Pupilio(config)

# Create a session (name must contain only letters, digits, underscores)
pupil_io.create_session(session_name="estimate_gaze_demo")

# Perform calibration and validation (required before gaze data can be used)
pupil_io.calibration_draw(validate=True, hands_free=False, screen=win)

# Start streaming gaze data from the tracker
pupil_io.start_sampling()
pygame.time.wait(100)  # allow the data buffer to fill


def get_gaze_data():
    """
    Get comprehensive gaze data using the estimate_gaze() method.

    This provides much more information than get_current_gaze():
    - Separate gaze positions for left eye, right eye, and binocular average
    - Pupil diameter in mm for each eye
    - 3D pupil position (x, y, z) for each eye
    - Visual angle in spherical coordinates (theta, phi) for each eye
    - Visual angle in vector form (x, y, z) for each eye
    - Pixels per degree (x, y) for each eye
    - Validity flag (0=invalid, 1=valid) for each eye
    - Timestamp in milliseconds

    Returns:
        tuple: (status, left_eye, right_eye, bino_eye, timestamp, trigger)

        status: ET_ReturnCode (0 = ET_SUCCESS, 1 = ET_FAILED)

        left_eye and right_eye: numpy arrays of 14 elements
        [0]  = gaze position x (0-1920)
        [1]  = gaze position y (0-1080)
        [2]  = pupil diameter in mm (0-10)
        [3]  = 3D pupil position x
        [4]  = 3D pupil position y
        [5]  = 3D pupil position z
        [6]  = visual angle spherical: theta
        [7]  = visual angle spherical: phi
        [8]  = visual angle vector: x
        [9]  = visual angle vector: y
        [10] = visual angle vector: z
        [11] = pixels per degree x
        [12] = pixels per degree y
        [13] = validity (0=invalid, 1=valid)

        bino_eye: numpy array of 10 elements
        [0]   = binocular gaze position x (0-1920)
        [1]   = binocular gaze position y (0-1080)
        [2-9] = currently unused

        timestamp: time in milliseconds
        trigger: trigger value (0 if none)
    """
    status, left_eye, right_eye, bino_eye, timestamp, trigger = pupil_io.estimate_gaze()
    return status, left_eye, right_eye, bino_eye, timestamp, trigger


def draw_fixation_cross():
    """
    Draw a green fixation cross at the center of the screen.
    The cross serves as the visual anchor for fixation tasks.
    """
    cx, cy = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
    # Horizontal line
    pygame.draw.line(win, CROSS_COLOR,
                     (cx - CROSS_SIZE, cy), (cx + CROSS_SIZE, cy),
                     CROSS_LINE_WIDTH)
    # Vertical line
    pygame.draw.line(win, CROSS_COLOR,
                     (cx, cy - CROSS_SIZE), (cx, cy + CROSS_SIZE),
                     CROSS_LINE_WIDTH)


def _draw_eye_cursor(x, y, color, label_text):
    """Draw one hollow gaze cursor with its letter label centred inside."""
    pos = (int(x), int(y))
    pygame.draw.circle(win, color, pos, GAZE_CURSOR_RADIUS, GAZE_CURSOR_LINE_WIDTH)
    label = label_font.render(label_text, True, LABEL_COLOR)
    win.blit(label, label.get_rect(center=pos))


def draw_gaze_cursors():
    """
    Draw separate gaze cursors for left and right eyes using estimate_gaze().

    Left eye gaze is shown as a red circle with "L" label.
    Right eye gaze is shown as a blue circle with "R" label.

    Each cursor is only drawn if:
    1. The gaze estimation was successful (status == ET_SUCCESS)
    2. The eye's validity flag is 1 (valid gaze)
    3. The gaze coordinates are finite (not inf or nan)
    4. The gaze coordinates are within screen bounds
    """
    # Get the latest gaze data from the tracker
    status, left_eye, right_eye, bino_eye, timestamp, trigger = get_gaze_data()

    # If gaze estimation failed, skip drawing this frame
    if status != 0:  # ET_ReturnCode.ET_SUCCESS
        return

    # Draw left eye gaze cursor (red). left_eye[13] is the validity flag.
    gx, gy = left_eye[0], left_eye[1]
    if (left_eye[13] == 1
            and math.isfinite(gx) and math.isfinite(gy)
            and 0 <= gx <= SCREEN_WIDTH and 0 <= gy <= SCREEN_HEIGHT):
        _draw_eye_cursor(gx, gy, LEFT_EYE_COLOR, "L")

    # Draw right eye gaze cursor (blue). right_eye[13] is the validity flag.
    gx, gy = right_eye[0], right_eye[1]
    if (right_eye[13] == 1
            and math.isfinite(gx) and math.isfinite(gy)
            and 0 <= gx <= SCREEN_WIDTH and 0 <= gy <= SCREEN_HEIGHT):
        _draw_eye_cursor(gx, gy, RIGHT_EYE_COLOR, "R")


# ---- Main loop: run until the user quits ----
running = True
while running:
    # Process all pending Pygame events
    for event in pygame.event.get():
        if event.type == QUIT:
            running = False
        elif event.type == KEYDOWN and event.key in (K_ESCAPE, K_q):
            running = False

    # Redraw the display
    win.fill(BACKGROUND_COLOR)  # clear the screen
    draw_fixation_cross()       # draw the fixation target
    draw_gaze_cursors()         # draw the gaze cursors via estimate_gaze()
    pygame.display.flip()       # update the display

# ---- Clean up and save data ----
pygame.time.wait(100)  # allow time for final samples
pupil_io.stop_sampling()

# Save the recorded data to a CSV file
data_dir = "./data"
os.makedirs(data_dir, exist_ok=True)
pupil_io.save_data(os.path.join(data_dir, "estimate_gaze_demo.csv"))

# Release tracker resources and quit Pygame
pupil_io.release()
pygame.quit()

