# _*_ coding: utf-8 _*_
# Author: GC Zhu
# Email: zhugc2016@gmail.com
import os
import time
import math
import random
import logging
from datetime import datetime
from pathlib import Path
import json
import pygame
import numpy as np

from .misc import ET_ReturnCode, Calculator
from .callback import CalibrationListener

logger = logging.getLogger(__name__)

SCREEN_CENTER_X = 960.0
SCREEN_CENTER_Y = 540.0
SCALE_X = 7.0
SCALE_Y = 10.0
BEST_RANGE_R = 80.0
BOUNDARY_R = 320.0
K_Z_RADIUS = 1.0
MIN_FACE_R = 10.0
Z_OPTIMAL_BASE = -500.0
Z_SAFE_MIN = -600.0
Z_SAFE_MAX = -400.0
LINE_THICK_BOUND = 6
LINE_THICK_BEST = 3

COLOR_GREEN = (0, 255, 0)
COLOR_RED = (255, 0, 0)
COLOR_YELLOW = (255, 255, 0)
COLOR_BLACK = (0, 0, 0)
COLOR_CRIMSON = (220, 20, 60)
COLOR_CORAL = (240, 128, 128)


class CalibrationUI:
    """
    Backend-agnostic calibration and validation routine.

    Owns the whole participant-facing flow: head-position adjustment with an optional live
    camera preview, the animated calibration targets, and an optional validation pass that
    reports per-point accuracy in degrees of visual angle. All drawing goes through a
    :class:`~pupilio.ui_backend.UIBackend`, so the same routine runs under Pygame and
    PsychoPy. Audio is always played through ``pygame.mixer`` so cues sound identical on
    either backend.

    The flow is a state machine advanced by :meth:`draw`, whose phases are tracked by the
    ``_phase_*`` and ``_*_preparing`` flags reset in :meth:`initialize_variables`.
    """

    def __init__(self, pupil_io, ui_backend):
        """
        Prepare the calibration UI for a single run.

        Loads the audio cues, measures the screen through the backend, and shuffles the four
        peripheral validation targets so participants cannot anticipate the order; the
        central target is always validated last.

        Args:
            pupil_io (Pupilio): Connected tracker instance to calibrate.
            ui_backend (UIBackend): Drawing and input backend to render through.
        """
        self._pupil_io = pupil_io
        self.ui = ui_backend
        self.config = self._pupil_io.config

        # --- 声音系统完全依赖 pygame，确保跨端行为一致 ---
        pygame.mixer.init()
        self._sound_beep = pygame.mixer.Sound(self.config.cali_target_beep)
        self._sound_ins = pygame.mixer.Sound(self.config.calibration_instruction_sound_path)
        self._sound_pos = pygame.mixer.Sound(os.path.join(self.config._current_dir, "asset", "adjust_position.wav"))
        self._just_pos_sound_once = False

        self._screen_width, self._screen_height = self.ui.get_screen_size()

        import platform
        self._font_name = "microsoftyaheiui" if platform.system().lower() == 'windows' else "Arial"

        self._calculator = Calculator(
            screen_width=self._screen_width,
            screen_height=self._screen_height,
            physical_screen_width=34.13,
            physical_screen_height=19.32
        )

        self._validation_points = [[0.5, 0.08], [0.08, 0.5], [0.92, 0.5], [0.5, 0.92]]
        random.shuffle(self._validation_points)
        self._validation_points.append([0.5, 0.5])
        # 转换为像素坐标系(左上角基准)
        for p in self._validation_points:
            p[0] = int(p[0] * self._screen_width)
            p[1] = int(p[1] * self._screen_height)

        self.initialize_variables()

    def initialize_variables(self):
        """
        Reset the state machine to its starting phase.

        Called before each run so a recalibration begins from head adjustment with empty
        sample stores rather than inheriting the previous attempt's state.
        """
        self._exit = False
        self._phase_adjust_position = True
        self._calibration_preparing = False
        self._validation_preparing = False
        self._phase_calibration = False
        self._phase_validation = False
        self._phase_calibration_failed = False
        self._need_validation = False
        self._drawing_validation_result = False
        self._calibration_drawing_list = [0, 1, 2, 3, 4]

        self._calibration_point_index = 0
        self._calibration_timer = 0
        self._validation_timer = 0

        self._validation_left_sample_store = [[] for _ in range(5)]
        self._validation_right_sample_store = [[] for _ in range(5)]
        self._validation_left_eye_distance_store = [[] for _ in range(5)]
        self._validation_right_eye_distance_store = [[] for _ in range(5)]

        self._n_validation = 0
        self._error_threshold = 2
        self._hands_free_adjust_head_wait_time = 11
        self._hands_free_start_timestamp = 0
        self._validation_finished_timer = 0
        self._preparing_hands_free_start = 0

    def play_sound(self, snd):
        """
        Play an audio cue, ignoring failures.

        Audio is a non-essential cue, so a missing device or busy mixer must not abort
        calibration.

        Args:
            snd (pygame.mixer.Sound): The cue to play.
        """
        try:
            snd.play()
        except Exception:
            logger.debug("Failed to play calibration sound.", exc_info=True)

    def stop_sound(self, snd):
        """
        Stop an audio cue, ignoring failures.

        Args:
            snd (pygame.mixer.Sound): The cue to stop.
        """
        try:
            snd.stop()
        except Exception:
            logger.debug("Failed to stop calibration sound.", exc_info=True)

    def _draw_text_center(self, text, x_offset=0, y_offset=0):
        """
        Draw multi-line text centred on screen.

        Args:
            text (str): Text to draw; ``\\n`` starts a new line, stacked 40 px apart.
            x_offset (int): Horizontal shift from screen centre, in pixels.
            y_offset (int): Vertical shift from screen centre, in pixels.
        """
        lines = text.split("\n")
        shift = 0
        cx = self._screen_width // 2 + x_offset
        cy = self._screen_height // 2 + y_offset
        for t in lines:
            self.ui.draw_text(t, self._font_name, 32, COLOR_BLACK, (cx - 400, cy + shift - 20, 800, 40))
            shift += 40

    def _draw_adjust_position(self):
        """
        Draw the head-positioning guide for one frame.

        Maps the tracked face onto screen as a circle whose size follows viewing distance and
        whose colour fades green to red as the participant leaves the optimal range, inside a
        boundary box that turns red when the face drifts out of the head box. In hands-free
        mode, holding a good position for the countdown advances to calibration automatically;
        drifting out resets the countdown.
        """
        if not self._just_pos_sound_once:
            if self._hands_free:
                self.play_sound(self._sound_pos)
            self._just_pos_sound_once = True

        _status, _face_position = self._pupil_io.face_position()
        face_mm_z = _face_position[2]
        face_x_offset = 32.0 if self._pupil_io.config.active_eye in [-1, 'left'] else (
            -32.0 if self._pupil_io.config.active_eye in [1, 'right'] else 0.0)

        # 转换为左上角像素坐标
        face_px_x = SCREEN_CENTER_X + (_face_position[0] - 172.08 + face_x_offset) * SCALE_X
        y_offset = 110.0 if self._pupil_io.config.sampling_rate == 200 else 130.0
        face_px_y = SCREEN_CENTER_Y + (_face_position[1] - y_offset) * SCALE_Y

        instruction_text = ""
        if face_mm_z > Z_SAFE_MAX or face_mm_z < Z_SAFE_MIN:
            face_rgb = COLOR_RED
            instruction_text = self.config.instruction_face_far if face_mm_z > Z_SAFE_MAX else self.config.instruction_face_near
        else:
            ratio = min(abs(face_mm_z - Z_OPTIMAL_BASE) / 100.0, 1.0)
            # RGB 过渡：绿 到 红
            face_rgb = (int(COLOR_RED[0] * ratio + COLOR_GREEN[0] * (1 - ratio)),
                        int(COLOR_RED[1] * ratio + COLOR_GREEN[1] * (1 - ratio)), 0)

        face_radius = max(BEST_RANGE_R + (face_mm_z - Z_OPTIMAL_BASE) * K_Z_RADIUS, MIN_FACE_R)

        dx = face_px_x - SCREEN_CENTER_X
        dy = face_px_y - SCREEN_CENTER_Y
        is_inside_bound = (np.sqrt(dx ** 2 + dy ** 2) + face_radius) <= BOUNDARY_R

        bound_color = COLOR_GREEN if is_inside_bound else COLOR_RED

        # 绘制边界框
        self.ui.draw_rect((int(SCREEN_CENTER_X - BOUNDARY_R), int(SCREEN_CENTER_Y - BOUNDARY_R),
                           int(BOUNDARY_R * 2), int(BOUNDARY_R * 2)), bound_color, LINE_THICK_BOUND)

        # 绘制人脸图片 (自动缩放)
        face_img = self.config.cali_frowning_face_img if face_mm_z > Z_SAFE_MAX or face_mm_z < Z_SAFE_MIN else self.config.cali_smiling_face_img
        r_size = int(face_radius * 3)
        self.ui.draw_image(face_img, (int(face_px_x - r_size // 2), int(face_px_y - r_size // 2), r_size, r_size))

        # 绘制最优圈
        self.ui.draw_circle(SCREEN_CENTER_X, SCREEN_CENTER_Y, BEST_RANGE_R, COLOR_YELLOW, LINE_THICK_BEST)

        if instruction_text:
            self._draw_text_center(instruction_text, x_offset=int(face_px_x - SCREEN_CENTER_X),
                                   y_offset=int(face_px_y + face_radius + 20 - SCREEN_CENTER_Y))

        if self._hands_free:
            safe_z_range = (Z_SAFE_MIN <= face_mm_z <= Z_SAFE_MAX)
            if safe_z_range and is_inside_bound and self._hands_free_adjust_head_wait_time <= 0:
                self._phase_adjust_position = False
                self._calibration_preparing = True
            elif safe_z_range and is_inside_bound:
                if self._hands_free_start_timestamp == 0:
                    self._hands_free_start_timestamp = time.time()
                else:
                    now = time.time()
                    self._hands_free_adjust_head_wait_time -= (now - self._hands_free_start_timestamp)
                    self._hands_free_start_timestamp = now
            else:
                self._hands_free_start_timestamp = 0

    def _draw_previewer(self):
        """
        Draw the live camera preview for both eyes.

        Each frame is rotated and flipped into screen orientation, then drawn to the outer
        edges of the display so the central head-position guide stays unobstructed.
        """
        _left_img, _right_img = self._pupil_io.get_preview_images()
        import cv2
        _left_img = cv2.resize(_left_img, (512, 512))
        _right_img = cv2.resize(_right_img, (512, 512))
        # _left_img = cv2.rotate(cv2.resize(_left_img, (512, 512)), cv2.ROTATE_180)
        # _right_img = cv2.rotate(cv2.resize(_right_img, (512, 512)), cv2.ROTATE_180)
        # _left_img = cv2.flip(_left_img, 0)
        # _right_img = cv2.flip(_right_img, 0)

        cy = self._screen_height // 2
        # 左眼
        self.ui.draw_texture(_left_img, (79, cy - 256, 512, 512))
        # 右眼
        self.ui.draw_texture(_right_img, (self._screen_width - 512 - 79, cy - 256, 512, 512))

    def _clear_pending_input(self):
        """
        Drop buffered key presses and clicks.

        Called when a screen that waits for a response appears, so input the participant made
        during the previous phase cannot dismiss it before they have seen it.
        """
        self.ui.clear_events()

    def _should_prompt_on_calibration_failure(self):
        """
        Decide whether a failed calibration should ask the participant what to do.

        The prompt is skipped in hands-free mode, where nobody can answer it, and when kappa
        verification is disabled, since the failure it reports is the one being ignored.

        Returns:
            bool: True if the retry-or-skip screen should be shown.
        """
        return not self._hands_free and bool(self.config.enable_kappa_verification)

    def _finish_calibration(self):
        """
        Leave the calibration phase for validation, or exit when validation is not wanted.
        """
        self._phase_calibration = False
        self._phase_calibration_failed = False
        if self._need_validation:
            self._validation_preparing = not self._hands_free
            self._phase_validation = self._hands_free
            self._clear_pending_input()
        else:
            self._exit = True

    def _draw_calibration_failed(self):
        """
        Ask the participant whether to recalibrate or continue after a failed calibration.

        Shown when the tracker rejects the calibration, typically because the estimated kappa
        angle failed verification. The routine waits here until the participant chooses.
        """
        self._draw_text_center(
            f"{self.config.instruction_calibration_failed}\n"
            f"{self.config.instruction_recalibration}\n"
            f"{self.config.instruction_calibration_over}"
        )

    def _draw_calibration_point(self):
        """
        Show the current calibration target and feed samples to the tracker.

        Draws the target with a ping-pong size animation that draws the eye to it, and calls
        :meth:`~pupilio.core.Pupilio.calibration` each frame. Advances to the next target or
        ends the calibration phase according to the returned status code, notifying
        ``config.calibration_listener`` whenever a new target appears.
        """
        if self._calibration_timer == 0:
            self.stop_sound(self._sound_beep)
            self.play_sound(self._sound_beep)
            self._calibration_timer = time.time()

        time_elapsed = time.time() - self._calibration_timer
        _status = self._pupil_io.calibration(self._calibration_point_index)

        if _status == ET_ReturnCode.ET_CALI_NEXT_POINT.value:
            if self._calibration_point_index + 1 == len(self._pupil_io.calibration_points):
                self._finish_calibration()
            else:
                self._calibration_point_index += 1
                self._calibration_timer = 0
                if hasattr(self.config, 'calibration_listener') and self.config.calibration_listener:
                    self.config.calibration_listener.on_calibration_target_onset(self._calibration_point_index)
        elif _status == ET_ReturnCode.ET_SUCCESS.value:
            self.stop_sound(self._sound_beep)
            self._finish_calibration()
        elif _status == ET_ReturnCode.ET_FAILED.value:
            self.stop_sound(self._sound_beep)
            self._phase_calibration = False
            if self._should_prompt_on_calibration_failure():
                self._phase_calibration_failed = True
                self._clear_pending_input()
            else:
                self._finish_calibration()
            return

        # 绘制呼吸效果风车
        _point = self._pupil_io.calibration_points[self._calibration_point_index]
        cx = int(_point[0] * self._screen_width) if _point[0] <= 1.0 else int(_point[0])
        cy = int(_point[1] * self._screen_height) if _point[1] <= 1.0 else int(_point[1])

        anim_idx = int(time_elapsed // (1 / (self.config.cali_target_animation_frequency * 10))) % 20
        anim_idx = anim_idx if anim_idx < 10 else 19 - anim_idx  # Ping-pong effect
        _max, _min = self.config.cali_target_img_maximum_size, self.config.cali_target_img_minimum_size
        size = int(_min + (_max - _min) * anim_idx / 9)
        self.ui.draw_image(self.config.cali_target_img, (cx - size // 2, cy - size // 2, size, size))

    def draw(self, validate=False, bg_color=(255, 255, 255), hands_free=False):
        """
        Run the calibration routine, blocking until it finishes.

        Drives the phase sequence head adjustment, calibration, and optionally validation,
        dispatching on input from the backend each frame: continue advances to the next
        phase, recali restarts from the validation result or calibration failure screen, and
        quit aborts. Buffered input is dropped whenever a screen that waits for a response
        appears, so a key pressed earlier cannot skip past it. Any existing calibration is
        discarded before starting.

        Args:
            validate (bool): Whether to run validation and show the accuracy report.
            bg_color (tuple): Background colour as RGB 0-255.
            hands_free (bool): When True, phases advance on timers rather than waiting for
                participant input.
        """
        self._pupil_io._recalibration()
        self.initialize_variables()
        self._hands_free = hands_free
        self._need_validation = validate
        self._clear_pending_input()

        self.ui.set_mouse_visible(getattr(self.config, 'simulation_mode', 0) == 1)

        while not self._exit:
            self.ui.before_draw(bg_color)

            action = self.ui.check_action()
            if action == 'quit':
                self._exit = True
            elif action == 'continue':
                if self._phase_adjust_position:
                    self._phase_adjust_position = False
                    self._calibration_preparing = True
                    self._clear_pending_input()
                elif self._calibration_preparing:
                    self._calibration_preparing = False
                    self._phase_calibration = True
                    self._clear_pending_input()
                    if hasattr(self.config, 'calibration_listener') and self.config.calibration_listener:
                        self.config.calibration_listener.on_calibration_target_onset(self._calibration_point_index)
                elif self._phase_calibration_failed:
                    # Accept the imperfect calibration and carry on.
                    self._clear_pending_input()
                    self._finish_calibration()
                elif self._validation_preparing:
                    self._validation_preparing = False
                    self._phase_validation = True
                    self._clear_pending_input()
                elif self._phase_validation and self._drawing_validation_result:
                    self._phase_validation = False
                    self._clear_pending_input()
            elif action == 'toggle_preview':
                if self._phase_adjust_position:
                    self.config.face_previewing = not getattr(self.config, 'face_previewing', True)
            elif action == 'recali' and (self._drawing_validation_result or self._phase_calibration_failed):
                self._phase_validation = False
                self._drawing_validation_result = False
                self._phase_calibration_failed = False
                self.draw(self._need_validation, bg_color, self._hands_free)
                return

            if self._phase_adjust_position:
                if self.config.face_previewing:
                    self._draw_previewer()
                self._draw_adjust_position()
            elif self._calibration_preparing:
                self._draw_text_center(self.config.instruction_enter_calibration)
            elif self._phase_calibration:
                self._draw_calibration_point()
            elif self._phase_calibration_failed:
                self._draw_calibration_failed()
            elif self._validation_preparing:
                self._draw_text_center(self.config.instruction_enter_validation)
            elif self._phase_validation:
                self._draw_validation_point()
            else:
                self._exit = True

            self.ui.after_draw()

        # Restore mouse visibility when exiting the calibration UI
        self.ui.set_mouse_visible(True)

        self.stop_sound(self._sound_beep)
        self.stop_sound(self._sound_ins)
        self.stop_sound(self._sound_pos)

    def draw_hands_free(self, validate=False, bg_color=(255, 255, 255)):
        """
        Run the calibration routine without requiring any input from the participant.

        Phases advance on timers instead of key presses or clicks, for participants who
        cannot operate an input device.

        Args:
            validate (bool): Whether to run validation and show the accuracy report.
            bg_color (tuple): Background colour as RGB 0-255.
        """
        self.draw(validate, bg_color, hands_free=True)

    def _draw_error_line(self, ground_truth_point, estimated_point, error_color):
        if estimated_point is None:
            return
            
        gt_x, gt_y = int(ground_truth_point[0]), int(ground_truth_point[1])
        es_x, es_y = int(estimated_point[0]), int(estimated_point[1])
        
        self.ui.draw_text("+", self._font_name, 32, COLOR_GREEN, (gt_x - 20, gt_y - 20, 40, 40))
        self.ui.draw_text("+", self._font_name, 32, error_color, (es_x - 20, es_y - 20, 40, 40))
        self.ui.draw_line(gt_x, gt_y, es_x, es_y, COLOR_BLACK, 1)

    def _draw_error_text(self, min_error, ground_truth_point, is_left=True):
        error_degrees = min_error
        height_position = 1
        if is_left:
            error_text = f"L: {error_degrees:.2f}°"
        else:
            error_text = f"R: {error_degrees:.2f}°"
            height_position += 1
            
        gt_x, gt_y = int(ground_truth_point[0]), int(ground_truth_point[1])
        
        text_h = 24
        y_offset = text_h * height_position
        
        self.ui.draw_text(error_text, self._font_name, 20, COLOR_BLACK, (gt_x - 100, gt_y + y_offset - 10, 200, 20))

    def _draw_recali_and_continue_tips(self):
        legend_texts = [
            getattr(self.config, 'instruction_calibration_over', "Press 'Enter' to continue"),
            getattr(self.config, 'instruction_recalibration', "Press 'R' to recalibrate")
        ]
        
        lang = getattr(self.config, '_lang', 'en-US')
        
        if 'en-' in lang:
            x = self._screen_width - 600
            y = self._screen_height - 96
        elif "zh-" in lang:
            x = self._screen_width - 464
            y = self._screen_height - 96
        elif "jp-" in lang:
            x = self._screen_width - 712
            y = self._screen_height - 96
        elif "ko-" in lang:
            x = self._screen_width - 464
            y = self._screen_height - 96
        elif 'fr-' in lang:
            x = self._screen_width - 715
            y = self._screen_height - 96
        elif 'es-' in lang:
            x = self._screen_width - 512
            y = self._screen_height - 144
        else:
            x = self._screen_width - 600
            y = self._screen_height - 96
            
        for content in legend_texts:
            for split_text in content.split("\n"):
                self.ui.draw_text(split_text, self._font_name, 20, COLOR_BLACK, (x, y - 10, 800, 20), align='left')
                y += 20 + 3

    def _draw_legend(self):
        legend_texts = [
            getattr(self.config, 'legend_target', "Target"), 
            getattr(self.config, 'legend_left_eye', "Left Eye"), 
            getattr(self.config, 'legend_right_eye', "Right Eye")
        ]
        color_list = [COLOR_GREEN, COLOR_CRIMSON, COLOR_CORAL]
        x = 128
        y = self._screen_height - 128

        for n, content in enumerate(legend_texts):
            self.ui.draw_text("+", self._font_name, 20, color_list[n], (x - 10, y - 10, 20, 20))
            _x = x + 15
            self.ui.draw_text(content, self._font_name, 20, COLOR_BLACK, (_x, y - 10, 400, 20), align='left')
            y += 20 + 3

    def _draw_validation_point(self):
        """
        Show the current validation target, or the accuracy report once all are done.

        While targets remain, displays each for 1.5 s and stores the valid gaze samples and
        viewing distances collected during that window. Once the list is exhausted, the
        first pass hands off to :meth:`_repeat_calibration_point` to re-run any target that
        failed its accuracy threshold; the second pass draws the report, showing per-eye
        error in degrees and a line from each target to the measured gaze position.
        """
        if not self._calibration_drawing_list:
            if self._n_validation == 1:
                self._repeat_calibration_point()
            else:
                if self._hands_free and not self._validation_finished_timer:
                    self._validation_finished_timer = time.time()
                elif self._hands_free and (time.time() - self._validation_finished_timer > 3):
                    self._phase_validation = False

                # 画图和显示误差
                for idx in range(len(self._validation_points)):
                    gt_pt = self._validation_points[idx]

                    if self._pupil_io.config.active_eye in [-1, 'left', 0, 'bino']:
                        res = self._calculator.calculate_error_by_sliding_window(
                            gt_pt, self._validation_left_sample_store[idx],
                            self._validation_left_eye_distance_store[idx]
                        )
                        if res and res["min_error"] < float('inf'):
                            self._draw_error_line(gt_pt, res["min_error_es_point"], COLOR_CRIMSON)
                            self._draw_error_text(res["min_error"], gt_pt, is_left=True)

                    if self._pupil_io.config.active_eye in [1, 'right', 0, 'bino']:
                        res = self._calculator.calculate_error_by_sliding_window(
                            gt_pt, self._validation_right_sample_store[idx],
                            self._validation_right_eye_distance_store[idx]
                        )
                        if res and res["min_error"] < float('inf'):
                            self._draw_error_line(gt_pt, res["min_error_es_point"], COLOR_CORAL)
                            self._draw_error_text(res["min_error"], gt_pt, is_left=False)

                self._draw_legend()
                self._draw_recali_and_continue_tips()

                if not self._drawing_validation_result:
                    self._clear_pending_input()
                self._drawing_validation_result = True
        else:
            if self._validation_timer == 0:
                self.stop_sound(self._sound_beep)
                self.play_sound(self._sound_beep)
                self._validation_timer = time.time()

            time_elapsed = time.time() - self._validation_timer
            if time_elapsed > 1.5:
                self._calibration_drawing_list.pop()
                self._validation_timer = 0
                if not self._calibration_drawing_list:
                    self._n_validation += 1
                self.stop_sound(self._sound_beep)
            else:
                idx = self._calibration_drawing_list[-1]
                pt = self._validation_points[idx]
                _status, _l_samp, _r_samp, _, _, _ = self._pupil_io.estimate_gaze()

                # 绘制靶点动画
                anim_idx = int(time_elapsed // (1 / (self.config.cali_target_animation_frequency * 10))) % 20
                anim_idx = anim_idx if anim_idx < 10 else 19 - anim_idx
                _max, _min = self.config.cali_target_img_maximum_size, self.config.cali_target_img_minimum_size
                size = int(_min + (_max - _min) * anim_idx / 9)
                self.ui.draw_image(self.config.cali_target_img,
                                   (int(pt[0] - size // 2), int(pt[1] - size // 2), size, size))

                if _l_samp[13] == 1:
                    self._validation_left_sample_store[idx].append([_l_samp[0], _l_samp[1]])
                    self._validation_left_eye_distance_store[idx].append(math.fabs(_l_samp[5]) / 10)
                if _r_samp[13] == 1:
                    self._validation_right_sample_store[idx].append([_r_samp[0], _r_samp[1]])
                    self._validation_right_eye_distance_store[idx].append(math.fabs(_r_samp[5]) / 10)

    def _repeat_calibration_point(self):
        """
        Queue validation targets that need a second attempt.

        A target is repeated when a tracked eye collected too few samples or its error
        exceeds ``_error_threshold`` degrees, which usually means a blink or a look away
        rather than a genuinely bad calibration. Repeated targets have their stored samples
        cleared first. When nothing needs repeating, validation is marked complete so the
        report can be drawn.
        """
        for idx in range(len(self._validation_points)):
            l_sam, r_sam = self._validation_left_sample_store[idx], self._validation_right_sample_store[idx]
            trk_l = self._pupil_io.config.active_eye in [-1, 'left', 0, 'bino']
            trk_r = self._pupil_io.config.active_eye in [1, 'right', 0, 'bino']

            needs_repeat = False
            if (len(l_sam) <= 5 and trk_l) or (len(r_sam) <= 5 and trk_r):
                needs_repeat = True
            else:
                if trk_l:
                    res = self._calculator.calculate_error_by_sliding_window(
                        self._validation_points[idx], l_sam, self._validation_left_eye_distance_store[idx]
                    )
                    if res["min_error"] > self._error_threshold: needs_repeat = True
                if trk_r:
                    res = self._calculator.calculate_error_by_sliding_window(
                        self._validation_points[idx], r_sam, self._validation_right_eye_distance_store[idx]
                    )
                    if res["min_error"] > self._error_threshold: needs_repeat = True

            if needs_repeat:
                self._validation_left_sample_store[idx].clear()
                self._validation_left_eye_distance_store[idx].clear()
                self._validation_right_sample_store[idx].clear()
                self._validation_right_eye_distance_store[idx].clear()
                self._calibration_drawing_list.append(idx)

        if not self._calibration_drawing_list:
            self._n_validation = 2