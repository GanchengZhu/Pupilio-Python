import unittest
from pupilio.ui_backend import PyGameUIBackend
import pygame
import inspect

class TestVersionCompat(unittest.TestCase):
    def test_pygame_font_compat(self):
        # Just testing import and module loading for pygame backend
        import pygame
        screen = pygame.display.set_mode((800, 600))
        backend = PyGameUIBackend(screen)
        backend.before_draw((128, 128, 128))
        
        # In different pygame versions SysFont behavior might vary or fail with certain types
        # We ensure draw_text handles unknown fonts gracefully
        try:
            backend.draw_text("Test", "some_nonexistent_font_123", 24, (0,0,0), (0,0,100,50))
        except Exception as e:
            self.fail(f"draw_text failed with unknown font: {e}")
            
    def test_psychopy_font_compat(self):
        from pupilio.ui_backend import PsychoPyUIBackend
        from psychopy import visual, core
        import psychopy
        win = visual.Window([400,300], units='pix')
        backend = PsychoPyUIBackend(win)
        try:
            backend.draw_text("Test Psychopy", "some_nonexistent_font_321", 24, (1,1,1), (0,0,100,50))
        except Exception as e:
            self.fail(f"draw_text in psychopy failed with unknown font: {e}")
        finally:
            win.close()
            
    def test_numpy_compat(self):
        # Numpy string type casting in earlier versions might differ, but we mainly care
        # about compatibility with psychopy which uses numpy extensively.
        # Check standard numpy operations used in SDK
        import numpy as np
        
        # Just a basic shape test common in cv2/numpy interactions
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        self.assertEqual(img.shape, (100, 100, 3))
        
        # Test basic statistics commonly used in calibration/gaze estimation
        arr = np.array([1, 2, 3, 4, 5])
        self.assertAlmostEqual(np.mean(arr), 3.0)
        
        # Check deprecated features (like np.float vs float)
        self.assertTrue(hasattr(np, 'float32'))
        self.assertTrue(hasattr(np, 'float64'))

if __name__ == '__main__':
    unittest.main()
