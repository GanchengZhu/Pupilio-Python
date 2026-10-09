#!/usr/bin/env python

# Copyright (c) 2026, Hangzhou DeepGaze Science and Technology Co., Ltd
# All Rights Reserved
#
# For use by Hangzhou Deep Gaze Science and Technology Co., Ltd customers
# only. Redistribution and use in source and binary forms, with or without
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
# Quick-start demo of the Pupilio Python SDK with Pygame.
#
# Connect to the tracker, calibrate, and run a free-viewing task with a
# real-time gaze cursor overlaid on each image:
#   - Left  eye: hollow blue  circle, labelled "L"
#   - Right eye: hollow green circle, labelled "R"
# Each cursor is drawn only when that eye reports a valid, finite sample.
#
# Author: Gancheng Zhu
# Last updated: 6/20/2026 by Zhiguo Wang

# Load libraries
import os
import math
import pygame
from pygame.locals import FULLSCREEN, HWSURFACE, KEYDOWN, K_RETURN, K_ESCAPE

from pupilio import Pupilio, DefaultConfig

# ---- Initialize Pygame and create a full-screen window ----
pygame.init()
scn_width, scn_height = (1920, 1080)
win = pygame.display.set_mode((scn_width, scn_height), FULLSCREEN | HWSURFACE)

# Font used for the "L" and "R" labels drawn inside the gaze cursors
font = pygame.font.SysFont("Arial", 48, bold=True)

# ---- Configure the eye tracker ----
config = DefaultConfig()
config.face_previewing = 1          # show face preview during calibration
config.look_ahead = 4               # heuristic filter (4 flanking samples)
config.sampling_rate = 200          # 200 Hz (falls back to 200 on 200 Hz models)
config.cali_mode = 9                # 5-point calibration
config.simulation_mode = 0          # 0 = hardware, 1 = simulation on any PC

# ---- Instantiate tracker and create a session ----
pupil_io = Pupilio(config)
pupil_io.create_session(session_name="deepgaze_demo")

# ---- Calibrate ----
pupil_io.calibration_draw(validate=False, hands_free=False, screen=win)

# ---- Start retrieving gaze data ----
pupil_io.start_sampling()
pygame.time.wait(100)  # let the tracker produce a few samples first

# ---- Free-viewing task with real-time gaze cursor ----
img_folder = "images"
images = ["gray_grid.jpg", "west_lake.jpg", "old_town.jpg"]

for _img in images:
    # load the image, converting to the display pixel format once so each
    # per-frame blit below is a fast memory copy rather than a conversion
    im = pygame.image.load(os.path.join(img_folder, _img)).convert()

    # show the image on screen
    win.fill((128, 128, 128))
    win.blit(im, (0, 0))
    pygame.display.flip()
    # send a trigger to mark picture onset in the eye movement data
    pupil_io.set_trigger(202)

    # ---- Gaze cursor loop: press ENTER or ESC to advance ----
    got_key = False
    max_duration = 100_000          # 100 s safety cap per image (ms)
    t_start = pygame.time.get_ticks()
    pygame.event.clear()            # drop stale events from the previous image

    # last known cursor positions; -65536 keeps them off-screen until the
    # first valid sample for each eye arrives
    lx, ly = -65536, -65536
    rx, ry = -65536, -65536

    while not (got_key or (pygame.time.get_ticks() - t_start) >= max_duration):

        # get_current_gaze() returns (left, right, bino). Each eye is a
        # (status, x, y) tuple, where status == 1 means the sample is valid.
        # The binocular tuple is unused by this demo.
        left, right, _bino = pupil_io.get_current_gaze()

        # ---- unpack left eye ----
        l_status, lx_new, ly_new = left
        has_left_valid = (l_status == 1 and math.isfinite(lx_new) and math.isfinite(ly_new))
        if has_left_valid:
            lx, ly = int(lx_new), int(ly_new)

        # ---- unpack right eye ----
        r_status, rx_new, ry_new = right
        has_right_valid = (r_status == 1 and math.isfinite(rx_new) and math.isfinite(ry_new))
        if has_right_valid:
            rx, ry = int(rx_new), int(ry_new)

        # check key presses
        for ev in pygame.event.get():
            if ev.type == KEYDOWN and ev.key in (K_RETURN, K_ESCAPE):
                got_key = True

        # redraw the image to erase the previous frame's cursors
        win.blit(im, (0, 0))

        # left eye cursor: hollow blue circle labelled "L"
        if has_left_valid:
            pygame.draw.circle(win, (0, 0, 255), (lx, ly), 55, 5)
            l_label = font.render("L", True, (0, 0, 255))
            win.blit(l_label, l_label.get_rect(center=(lx, ly)))

        # right eye cursor: hollow green circle labelled "R"
        if has_right_valid:
            pygame.draw.circle(win, (0, 255, 0), (rx, ry), 55, 5)
            r_label = font.render("R", True, (0, 255, 0))
            win.blit(r_label, r_label.get_rect(center=(rx, ry)))

        pygame.display.flip()

# ---- Stop sampling and save data ----
pygame.time.wait(100)  # capture trailing samples
pupil_io.stop_sampling()

data_dir = "data"
if not os.path.exists(data_dir):
    os.makedirs(data_dir)
pupil_io.save_data(os.path.join(data_dir, "deepgaze_demo.csv"))

# ---- Clean up ----
pupil_io.release()
pygame.quit()