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
# This demo shows how to configure the calibration process and set
# the instruction language for the calibration UI using Psychopy.
#
# Supported languages:
# - 'en-US': English (default)
# - 'zh-CN': Simplified Chinese
# - 'zh-HK': Traditional Chinese
# - 'fr-FR': French
# - 'es-ES': Spanish
# - 'jp-JP': Japanese
# - 'ko-KR': Korean

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

# Show face preview during calibration (1 = enable, 0 = disable)
config.face_previewing = 1

# Set the instruction language for the calibration UI
# English (default)
config.instruction_language(lang='en-US')

# Alternative languages (uncomment to use):
# config.instruction_language(lang='zh-CN')  # Simplified Chinese
# config.instruction_language(lang='zh-HK')  # Traditional Chinese
# config.instruction_language(lang='fr-FR')  # French
# config.instruction_language(lang='es-ES')  # Spanish
# config.instruction_language(lang='jp-JP')  # Japanese
# config.instruction_language(lang='ko-KR')  # Korean

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

# Initialize the tracker with custom configuration
pupil_io = Pupilio(config)

# Open a Psychopy Window
scn_width, scn_height = (1920, 1080)
win = visual.Window((scn_width, scn_height), fullscr=True, units='pix')

# Create a task session
# Session name must contain only letters, digits, underscores, hyphens, plus signs, or parentheses
# Spaces are not allowed - replace with underscores if needed
pupil_io.create_session(session_name="language_demo")

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
pupil_io.save_data(os.path.join(data_dir, "language_demo.csv"))

# Release tracker resources and quit Psychopy
pupil_io.release()
core.quit()
print("Done.")
