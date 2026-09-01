import unittest
import os
import sys
from unittest.mock import patch
import pygame
import runpy

class TestVersionCompat(unittest.TestCase):
    def setUp(self):
        # Insert project root to import test module
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        
        # Insert example paths
        self.example_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../example/picture_viewing'))
        if self.example_dir not in sys.path:
            sys.path.insert(0, self.example_dir)

    def test_pygame_example(self):
        from pupilio import Pupilio
        
        # Add test dir to path to import auto_cali_graphics
        test_dir = os.path.abspath(os.path.dirname(__file__))
        if test_dir not in sys.path: sys.path.insert(0, test_dir)
        from auto_cali_graphics import AutoCalibrationUI
        
        from pupilio.ui_backend import PyGameUIBackend
        
        def mock_calibration_draw(self_obj, validate=False, hands_free=False, screen=None):
            ui_backend = PyGameUIBackend(screen)
            cali_ui = AutoCalibrationUI(self_obj, ui_backend)
            cali_ui.draw(validate=validate, bg_color=(255, 255, 255), hands_free=hands_free)
            
        with patch.object(Pupilio, 'calibration_draw', mock_calibration_draw):
            # Patch pygame event loop in the example to exit immediately
            def mock_event_get():
                ev = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)
                return [ev]
                
            with patch('pygame.event.get', side_effect=mock_event_get):
                # We also need to patch time.wait to speed up the script
                with patch('pygame.time.wait', return_value=None):
                    old_cwd = os.getcwd()
                    os.chdir(self.example_dir)
                    try:
                        runpy.run_path('picture_viewing_pygame.py')
                    finally:
                        os.chdir(old_cwd)

    def test_psychopy_example(self):
        from pupilio import Pupilio
        
        # Add test dir to path to import auto_cali_graphics
        test_dir = os.path.abspath(os.path.dirname(__file__))
        if test_dir not in sys.path: sys.path.insert(0, test_dir)
        from auto_cali_graphics import AutoCalibrationUI
        
        from pupilio.ui_backend import PsychoPyUIBackend
        
        def mock_calibration_draw(self_obj, validate=False, hands_free=False, screen=None):
            ui_backend = PsychoPyUIBackend(screen)
            cali_ui = AutoCalibrationUI(self_obj, ui_backend)
            cali_ui.draw(validate=validate, bg_color=(255, 255, 255), hands_free=hands_free)
            
        with patch.object(Pupilio, 'calibration_draw', mock_calibration_draw):
            def mock_getKeys(*args, **kwargs):
                return ['return']
            with patch('psychopy.event.getKeys', side_effect=mock_getKeys):
                with patch('psychopy.core.wait', return_value=None):
                    old_cwd = os.getcwd()
                    os.chdir(self.example_dir)
                    try:
                        runpy.run_path('picture_viewing_psychopy.py')
                    except SystemExit as e:
                        if e.code != 0:
                            raise e
                    finally:
                        os.chdir(old_cwd)

if __name__ == '__main__':
    unittest.main()
