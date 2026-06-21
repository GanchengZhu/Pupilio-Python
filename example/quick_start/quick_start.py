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
# This script shows the most basic commands needed for an eye-tracking task
# It demonstrates: initialization, calibration, data recording, and saving.

# Author: Gancheng Zhu
# Last updated: 6/21/2026 by Zhiguo Wang

# ---- Load libraries ----
import pygame
import os
from pygame.locals import FULLSCREEN, HWSURFACE
from pupilio import Pupilio

# ---- Initialize Pygame and create a full-screen window ----
pygame.init()

# screen size
scn_width, scn_height = (1920, 1080)

# open a window in fullscreen mode
win = pygame.display.set_mode((scn_width, scn_height), FULLSCREEN | HWSURFACE)

# ---- Initialize the tracker and create a session ----
# Initialize the tracker with custom configuration
pupil_io = Pupilio()

# create a task session, and set a session name
# If the session name contains spaces, it is recommended to replace them with underscores '_'.
# The session name must contain only letters, digits or underscores without any special characters.
pupil_io.create_session(session_name="quick_start")

# ---- Calibrate and validate ----
# set 'validate' to True if we would like to verify the calibration results
pupil_io.calibration_draw(validate=True, screen=win)

# ---- Start recording ----
# start retrieving gaze
pupil_io.start_sampling()

# ---- Recording data for 5 seconds ----
# Display a message on screen
msg = 'Recording... Script will terminate in 5 seconds.'
font = pygame.font.SysFont('Arial', 32)
_w, _h = font.size(msg)
txt = font.render(msg, True, (255, 255, 255))
win.fill((128, 128, 128))
win.blit(txt, ((scn_width - _w) // 2, (scn_height - _h) // 2))
pygame.display.flip()

pygame.time.wait(5 * 1000)  # 5 seconds

# ---- Stop recording and save data ----
# stop sampling
pupil_io.stop_sampling()

# sleep for 100 ms to capture ending samples
pygame.time.wait(100)

# save the sample data to file
data_dir = "./data"
os.makedirs(data_dir, exist_ok=True)

file_name = "quick_start.csv"
pupil_io.save_data(os.path.join(data_dir, file_name))

# ---- Clean up ----
# release the tracker
pupil_io.release()

# quit pygame
pygame.quit()
