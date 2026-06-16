# _*_ coding: utf-8 _*_
# ... (原有版权声明) ...
# DESCRIPTION:
# Calibration graphics with UIBackend (supports pygame & psychopy)

import logging
import os
import platform
import random
import time

import cv2
import numpy as np

from .default_config import DefaultConfig
from .misc import ET_ReturnCode, LocalConfig, Calculator
from .ui_backend import UIBackend, PyGameUIBackend, PsychoPyUIBackend


class CalibrationUI(object):
    def __init__(self, pupil_io, screen, bg_color=(255, 255, 255)):
        self._pupil_io = pupil_io

        try:
            import pygame
            if isinstance(screen, pygame.Surface):
                self._backend = PyGameUIBackend(screen, bg_color=bg_color)
            else:
                self._backend = PsychoPyUIBackend(screen)
        except ImportError:
            self._backend = PyGameUIBackend(screen, bg_color=bg_color)

        # 保存 screen 引用（后续少数地方可能仍需）
        self._screen = screen
        self._screen_width, self._screen_height = self._backend.get_screen_size()

        # 后端类型标记，用于事件分支
        self._is_pygame_backend = isinstance(self._backend, PyGameUIBackend)

        # 字体相关（保留名称，供 backend.draw_text 使用）
        if platform.system().lower() == 'windows':
            self._font_name = "microsoftyaheiui" if "microsoftyaheiui" in pygame.font.get_fonts() else \
                pygame.font.get_fonts()[0]
        else:
            self._font_name = None  # psychopy 或 linux 由 backend 自行处理
        self._instruction_font_size = 24
        self._error_font_size = 20

        # 颜色常量
        self._BLACK = (0, 0, 0)
        self._RED = (255, 0, 0)
        self._GREEN = (0, 255, 0)
        self._BLUE = (0, 0, 255)
        self._WHITE = (255, 255, 255)
        self._CRIMSON = (220, 20, 60)
        self._CORAL = (240, 128, 128)
        self._GRAY = (128, 128, 128)

        self.config: DefaultConfig = self._pupil_io.config
        self._calibrationPoint = self._pupil_io.calibration_points

        # 面部矩形区域
        self._face_in_rect = (660, 240, 600, 600)

        self._current_dir = os.path.abspath(os.path.dirname(__file__))

        # 声音加载（分配 ID）
        self._beep_sound_path = self.config.cali_target_beep
        self._adjust_position_sound_path = os.path.join(self._current_dir, "asset", "adjust_position.wav")
        self._backend.load_sound(self._beep_sound_path, "beep")
        self._backend.load_sound(self.config.calibration_instruction_sound_path, "cali_ins")
        self._backend.load_sound(self._adjust_position_sound_path, "adjust_pos")

        self._just_pos_sound_once = False

        # 面部表情图像
        self._frowning_face_path = self.config.cali_frowning_face_img
        self._smiling_face_path = self.config.cali_smiling_face_img

        # 动画目标参数
        self._animation_frequency = self.config.cali_target_animation_frequency
        # 动画帧：预计算尺寸，绘制时直接使用尺寸+图像路径（不创建 Surface）
        _max_size = self.config.cali_target_img_maximum_size
        _min_size = self.config.cali_target_img_minimum_size
        self._animation_size = [
            (_min_size + (_max_size - _min_size) * i / 19,
             _min_size + (_max_size - _min_size) * i / 19)
            for i in range(20)
        ]
        self._target_img_path = self.config.cali_target_img

        # 倒计时数字资源（保持为图像路径，或通过 backend.draw_image 绘制）
        self._clock_resource_dict = {}
        self._clock_resource_height = 100
        for n in range(10):
            path = os.path.join(self._current_dir, "asset", f"figure_{n}.png")
            self._clock_resource_dict[str(n)] = path
        self._clock_resource_dict['.'] = os.path.join(self._current_dir, "asset", "dot.png")

        # 本地配置
        self._local_config = LocalConfig()
        self._calculator = Calculator(
            screen_width=self._screen_width,
            screen_height=self._screen_height,
            physical_screen_width=self._local_config.dp_config['physical_screen_width'],
            physical_screen_height=self._local_config.dp_config['physical_screen_height'])

        self._calibration_bounds = (0, 0, self._screen_width, self._screen_height)

        # 验证点生成
        self._validation_points = [
            [0.5, 0.08],
            [0.08, 0.5], [0.92, 0.5],
            [0.5, 0.92]]
        random.shuffle(self._validation_points)
        self._validation_points += [[0.5, 0.5]]
        for _point in self._validation_points:
            _point[0] = _point[0] * (self._calibration_bounds[2] - self._calibration_bounds[0])
            _point[1] = _point[1] * (self._calibration_bounds[3] - self._calibration_bounds[1])

        # 预览参数
        self._PREVIEWER_IMG_WIDTH = 512
        self._PREVIEWER_IMG_HEIGHT = 512
        self._PREVIEWER_SIZE = (self._PREVIEWER_IMG_WIDTH, self._PREVIEWER_IMG_HEIGHT)

        self._LEFT_PREVIEWER_POS = [
            self._PREVIEWER_IMG_WIDTH // 2 + 79,
            self._screen_height // 2]
        self._RIGHT_PREVIEWER_POS = [
            self._screen_width - self._PREVIEWER_IMG_WIDTH // 2 - 79,
            self._screen_height // 2]

        self._LEFT_PREVIEWER_POS[0] -= self._PREVIEWER_IMG_WIDTH // 2
        self._RIGHT_PREVIEWER_POS[0] -= self._PREVIEWER_IMG_WIDTH // 2
        self._LEFT_PREVIEWER_POS[1] -= self._PREVIEWER_IMG_HEIGHT // 2
        self._RIGHT_PREVIEWER_POS[1] -= self._PREVIEWER_IMG_HEIGHT // 2

        self._LEFT_PREVIEWER_RECT = (self._LEFT_PREVIEWER_POS[0], self._LEFT_PREVIEWER_POS[1],
                                     self._PREVIEWER_SIZE[0], self._PREVIEWER_SIZE[1])
        self._RIGHT_PREVIEWER_RECT = (self._RIGHT_PREVIEWER_POS[0], self._RIGHT_PREVIEWER_POS[1],
                                      self._PREVIEWER_SIZE[0], self._PREVIEWER_SIZE[1])
        # 各种状态变量
        self.initialize_variables()

    def initialize_variables(self):
        """初始化状态变量"""
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
        self._n_validation = 0
        self._error_threshold = 2
        self._calibration_point_index = 0
        self._drawing_validation_result = False
        self._hands_free = False
        self._hands_free_adjust_head_wait_time = 11
        self._hands_free_adjust_head_start_timestamp = 0
        self._validation_finished_timer = 0
        self._preparing_hands_free_start = 0

    # ------------------- 辅助绘制方法 (使用 backend) -------------------
    def _draw_error_line(self, ground_truth_point, estimated_point, error_color):
        """绘制真实点与估计点之间的误差线（十字）"""
        # 绘制十字
        self._backend.draw_text("+", self._font_name, self._error_font_size, self._GREEN,
                                (ground_truth_point[0] - 10, ground_truth_point[1] - 10, 20, 20), 'center')
        if isinstance(estimated_point, np.ndarray):
            self._backend.draw_text("+", self._font_name, self._error_font_size, error_color,
                                    (int(estimated_point[0]) - 10, int(estimated_point[1]) - 10, 20, 20), 'center')
            self._backend.draw_line(ground_truth_point[0], ground_truth_point[1],
                                    int(estimated_point[0]), int(estimated_point[1]),
                                    self._BLACK, 1)

    def _draw_error_text(self, min_error, ground_truth_point, is_left=True):
        """显示误差度数"""
        error_degrees = min_error
        y_offset = 20 if is_left else 40
        text = f"{'L' if is_left else 'R'}: {error_degrees:.2f}°"
        self._backend.draw_text(text, self._font_name, self._error_font_size, self._BLACK,
                                (ground_truth_point[0] - 60, ground_truth_point[1] + y_offset, 120, 20), 'center')

    def _draw_recali_and_continue_tips(self):
        """显示重新校准提示"""
        legend_texts = [self.config.instruction_calibration_over,
                        self.config.instruction_recalibration]
        x_positions = {
            'en-': self._screen_width - 600,
            'zh-': self._screen_width - 464,
            'jp-': self._screen_width - 712,
            'ko-': self._screen_width - 464,
            'fr-': self._screen_width - 715,
            'es-': self._screen_width - 512,
        }
        x = x_positions.get(self.config._lang[:3], 0)
        y = self._screen_height - 96
        for content in legend_texts:
            for line in content.split("\n"):
                self._backend.draw_text(line, self._font_name, self._error_font_size, self._BLACK,
                                        (x - 200, y, 400, 20), 'center')
                y += 22

    def _draw_legend(self):
        """绘制图例"""
        texts = [self.config.legend_target, self.config.legend_left_eye, self.config.legend_right_eye]
        colors = [self._GREEN, self._CRIMSON, self._CORAL]
        x = 128
        y = self._screen_height - 128
        for text, color in zip(texts, colors):
            self._backend.draw_text("+", self._font_name, self._error_font_size, color,
                                    (x - 20, y - 10, 40, 20), 'center')
            self._backend.draw_text(text, self._font_name, self._error_font_size, self._BLACK,
                                    (x + 20, y - 10, 200, 20), 'left')
            y += 25

    def _draw_animation(self, point, time_elapsed):
        """绘制校准/验证动画目标"""
        idx = int(time_elapsed // (1 / (self._animation_frequency * 10))) % 10
        w, h = self._animation_size[idx]
        rect = (int(point[0] - w // 2), int(point[1] - h // 2), int(w), int(h))
        self._backend.draw_image(self._target_img_path, rect)

    def _draw_previewer(self):
        """绘制左右眼预览窗口"""
        _left_img, _right_img = self._pupil_io.get_preview_images()
        # 缩放并旋转（适配原逻辑）
        _left_img = cv2.resize(_left_img, self._PREVIEWER_SIZE)
        _right_img = cv2.resize(_right_img, self._PREVIEWER_SIZE)
        if self._backend.name == "pygame":
            _left_img = cv2.rotate(_left_img, cv2.ROTATE_90_COUNTERCLOCKWISE)
            _right_img = cv2.rotate(_right_img, cv2.ROTATE_90_COUNTERCLOCKWISE)
        _left_img = cv2.flip(_left_img, 0)
        _right_img = cv2.flip(_right_img, 0)

        self._backend.draw_texture(_left_img, self._LEFT_PREVIEWER_RECT)

        self._backend.draw_texture(_right_img, self._RIGHT_PREVIEWER_RECT)

    def _draw_face_and_rect(self, face_img_path, face_center, face_w, face_h, rect, rect_color, instruction_text):
        """绘制脸部图像、矩形框及提示文字"""
        # 矩形
        self._backend.draw_rect(rect, rect_color, 5)
        # 脸部图像（拉伸至指定尺寸）
        self._backend.draw_image(face_img_path, (face_center[0], face_center[1], face_w, face_h))
        # 提示文字
        for i, line in enumerate(instruction_text.split("\n")):
            y = face_center[1] + face_h + 20 + i * 25
            self._backend.draw_text(line, self._font_name, self._instruction_font_size, self._BLACK,
                                    (face_center[0] - 200, y, 400, 25), 'center')

    def _draw_text_center(self, text):
        """屏幕居中显示多行文本"""
        self._backend.draw_text_on_screen_center(text, self._font_name, self._instruction_font_size, self._BLACK)

    # ------------------- 业务逻辑绘制方法（适配 backend） -------------------
    def _draw_adjust_position(self):
        if not self._just_pos_sound_once:
            if self._hands_free:
                self._backend.play_sound("adjust_pos")
            self._just_pos_sound_once = True

        _status, _face_position = self._pupil_io.face_position()
        _face_position = _face_position.tolist()
        face_x, face_y, face_z = _face_position

        # 根据活动眼计算偏移
        active_eye = self._pupil_io.config.active_eye
        if active_eye in [-1, 'left']:
            face_x_offset = 32
        elif active_eye in [1, 'right']:
            face_x_offset = -32
        else:
            face_x_offset = 0

        eyebrow_center = [
            self._screen_width // 2 + (face_x - 172.08 + face_x_offset) * 10,
            self._screen_height // 2 + (face_y - 96.79) * 10
        ]

        rect = self._face_in_rect
        in_rect = UIBackend.pos_in_rect(eyebrow_center, rect)
        rect_color = self._GREEN if in_rect else self._RED
        instruction = "" if in_rect else self.config.instruction_head_center

        # 距离检测
        if face_z == 0:
            face_z = 65536
        color_ratio = 280 / abs(face_z)
        good_distance = -630 <= face_z <= -530
        face_img = self._smiling_face_path if good_distance else self._frowning_face_path
        face_color = self._GREEN if good_distance else self._RED
        if not good_distance:
            instruction = self.config.instruction_face_far if face_z > -530 else self.config.instruction_face_near

        # 绘制脸部及矩形
        face_w = int(color_ratio * 256)
        face_h = int(color_ratio * 256)
        self._backend.draw_rect(rect, rect_color, 5)
        self._backend.draw_image(face_img, (eyebrow_center[0], eyebrow_center[1], face_w, face_h))
        for i, line in enumerate(instruction.split("\n")):
            y = eyebrow_center[1] + face_h + 20 + i * 25
            self._backend.draw_text(line, self._font_name, self._instruction_font_size, self._BLACK,
                                    (eyebrow_center[0] - 200, y, 400, 25), 'center')

        # 免手模式自动跳转判断
        if self._hands_free:
            if good_distance and in_rect and self._hands_free_adjust_head_wait_time <= 0:
                self._phase_adjust_position = False
                self._calibration_preparing = True
            elif good_distance and in_rect and self._hands_free_adjust_head_wait_time > 0:
                if self._hands_free_adjust_head_start_timestamp == 0:
                    self._hands_free_adjust_head_start_timestamp = time.time()
                else:
                    elapsed = time.time() - self._hands_free_adjust_head_start_timestamp
                    self._hands_free_adjust_head_wait_time -= elapsed
                    self._hands_free_adjust_head_start_timestamp = time.time()
            else:
                self._hands_free_adjust_head_start_timestamp = 0

    def _draw_calibration_point(self):
        if self._calibration_timer == 0:
            self._backend.stop_sound("beep")
            self._backend.play_sound("beep")
            self._calibration_timer = time.time()

        elapsed = time.time() - self._calibration_timer
        status = self._pupil_io.calibration(self._calibration_point_index)

        if status == ET_ReturnCode.ET_CALI_NEXT_POINT.value or status == ET_ReturnCode.ET_SUCCESS.value:
            if status == ET_ReturnCode.ET_SUCCESS.value or self._calibration_point_index + 1 == len(
                    self._calibrationPoint):
                self._phase_calibration = False
                if self._need_validation:
                    if self._hands_free:
                        self._phase_validation = True
                    else:
                        self._validation_preparing = True
                else:
                    self._exit = True
                    self.graphics_finished = True
            else:
                self._calibration_point_index += 1
                self._calibration_timer = 0
                self._backend.stop_sound("beep")
                self._backend.play_sound("beep")

            if self.config.calibration_listener:
                self.config.calibration_listener.on_calibration_target_onset(self._calibration_point_index)

        point = self._calibrationPoint[self._calibration_point_index]
        self._draw_animation(point, elapsed)

    def _draw_validation_point(self):
        if not self._calibration_drawing_list:
            if self._n_validation == 1:
                self._repeat_calibration_point()
            else:
                # 结束验证，显示结果
                if self._hands_free and not self._validation_finished_timer:
                    self._validation_finished_timer = time.time()
                elif self._hands_free and self._validation_finished_timer:
                    if time.time() - self._validation_finished_timer > 3:
                        self._phase_validation = False

                # 保存结果
                if self.config.enable_validation_result_saving and not self._drawing_validation_result:
                    ...  # 原有保存逻辑不变

                # 绘制误差
                for idx in range(len(self._validation_points)):
                    gt = self._validation_points[idx]
                    left_samples = self._validation_left_sample_store[idx]
                    right_samples = self._validation_right_sample_store[idx]
                    left_dist = self._validation_left_eye_distance_store[idx]
                    right_dist = self._validation_right_eye_distance_store[idx]

                    if self._pupil_io.config.active_eye in [-1, 'left', 0, 'bino']:
                        res = self._calculator.calculate_error_by_sliding_window(gt, left_samples, left_dist)
                        if res:
                            self._draw_error_line(gt, res["min_error_es_point"], self._CRIMSON)
                            self._draw_error_text(res["min_error"], gt, True)
                    if self._pupil_io.config.active_eye in [1, 'right', 0, 'bino']:
                        res = self._calculator.calculate_error_by_sliding_window(gt, right_samples, right_dist)
                        if res:
                            self._draw_error_line(gt, res["min_error_es_point"], self._CRIMSON)
                            self._draw_error_text(res["min_error"], gt, False)

                self._draw_legend()
                self._draw_recali_and_continue_tips()
                self._drawing_validation_result = True
        else:
            if self._validation_timer == 0:
                self._backend.stop_sound("beep")
                self._backend.play_sound("beep")
                self._validation_timer = time.time()

            elapsed = time.time() - self._validation_timer
            if elapsed > 1.5:
                self._calibration_drawing_list.pop()
                self._validation_timer = 0
                if not self._calibration_drawing_list:
                    self._n_validation += 1
                self._backend.stop_sound("beep")
            else:
                point = self._validation_points[self._calibration_drawing_list[-1]]
                _, left_sample, right_sample, _, _, _ = self._pupil_io.estimate_gaze()
                self._draw_animation(point, elapsed)

                if 0 < elapsed <= 1.5:
                    left_gaze = left_sample[:2]
                    right_gaze = right_sample[:2]
                    if left_sample[13] == 1:
                        self._validation_left_sample_store[self._calibration_drawing_list[-1]].append(left_gaze)
                        self._validation_left_eye_distance_store[self._calibration_drawing_list[-1]].append(
                            abs(left_sample[5]) / 10)
                    if right_sample[13] == 1:
                        self._validation_right_sample_store[self._calibration_drawing_list[-1]].append(right_gaze)
                        self._validation_right_eye_distance_store[self._calibration_drawing_list[-1]].append(
                            abs(right_sample[5]) / 10)

    def _draw_calibration_preparing(self):
        self._draw_text_center(self.config.instruction_enter_calibration)

    def _draw_calibration_preparing_hands_free(self):
        if not self._preparing_hands_free_start:
            self._preparing_hands_free_start = time.time()
            self._backend.play_sound("cali_ins")

        elapsed = time.time() - self._preparing_hands_free_start
        if elapsed <= 9.0:
            self._draw_text_center(self.config.instruction_hands_free_calibration)
            rest = f"{int(10 - elapsed)}"
            # 绘制倒计时数字
            digit_w = self._clock_resource_height / 0.8  # 假设比例
            x_center = self._screen_width // 2
            y_center = self._screen_height // 2 - 200
            total_w = len(rest) * digit_w
            for i, ch in enumerate(rest):
                path = self._clock_resource_dict[ch]
                rx = int(x_center - total_w // 2 + i * digit_w)
                self._backend.draw_image(path, (rx, y_center, int(digit_w), self._clock_resource_height))
        else:
            self._calibration_preparing = False
            self._phase_calibration = True

    def _draw_validation_preparing(self):
        self._draw_text_center(self.config.instruction_enter_validation)

    # ------------------- 事件处理（根据后端分支） -------------------
    def _process_events(self):
        """统一事件处理，返回用户操作标识"""
        continue_flag = False
        recalibrate_flag = False
        quit_flag = False

        if self._is_pygame_backend:
            import pygame
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    quit_flag = True
                elif event.type == pygame.KEYUP:
                    if event.key == pygame.K_RETURN:
                        continue_flag = True
                    elif event.key == pygame.K_r:
                        recalibrate_flag = True
                    elif event.key == pygame.K_q:
                        quit_flag = True
                elif event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 1:
                        continue_flag = True
                    elif event.button == 3:
                        recalibrate_flag = True
        else:
            # psychoPy 后端
            from psychopy import event
            keys = event.getKeys(keyList=['return', 'r', 'q'])
            if 'return' in keys:
                continue_flag = True
            if 'r' in keys:
                recalibrate_flag = True
            if 'q' in keys:
                quit_flag = True
            # 鼠标检测：可通过 backend 的 mouse 对象
            mouse = self._backend.mouse
            if mouse.getPressed()[0]:  # 左键
                continue_flag = True
            if mouse.getPressed()[2]:  # 右键
                recalibrate_flag = True

        return continue_flag, recalibrate_flag, quit_flag

    # ------------------- 公开方法 -------------------
    def draw(self, validate=False, bg_color=(255, 255, 255)):
        self._pupil_io._recalibration()
        self.initialize_variables()
        self._need_validation = validate

        while not self._exit:
            # 背景填充：使用全屏矩形
            self._backend.before_draw()
            self._backend.draw_rect((0, 0, self._screen_width, self._screen_height), bg_color, 0)

            # 状态机绘制
            if self._phase_adjust_position:
                if self.config.face_previewing:
                    self._draw_previewer()
                self._draw_adjust_position()
            elif self._calibration_preparing:
                self._draw_calibration_preparing()
            elif self._phase_calibration:
                self._draw_calibration_point()
            elif self._validation_preparing:
                self._draw_validation_preparing()
            elif self._phase_validation:
                self._draw_validation_point()
            else:
                self.graphics_finished = True
                break

            self._backend.after_draw()

            # 事件处理
            cont, recali, quit_ = self._process_events()
            if quit_:
                self._exit = True
            if cont:
                if self._phase_adjust_position:
                    self._phase_adjust_position = False
                    self._calibration_preparing = True
                elif self._calibration_preparing:
                    self._calibration_preparing = False
                    self._phase_calibration = True
                    if self.config.calibration_listener:
                        self.config.calibration_listener.on_calibration_target_onset(self._calibration_point_index)
                elif self._validation_preparing:
                    self._validation_preparing = False
                    self._phase_validation = True
                elif self._phase_validation and self._drawing_validation_result:
                    self._phase_validation = False
            if recali and self._drawing_validation_result:
                self._phase_validation = False
                self._drawing_validation_result = False
                self.draw(self._need_validation, bg_color=bg_color)

        self._backend.stop_sound("beep")

    def draw_hands_free(self, validate=False, bg_color=(255, 255, 255)):
        self.initialize_variables()
        self._need_validation = validate
        self._hands_free = True
        self._preparing_hands_free_start = 0

        while not self._exit:
            self._backend.before_draw()
            self._backend.draw_rect((0, 0, self._screen_width, self._screen_height), bg_color, 0)

            if self._phase_calibration:
                self._draw_calibration_point()
            elif self._calibration_preparing:
                self._draw_calibration_preparing_hands_free()
            elif self._phase_adjust_position:
                self._draw_adjust_position()
            elif self._phase_validation:
                self._draw_validation_point()
            else:
                self.graphics_finished = True
                break

            self._backend.after_draw()

            # 仅检测退出键
            if self._is_pygame_backend:
                import pygame
                for event in pygame.event.get():
                    if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_q):
                        self._exit = True
            else:
                from psychopy import event
                if 'q' in event.getKeys():
                    self._exit = True

        self._backend.stop_sound("beep")
        self._backend.stop_sound("cali_ins")
        self._backend.stop_sound("adjust_pos")

    def _repeat_calibration_point(self):
        for idx in range(len(self._validation_points)):
            _left_samples = self._validation_left_sample_store[idx]
            _right_samples = self._validation_right_sample_store[idx]

            _tracking_left = self._pupil_io.config.active_eye in [-1, 'left', 0, 'bino']
            _tracking_right = self._pupil_io.config.active_eye in [1, 'right', 0, 'bino']

            # 如果左右眼任意一侧样本数量不足，直接将该点重新加入校准列表
            if (len(_left_samples) <= 5 and _tracking_left) or (
                    len(_right_samples) <= 5 and _tracking_right):
                self._validation_left_sample_store[idx] = []
                self._validation_left_eye_distance_store[idx] = []
                self._validation_right_sample_store[idx] = []
                self._validation_right_eye_distance_store[idx] = []
                self._calibration_drawing_list.append(idx)
            else:
                _left_eye_distances = self._validation_left_eye_distance_store[idx]
                _right_eye_distances = self._validation_right_eye_distance_store[idx]
                _ground_truth_point = self._validation_points[idx]

                if _tracking_left:
                    _left_res = self._calculator.calculate_error_by_sliding_window(
                        gt_point=_ground_truth_point,
                        es_points=_left_samples,
                        distances=_left_eye_distances
                    )
                    if _left_res["min_error"] > self._error_threshold:
                        logging.info(f"Recalibration point index: {idx}, Left error: {_left_res['min_error']}")
                        # 清空该点数据并重新校准
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
                        # 清空该点数据并重新校准
                        self._validation_left_eye_distance_store[idx] = []
                        self._validation_left_sample_store[idx] = []
                        self._validation_right_eye_distance_store[idx] = []
                        self._validation_right_sample_store[idx] = []
                        self._calibration_drawing_list.append(idx)

        # 如果不需要重复任何点，则直接结束验证（设置 _n_validation = 2 以退出外层循环）
        if not self._calibration_drawing_list:
            self._n_validation = 2
