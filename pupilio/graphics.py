# _*_ coding: utf-8 _*_
# Copyright (c) 2024, Hangzhou Deep Gaze Sci & Tech Ltd
# All Rights Reserved
#
# For use by  Hangzhou Deep Gaze Sci & Tech Ltd licencees only.
# Redistribution and use in source and binary forms, with or without
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
# Calibration graphics for psychopy applications

# !/usr/bin/python
# Author: GC Zhu
# Email: zhugc2016@gmail.com

import json
import logging
import math
import os
import random
import time
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
from psychopy import visual, sound, event

from .annotation import deprecated
from .callback import CalibrationListener
from .default_config import DefaultConfig
from .misc import ET_ReturnCode, LocalConfig, Calculator


class CalibrationUI(object):
    def __init__(self, pupil_io, screen):

        # pupil.io tracker object
        self._pupil_io = pupil_io
        # print('Using %s (with %s) for sounds' % (sound.audioLib, sound.audioDriver))

        # constant--fonts
        self._font = "Microsoft YaHei UI Light"
        # self._font = os.path.join(self._current_dir, "asset", "simsun.ttc")

        # constant colors
        self._BLACK = (-1, -1, -1)
        self._RED = (1, -1, -1)
        self._GREEN = (-1, 1, -1)
        self._BLUE = (-1, -1, 1)
        self._WHITE = (1, 1, 1)
        self._CRIMSON = (0.72, 0.16, 0.47)
        self._CORAL = (0.88, 0, 0)
        self._GRAY = (0, 0, 0)

        # error color
        self.error_color = self._RED

        # constant calibration points
        self._calibrationPoint = self._pupil_io.calibration_points

        # initialize a psychopy window
        self._screen = screen
        self._screen_width = 1920
        self._screen_height = 1080
        # self._screen.units = 'pix'

        # initialize previewer parameters
        self._PREVIEWER_IMG_WIDTH = int(512 / 1)
        self._PREVIEWER_IMG_HEIGHT = int(512 / 1)

        self._LEFT_PREVIEWER_POS = [
            self._PREVIEWER_IMG_WIDTH // 2 + 79,
            self._screen_height // 2]
        self._RIGHT_PREVIEWER_POS = [
            self._screen_width - self._PREVIEWER_IMG_WIDTH // 2 - 79,
            self._screen_height // 2]

        # self._screen = visual.Window(
        #     size=(self._screen_width, self._screen_height),
        #     fullscr=True,
        #     color=self._GRAY,
        #     units='pix')

        # headbox to show the relative position of the head
        self._face_in_rect = visual.Rect(self._screen, size=(600, 600), lineWidth=5, units='pix')

        # Text object for instructions
        self._txt = visual.TextStim(
            win=self._screen,
            text='',
            font=self._font,
            height=32,
            color=self._BLACK, units='pix')

        # self._left_previewer_img_stim = visual.ImageStim(
        #     win=self._screen,
        #     image=None,
        #     size=(self._PREVIEWER_IMG_WIDTH, self._PREVIEWER_IMG_HEIGHT),
        #     pos=self._to_psychopy_coords(self._LEFT_PREVIEWER_POS),
        #     colorSpace='rgb',
        #     units='pix'
        # )
        #
        # self._right_previewer_img_stim = visual.ImageStim(
        #     win=self._screen,
        #     image=None,
        #     size=(self._PREVIEWER_IMG_WIDTH, self._PREVIEWER_IMG_HEIGHT),
        #     pos=self._to_psychopy_coords(self._RIGHT_PREVIEWER_POS),
        #     colorSpace='rgb',
        #     units='pix'
        # )

        self._left_previewer_img_stim = visual.GratingStim(
            win=self._screen,
            tex='None',
            mask='None',
            size=(self._PREVIEWER_IMG_WIDTH, self._PREVIEWER_IMG_HEIGHT),
            pos=self._to_psychopy_coords(self._LEFT_PREVIEWER_POS),
            colorSpace='rgb',
            units='pix'
        )

        self._right_previewer_img_stim = visual.GratingStim(
            win=self._screen,
            tex='None',
            mask='None',
            size=(self._PREVIEWER_IMG_WIDTH, self._PREVIEWER_IMG_HEIGHT),
            pos=self._to_psychopy_coords(self._RIGHT_PREVIEWER_POS),
            colorSpace='rgb',
            units='pix'
        )

        self._center_text_stim = visual.TextStim(
            win=self._screen,
            font=self._font,
            height=26,
            pos=(0, 0),
            color=self._BLACK, units='pix')

        self._validation_instruction = visual.TextStim(
            win=self._screen,
            font=self._font,
            height=20,
            pos=(0, 0),
            color=self._BLACK, units='pix')

        self._error_bar = visual.Line(
            win=self._screen,
            start=(0, 0),
            end=(0, 0),
            lineColor=self._BLACK,
            lineWidth=1.0, units='pix')

        self.config: DefaultConfig = self._pupil_io.config

        # constant library path
        self._current_dir = os.path.abspath(os.path.dirname(__file__))

        # audio instructions
        # a beep that goes with the calibration target
        self._sound = sound.Sound(self.config.cali_target_beep)
        # calibration instructions
        self._cali_ins_sound = sound.Sound(
            os.path.join(self._current_dir, "asset", "calibration_instruction.wav"))
        # head position adjustment instructions
        self._just_pos_sound = sound.Sound(
            os.path.join(self._current_dir, "asset", "adjust_position.wav"))
        # play sound times
        self._just_pos_sound_once = False

        # set mouse cursor invisible
        self._mouse = event.Mouse(visible=False)

        # load face image to show head pose
        self._frowning_face = visual.ImageStim(
            win=self._screen, size=(128, 128),
            image=self.config.cali_frowning_face_img, units='pix')

        self._smiling_face = visual.ImageStim(
            win=self._screen, size=(128, 128),
            image=self.config.cali_smiling_face_img, units='pix')

        # clock counter
        self._clock_resource_dict = {}
        self._clock_resource_height = 100
        for n in range(0, 10):
            self._clock_resource_dict[str(n)] = visual.ImageStim(
                win=self._screen,
                image=os.path.join(self._current_dir, "asset", f"figure_{n}.png"), units='pix')
        self._clock_resource_dict['.'] = visual.ImageStim(
            win=self._screen,
            image=os.path.join(self._current_dir, "asset", "dot.png"), units='pix')

        for key in self._clock_resource_dict:
            _img = self._clock_resource_dict[key]
            self._clock_resource_dict[key].size = (
                self._clock_resource_height / (_img.height / _img.width), self._clock_resource_height)

        # load local config
        self._local_config = LocalConfig()

        # initialize a calculator
        self._calculator = Calculator(
            screen_width=self._screen_width,
            screen_height=self._screen_height,
            physical_screen_width=self._local_config.dp_config['physical_screen_width'],
            physical_screen_height=self._local_config.dp_config['physical_screen_height'])

        self._cal_bounds = (0, 0, self._screen_width, self._screen_height)

        # do a quick 5-point validation of the calibration results
        self._validation_points = [
            [0.5, 0.08],
            [0.08, 0.5], [0.92, 0.5],
            [0.5, 0.92]]
        random.shuffle(self._validation_points)
        self._validation_points += [[0.5, 0.5]]

        # validation points coordinates in psychopy screen coordinates (center = [0, 0])
        # for _point in self._validation_points:
        #     _point[0] = int((_point[0] - 0.5) * self._screen_width)
        #     _point[1] = int((_point[1] - 0.5) * self._screen_height)

        self._validation_points = [
            [int((_point[0] - 0.5) * self._screen_width),
             int((_point[1] - 0.5) * self._screen_height)] for _point in self._validation_points]

        # image resource for calibration and validation points
        _max_size, _min_size = (self.config.cali_target_img_maximum_size,
                                self.config.cali_target_img_minimum_size)
        self._animation_size = [
            (_min_size + (_max_size - _min_size) * i / 19, _min_size + (_max_size - _min_size) * i / 19)
            for i in range(20)]
        self._animation_list = []
        for i in range(10):
            _source_image = visual.ImageStim(
                self._screen,
                self.config.cali_target_img, units='pix')
            _source_image.size = self._animation_size[i]
            _source_image.ori = 40 * i * 0
            self._animation_list.append(_source_image)

        # set variables
        self.initialize_variables()

        # animation frequency
        self._animation_frequency = self.config.cali_target_animation_frequency

    def initialize_variables(self):
        """Initialize variables for plotting and visualization."""
        self._phase_adjust_position = True
        self._calibration_preparing = False
        self._validation_preparing = False
        self._phase_calibration = False
        self._phase_validation = False
        self._need_validation = False
        self.graphics_finished = False
        self._exit = False
        self._calibration_drawing_list = [0, 1, 2, 3, 4]
        self._calibration_timer = 0
        self._validation_timer = 0
        self._validation_left_sample_store = [[] for _ in range(len(self._validation_points) + 1)]
        self._validation_right_sample_store = [[] for _ in range(len(self._validation_points) + 1)]
        self._validation_left_eye_distance_store = [[] for _ in range(len(self._validation_points) + 1)]
        self._validation_right_eye_distance_store = [[] for _ in range(len(self._validation_points) + 1)]
        self._n_validation = 0  # n times of validation
        self._error_threshold = 2
        self._calibration_point_index = 0
        self._drawing_validation_result = False
        self._hands_free = False
        self._hands_free_adjust_head_wait_time = 11  # 3
        self._hands_free_adjust_head_start_timestamp = 0
        self._validation_finished_timer = 0

    def _to_psychopy_coords(self, coords):
        """ convert a coords into the psychopy screen coords"""

        return [coords[0] - self._screen_width // 2, self._screen_height // 2 - coords[1]]

    def _to_pygame_coords(self, coords):
        """ convert a coords into the psychopy screen coords"""

        return [coords[0] + self._screen_width // 2, self._screen_height // 2 - coords[1]]

    def _draw_error_line(self, ground_truth_point, estimated_point, error_color):
        """ draw the ground truth position, and the estimated gaze position"""
        # convert to psychopy screen coordinates
        ground_truth_point = self._to_psychopy_coords(ground_truth_point)
        estimated_point = self._to_psychopy_coords(estimated_point)

        # ground truth positoin, represented as a "+"
        self._txt.text = '+'
        self._txt.height = 24
        self._txt.color = self._GREEN
        self._txt.pos = ground_truth_point
        self._txt.draw()

        # estimated gaze position, represented as a "+"
        self._txt.text = '+'
        self._txt.height = 24
        self._txt.pos = estimated_point
        self._txt.color = error_color
        self._txt.draw()

        # error bar
        self._error_bar.start = ground_truth_point
        self._error_bar.end = estimated_point
        self._error_bar.lineColor = self._BLACK
        self._error_bar.draw()

    def _draw_error_text(self, gaze_error, ground_truth_point, is_left=True):
        """show the gaze error in texts"""
        # format the error message
        if is_left:
            error_text = f"L: {gaze_error:.2f}°"
            _new_text_pos = [ground_truth_point[0], ground_truth_point[1] + self._txt.height]
        else:
            error_text = f"R: {gaze_error:.2f}°"
            _new_text_pos = [ground_truth_point[0], ground_truth_point[1] + self._txt.height * 2.2]

        self._txt.text = error_text
        self._txt.pos = self._to_psychopy_coords(_new_text_pos)
        self._txt.color = self._BLACK
        self._txt.draw()

    def _draw_recali_and_continue_tips(self):
        legend_texts = [self.config.instruction_calibration_over,
                        self.config.instruction_recalibration]

        if 'en-' in self.config._lang:
            x = self._screen_width - 562
            y = self._screen_height - 128
            text_size = [562, 48]

        elif "zh-" in self.config._lang:
            x = self._screen_width - 562
            y = self._screen_height - 128
            text_size = [562, 48]

        elif "jp-" in self.config._lang:
            x = self._screen_width - 756
            y = self._screen_height - 96
            text_size = [562, 48]

        elif "ko-" in self.config._lang:
            x = self._screen_width - 562
            y = self._screen_height - 128
            text_size = [562, 48]

        elif 'fr-' in self.config._lang:
            x = self._screen_width - 562
            y = self._screen_height - 128
            text_size = [562, 48]

        elif 'es-' in self.config._lang:
            x = self._screen_width - 648
            y = self._screen_height - 180
            text_size = [648, 56]
        else:
            x, y = 0, 0
            raise Exception(f"Unknown language: {self.config._lang}, please check the code.")

        margin = 10
        pos = [x + text_size[0] // 2, y + text_size[1] // 2]

        for n, content in enumerate(legend_texts):
            self._validation_instruction.text = legend_texts[n]
            self._validation_instruction.color = "black"
            self._validation_instruction.pos = self._to_psychopy_coords(pos)
            _w, _h = self._validation_instruction.boundingBox
            pos[1] += (_h + margin)
            self._validation_instruction.draw()

    def _draw_legend(self):
        legend_texts = [f"+   {self.config.legend_target}",
                        f"+   {self.config.legend_left_eye}",
                        f"+   {self.config.legend_right_eye}"]

        color_list = [self._GREEN, self._CRIMSON, self._CORAL]
        x = -self._screen_width // 2 + 128
        y = -self._screen_height // 2 + 128

        for n, content in enumerate(legend_texts):
            # draw colored fixation
            self._txt.text = legend_texts[n][0]
            self._txt.height = 24
            self._txt.color = color_list[n]
            # print(self._txt.boundingBox)
            self._txt.pos = [x + self._txt.boundingBox[0] // 2, y - 36 * n]
            self._txt.draw()

            # draw black text
            self._txt.text = legend_texts[n][1:]
            self._txt.height = 24
            self._txt.color = "black"
            # print(self._txt.boundingBox)
            self._txt.pos = [x + self._txt.boundingBox[0] // 2, y - 36 * n]
            self._txt.draw()

    def _repeat_calibration_point(self):
        """repeat a validation position, if the gaze error was large or too few samples
        have been collected there"""

        for idx in range(len(self._validation_points)):
            _left_samples = self._validation_left_sample_store[idx]  # left-eye samples collected at idx
            _right_samples = self._validation_right_sample_store[idx]  # left-eye samples collected at idx

            _tracking_left = self._pupil_io.config.active_eye in [-1, 'left', 0, 'bino']
            _tracking_right = self._pupil_io.config.active_eye in [1, 'right', 0, 'bino']

            if (len(_left_samples) <= 5 and _tracking_left) or (len(_right_samples) <= 5 and _tracking_right):
                # validate a positoin, if less than 5 samples were collected for each eye
                # get ready to collect more samples
                self._validation_left_sample_store[idx] = []
                self._validation_right_sample_store[idx] = []
                self._validation_left_eye_distance_store[idx] = []
                self._validation_right_eye_distance_store[idx] = []
                # repeat this validation point
                self._calibration_drawing_list.append(idx)
            else:
                _left_samples = self._validation_left_sample_store[idx]  # n * 2
                _right_samples = self._validation_right_sample_store[idx]  # n * 2
                _left_eye_distances = self._validation_left_eye_distance_store[idx]  # n * 1
                _right_eye_distances = self._validation_right_eye_distance_store[idx]  # n * 1

                # ground truth position in pygame coordinates
                _ground_truth_point = self._to_pygame_coords(self._validation_points[idx])

                if _tracking_left:
                    _left_res = self._calculator.calculate_error_by_sliding_window(
                        gt_point=_ground_truth_point,
                        es_points=_left_samples,
                        distances=_left_eye_distances
                    )
                    # if the validation gaze error is greater than 2 degree, repeat this point
                    if _left_res["min_error"] > self._error_threshold:
                        logging.info(f"Recalibration point index: {idx}, Left error: {_left_res['min_error']}")
                        self._validation_left_eye_distance_store[idx] = []
                        self._validation_left_sample_store[idx] = []
                        self._validation_right_eye_distance_store[idx] = []
                        self._validation_right_sample_store[idx] = []
                        self._calibration_drawing_list.append(idx)

                if _tracking_right:
                    _right_res = self._calculator.calculate_error_by_sliding_window(
                        gt_point=_ground_truth_point,
                        es_points=_right_samples,
                        distances=_right_eye_distances
                    )
                    # if the validation gaze error is greater than 2 degree, repeat this point
                    if _right_res["min_error"] > self._error_threshold:
                        logging.info(f"Recalibration point index: {idx}, Right error: {_right_res['min_error']}")
                        self._validation_left_eye_distance_store[idx] = []
                        self._validation_left_sample_store[idx] = []
                        self._validation_right_eye_distance_store[idx] = []
                        self._validation_right_sample_store[idx] = []
                        self._calibration_drawing_list.append(idx)

        # if all validation have been completed, update the _n_validation status
        if not self._calibration_drawing_list:
            self._n_validation = 2

    def _draw_validation_point(self):
        """tracker validation process"""

        # the validation process is completed if there is no point in the pos list
        if not self._calibration_drawing_list:
            # whether we have bad validation points to repeat
            if self._n_validation == 1:
                self._repeat_calibration_point()
            else:
                # wait for 3 seconds when the validation process is completed
                # in the hands_free mode
                if self._hands_free and not self._validation_finished_timer:
                    self._validation_finished_timer = time.time()
                elif self._hands_free and self._validation_finished_timer:
                    __time_elapsed = time.time() - self._validation_finished_timer
                    if __time_elapsed > 1.5:
                        self._phase_validation = False

                # dump data into a json file
                if self.config.enable_validation_result_saving and not self._drawing_validation_result:
                    # save validation results to a json file
                    current_directory = Path.cwd()
                    _calibrationDir = current_directory / "calibration" / self._pupil_io._session_name
                    _calibrationDir.mkdir(parents=True, exist_ok=True)

                    # use a time string name the calibration results file
                    _currentTime = datetime.now()
                    _timeString = _currentTime.strftime("%Y-%m-%d_%H-%M-%S")
                    with _calibrationDir.joinpath(f"{_timeString}.json").open('w') as handle:
                        json.dump({
                            "validation_left_samples": self._validation_left_sample_store,
                            "validation_right_samples": self._validation_right_sample_store,
                            "validation_ground_truth_point": self._validation_points,
                            "validation_left_eye_distances": self._validation_left_eye_distance_store,
                            "validation_right_eye_distances": self._validation_right_eye_distance_store
                        }, handle)

                # now the validation process is completed, plot the results
                for idx in range(len(self._validation_points)):
                    _left_samples = self._validation_left_sample_store[idx]  # n * 2
                    _right_samples = self._validation_right_sample_store[idx]  # n * 2
                    _left_eye_distances = self._validation_left_eye_distance_store[idx]  # n * 1
                    _right_eye_distances = self._validation_right_eye_distance_store[idx]  # n * 1

                    # must convert the validation target position into Pygame coordinates for error calculation
                    _ground_truth_point = self._to_pygame_coords(self._validation_points[idx])

                    if self._pupil_io.config.active_eye in [-1, 'left', 0, 'bino']:
                        # modified it by slide window
                        # _avg_left_eye_distance = np.mean(_left_eye_distances)
                        # _avg_left_eye_sample = np.mean(_left_samples, axis=0)
                        _res = self._calculator.calculate_error_by_sliding_window(
                            gt_point=_ground_truth_point,
                            es_points=_left_samples,
                            distances=_left_eye_distances
                        )
                        if _res:
                            self._draw_error_line(_res["gt_point"], _res["min_error_es_point"], self._CRIMSON)
                            self._draw_error_text(_res["min_error"], _res["gt_point"], is_left=True)
                    if self._pupil_io.config.active_eye in [1, 'right', 0, 'bino']:
                        _res = self._calculator.calculate_error_by_sliding_window(
                            gt_point=_ground_truth_point,
                            es_points=_right_samples,
                            distances=_right_eye_distances
                        )
                        if _res:
                            self._draw_error_line(_res["gt_point"], _res["min_error_es_point"], self._CORAL)
                            self._draw_error_text(_res["min_error"], _res["gt_point"], is_left=False)

                    self._draw_legend()
                    self._draw_recali_and_continue_tips()
                    self._drawing_validation_result = True

        # do the following if the validation process is not completed yet
        else:
            # each validation point is presented for 3.0 seconds
            if self._validation_timer == 0:
                self._sound.stop()
                self._sound.play()
                self._validation_timer = time.time()

            _time_elapsed = time.time() - self._validation_timer
            if _time_elapsed > 1.5:
                self._calibration_drawing_list.pop()
                self._validation_timer = 0
                if not self._calibration_drawing_list:
                    self._n_validation += 1  # 检查是否重新进行校准
                else:
                    logging.info("Validation point index: " + str(self._calibration_drawing_list[-1]))
                # stop the sound
                self._sound.stop()

            else:
                _pos_idx = self._calibration_drawing_list[-1]
                _point = self._validation_points[_pos_idx]
                _status, _left_sample, _right_sample, _bino, _timestamp, _marker = self._pupil_io.estimate_gaze()

                self._draw_animation(point=_point, time_elapsed=_time_elapsed)

                if 0.0 < _time_elapsed <= 1.5:
                    # face_status, face_position = self._pupil_io.face_position()
                    _left_sample = _left_sample.tolist()
                    _right_sample = _right_sample.tolist()
                    _left_gaze_point = [_left_sample[0], _left_sample[1]]
                    _right_gaze_point = [_right_sample[0], _right_sample[1]]

                    # _eyebrow_distance = math.fabs(face_position[2]) / 10
                    # logging.info("validation left gaze estimated example: " + str(_left_sample))
                    # logging.info("validation right gaze estimated example: " + str(_right_sample))
                    if _left_sample[13] == 1:
                        self._validation_left_sample_store[_pos_idx].append(_left_gaze_point)
                        self._validation_left_eye_distance_store[_pos_idx].append(math.fabs(_left_sample[5]) / 10)
                    else:
                        logging.info(
                            f"calibration left eye sample loss, "
                            f"calibration position index: {_pos_idx},"
                            f"calibration position: {self._validation_points[_pos_idx]}")
                    if _right_sample[13] == 1:
                        self._validation_right_sample_store[_pos_idx].append(_right_gaze_point)
                        self._validation_right_eye_distance_store[_pos_idx].append(math.fabs(_right_sample[5]) / 10)
                    else:
                        logging.info(
                            f"calibration sample right eye loss, "
                            f"calibration position index: {_pos_idx},"
                            f"calibration position: {self._validation_points[_pos_idx]}")

    def _draw_calibration_point(self):
        if self._calibration_timer == 0:
            self._sound.stop()
            self._sound.play()
            self._calibration_timer = time.time()

        _time_elapsed = time.time() - self._calibration_timer

        _status = self._pupil_io.calibration(self._calibration_point_index)
        if _status == ET_ReturnCode.ET_CALI_CONTINUE.value:
            pass
        elif _status == ET_ReturnCode.ET_CALI_NEXT_POINT.value:
            # print("NEXT POINT")
            # print(self._calibration_point_index)
            if self._calibration_point_index + 1 == len(self._calibrationPoint):
                self._phase_calibration = False
                self._validation_preparing = False
                if self._need_validation and not self._hands_free:
                    self._validation_preparing = True
                    self._phase_validation = False
                elif self._hands_free and self._need_validation:
                    self._phase_calibration = False
                    self._validation_preparing = False
                    self._phase_validation = True
                else:
                    self._exit = True
                    self.graphics_finished = True
            else:
                self._calibration_point_index += 1
                self._calibration_timer = 0
                self._sound.stop()
                self._sound.play()

            if (self.config.calibration_listener is not None) and (
                    isinstance(self.config.calibration_listener, CalibrationListener)):
                self.config.calibration_listener.on_calibration_target_onset(self._calibration_point_index)

        elif _status == ET_ReturnCode.ET_SUCCESS.value:
            self._phase_calibration = False
            self._validation_preparing = False
            if self._need_validation and not self._hands_free:
                self._validation_preparing = True
                self._phase_validation = False
            elif self._hands_free and self._need_validation:
                self._phase_calibration = False
                self._validation_preparing = False
                self._phase_validation = True
            else:
                self._exit = True
                self.graphics_finished = True

            self._sound.stop()

        _point = self._calibrationPoint[self._calibration_point_index]
        self._draw_animation(
            point=self._to_psychopy_coords(_point),
            time_elapsed=_time_elapsed)

    def _draw_animation(self, point, time_elapsed):
        _index = int(time_elapsed // (1 / (self._animation_frequency * 10))) % 10
        _width = self._animation_size[_index][0]
        _height = self._animation_size[_index][1]
        self._animation_list[_index].pos = point
        self._animation_list[_index].draw()

    def _draw_previewer(self):
        _left_img, _right_img = self._pupil_io.get_preview_images()
        _previewer_size = (self._PREVIEWER_IMG_HEIGHT, self._PREVIEWER_IMG_WIDTH)
        # #  resize and rotate
        # _left_img = cv2.rotate(cv2.resize(_left_img, _previewer_size), cv2.ROTATE_90_COUNTERCLOCKWISE)
        # _right_img = cv2.rotate(cv2.resize(_right_img, _previewer_size), cv2.ROTATE_90_COUNTERCLOCKWISE)
        # # flip
        _left_img = cv2.flip(_left_img, 0)
        _right_img = cv2.flip(_right_img, 0)
        #  resize
        _left_img = cv2.resize(_left_img, _previewer_size)
        _right_img = cv2.resize(_right_img, _previewer_size)

        # normalize to [-1, 1]
        _left_img = (_left_img / 127.5) - 1.0
        _right_img = (_right_img / 127.5) - 1.0

        self._left_previewer_img_stim.tex = _left_img
        self._right_previewer_img_stim.tex = _right_img
        self._left_previewer_img_stim.draw()
        self._right_previewer_img_stim.draw()

    def _draw_adjust_position(self):
        if (not self._just_pos_sound_once):
            if self._hands_free:
                self._just_pos_sound.play()
            self._just_pos_sound_once = True
            # time.sleep(5)

        _instruction_text = " "
        _eyebrow_center_point = [-1, -1]
        _start_time = time.time()
        _status, _face_position = self._pupil_io.face_position()
        _face_position = _face_position.tolist()
        logging.info(f'Get face position cost {(time.time() - _start_time):.4f} seconds.')
        logging.info(f'Face position: {str(_face_position)}')

        _face_pos_x = _face_position[0]
        _face_pos_y = _face_position[1]
        _face_pos_z = _face_position[2]  # Emulating face_pos.z for testing

        # face cartoon
        # Update face point (righteye~=204, lefteye~=137, bino~=165)
        if self._pupil_io.config.active_eye in [-1, 'left']:
            _face_x_offset = 32
        elif self._pupil_io.config.active_eye in [1, 'right']:
            _face_x_offset = -32
        else:
            _face_x_offset = 0

        _eyebrow_center_point[0] = (_face_pos_x - 172.08 + _face_x_offset) * 10
        _eyebrow_center_point[1] = -(_face_pos_y - 96.79) * 10

        # Update rectangle color based on face point inside the rectangle
        if self._face_in_rect.contains(_eyebrow_center_point[0], _eyebrow_center_point[1]):
            _rectangle_color = self._GREEN
        else:
            _rectangle_color = self._RED
            _instruction_text = self.config.instruction_head_center

        # Update face point color based on face position in Z-axis
        if _face_pos_z == 0:
            _face_pos_z = 65536
        _color_ratio = 280 / abs(_face_pos_z)
        if _face_pos_z > -530 or _face_pos_z < -630:
            _face = self._frowning_face
            _face_point_color = self._RED
            if _face_pos_z > -530:
                _instruction_text = self.config.instruction_face_far
            if _face_pos_z < -630:
                _instruction_text = self.config.instruction_face_near
        else:
            _face = self._smiling_face
            _c = np.multiply(self._GREEN, (1 - _color_ratio)) + np.multiply(self._RED, _color_ratio)
            _c = np.divide(np.subtract(_c, 128), 128)
            _face_point_color = tuple(_c)
            # print('rect color....', _face_point_color)
            _face_point_color = self._GREEN

        # scale the face image
        _face_w, _face_h = int(_color_ratio * 256), int(_color_ratio * 256)

        # Draw a rectangle to signify the headbox
        self._face_in_rect.lineColor = _face_point_color
        self._face_in_rect.draw()
        # print(self._face_in_rect.width)

        if _status == ET_ReturnCode.ET_SUCCESS.value or not (
                _face_position[0] == 0 and _face_position[1] == 0 and _face_position[2] == 0):
            # Draw face point as a circle
            # pygame.draw.circle(self._screen, _face_point_color, (int(_eyebrow_center_point[0]),
            #                                                      int(_eyebrow_center_point[1])), 50)
            _face.pos = (int(_eyebrow_center_point[0]), int(_eyebrow_center_point[1]))
            _face.size = (_face_w, _face_h)
            _face.draw()

        self._txt.text = _instruction_text
        self._txt.pos = (int(_eyebrow_center_point[0]), int(_eyebrow_center_point[1]) - _face_h * 3 // 4)
        self._txt.color = self._BLACK
        self._txt.draw()

        if self._hands_free:
            if (-630 <= _face_pos_z <= -530 and self._face_in_rect.contains(_eyebrow_center_point[0],
                                                                            _eyebrow_center_point[1])
                    and self._hands_free_adjust_head_wait_time <= 0):
                # meet the criterion and wait time > 0
                self._phase_adjust_position = False
                self._calibration_preparing = True
            elif (-630 <= _face_pos_z <= -530 and self._face_in_rect.contains(_eyebrow_center_point[0],
                                                                              _eyebrow_center_point[1])
                  and not self._hands_free_adjust_head_wait_time <= 0):
                if self._hands_free_adjust_head_start_timestamp == 0:
                    self._hands_free_adjust_head_start_timestamp = time.time()
                else:
                    _tmp = time.time()
                    self._hands_free_adjust_head_wait_time -= (_tmp - self._hands_free_adjust_head_start_timestamp)
                    self._hands_free_adjust_head_start_timestamp = _tmp
            else:
                self._hands_free_adjust_head_start_timestamp = 0

    def _draw_text_center(self, text):
        """draw some text at the screen center"""
        # self._center_text_stim.text = text
        # self._center_text_stim.pos = (0, 0)
        # self._center_text_stim.draw()

        self._draw_segment_text(text, 0, 0)

    def _draw_segment_text(self, text, x, y):
        _segment_text = text.split("\n")
        self._txt._wrapWidthPix = 960
        _shift = 0
        for t in _segment_text:
            self._txt.text = t
            self._txt.color = self._BLACK
            self._txt.pos = (x, y + _shift)
            _shift += self._txt.boundingBox[1] + self._txt.height
            self._txt.draw()

    def _draw_calibration_preparing(self):
        _text = self.config.instruction_enter_calibration
        self._draw_text_center(_text)

    def _draw_calibration_preparing_hands_free(self):
        if not self._preparing_hands_free_start:
            self._preparing_hands_free_start = time.time()
            self._cali_ins_sound.play()

        _time_elapsed = time.time() - self._preparing_hands_free_start
        if _time_elapsed <= 9.0:
            _text = self.config.instruction_hands_free_calibration
            self._draw_segment_text(_text, 0, 0)
            _rest = f"{int(10 - _time_elapsed)}"
            print(_rest)
            for n, _character in enumerate(_rest):
                self._clock_resource_dict[_character].pos = (0, 200)
                self._clock_resource_dict[_character].draw()
        else:
            self._calibration_preparing = False
            self._phase_calibration = True

    def _draw_validation_preparing(self):
        _text = self.config.instruction_enter_validation
        self._draw_text_center(_text)

    def draw(self, validate=False, bg_color=(0, 0, 0)):
        # self._pupil_io._recalibration()
        self.initialize_variables()
        self._need_validation = validate
        _calibration_preparing_wait = 1
        _calibration_preparing_start = 0
        while not self._exit:
            _keys = event.getKeys()
            if (('return' in _keys) or self._mouse.getPressed()[0]) and self._phase_adjust_position:
                self._phase_adjust_position = False
                self._calibration_preparing = True
                if _calibration_preparing_start == 0:
                    _calibration_preparing_start = time.time()

            elif (('return' in _keys) or (self._mouse.getPressed()[0] and (
                    _calibration_preparing_wait < (
                    time.time() - _calibration_preparing_start)))) and self._calibration_preparing:
                self._phase_adjust_position = False
                self._calibration_preparing = False
                self._phase_calibration = True

                # callback: on_calibration_target_onset
                if (self.config.calibration_listener is not None) and (
                        isinstance(self.config.calibration_listener, CalibrationListener)):
                    self.config.calibration_listener.on_calibration_target_onset(self._calibration_point_index)

            elif (('return' in _keys) or self._mouse.getPressed()[0]) and self._validation_preparing:
                self._phase_validation = True
                self._validation_preparing = False

            elif (('return' in _keys) or self._mouse.getPressed()[
                0]) and self._phase_validation and self._drawing_validation_result:
                self._phase_validation = False

            elif ('esc' in _keys) or ('q' in _keys) or ('Q' in _keys):
                self._exit = True

            elif (('r' in _keys) or self._mouse.getPressed()[
                2]) and self._drawing_validation_result and self._phase_validation:
                self._phase_validation = False
                self._drawing_validation_result = False
                self._txt.height = 32
                self._txt.font = self._font
                self._pupil_io._recalibration()
                # print("recalibration")
                self.draw(self._need_validation, bg_color=bg_color)

            # self._fps_clock.tick(self._fps)
            # draw white background
            # self._screen.color = self._GRAY  # Fill the screen gray

            # draw point
            if not self._phase_adjust_position and not self._calibration_preparing and self._phase_calibration:
                self._draw_calibration_point()
            elif self._calibration_preparing:
                self._draw_calibration_preparing()
            elif self._validation_preparing:
                self._draw_validation_preparing()

            elif self._phase_adjust_position:
                # show face previewer
                if self.config.face_previewing:
                    self._draw_previewer()
                self._draw_adjust_position()
            elif self._phase_validation:
                self._draw_validation_point()

            elif (not self._phase_validation and not self._calibration_preparing and
                  not self._phase_calibration and not self._phase_adjust_position
                  and not self._validation_preparing):
                self.graphics_finished = True
                break

            self._screen.flip()

        # callback: on_calibration_over
        # if (self.config.calibration_listener is not None) and (
        #         isinstance(self.config.calibration_listener, CalibrationListener)):
        #     self.config.calibration_listener.on_calibration_over()

    @deprecated("1.1.2")
    def draw_hands_free(self, validate=False, bg_color=(1, 1, 1)):
        self.initialize_variables()
        self._need_validation = validate
        self._preparing_hands_free_start = 0
        self._hands_free = True
        while not self._exit:
            _keys = event.getKeys()
            if ('esc' in _keys) or ('q' in _keys) or ('Q' in _keys):
                self._exit = True

            self._screen.color = bg_color  # Fill bg color
            # draw point
            if self._phase_calibration:
                self._draw_calibration_point()
            elif self._calibration_preparing:
                self._draw_calibration_preparing_hands_free()
            # elif self._validation_preparing:
            #     self._draw_validation_preparing_hands_free()
            elif self._phase_adjust_position:
                self._draw_adjust_position()
            elif self._phase_validation:
                self._draw_validation_point()

            elif (not self._phase_validation and not self._calibration_preparing and
                  not self._phase_calibration and not self._phase_adjust_position
                  and not self._validation_preparing):
                self.graphics_finished = True
                break

            self._screen.flip()
        self._sound.stop()
        self._cali_ins_sound.stop()
        self._just_pos_sound.stop()
