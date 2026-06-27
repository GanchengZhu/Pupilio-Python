#!/usr/bin/env python

# Copyright (c) 2026, Hangzhou DeepGaze Science and Technology Co., Ltd
# All Rights Reserved
#
# For use by  Hangzhou Deep Gaze Science and Technology Co., Ltd customers
# only. Redistribution and use in source and binary forms, with or without
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
# This is a demo showing how to use deep gaze pythonic library
# In this script, we connect to the tracker, perform a calibration,
# validate the calibration results, then we subscribe to the sample data
# stream, with which we constantly update the position of a gaze cursor

# Author: Gancheng Zhu
# Last updated: 6/20/2026 by Zhiguo Wang

# Load libraries
import os
import math
import pygame
from pygame.locals import *
from pupilio import Pupilio, DefaultConfig
from pupilio.misc import ActiveEye, CalibrationMode

# ---- Initialize Pygame and create a full-screen window ----
# use the Pygame library for graphics, first init pygame and open a full screen window
pygame.init()
scn_width, scn_height = (1920, 1080)
win = pygame.display.set_mode((scn_width, scn_height), FULLSCREEN | HWSURFACE)

# ---- Configure the eye tracker ----
# use a custom config file to control the tracker
config = DefaultConfig()

# If previewing the face image during calibration
config.face_previewing = 1

# Heuristic filter, recommended look_ahead = 2 (i.e., a noisy spike is determined by
# 4 flanking samples)
config.look_ahead = 1

# Set the sampling rate (for models that support 400/800/1000 Hz),
# on the 200 Hz model, sampling rate will fall back to 200 Hz
config.sampling_rate = 400

# Set the calibration mode (2-point, 4-point, 5-point)
config.cali_mode = 2
# alternatively, use the constants defined in .misc
# config.cali_mode = CalibrationMode.FOUR_POINTS

# Run the script in gaze simulation mode, i.e., any Windows computer; here we set it to 0
config.simulation_mode = 0

# ---- Instantiate tracker object and create a session ----
# instantiate a tracker object
pupil_io = Pupilio(config)

# create a task session, and set a session name
# The session name must contain only letters, digits or underscores without any special characters.
pupil_io.create_session(session_name="deepgaze_demo")

# ---- Calibrate and validate ----
# set 'validate' to True if you would like to verify the calibration results
pupil_io.calibration_draw(validate=False, hands_free=False, screen=win)

# ---- Start retrieving gaze data ----
# start retrieving gaze
pupil_io.start_sampling()
pygame.time.wait(100)  # sleep for 100 ms so the tracker cache some sample

# ---- Display images with real-time gaze cursor ----
# A free viewing task, in which we show a picture and overlay the gaze cursor
img_folder = 'images'
images = ['gray_grid.jpg', 'west_lake.jpg', 'old_town.jpg']

# show the images one by one in a loop, press a ENTER key to exit the program
for _img in images:
    # show the image on screen
    win.fill((128, 128, 128))
    im = pygame.image.load(os.path.join(img_folder, _img))
    win.blit(im, (0, 0))
    pygame.display.flip()
    # send a trigger to record in the eye movement data to mark picture onset
    pupil_io.set_trigger(202)

    # now lets show the gaze cursor, press any key to close the window
    got_key = False
    max_duration = 10000
    t_start = pygame.time.get_ticks()
    pygame.event.clear()  # clear all cached events if there were any
    gx, gy = -65536, -65536
    has_valid_gaze = False  # track whether we have received valid gaze data

    while not (got_key or (pygame.time.get_ticks() - t_start) >= max_duration):
        # get the newest gaze position
        left, right, bino = pupil_io.get_current_gaze()
        if pupil_io.config.active_eye == ActiveEye.BINO_EYE:
            status, gx_new, gy_new = bino
        elif pupil_io.config.active_eye == ActiveEye.LEFT_EYE:
            status, gx_new, gy_new = left
        elif pupil_io.config.active_eye == ActiveEye.RIGHT_EYE:
            status, gx_new, gy_new = right
        else:
            # fallback to binocular if active eye is not set
            status, gx_new, gy_new = bino

        # update the gaze position when got valid gaze position (not inf, not nan)
        # only update if we have a valid sample (status=1) and the values are finite
        if (status == 1 and
                math.isfinite(gx_new) and math.isfinite(gy_new) and
                0 <= gx_new <= scn_width and 0 <= gy_new <= scn_height):
            gx = int(gx_new)
            gy = int(gy_new)
            has_valid_gaze = True

        # check key presses
        for ev in pygame.event.get():
            if ev.type == KEYDOWN:
                if ev.key == K_RETURN:
                    got_key = True
                # if ev.key == K_SPACE:

        # update the visual (image and gaze cursor)
        win.blit(im, (0, 0))
        # only draw the cursor if we have valid gaze data
        if has_valid_gaze:
            pygame.draw.circle(win, (0, 255, 0), (gx, gy), 50, 5)  # cursor for the left eye
        pygame.display.flip()

# ---- Stop sampling and save data ----
# stop sampling
pygame.time.wait(100)  # sleep for 100 ms to capture ending samples
pupil_io.stop_sampling()

# save the sample data to file
data_dir = "./data"
if not os.path.exists(data_dir):
    os.makedirs(data_dir)

file_name = "deepgaze_demo.csv"
pupil_io.save_data(os.path.join(data_dir, file_name))

# ---- Clean up ----
# release the tracker instance
pupil_io.release()

# quit pygame
pygame.quit()
