# Pupilio SDK Update Log

## Version 1.4.0 (Build 1) - 2025-12-03

- Fix bugs.
- Add a new function `estimate_gaze`.

## Version 1.3.2 (Build 1) - 2025-10-08

- Add fixation detection feature (I-DT).


## Version 1.3.1 (Build 1) - 2025-09-23

- Updated the DLL to support gaze simulation mode using the mouse, allowing you to debug your program on any Windows PC.

## Version 1.3.0 (Build 1) - 2025-06-29

- Updated the DLL to better support single/bino eye-tracking.
- Update the calibration graphics (Pygame and Psychopy) to support single/bino eye gaze tracking.
- Output the estimated optical axes before calibration.

## Version 1.2.8 (Build 1) - 2025-06-23

- Fix `invalid destination position for blit` error in Line 630 of `graphics_pygame.py`.
- Support single eye gaze tracking.
- Adjust the output of optical axes.

## Version 1.2.7 (Build 1) - 2025-04-15

- Minor bug: fix `pupil_io_get_current_gaze` function.

## Version 1.2.6 (Build 1) - 2025-03-30

- Improve UI.

## Version 1.2.5 (Build 1) - 2025-02-11

- Fix native library bugs.

## Version 1.2.4 (Build 1) - 2025-01-07

- Fixed a potential crash bug in pygame calibration.
- Fixed an issue with the `CalibrationListener` callback.
- Improved the calibration UI.

## Version 1.2.3 (Build 1) - 2024-12-12

- Added `enable_kappa_verify`, `enable_debug`, and `log_dir` to `DefaultConfig`.
- Updated `previewer_demo` and renamed the old version to `previewer_demo_legacy.py`.
- Reduced native library calibration time.
- Added preview images to calibration UI.
- Improve UX design of demonstrations.
- Added five calibration mode in `graphics.py` and `graphics_pygame.py`.
- Added `_et_native_lib.pupil_io_set_cali_mode` function signature.
- Updated `docs`.
- Added previewer function on calibration.
- Added multiple international language.
- Added calibration callbacks
- Update default config

---

## Version 1.2.1 (Build 1) - 2024-12-08

- Fixed video playback stuttering caused by the OpenCV library.
- Fixed minor issues with `PupilioET`.
- Added configuration for Pupilio (major update).
- Removed `msvcp120.dll`, `msvcr120.dll`.
- Added three demos: preview demo, custom configuration demo, and previewer demo.
- Fix a bug when user calls `save_data` function passing a file name without directory.
- Improve calibration UI

---

## Version 1.2.0 (Build 1) - 2024-11-22

- Added support for filter parameter: look_ahead.
- Fixed issues with saving to paths containing Chinese characters.
- Resolved UI problems in PsychoPy calibration.
- Native library compiled statically with MSVC.
- The valid field is set to -1 when no face is detected.
- Simplified the DLL environment.
- Added support for the PsychoPy GUI interface.
- Added a timestamp to the session name to serve as a unique session ID.
- Prepare to add a config for controlling the behavior of the eye tracker.
- More precision trigger sender.
- Add LICENSE file.

---

## Version 1.1.7 (Build 1) - 2024-11-15

- Fix recalibration issues.
- Improve the calibration UI.

---

## Version 1.1.6 (Build 1) - 2024-11-08

- Resolve a bug causing Python processes to hang indefinitely.
- Fix an issue where temporary sampling files may not fully write to disk, remaining in the buffer.

---

## Version 1.1.4 (Build 1) - 2024-11-04

- Add create session name checking. The session name must contain only letters, digits or underscores without any special characters.
- Delete resource deep gaze icon.
- Update libfilter.dll with MSVC_RUNTIME_LIBRARY.
- Delete /example/run_demo.bat. Add example/picture_free_viewing/run_demo_psychopy.bat, and 
example/picture_free_viewing/run_demo_pygame.bat.
- Integrating dll files needed

---

## Version 1.1.3 (Build 1) - 2024-11-02

- Calibration_draw function logic modify.
- Calibration PsychoPy components set units `pix`.
- Press R to recalibrate.
- Deleting pygame.init in graphics.py, this may cause minimizing pygame screen.

---

## Version 1.1.2 (Build 1) - 2024-10-28

- Rewrite some features using c++
- Support PyGame and PsychoPy
- Removing some useless py files
- Update example code

---

## Version 1.1.1 (Build 3) - 2024-10-26

- Added `build` number mechanism using timestamp.
- Added `bino_eye_gaze_position`.
- Added heuristic filter.
- Added image previewer.
- 

---

## Version 1.1.0 - 2024-09

- Introduced support for multiple libraries (`lib/*.dll`) in package data.
- Added dependencies: `numpy`, `pygame`, `websockets`.
- Fixed missing files in `lib` directory during packaging.
- Resolved compatibility issues with Python 3.8+.

---

