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
# Calibration graphics for pygame applications

# Author: GC Zhu
# Email: zhugc2016@gmail.com

import json
import logging
import math
import os
import platform
import random
import time
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
import pygame
from pygame import Rect

from .callback import CalibrationListener
from .default_config import DefaultConfig
from .misc import ET_ReturnCode, LocalConfig, Calculator


class CalibrationUI(object):
    def __init__(self, pupil_io, screen):

        # set deep gaze
        self._pupil_io = pupil_io

        # pygame.init()
        # set pygame window caption
        # pygame.display.set_caption('deep gaze calibration')

        # set pygame window icon
        # _icon_path = os.path.join(self._current_dir, "asset", "pupil_io_favicon.png")
        # _icon = pygame.image.load(_icon_path)
        # pygame.display.set_icon(_icon)

        # constant fonts
        pygame.font.init()
        if platform.system().lower() == 'windows':
            if "microsoftyaheiui" in pygame.font.get_fonts():
                _font_name = "microsoftyaheiui"
            else:
                _font_name = pygame.font.get_fonts()[0]

            self._font = pygame.font.SysFont(_font_name, 32, bold=False, italic=False)
            self._error_text_font = pygame.font.SysFont(_font_name, 20, bold=False, italic=False)
            self._instruction_font = pygame.font.SysFont(_font_name, 24, bold=False, italic=False)

        elif platform.system().lower() == 'linux':
            self._font = pygame.font.Font(None, 36)
            self._error_text_font = pygame.font.Font(None, 18)
            self._instruction_font = pygame.font.Font(None, 24)

        # set pygame clock
        self._fps_clock = pygame.time.Clock()
        self._fps = 60

        # constant colors
        self._BLACK = (0, 0, 0)
        self._RED = (255, 0, 0)
        self._GREEN = (0, 255, 0)
        self._BLUE = (0, 0, 255)
        self._WHITE = (255, 255, 255)
        self._CRIMSON = (220, 20, 60)
        self._CORAL = (240, 128, 128)
        self._GRAY = (128, 128, 128)

        # configuration
        self.config: DefaultConfig = self._pupil_io.config

        # constant calibration points
        self._calibrationPoint = self._pupil_io.calibration_points

        # constant calibration stuffs
        self._face_in_rect = pygame.Rect(660, 240, 600, 600)  # x,y, w, h

        # constant library path
        self._current_dir = os.path.abspath(os.path.dirname(__file__))

        # audio path
        self._beep_sound_path = self.config.cali_target_beep
        # self._calibration_instruction_sound_path = os.path.join(self._current_dir, "asset",
        #                                                         "calibration_instruction.wav")

        self._adjust_position_sound_path = os.path.join(self._current_dir, "asset", "adjust_position.wav")

        # load audio files
        pygame.mixer.init()
        self._sound = pygame.mixer.Sound(self._beep_sound_path)
        self._cali_ins_sound = pygame.mixer.Sound(self.config.calibration_instruction_sound_path)

        self._just_pos_sound = pygame.mixer.Sound(self._adjust_position_sound_path)

        self._just_pos_sound_once = False

        # image transformer
        _rotate = pygame.transform.rotate
        _scale = pygame.transform.scale

        # set mouse cursor invisible
        pygame.mouse.set_visible(False)

        # load face image
        self._frowning_face = pygame.image.load(self.config.cali_frowning_face_img)
        self._smiling_face = pygame.image.load(self.config.cali_smiling_face_img)

        # constant animation frequency (times per second)
        self._animation_frequency = self.config.cali_target_animation_frequency

        # clock counter
        self._clock_resource_dict = {}
        self._clock_resource_height = 100
        for n in range(0, 10):
            self._clock_resource_dict[str(n)] = pygame.image.load(
                os.path.join(self._current_dir, "asset", f"figure_{n}.png"))
        self._clock_resource_dict['.'] = pygame.image.load(os.path.join(self._current_dir, "asset", "dot.png"))

        for key in self._clock_resource_dict:
            _img = self._clock_resource_dict[key]
            self._clock_resource_dict[key] = _scale(
                _img,
                (self._clock_resource_height / (_img.get_height() / _img.get_width()), self._clock_resource_height))

        # load local config
        self._local_config = LocalConfig()

        # set up the screen for drawing
        # self._screen = pygame.display.set_mode((self._screen_width, self._screen_height))
        self._screen = screen
        # self._screen = screen
        self._screen.fill(self._BLACK)

        # get monitor size
        self._screen_width = self._local_config.dp_config['screen_width']
        self._screen_height = self._local_config.dp_config['screen_height']
        logging.info("screen size: %d x %d" % (self._screen_width, self._screen_height))

        # initialize a calculator
        self._calculator = Calculator(
            screen_width=self._screen_width,
            screen_height=self._screen_height,
            physical_screen_width=self._local_config.dp_config['physical_screen_width'],
            physical_screen_height=self._local_config.dp_config['physical_screen_height'])

        self._calibration_bounds = Rect(0, 0, self._screen_width, self._screen_height)

        # do a quick 5-point validation of the calibration results
        self._validation_points = [
            [0.5, 0.08],
            [0.08, 0.5], [0.92, 0.5],
            [0.5, 0.92]]
        random.shuffle(self._validation_points)
        self._validation_points += [[0.5, 0.5]]

        # scale
        for _point in self._validation_points:
            _point[0] = _point[0] * (
                    self._calibration_bounds.width - self._calibration_bounds.left)
            _point[1] = _point[1] * (
                    self._calibration_bounds.height - self._calibration_bounds.top)

        # image resource for calibration and validation points
        _source_image = pygame.image.load(self.config.cali_target_img)
        _max_size, _min_size = (self.config.cali_target_img_maximum_size,
                                self.config.cali_target_img_minimum_size)
        self._animation_size = [
            (_min_size + (_max_size - _min_size) * i / 19, _min_size + (_max_size - _min_size) * i / 19)
            for i in range(20)
        ]
        self._animation_list = [
            _rotate(_scale(_source_image, self._animation_size[i]), 40 * i * 0)
            for i in range(10)
        ]

        # initialize previewer parameters
        self._PREVIEWER_IMG_WIDTH = 512
        self._PREVIEWER_IMG_HEIGHT = 512

        self._LEFT_PREVIEWER_POS = [
            self._PREVIEWER_IMG_WIDTH // 2 + 79
            ,
            self._screen_height // 2]
        self._RIGHT_PREVIEWER_POS = [
            self._screen_width - self._PREVIEWER_IMG_WIDTH // 2 - 79,
            self._screen_height // 2]

        # self._LEFT_PREVIEWER_POS = [
        #     (self._screen_width - self._PREVIEWER_IMG_WIDTH) // 2 - 5,
        #     self._screen_height - self._PREVIEWER_IMG_HEIGHT // 2 - 10]
        # self._RIGHT_PREVIEWER_POS = [
        #     (self._screen_width + self._PREVIEWER_IMG_WIDTH) // 2 + 5,
        #     self._screen_height - self._PREVIEWER_IMG_HEIGHT // 2 - 10]
        #

        # TOP-BOTTOM COODS
        self._LEFT_PREVIEWER_POS[0] -= self._PREVIEWER_IMG_WIDTH // 2
        self._RIGHT_PREVIEWER_POS[0] -= self._PREVIEWER_IMG_WIDTH // 2
        self._LEFT_PREVIEWER_POS[1] -= self._PREVIEWER_IMG_HEIGHT // 2
        self._RIGHT_PREVIEWER_POS[1] -= self._PREVIEWER_IMG_HEIGHT // 2

        _pygame_previewer_size = (self._PREVIEWER_IMG_WIDTH, self._PREVIEWER_IMG_HEIGHT)
        self._left_previewer_surface = pygame.Surface(_pygame_previewer_size)
        self._right_previewer_surface = pygame.Surface(_pygame_previewer_size)

        """
        variable
        """
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
        self._validation_left_sample_store = [[] * len(self._validation_points)]
        self._validation_right_sample_store = [[] * len(self._validation_points)]
        self._validation_left_eye_distance_store = [[] * len(self._validation_points)]
        self._validation_right_eye_distance_store = [[] * len(self._validation_points)]
        self._n_validation = 0  # n times of validation
        self._error_threshold = 2
        self._calibration_point_index = 0
        self._drawing_validation_result = False
        self._hands_free = False
        self._hands_free_adjust_head_wait_time = 5  # 3
        self._hands_free_adjust_head_start_timestamp = 0
        self._validation_finished_timer = 0

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

    def _draw_error_line(self, ground_truth_point, estimated_point, error_color):
        fixation_text = "+"
        text_surface = self._font.render(fixation_text, True, self._GREEN)
        text_rect = text_surface.get_rect()
        text_rect.center = (ground_truth_point[0],
                            ground_truth_point[1])
        self._screen.blit(text_surface, text_rect)

        fixation_text = "+"
        text_surface = self._font.render(fixation_text, True, error_color)
        text_rect = text_surface.get_rect()

        if not isinstance(estimated_point, np.ndarray):
            return
        text_rect.center = (estimated_point[0],
                            estimated_point[1])
        self._screen.blit(text_surface, text_rect)

        pygame.draw.line(self._screen, self._BLACK, ground_truth_point, estimated_point, width=1)

    def _draw_error_text(self, min_error, ground_truth_point, is_left=True):
        """draw error text on the screen."""
        error_degrees = min_error
        height_position = 1
        # 将错误以两位小数显示，并加上度符号
        if is_left:
            error_text = f"L: {error_degrees:.2f}°"
        else:
            error_text = f"R: {error_degrees:.2f}°"
            height_position += 1
        # 渲染文本
        text_surface = self._error_text_font.render(error_text, True, self._BLACK)
        text_rect = text_surface.get_rect()

        # 将文本居中
        text_rect.center = (ground_truth_point[0],
                            ground_truth_point[1] + text_rect.height * height_position)

        # 将文本绘制到屏幕上
        self._screen.blit(text_surface, text_rect)

    def _draw_recali_and_continue_tips(self):
        legend_texts = [self.config.instruction_calibration_over,
                        self.config.instruction_recalibration]

        if 'en-' in self.config._lang:
            x = self._screen_width - 600
            y = self._screen_height - 96

        elif "zh-" in self.config._lang:
            x = self._screen_width - 464
            y = self._screen_height - 96

        elif "jp-" in self.config._lang:
            x = self._screen_width - 712
            y = self._screen_height - 96

        elif "ko-" in self.config._lang:
            x = self._screen_width - 464
            y = self._screen_height - 96

        elif 'fr-' in self.config._lang:
            x = self._screen_width - 715
            y = self._screen_height - 96

        elif 'es-' in self.config._lang:
            x = self._screen_width - 512
            y = self._screen_height - 144
        else:
            x, y = 0, 0
            raise Exception(f"Unknown language: {self.config._lang}, please check the code.")

        for n, content in enumerate(legend_texts):
            for m, split_text in enumerate(content.split("\n")):
                content_text_surface = self._error_text_font.render(split_text, True, self._BLACK)
                content_text_rect = content_text_surface.get_rect()
                _x = x + content_text_rect.width // 2
                content_text_rect.center = (_x, y)
                # text_rect.center = (self._screen_width // 2 + n * text_rect.width, self._screen_height // 2)
                self._screen.blit(content_text_surface, content_text_rect)
                y += content_text_rect.height + 3

    def _draw_legend(self):
        legend_texts = [self.config.legend_target, self.config.legend_left_eye, self.config.legend_right_eye]
        color_list = [self._GREEN, self._CRIMSON, self._CORAL]
        x = 128
        y = self._screen_height - 128

        for n, content in enumerate(legend_texts):
            add_text_surface = self._error_text_font.render("+", True, color_list[n])
            add_text_rect = add_text_surface.get_rect()
            add_text_rect.center = (x, y)
            # text_rect.center = (self._screen_width // 2 + n * text_rect.width, self._screen_height // 2)
            self._screen.blit(add_text_surface, add_text_rect)
            _x = x + add_text_rect.width

            content_text_surface = self._error_text_font.render(content, True, self._BLACK)
            content_text_rect = content_text_surface.get_rect()
            _x += content_text_rect.width // 2
            content_text_rect.center = (_x, y)
            # text_rect.center = (self._screen_width // 2 + n * text_rect.width, self._screen_height // 2)
            self._screen.blit(content_text_surface, content_text_rect)
            y += content_text_rect.height + 3

    def _repeat_calibration_point(self):
        for idx in range(len(self._validation_points)):
            _left_samples = self._validation_left_sample_store[idx]  # n * 2
            _right_samples = self._validation_right_sample_store[idx]  # n * 2

            _tracking_left = self._pupil_io.config.active_eye in [-1, 'left', 0, 'bino']
            _tracking_right = self._pupil_io.config.active_eye in [1, 'right', 0, 'bino']

            if (len(_left_samples) <= 5 and _tracking_left) or (
                    len(_right_samples) <= 5 and _tracking_right):  # 小于五个样本点，说明该点需要重新校准
                # less than ten samples collected
                self._validation_left_sample_store[idx] = []
                self._validation_left_eye_distance_store[idx] = []
                self._validation_right_sample_store[idx] = []
                self._validation_right_eye_distance_store[idx] = []
                self._calibration_drawing_list.append(idx)
            else:
                _left_samples = self._validation_left_sample_store[idx]  # n * 2
                _right_samples = self._validation_right_sample_store[idx]  # n * 2
                _left_eye_distances = self._validation_left_eye_distance_store[idx]  # n * 1
                _right_eye_distances = self._validation_right_eye_distance_store[idx]  # n * 1
                _ground_truth_point = self._validation_points[idx]

                if _tracking_left:
                    _left_res = self._calculator.calculate_error_by_sliding_window(
                        gt_point=_ground_truth_point,
                        es_points=_left_samples,
                        distances=_left_eye_distances
                    )

                    if _left_res["min_error"] > self._error_threshold:
                        logging.info(f"Recalibration point index: {idx}, Left error: {_left_res['min_error']}")
                        # 如果误差大于设定值该点的所有数据清空，并且重新加入校准
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

                    if _right_res["min_error"] > self._error_threshold:
                        logging.info(f"Recalibration point index: {idx}, Right error: {_right_res['min_error']}")
                        # 如果误差大于设定值该点的所有数据清空，并且重新加入校准
                        self._validation_left_eye_distance_store[idx] = []
                        self._validation_left_sample_store[idx] = []
                        self._validation_right_eye_distance_store[idx] = []
                        self._validation_right_sample_store[idx] = []
                        self._calibration_drawing_list.append(idx)

        if not self._calibration_drawing_list:  # 不需要再次校准了
            self._n_validation = 2

    def _draw_validation_point(self):
        # 校准点不存在了，也就是校准结束
        if not self._calibration_drawing_list:
            # whether to revalidation
            if self._n_validation == 1:  # 是否进行重新校准
                self._repeat_calibration_point()
            else:
                if self._hands_free and not self._validation_finished_timer:
                    self._validation_finished_timer = time.time()
                elif self._hands_free and self._validation_finished_timer:
                    __time_elapsed = time.time() - self._validation_finished_timer
                    if __time_elapsed > 3:
                        self._phase_validation = False

                if self.config.enable_validation_result_saving and not self._drawing_validation_result:
                    # save validation results to a json file
                    current_directory = Path.cwd()
                    _calibrationDir = current_directory / "calibration" / self._pupil_io._session_name
                    _calibrationDir.mkdir(parents=True, exist_ok=True)

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

                for idx in range(len(self._validation_points)):
                    _left_samples = self._validation_left_sample_store[idx]  # n * 2
                    _right_samples = self._validation_right_sample_store[idx]  # n * 2
                    _left_eye_distances = self._validation_left_eye_distance_store[idx]  # n * 1
                    _right_eye_distances = self._validation_right_eye_distance_store[idx]  # n * 1
                    _ground_truth_point = self._validation_points[idx]

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
                            self._draw_error_line(_ground_truth_point, _res["min_error_es_point"], self._CRIMSON)
                            self._draw_error_text(_res["min_error"], _ground_truth_point, is_left=True)

                    if self._pupil_io.config.active_eye in [1, 'right', 0, 'bino']:
                        _res = self._calculator.calculate_error_by_sliding_window(
                            gt_point=_ground_truth_point,
                            es_points=_right_samples,
                            distances=_right_eye_distances
                        )

                        if _res:
                            self._draw_error_line(_ground_truth_point, _res["min_error_es_point"], self._CRIMSON)
                            self._draw_error_text(_res["min_error"], _ground_truth_point, is_left=False)

                    self._draw_legend()
                    self._draw_recali_and_continue_tips()
                    self._drawing_validation_result = True

        else:
            # initial for each point
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
                _point = self._validation_points[self._calibration_drawing_list[-1]]
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
                        self._validation_left_sample_store[self._calibration_drawing_list[-1]].append(
                            _left_gaze_point
                        )
                        self._validation_left_eye_distance_store[self._calibration_drawing_list[-1]].append(
                            math.fabs(_left_sample[5]) / 10
                        )
                    else:
                        logging.info(
                            f"calibration left eye sample loss, "
                            f"calibration position index: {self._calibration_drawing_list[-1]},"
                            f"calibration position: {self._validation_points[self._calibration_drawing_list[-1]]}")
                    if _right_sample[13] == 1:
                        self._validation_right_sample_store[self._calibration_drawing_list[-1]].append(
                            _right_gaze_point
                        )
                        self._validation_right_eye_distance_store[self._calibration_drawing_list[-1]].append(
                            math.fabs(_right_sample[5]) / 10
                        )
                    else:
                        logging.info(
                            f"calibration sample right eye loss, "
                            f"calibration position index: {self._calibration_drawing_list[-1]},"
                            f"calibration position: {self._validation_points[self._calibration_drawing_list[-1]]}")

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

            # callback: on_calibration_target_onset
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

            # stop the sound
            self._sound.stop()

        _point = self._calibrationPoint[self._calibration_point_index]
        self._draw_animation(point=_point, time_elapsed=_time_elapsed)

    def _draw_animation(self, point, time_elapsed):
        _index = int(time_elapsed // (1 / (self._animation_frequency * 10))) % 10
        _width = self._animation_size[_index][0]
        _height = self._animation_size[_index][1]
        self._screen.blit(self._animation_list[_index],
                          (int(point[0] - _width // 2), int(point[1] - _height // 2)))

    def _draw_previewer(self):
        _left_img, _right_img = self._pupil_io.get_preview_images()
        _previewer_size = (self._PREVIEWER_IMG_WIDTH, self._PREVIEWER_IMG_HEIGHT)
        #  resize and rotate
        _left_img = cv2.rotate(cv2.resize(_left_img, _previewer_size), cv2.ROTATE_90_COUNTERCLOCKWISE)
        _right_img = cv2.rotate(cv2.resize(_right_img, _previewer_size), cv2.ROTATE_90_COUNTERCLOCKWISE)
        # flip
        _left_img = cv2.flip(_left_img, 0)
        _right_img = cv2.flip(_right_img, 0)
        pygame.surfarray.blit_array(self._left_previewer_surface, _left_img)
        pygame.surfarray.blit_array(self._right_previewer_surface, _right_img)
        self._screen.blit(self._left_previewer_surface, self._LEFT_PREVIEWER_POS)
        self._screen.blit(self._right_previewer_surface, self._RIGHT_PREVIEWER_POS)

    def _draw_adjust_position(self):
        if (not self._just_pos_sound_once):
            if self._hands_free:
                self._just_pos_sound.play()
            self._just_pos_sound_once = True
            # time.sleep(5)

        _instruction_text = " "
        _color = [255, 255, 255]
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

        _eyebrow_center_point[0] = self._screen.get_width() // 2 + (_face_pos_x - 172.08 + _face_x_offset) * 10
        _eyebrow_center_point[1] = self._screen.get_height() // 2 + (_face_pos_y - 96.79) * 10

        # Update rectangle color based on face point inside the rectangle
        if self._face_in_rect.collidepoint(_eyebrow_center_point):
            _rectangle_color = self._GREEN
        else:
            _rectangle_color = self._RED
            _instruction_text = self.config.instruction_head_center
            # _instruction_text = str(_face_position)

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
            _face_point_color = tuple(
                np.multiply(self._GREEN, (1 - _color_ratio)) + np.multiply(self._RED, _color_ratio))

        # scale the face image
        _face = pygame.transform.scale(_face, (int(_color_ratio * 256), int(_color_ratio * 256)))
        _face_w, _face_h = _face.get_size()

        # Draw rectangle
        pygame.draw.rect(self._screen, _rectangle_color, self._face_in_rect, 5)

        if _status == ET_ReturnCode.ET_SUCCESS.value or not (
                _face_position[0] == 0 and _face_position[1] == 0 and _face_position[2] == 0):
            self._screen.blit(_face, (int(_eyebrow_center_point[0]), int(_eyebrow_center_point[1])))

        _segment_text = _instruction_text.split("\n")
        _shift = 0
        for t in _segment_text:
            text_surface = self._font.render(t, True, self._BLACK)
            text_rect = text_surface.get_rect()
            # text_rect.center = (self._screen_width // 2,
            #                     190 + 700 + 20 + _shift)
            text_rect.center = (int(_eyebrow_center_point[0] + _face_w // 2),
                                int(_eyebrow_center_point[1]) + 100 + _shift + _face_h // 2)
            _shift += text_rect.height
            self._screen.blit(text_surface, text_rect)

        if self._hands_free:
            if (-630 <= _face_pos_z <= -530 and self._face_in_rect.collidepoint(_eyebrow_center_point)
                    and self._hands_free_adjust_head_wait_time <= 0):
                # meet the criterion and wait time > 0
                self._phase_adjust_position = False
                self._calibration_preparing = True
            elif (-630 <= _face_pos_z <= -530 and self._face_in_rect.collidepoint(_eyebrow_center_point)
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
        self._draw_segment_text(text, self._screen_width // 2, self._screen_height // 2)

    def _draw_segment_text(self, text, x, y):
        _segment_text = text.split("\n")
        _shift = 0
        for t in _segment_text:
            text_surface = self._font.render(t, True, self._BLACK)
            text_rect = text_surface.get_rect()
            text_rect.center = (x, y + _shift)
            _shift += text_rect.height
            self._screen.blit(text_surface, text_rect)

    def _draw_calibration_preparing(self):
        _text = self.config.instruction_enter_calibration
        self._draw_text_center(_text)

    def _draw_calibration_preparing_hands_free(self):
        if not self._preparing_hands_free_start:
            self._preparing_hands_free_start = time.time()
            self._cali_ins_sound.play()

        _time_elapsed = time.time() - self._preparing_hands_free_start
        if _time_elapsed <= 9.0:
            _text = self.config.instruction_hands_free_calibration  # "9秒钟后，屏幕上会出现几个点，请依次注视它们"
            _center_x = self._screen_width // 2
            _center_y = self._screen_height // 2
            self._draw_segment_text(_text, _center_x, _center_y)
            _rest = f"{int(10 - _time_elapsed)}"
            _w = self._clock_resource_dict['.'].get_width()
            _h = self._clock_resource_dict['.'].get_height()

            # print(_rest)

            for n, _character in enumerate(_rest):
                # _x = _center_x - (3 - n) * _w
                _x = _center_x - _w
                _y = _center_y - 200
                self._screen.blit(self._clock_resource_dict[_character], (_x + _w // 2, _y + _h // 2))
        else:
            self._calibration_preparing = False
            self._phase_calibration = True

    def _draw_validation_preparing(self):
        _text = self.config.instruction_enter_validation
        self._draw_text_center(_text)

    def draw(self, validate=False, bg_color=(255, 255, 255)):
        self._pupil_io._recalibration()
        self.initialize_variables()
        self._need_validation = validate
        while not self._exit:
            for event in pygame.event.get():
                # if event.type == pygame.quit():
                #     break
                _left_mouse_click = 0
                _right_mouse_click = 0
                _keyboard_return = 0
                _keyboard_r = 0
                _keyboard_quit = 0
                if event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 1:  # left key press
                        _left_mouse_click = 1
                    elif event.button == 3:  # right key press
                        _right_mouse_click = 1

                if event.type == pygame.KEYUP:
                    _keyboard_return = event.key == pygame.K_RETURN
                    _keyboard_r = event.key == pygame.K_r
                    _keyboard_quit = event.key == pygame.K_q

                _user_response_continue = _keyboard_return or _left_mouse_click
                _user_response_recali = _keyboard_r or _right_mouse_click

                if event.type == pygame.KEYUP or event.type == pygame.MOUSEBUTTONUP:

                    if _user_response_continue and self._phase_adjust_position:
                        self._phase_adjust_position = False
                        self._calibration_preparing = True

                    elif _user_response_continue and self._calibration_preparing:
                        self._phase_adjust_position = False
                        self._calibration_preparing = False
                        self._phase_calibration = True

                        # callback: on_calibration_target_onset
                        if (self.config.calibration_listener is not None) and (
                                isinstance(self.config.calibration_listener, CalibrationListener)):
                            self.config.calibration_listener.on_calibration_target_onset(self._calibration_point_index)

                    elif _user_response_continue and self._validation_preparing:
                        self._phase_validation = True
                        self._validation_preparing = False

                    elif _user_response_continue and self._phase_validation and self._drawing_validation_result:
                        self._phase_validation = False

                    elif _user_response_recali and self._drawing_validation_result:
                        self._phase_validation = False
                        self._drawing_validation_result = False
                        # self._pupil_io._recalibration()
                        # print("recalibration")
                        self.draw(self._need_validation, bg_color=bg_color)

                    elif _keyboard_quit:
                        self._exit = True

            self._fps_clock.tick(self._fps)
            # draw white background
            self._screen.fill(bg_color)  # Fill white color

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

            pygame.display.flip()

        self._sound.stop()

        # callback: on_calibration_over
        # if (self.config.calibration_listener is not None) and (
        #         isinstance(self.config.calibration_listener, CalibrationListener)):
        #     self.config.calibration_listener.on_calibration_over()

    def draw_hands_free(self, validate=False, bg_color=(255, 255, 255)):
        self.initialize_variables()
        self._need_validation = validate
        self._preparing_hands_free_start = 0
        self._hands_free = True
        while not self._exit:
            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_q:
                        self._exit = True

            self._screen.fill(bg_color)  # Fill bg color
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

            pygame.display.flip()
        self._sound.stop()
        self._cali_ins_sound.stop()
        self._just_pos_sound.stop()
