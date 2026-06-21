# _*_ coding: utf-8 _*_

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
# Quick start script demonstrating basic eye tracking functionality using Psychopy.
# This script shows how to:
# 1. Configure the eye tracker with custom settings
# 2. Perform calibration
# 3. Record gaze data for a fixed duration
# 4. Save the recorded data to a file

# Author: Gancheng Zhu
# Email: zhugc2016@gmail.com
# Last updated: 6/21/2026 by Zhiguo Wang

import os
from psychopy import visual, core
from pupilio import Pupilio, DefaultConfig
from pupilio.misc import CalibrationMode

# Configure the eye tracker
# A custom config file allows fine control over tracker parameters
config = DefaultConfig()

# Heuristic filter: recommended look_ahead = 2
# A noisy spike is determined by 4 flanking samples
config.look_ahead = 2

# Kappa angle verification after calibration
# Set to 0 ONLY for strabismus patients (disables verification)
config.enable_kappa_verification = 1

# Active eye selection:
# 0 = binocular (both eyes), -1 = left eye only, 1 = right eye only
config.active_eye = 0

# Set the API to run in gaze simulation mode
# 0 = use real hardware, 1 = simulate with mouse (useful for testing without hardware)
config.simulation_mode = 0

# Calibration mode: 2-point vs. 5-point
# Both integer values and enum constants are supported:
# config.cali_mode = CalibrationMode.TWO_POINTS
# config.cali_mode = CalibrationMode.FIVE_POINTS
# config.cali_mode = 2  (two-point)
# config.cali_mode = 5  (five-point)
config.cali_mode = 2

# Show face preview during calibration (1 = enable, 0 = disable)
config.face_previewing = 1

# Custom calibration target image and beep sound
# These override the default assets in the pupilio library
config.cali_target_img = "cute_duck.png"
config.cali_target_beep = "duck_beep.wav"

# Calibration target animation parameters
# The target image zooms in and out during calibration
config.cali_target_img_maximum_size = 120  # Maximum size in pixels
config.cali_target_img_minimum_size = 60   # Minimum size in pixels

# Face images for head position feedback during calibration
# These cartoon faces help users adjust their head position
# Recommended size: 128 x 128 pixels
config.cali_smiling_face_img = "cute_duck.png"
config.cali_frowning_face_img = "cute_duck.png"

# Initialize the tracker
pupil_io = Pupilio(config)

# Open a Psychopy Window
scn_width, scn_height = (1920, 1080)
win = visual.Window((scn_width, scn_height), fullscr=True, units='pix')

# Create a task session
# Session name must contain only letters, digits, underscores, hyphens, plus signs, or parentheses
# Spaces are not allowed - replace with underscores if needed
pupil_io.create_session(session_name="quick_start")

# Perform calibration and validation
# validate=True verifies calibration results after completion
pupil_io.calibration_draw(screen=win, validate=True, hands_free=False)

# Start streaming gaze data from the tracker
pupil_io.start_sampling()

# Display a message on screen and record data for 5 seconds
msg = 'Recording... Script will terminate in 5 seconds.'
txt = visual.TextStim(win, msg, height=32, color=(-1, -1, -1))
txt.draw()
win.flip()
core.wait(5.0)  # Wait for 5 seconds

# Stop eye tracking sampling
pupil_io.stop_sampling()

# Allow time to capture ending samples
core.wait(0.1)

# Save the recorded eye movement data to a file
data_dir = "./data"
os.makedirs(data_dir, exist_ok=True)
pupil_io.save_data(os.path.join(data_dir, "quick_start.csv"))

# Release tracker resources and quit Psychopy
pupil_io.release()
core.quit()
print("Done.")
