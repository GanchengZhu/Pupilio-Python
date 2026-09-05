# _*_ coding: utf-8 _*_
# Author: GC Zhu
# Email: zhugc2016@gmail.com
import pygame

import pupilio

# set your custom config
config = pupilio.DefaultConfig()
config.look_ahead = 2
config.cali_mode = pupilio.CalibrationMode.TWO_POINTS
"""
# The following usage methods are both correct, and only these four usage methods are allowed:
config.cali_mode = pupilio.CalibrationMode.TWO_POINTS
config.cali_mode = pupilio.CalibrationMode.FIVE_POINTS
config.cali_mode = 2
config.cali_mode = 5
"""

config.cali_target_img = "cute_duck.png"
config.cali_target_beep = "duck_beep.wav"

pupil_io = pupilio.Pupilio(config)

# create a task session, and set a session name
# If the session name contains spaces,
# it is recommended to replace them with underscores '_'.
pupil_io.create_session(session_name="quick_start")

# calibration and validation (recommended)
# set 'validate' to True if we would like to verify the calibration results
pupil_io.calibration_draw(validate=True)

# start retrieving gaze
pupil_io.start_sampling()

# hang the main thread for 5 seconds by game
# eye tracking sampling are running on the background thread
pygame.time.wait(5 * 1000)

# stop eye tracking sampling
pupil_io.stop_sampling()

# sleep for 100 ms to capture ending samples
pygame.time.wait(100)

# save eye movement data
pupil_io.save_data("eye_movement.csv")

# release the tracker instance
# clean up Pupilio resources
pupil_io.release()

# quit pygame
pygame.quit()
