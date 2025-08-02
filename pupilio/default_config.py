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
# Default configuration file

# Author: GC Zhu
# Email: zhugc2016@gmail.com
# date: 2024/12/13

import os
from pathlib import Path
from .callback import CalibrationListener
from .misc import CalibrationMode, ActiveEye


class DefaultConfig:
    """
    Default configuration class containing various parameters required for program execution.
    Includes settings for file paths, hyperparameters, and resources like images and audio.

    Attributes:

        Filter Hyperparameters:
            `look_ahead` (int): Look-ahead steps for predicting target position.

        Calibration Resources:
            `cali_target_beep` (str): Path to the beep sound used during calibration.
            `cali_frowning_face_img` (str): Path to the frowning face image used during calibration.
            `cali_smiling_face_img` (str): Path to the smiling face image used during calibration.
            `cali_target_img` (str): Path to the windmill image used as the calibration target.

        Calibration Target Settings:
            `cali_target_img_maximum_size` (int): Maximum size of the calibration target image.
            `cali_target_img_minimum_size` (int): Minimum size of the calibration target image.
            `cali_target_animation_frequency` (int): Frequency of the calibration target animation (in Hz).

        Calibration Mode:
            `cali_mode` (CalibrationMode): Specifies the calibration mode, default is TWO_POINTS.

        Kappa Angle Verification:
            `enable_kappa_verification` (int): Verification of the kappa angle after calibration. Default is 1.
                                         When this value is 0, the verification of the kappa angle after calibration
                                         is disabled, suitable for users with strabismus.

        Debug Settings:
            - `enable_debug_logging` (int): Toggle for enabling debug logging. Disabled by default (0).
            - `log_directory` (str): Directory path for storing debug logs.

        Calibration Instructions:
            - `instruction_face_far` (str): Instruction when the face is too close.
            - `instruction_face_near` (str): Instruction when the face is too far.
            - `instruction_head_center` (str): Instruction to align the head to the center of the frame.
            - `instruction_enter_calibration` (str): Instruction for entering calibration.
            - `instruction_hands_free_calibration` (str): Instruction for hands-free calibration.

        Validation Instructions:
            - `instruction_enter_validation` (str): Instruction for entering validation.

        Validation Legends:
            - `legend_target` (str): Legend for target points.
            - `legend_left_eye` (str): Legend for left eye gaze.
            - `legend_right_eye` (str): Legend for right eye gaze.
            - `instruction_calibration_over` (str): Instruction for continuing after validation.
            - `instruction_recalibration` (str): Instruction for initiating recalibration.

        Calibration Previewing:
            - `face_previewing` (int): Whether show calibration previewing,default is 1.

        Active Eye:
            - `active_eye` (str): Which one or two eyes you want to track.`

        Simulation mode:
            - `simulation_mode` (bool): Switch of simulation mode. If true, use your mouse to replace the eye position.
                Default is false.
    """

    def __init__(self):
        # Get the absolute path of the current file's directory
        self._current_dir = os.path.abspath(os.path.dirname(__file__))

        # Filter hyperparameters
        self.look_ahead: int = 2  # Look-ahead steps for predicting target position

        # Font settings
        # self.font_name = "Microsoft YaHei UI Light"  # Font used for displaying text

        # Calibration resource file paths
        # calibration instruction wav file
        self.calibration_instruction_sound_path = os.path.join(
            self._current_dir,
            "asset",
            "calibration_instruction.wav")  # Path to the calibration instruction wav file

        # Sound file for target beep during calibration
        self.cali_target_beep = os.path.join(
            self._current_dir,
            "asset",
            "beep.wav")  # Path to the calibration target beep sound

        # Calibration face images
        self.cali_frowning_face_img = os.path.join(
            self._current_dir,
            "asset",
            "frowning-face.png")  # Path to frowning face image

        self.cali_smiling_face_img = os.path.join(
            self._current_dir,
            "asset",
            "smiling-face.png")  # Path to smiling face image

        # Calibration target image
        self.cali_target_img = os.path.join(
            self._current_dir,
            "asset",
            "windmill.png")  # Path to windmill image used as calibration target

        # Calibration target image size limits
        self.cali_target_img_maximum_size = 60  # Maximum size of the calibration target image
        self.cali_target_img_minimum_size = 30  # Minimum size of the calibration target image

        # Calibration target animation frequency
        self.cali_target_animation_frequency = 2  # Frequency of the calibration target animation (in Hz)

        # Calibration mode (either 2 or 5)
        self.cali_mode = CalibrationMode.TWO_POINTS  # Default to TWO_POINTS calibration mode

        # Verification of the kappa angle after calibration, default is 1 (verify the estimated kappa angle).
        # When this value is 0, the verification of the kappa angle after calibration
        # is disabled, allowing calibration for users with strabismus.
        self.enable_kappa_verification = 1

        # calibration listener
        self.calibration_listener: CalibrationListener = CalibrationListener()

        # save validation result
        self.enable_validation_result_saving = 1

        # debug parameters
        self.enable_debug_logging = 0
        self.log_directory = str(Path.home().absolute() / "Pupilio" / "native_log")

        # instructions for face previewing during calibration
        # Face previewing and head pose adjustment instructions
        self.instruction_face_far = "Move further away"  # face is too close
        self.instruction_face_near = "Move closer"  # face is too far
        self.instruction_head_center = "Move your head to the center of the box"  # move head into the headbox

        # Calibration entry instructions
        # entering manual calibration
        self.instruction_enter_calibration = (
            "Two points will appear. Please look at them in sequence.\n"
            "Press Enter / click the left mouse button (or touch the screen) to start calibration."
        )
        # hands-free calibration
        self.instruction_hands_free_calibration = (
            "After the countdown, several points will appear. Please look at them in sequence."
        )

        # Validation entry instructions
        self.instruction_enter_validation = (
            "Five points will appear. Please look at them.\n"
            "Press Enter / click the left mouse button (or touch the screen) to start validation."
        )

        # Validation result legends
        self.legend_target = "Target"  # Legend label for target points (legend_target)
        self.legend_left_eye = "Left Eye Gaze"  # Legend label for left eye gaze (legend_left_eye)
        self.legend_right_eye = "Right Eye Gaze"  # Legend label for right eye gaze (legend_right_eye)
        self.instruction_calibration_over = (
            "Press \"Enter\" / click on the left mouse to continue."
        )  # Instruction for continuing after validation (legend_continue)
        self.instruction_recalibration = (
            "Press \"R\" / click on the right mouse button to recalibrate."
        )  # Instruction for initiating recalibration (legend_recalibration)

        #
        self._lang = "zh-CN"
        self.instruction_language()

        # show preview? 0=no, 1=yes
        self.face_previewing = 1

        self.active_eye = ActiveEye.BINO_EYE

        self._simulation_mode = False

    @property
    def cali_mode(self):
        return self._cali_mode

    @cali_mode.setter
    def cali_mode(self, mode):
        if isinstance(mode, CalibrationMode):
            self._cali_mode = mode
        elif mode == 2:
            self._cali_mode = CalibrationMode.TWO_POINTS
        elif mode == 5:
            self._cali_mode = CalibrationMode.FIVE_POINTS  # Assuming FIVE_POINTS exists in CalibrationMode
        else:
            raise ValueError("Invalid calibration mode. Must be 2, 5, or a CalibrationMode instance.")

    @property
    def active_eye(self):
        return self._active_eye

    @active_eye.setter
    def active_eye(self, mode):
        if isinstance(mode, ActiveEye):
            self._active_eye = mode
        elif mode == -1:
            self._active_eye = ActiveEye.LEFT_EYE
        elif mode == 1:
            self._active_eye = ActiveEye.RIGHT_EYE
        elif mode == "left":
            self._active_eye = ActiveEye.LEFT_EYE
        elif mode == "right":
            self._active_eye = ActiveEye.RIGHT_EYE
        elif mode == 0:
            self._active_eye = ActiveEye.BINO_EYE
        elif mode == "bino":
            self._active_eye = ActiveEye.BINO_EYE
        else:
            raise ValueError("Invalid tracking mode. Must be 0 (bino), -1 (left eye), "
                             "1 (right eye), left, right, or bino.")

    @property
    def simulation_mode(self):
        return self._simulation_mode

    @simulation_mode.setter
    def simulation_mode(self, value):
        if isinstance(value, bool):
            pass  # OK
        elif isinstance(value, int):
            if value not in (0, 1):
                raise TypeError(f"simulation_mode must be a bool or 0/1, got {type(value).__name__}")
            value = bool(value)  # 宽容处理 0/1
        else:
            raise TypeError(f"simulation_mode must be a bool or 0/1, got {type(value).__name__}")

        self._simulation_mode = value

    def instruction_language(self, lang='zh-CN'):
        """
        Update the instructions and legends based on the specified language.

        Args:
            lang (str): The language to update to. Supported values are:
                - 'zh-CN': Updates instructions to Simplified Chinese.
                - 'zh-HK': Updates instructions to Traditional Chinese.
                - 'en-US': Updates instructions to English.
                - 'fr-FR': Updates instructions to French.
                - 'es-ES': Updates instructions to Spanish.
                - 'jp-JP': Updates instructions to Japanese.
                - 'ko-KR': Updates instructions to Korean.

        Raises:
            ValueError: If an unsupported language is specified.
        """

        self._lang = lang
        if lang in ['zh-CN', 'zh-SG']:
            self.simplified_chinese()
        elif lang in ['zh-HK', 'zh-TW', 'zh-MO']:
            self.traditional_chinese()
        elif 'en-' in lang:
            self.english()
        elif 'fr' in lang:
            self.french()
        elif lang == 'es-ES':
            self.spanish()
        elif lang == "jp-JP":
            self.japanese()
        elif lang == "ko-KR":
            self.korean()
        else:
            raise ValueError(f"Unsupported language: {lang}")

    def simplified_chinese(self):
        """
        Update all instructions and legends to Simplified Chinese.
        """
        # Calibration preview instructions
        self.instruction_face_far = "请后移一些"
        self.instruction_face_near = "请靠近一些"
        self.instruction_head_center = "请将头移动到方框中央"

        # Calibration entry instructions
        self.instruction_enter_calibration = "屏幕上会出现两个点，请依次注视这些点\n" \
                                             "按回车键或鼠标左键(或触击屏幕)开始校准"

        self.instruction_hands_free_calibration = (
            "倒计时结束后屏幕上会出现几个点，请依次注视这些点"
        )

        # Validation entry instructions
        self.instruction_enter_validation = (
            "屏幕上会出现五个点，请依次注视这些点\n"
            "按回车键或鼠标左键(或触击屏幕)开始验证"
        )

        # Validation result legends
        self.legend_target = "目标点"
        self.legend_left_eye = "左眼注视点"
        self.legend_right_eye = "右眼注视点"
        self.instruction_calibration_over = (
            "按\"回车键\"或鼠标左键(触击屏幕)继续"
        )
        self.instruction_recalibration = (
            "按\"R\"键或鼠标右键(长按屏幕)重新校准"
        )

    def english(self):
        # Calibration preview instructions
        self.instruction_face_far = "Move farther back"
        self.instruction_face_near = "Move closer"
        self.instruction_head_center = "Move your head to the center of the box"

        # Calibration entry instructions
        self.instruction_enter_calibration = "Two points will appear on screen, please look at them in sequence\n" \
                                             "Press Enter or left-click the mouse (or touch the screen) to start calibration"

        self.instruction_hands_free_calibration = (
            "Following the countdown, several points will appear on screen, please look at them in sequence"
        )

        # Validation entry instructions
        self.instruction_enter_validation = (
            "Five points will appear on screen, please look at them in sequence\n"
            "Press Enter or left-click the mouse (or touch the screen) to start validation."
        )

        # Validation result legends
        self.legend_target = "Target"
        self.legend_left_eye = "Left Eye Gaze"
        self.legend_right_eye = "Right Eye Gaze"
        self.instruction_calibration_over = (
            "Press \"Enter\" or left-click (click the screen) to continue."
        )
        self.instruction_recalibration = (
            "Press \"R\" or right-click (long press the screen) to recalibrate."
        )

    def french(self):
        # Calibration preview instructions
        self.instruction_face_far = "Veuillez vous éloigner"
        self.instruction_face_near = "Veuillez vous rapprocher"
        self.instruction_head_center = "Veuillez centrer votre tête dans l'image"

        # Calibration entry instructions
        self.instruction_enter_calibration = "Deux points apparaîtront à l'écran, veuillez les regarder dans l'ordre\n" \
                                             "Appuyez sur Entrée ou cliquez à gauche (cliquez sur l'écran) pour commencer l'étalonnage"

        self.instruction_hands_free_calibration = (
            "Après le compte à rebours, plusieurs points apparaîtront à l'écran, veuillez les regarder dans l'ordre."
        )

        # Validation entry instructions
        self.instruction_enter_validation = (
            "Cinq points apparaîtront à l'écran, veuillez les regarder.\n"
            "Appuyez sur Entrée ou cliquez sur l'écran (ou cliquez à gauche) pour commencer la validation."
        )

        # Validation result legends
        self.legend_target = "Point cible"
        self.legend_left_eye = "Point de focus œil gauche"
        self.legend_right_eye = "Point de focus œil droit"
        self.instruction_calibration_over = (
            "Appuyez sur \"Entrée\" ou cliquez à gauche (cliquez sur l'écran) pour continuer."
        )
        self.instruction_recalibration = (
            "Appuyez sur \"R\" ou cliquez à droite (maintenez l'écran) pour recalibrer."
        )

    def spanish(self):
        # Calibration preview instructions
        self.instruction_face_far = "Por favor, retroceda"
        self.instruction_face_near = "Por favor, acérquese"
        self.instruction_head_center = "Por favor, centre su cabeza en la pantalla"

        # Calibration entry instructions
        self.instruction_enter_calibration = \
            ("Aparecerán dos puntos en la pantalla, por favor mírelos en orden\n"
             "Presione Enter o haga clic con el botón izquierdo "
             "(haga clic en la pantalla) para comenzar la calibración")

        self.instruction_hands_free_calibration = (
            "Después de la cuenta regresiva, aparecerán varios puntos en la pantalla, por favor mírelos en orden."
        )

        # Validation entry instructions
        self.instruction_enter_validation = (
            "Aparecerán cinco puntos en la pantalla, por favor mírelos.\n"
            "Presione Enter o haga clic en la pantalla (o haga clic con el botón izquierdo) para comenzar la validación."
        )

        # Validation result legends
        self.legend_target = "Punto objetivo"
        self.legend_left_eye = "Punto de enfoque ojo izquierdo"
        self.legend_right_eye = "Punto de enfoque ojo derecho"
        self.instruction_calibration_over = (
            "Presione \"Enter\" o haga clic con el botón \nizquierdo (haga clic en la pantalla) para continuar."
        )
        self.instruction_recalibration = (
            "Presione \"R\" o haga clic con el botón derecho \n(mantenga presionada la pantalla) para recalibrar."
        )

    def traditional_chinese(self):
        # Calibration preview instructions
        self.instruction_face_far = "請後移一些"
        self.instruction_face_near = "請靠近一些"
        self.instruction_head_center = "請將頭移到畫面中央"

        # Calibration entry instructions
        self.instruction_enter_calibration = "畫面上會出現兩個點，請按順序注視這些點\n" \
                                             "按下回車鍵或鼠標左鍵(點擊螢幕)開始校準"

        self.instruction_hands_free_calibration = (
            "倒數計時後畫面會顯示幾個點，請按順序注視這些點。"
        )

        # Validation entry instructions
        self.instruction_enter_validation = (
            "畫面上會出現五個點，請注視這些點。\n"
            "按下回車鍵或點擊螢幕（或者鼠標左鍵）開始驗證。"
        )

        # Validation result legends
        self.legend_target = "目標點"
        self.legend_left_eye = "左眼注視點"
        self.legend_right_eye = "右眼注視點"
        self.instruction_calibration_over = (
            "按下\"回車鍵\"或鼠標左鍵(點擊螢幕)繼續。"
        )
        self.instruction_recalibration = (
            "按下\"R\"鍵或鼠標右鍵(長按螢幕)重新校準。"
        )

    def japanese(self):
        # Calibration preview instructions
        self.instruction_face_far = "もっと後ろに移動してください"
        self.instruction_face_near = "もっと近づいてください"
        self.instruction_head_center = "画面の中央に頭を移動してください"

        # Calibration entry instructions
        self.instruction_enter_calibration = "画面に2つの点が表示されますので、その順番で注視してください\nEnterキーまたは左クリック（画面をクリック）でキャリブレーションを開始します"

        self.instruction_hands_free_calibration = (
            "カウントダウン後、画面にいくつかの点が表示されますので、その順番で注視してください。"
        )

        # Validation entry instructions
        self.instruction_enter_validation = (
            "画面に5つの点が表示されますので、それらを注視してください。\n"
            "Enterキーまたは左クリック（画面をクリック）で検証を開始します。"
        )

        # Validation result legends
        self.legend_target = "ターゲットポイント"
        self.legend_left_eye = "左目の注視点"
        self.legend_right_eye = "右目の注視点"
        self.instruction_calibration_over = (
            "「Enterキー」または左クリック（画面をクリック）で続行します。"
        )
        self.instruction_recalibration = (
            "「R」キーまたは右クリック（画面を長押し）で再キャリブレーションします。"
        )

    def korean(self):
        # Calibration preview instructions
        self.instruction_face_far = "조금 더 뒤로 가주세요"
        self.instruction_face_near = "조금 더 가까이 가세요"
        self.instruction_head_center = "화면 중앙에 머리를 위치시켜 주세요"

        # Calibration entry instructions
        self.instruction_enter_calibration = "화면에 두 개의 점이 나타나면 순서대로 주시하세요\nEnter 키 또는 왼쪽 클릭(화면 클릭)으로 교정 시작"

        self.instruction_hands_free_calibration = (
            "카운트다운 후 화면에 여러 점이 나타납니다. 순서대로 주시해주세요."
        )

        # Validation entry instructions
        self.instruction_enter_validation = (
            "화면에 다섯 개의 점이 나타납니다. 그 점들을 주시해주세요.\n"
            "Enter 키 또는 왼쪽 클릭(화면 클릭)으로 검증을 시작합니다."
        )

        # Validation result legends
        self.legend_target = "목표 점"
        self.legend_left_eye = "왼쪽 눈 주시점"
        self.legend_right_eye = "오른쪽 눈 주시점"
        self.instruction_calibration_over = (
            "「Enter 키」 또는 왼쪽 클릭(화면 클릭)으로 계속 진행합니다."
        )
        self.instruction_recalibration = (
            "「R」 키 또는 오른쪽 클릭(화면 길게 누르기)으로 재교정합니다."
        )
