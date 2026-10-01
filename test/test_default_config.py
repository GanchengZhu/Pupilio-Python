# _*_ coding: utf-8 _*_
# Tests for pupilio.default_config: validation of the user-facing settings.

import os

import pytest

from pupilio.callback import CalibrationListener
from pupilio.default_config import DefaultConfig
from pupilio.misc import ActiveEye, CalibrationMode


@pytest.fixture
def config():
    return DefaultConfig()


class TestDefaults:
    def test_starts_in_two_point_binocular_mode(self, config):
        assert config.cali_mode == CalibrationMode.TWO_POINTS
        assert config.active_eye == ActiveEye.BINO_EYE

    def test_hardware_is_used_unless_simulation_is_requested(self, config):
        assert config.simulation_mode is False

    def test_sampling_rate_defaults_to_auto_select(self, config):
        # 0 means "let Pupilio.__init__ pick the highest supported rate"; the
        # literal None that used to signal this was unreachable through the
        # setter, so the sentinel is now 0.
        assert config.sampling_rate == 0

    def test_look_ahead_is_within_the_range_core_accepts(self, config):
        # Pupilio.__init__ rejects anything outside 0 < look_ahead <= 4.
        assert 0 < config.look_ahead <= 4

    def test_ships_with_a_default_calibration_listener(self, config):
        assert isinstance(config.calibration_listener, CalibrationListener)

    @pytest.mark.parametrize(
        "attribute",
        [
            "cali_target_beep",
            "calibration_instruction_sound_path",
            "cali_frowning_face_img",
            "cali_smiling_face_img",
            "cali_target_img",
        ],
    )
    def test_bundled_assets_exist_on_disk(self, config, attribute):
        # These are loaded eagerly by CalibrationUI, so a missing file breaks
        # calibration at the worst possible moment.
        assert os.path.isfile(getattr(config, attribute))

    def test_target_animation_sizes_are_ordered(self, config):
        assert config.cali_target_img_minimum_size < config.cali_target_img_maximum_size


class TestSamplingRate:
    @pytest.mark.parametrize("rate", [200, 400])
    def test_accepts_supported_rates(self, config, rate):
        config.sampling_rate = rate
        assert config.sampling_rate == rate

    def test_accepts_zero_as_auto_select(self, config):
        # 0 is the documented "auto-select the highest supported rate" sentinel,
        # resolved by Pupilio.__init__ against HARDWARE_RATES.
        config.sampling_rate = 0
        assert config.sampling_rate == 0

    @pytest.mark.parametrize("rate", [100, 300, 800, -200])
    def test_rejects_out_of_range_integers(self, config, rate):
        with pytest.raises(ValueError, match="sampling_rate"):
            config.sampling_rate = rate

    @pytest.mark.parametrize("rate", ["200", 200.0, None])
    def test_rejects_non_integers(self, config, rate):
        with pytest.raises(TypeError, match="int"):
            config.sampling_rate = rate

    @pytest.mark.parametrize("rate", [True, False])
    def test_rejects_bools(self, config, rate):
        # bool is a subclass of int; the setter must reject it explicitly so
        # True doesn't silently become rate 1 (and fail as out-of-range) or
        # False doesn't become 0 (auto-select).
        with pytest.raises(TypeError, match="int"):
            config.sampling_rate = rate


class TestCalibrationMode:
    @pytest.mark.parametrize(
        "value, expected",
        [
            (2, CalibrationMode.TWO_POINTS),
            (4, CalibrationMode.FOUR_POINTS),
            (5, CalibrationMode.FIVE_POINTS),
            (CalibrationMode.TWO_POINTS, CalibrationMode.TWO_POINTS),
            (CalibrationMode.FOUR_POINTS, CalibrationMode.FOUR_POINTS),
            (CalibrationMode.FIVE_POINTS, CalibrationMode.FIVE_POINTS),
        ],
    )
    def test_accepts_ints_and_enum_members(self, config, value, expected):
        config.cali_mode = value
        assert config.cali_mode == expected

    def test_accepts_zero_as_no_calibration(self, config):
        # 0 maps to CalibrationMode.NO_CALI, which cali_graphics uses to skip
        # the instruction screen entirely.
        config.cali_mode = 0
        assert config.cali_mode == CalibrationMode.NO_CALI

    def test_accepts_no_cali_enum_directly(self, config):
        config.cali_mode = CalibrationMode.NO_CALI
        assert config.cali_mode == CalibrationMode.NO_CALI

    @pytest.mark.parametrize("value", [1, 3, 6, "two", None])
    def test_rejects_unsupported_modes(self, config, value):
        with pytest.raises(ValueError):
            config.cali_mode = value

    @pytest.mark.parametrize("value", [True, False])
    def test_rejects_bools(self, config, value):
        # True == 1 and False == 0 in Python; without an explicit guard the
        # setter would bind them to TWO_POINTS and NO_CALI respectively.
        with pytest.raises(TypeError, match="bool"):
            config.cali_mode = value

    def test_changing_mode_rewrites_the_instructions(self, config):
        # The instruction text names the number of points, so it has to follow
        # the mode rather than go stale.
        config.instruction_language("en-US")
        config.cali_mode = 2
        two_point_text = config.instruction_enter_calibration

        config.cali_mode = 5
        assert config.instruction_enter_calibration != two_point_text

    def test_changing_mode_keeps_the_selected_language(self, config):
        config.instruction_language("zh-CN")
        config.cali_mode = 5
        assert config._lang == "zh-CN"


class TestActiveEye:
    @pytest.mark.parametrize(
        "value, expected",
        [
            (-1, ActiveEye.LEFT_EYE),
            (1, ActiveEye.RIGHT_EYE),
            (0, ActiveEye.BINO_EYE),
            ("left", ActiveEye.LEFT_EYE),
            ("right", ActiveEye.RIGHT_EYE),
            ("bino", ActiveEye.BINO_EYE),
            (ActiveEye.LEFT_EYE, ActiveEye.LEFT_EYE),
            (ActiveEye.RIGHT_EYE, ActiveEye.RIGHT_EYE),
            (ActiveEye.BINO_EYE, ActiveEye.BINO_EYE),
        ],
    )
    def test_accepts_every_documented_spelling(self, config, value, expected):
        config.active_eye = value
        assert config.active_eye == expected

    @pytest.mark.parametrize("value", [2, -2, "both", "LEFT", None])
    def test_rejects_anything_else(self, config, value):
        with pytest.raises(ValueError):
            config.active_eye = value

    @pytest.mark.parametrize("value", [True, False])
    def test_rejects_bools(self, config, value):
        # True == 1 and False == 0; without an explicit guard they would bind
        # to RIGHT_EYE and BINO_EYE respectively.
        with pytest.raises(TypeError, match="bool"):
            config.active_eye = value


class TestSimulationMode:
    @pytest.mark.parametrize("value, expected", [(True, True), (False, False), (1, True), (0, False)])
    def test_accepts_bools_and_zero_or_one(self, config, value, expected):
        config.simulation_mode = value
        assert config.simulation_mode is expected

    @pytest.mark.parametrize("value", [2, -1, "true", None, 1.0])
    def test_rejects_anything_else(self, config, value):
        with pytest.raises(TypeError):
            config.simulation_mode = value


class TestInstructionLanguage:
    @pytest.mark.parametrize(
        "lang",
        ["zh-CN", "zh-SG", "zh-HK", "zh-TW", "zh-MO", "en-US", "en-GB", "fr-FR", "es-ES", "jp-JP", "ko-KR"],
    )
    def test_supported_locales_populate_every_instruction(self, config, lang):
        config.instruction_language(lang)

        for attribute in (
            "instruction_face_far",
            "instruction_face_near",
            "instruction_head_center",
            "instruction_enter_calibration",
            "instruction_enter_validation",
            "legend_target",
            "legend_left_eye",
            "legend_right_eye",
        ):
            assert getattr(config, attribute)

    @pytest.mark.parametrize("lang", ["de-DE", "ru-RU", "klingon", ""])
    def test_unsupported_locales_raise(self, config, lang):
        with pytest.raises(ValueError):
            config.instruction_language(lang)

    @pytest.mark.parametrize("lang", ["en-AU", "en-CA", "fr-BE", "fr-CH", "es-MX", "es-AR", "ja-JP", "ko-KP"])
    def test_regional_variants_are_accepted_by_prefix(self, config, lang):
        # Language codes are matched by prefix so regional variants resolve to
        # the same translations as their canonical form. ja-JP is the ISO 639-1
        # code and must work alongside the shorthand jp-JP.
        config.instruction_language(lang)
        assert config._lang == lang

    def test_unsupported_locale_leaves_previous_language_intact(self, config):
        # A failed language switch must not leave _lang pointing at a code the
        # config cannot translate.
        config.instruction_language("en-US")
        with pytest.raises(ValueError):
            config.instruction_language("klingon")

        assert config._lang == "en-US"
        assert config.instruction_face_far == "Move farther back"

    def test_switching_language_actually_changes_the_text(self, config):
        config.instruction_language("en-US")
        english = config.instruction_face_far

        config.instruction_language("zh-CN")
        assert config.instruction_face_far != english

    def test_language_choice_is_remembered(self, config):
        config.instruction_language("ko-KR")
        assert config._lang == "ko-KR"
