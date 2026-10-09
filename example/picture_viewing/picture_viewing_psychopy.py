#!/usr/bin/env python

# Copyright (c) 2026, Hangzhou DeepGaze Science and Technology Co., Ltd
# All Rights Reserved
#
# For use by Hangzhou DeepGaze Science and Technology Co., Ltd customers
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
# Quick-start demo of the Pupilio Python SDK with PsychoPy.
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
from psychopy import visual, core, event
from pupilio import Pupilio, DefaultConfig

# Cursor colors in PsychoPy's -1..1 RGB space (same as pygame's blue/green)
CURSOR_BLUE = (-1, -1, 1)    # pygame equivalent: (0, 0, 255)
CURSOR_GREEN = (-1, 1, -1)   # pygame equivalent: (0, 255, 0)

# ---- Initialize PsychoPy and create a full-screen window ----
scn_width, scn_height = (1920, 1080)
win = visual.Window((scn_width, scn_height), fullscr=True, units='pix', color='black')

# ---- Configure the eye tracker ----
config = DefaultConfig()
config.face_previewing = 1          # show face preview during calibration
config.look_ahead = 2               # heuristic filter (4 flanking samples)
config.sampling_rate = 200          # 200 Hz (falls back to 200 on 200 Hz models)
config.cali_mode = 5                # 5-point calibration
config.simulation_mode = 0          # 0 = hardware, 1 = simulation on any PC

# ---- Instantiate tracker and create a session ----
pupil_io = Pupilio(config)
pupil_io.create_session(session_name="deepgaze_demo")

# ---- Calibrate ----
pupil_io.calibration_draw(validate=True, hands_free=False, screen=win)

# ---- Start retrieving gaze data ----
pupil_io.start_sampling()
core.wait(0.1)  # let the tracker produce a few samples first

# ---- Gaze cursor stimuli (created once, repositioned each frame) ----
left_cursor = visual.Circle(win, radius=55, lineColor=CURSOR_BLUE, lineWidth=5, fillColor=None)
right_cursor = visual.Circle(win, radius=55, lineColor=CURSOR_GREEN, lineWidth=5, fillColor=None)
left_label = visual.TextStim(win, text="L", color=CURSOR_BLUE, bold=True, height=48)
right_label = visual.TextStim(win, text="R", color=CURSOR_GREEN, bold=True, height=48)

# ---- Free-viewing task with real-time gaze cursor ----
img_folder = 'images'
images = ['gray_grid.jpg', 'west_lake.jpg', 'old_town.jpg']

for _img in images:
    # show the image on screen
    im = visual.ImageStim(win, image=os.path.join(img_folder, _img))
    im.draw()
    win.flip()
    # send a trigger to mark picture onset in the eye movement data
    pupil_io.set_trigger(202)

    # ---- Gaze cursor loop: press any key to advance ----
    got_key = False
    max_duration = 10.0  # seconds
    t_start = core.getTime()
    event.clearEvents()

    # last known cursor positions; -65536 keeps them off-screen until the
    # first valid sample for each eye arrives
    lx, ly = -65536, -65536
    rx, ry = -65536, -65536

    while not (got_key or (core.getTime() - t_start) >= max_duration):
        # get the newest gaze position for each eye
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

        # check keyboard events
        if event.getKeys():
            got_key = True

        # redraw the image to erase the previous frame's cursors
        im.draw()

        # convert screen pixels to PsychoPy coordinates (center = 0,0; +Y up)
        if has_left_valid:
            left_pos = (lx - scn_width / 2, scn_height / 2 - ly)
            left_cursor.pos = left_pos
            left_cursor.draw()
            left_label.pos = left_pos
            left_label.draw()

        if has_right_valid:
            right_pos = (rx - scn_width / 2, scn_height / 2 - ry)
            right_cursor.pos = right_pos
            right_cursor.draw()
            right_label.pos = right_pos
            right_label.draw()

        win.flip()

# ---- Stop sampling and save data ----
core.wait(0.1)  # capture trailing samples
pupil_io.stop_sampling()

data_dir = "../event_detection/data"
if not os.path.exists(data_dir):
    os.makedirs(data_dir)
pupil_io.save_data(os.path.join(data_dir, "deepgaze_demo.csv"))

# ---- Clean up ----
pupil_io.release()
win.close()
core.quit()