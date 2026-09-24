# -*- coding: utf-8 -*-
# Author: GC Zhu
# Email: zhugc2016@gmail.com
import pygame

import pupilio

# Set your custom config.
config = pupilio.DefaultConfig()
config.look_ahead = 2
config.cali_mode = pupilio.CalibrationMode.TWO_POINTS

# Calibration modes, the following usage methods are all correct (cali_mode = 0, 2, 4, 5)
# config.cali_mode = 0  # skip calibration
# config.cali_mode = pupilio.CalibrationMode.NO_CALI
# config.cali_mode = 5
# config.cali_mode = pupilio.CalibrationMode.FIVE_POINTS
config.cali_mode = 5

config.cali_target_img = "cute_duck.png"
config.cali_target_beep = "duck_beep.wav"

pupil_io = pupilio.Pupilio(config)

# Create a task session and set a session name.
# If the session name contains spaces,
# it is recommended to replace them with underscores ('_').
pupil_io.create_session(session_name="quick_start")

# Calibration and validation (recommended).
# Set 'validate' to True to verify the calibration results.
pupil_io.calibration_draw(validate=True)

# Start retrieving gaze data.
pupil_io.start_sampling()

# Show a message for 5 seconds while recording.
# Eye tracking sampling runs on a background thread.
font = pygame.font.Font(None, 48)
text = font.render("Recording, exiting in 5 seconds", True, (255, 255, 255))
screen = pygame.display.get_surface()
if screen is None:
    screen = pygame.display.set_mode((800, 600))
screen.fill((0, 0, 0))
screen.blit(text, (100, 250))
pygame.display.flip()
pygame.time.wait(5 * 1000)

# Stop eye tracking sampling.
pupil_io.stop_sampling()

# Wait 100 ms to allow the final samples to be captured.
pygame.time.wait(100)

# Save eye movement data.
pupil_io.save_data("eye_movement.csv")

# Release the tracker instance.
# Clean up Pupilio resources.
pupil_io.release()

# Quit pygame.
pygame.quit()