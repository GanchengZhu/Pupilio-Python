# _*_ coding: utf-8 _*_
# Author: GC Zhu
# Email: zhugc2016@gmail.com
# encoding=utf-8

from typing import Tuple

import cv2
import numpy as np
import platform


class UIBackend:
    """
    Drawing and input interface that the calibration UI renders through.

    Subclasses adapt a specific windowing library, letting
    :class:`~pupilio.cali_graphics.CalibrationUI` run unchanged under PsychoPy and Pygame.

    All coordinates are in pixels with the origin at the **top-left** of the screen, and
    rectangles are ``(x, y, width, height)``. Backends whose native coordinate system
    differs are responsible for converting.
    """

    def __init__(self, win):
        """
        Args:
            win: The backend-specific window or surface to draw on.
        """
        self.win = win

    def draw_circle(self, x: int, y: int, radius: int, color: Tuple[int, int, int], line_width: int = 0):
        """
        Draw a circle.

        Args:
            x (int): Centre x in pixels.
            y (int): Centre y in pixels.
            radius (int): Radius in pixels.
            color (tuple): RGB colour, 0-255 per channel.
            line_width (int): Outline thickness in pixels; 0 fills the circle.
        """
        raise NotImplementedError

    def draw_line(self, sx: int, sy: int, ex: int, ey: int, color: Tuple[int, int, int], line_width: int):
        """
        Draw a straight line.

        Args:
            sx (int): Start x in pixels.
            sy (int): Start y in pixels.
            ex (int): End x in pixels.
            ey (int): End y in pixels.
            color (tuple): RGB colour, 0-255 per channel.
            line_width (int): Line thickness in pixels.
        """
        raise NotImplementedError

    def draw_image(self, img_path: str, rect: Tuple[int, int, int, int]):
        """
        Draw an image file, scaled to fill the given rectangle.

        Args:
            img_path (str): Path to the image file.
            rect (tuple): Destination ``(x, y, width, height)`` in pixels.
        """
        raise NotImplementedError

    def draw_texture(self, img: np.ndarray, rect: Tuple[int, int, int, int]):
        """
        Draw an in-memory image, scaled to fill the given rectangle.

        Args:
            img (np.ndarray): ``(H, W, 3)`` RGB image data.
            rect (tuple): Destination ``(x, y, width, height)`` in pixels.
        """
        raise NotImplementedError

    def draw_rect(self, rect: Tuple[int, int, int, int], color: Tuple[int, int, int], line_width: int):
        """
        Draw a rectangle.

        Args:
            rect (tuple): ``(x, y, width, height)`` in pixels.
            color (tuple): RGB colour, 0-255 per channel.
            line_width (int): Outline thickness in pixels; 0 fills the rectangle.
        """
        raise NotImplementedError

    def draw_text(self, text: str, font_name: str, font_size: int, text_color: Tuple[int, int, int],
                  rect: Tuple[int, int, int, int], align='center'):
        """
        Draw a single line of text positioned within a rectangle.

        Args:
            text (str): Text to draw.
            font_name (str): System font name.
            font_size (int): Font height in pixels.
            text_color (tuple): RGB colour, 0-255 per channel.
            rect (tuple): Bounding ``(x, y, width, height)`` in pixels.
            align (str): Horizontal alignment within ``rect``: 'center', 'left', or 'right'.
        """
        raise NotImplementedError

    def get_screen_size(self):
        """
        Return the drawable size.

        Returns:
            tuple[int, int]: Width and height in pixels.
        """
        raise NotImplementedError

    def before_draw(self, bg_color):
        """
        Begin a frame by clearing to the background colour.

        Args:
            bg_color (tuple): RGB colour, 0-255 per channel.
        """
        raise NotImplementedError

    def after_draw(self):
        """Finish a frame and present it to the display."""
        raise NotImplementedError

    def check_action(self):
        """
        Poll input and report the participant's requested action.

        Returns:
            str | None: 'continue' to advance, 'recali' to restart calibration, 'quit' to
            abort, or None when nothing was pressed.
        """
        raise NotImplementedError

    def clear_events(self):
        """
        Discard buffered input.

        Called before each screen that waits for a response, so key presses or clicks made
        earlier cannot dismiss it instantly.
        """
        raise NotImplementedError


class PsychoPyUIBackend(UIBackend):
    """
    :class:`UIBackend` implementation for a PsychoPy ``Window``.

    Stimulus objects are created once and reused across frames, since building them per
    frame is far too slow for the calibration animation. Coordinates are converted from
    top-left pixels to PsychoPy's centre-origin space by
    :meth:`pixel_to_psychopy_coordinate`.
    """

    def __init__(self, win):
        """
        Args:
            win (psychopy.visual.Window): Window to draw on.
        """
        super().__init__(win)
        from psychopy import visual, event
        self.event = event
        self.mouse = self.event.Mouse()
        self.win_units = self.win.units

        self.circle_stim = visual.ShapeStim(self.win, vertices='circle', colorSpace='rgb255', units='pix')
        self.line_stim = visual.ShapeStim(self.win, vertices=[(0, 0), (0, 0)], colorSpace='rgb255', units='pix',
                                          closeShape=False)
        self.rect_stim = visual.ShapeStim(self.win, vertices='rectangle', colorSpace='rgb255', units='pix',
                                          anchor='top-left')
        self.text_stim = visual.TextStim(self.win, text='', colorSpace='rgb255', units="pix")
        self.image_stim = visual.ImageStim(self.win, image=None, mask=None, units="pix")

        self.texture_cache = {}
        self.visual = visual

    def pixel_to_psychopy_coordinate(self, x: int, y: int) -> Tuple:
        """
        Convert top-left pixel coordinates to PsychoPy's centre-origin space.

        Args:
            x (int): X in pixels from the left edge.
            y (int): Y in pixels from the top edge.

        Returns:
            tuple[int, int]: Position relative to screen centre, with y pointing up.
        """
        screen_width, screen_height = self.win.size
        return (x - screen_width // 2), -(y - screen_height // 2)

    def draw_circle(self, x, y, radius, color, line_width=0):
        self.circle_stim.pos = self.pixel_to_psychopy_coordinate(x, y)
        self.circle_stim.size = (2 * radius, 2 * radius)
        self.circle_stim.lineColor = color if line_width > 0 else None
        self.circle_stim.fillColor = color if line_width == 0 else None
        self.circle_stim.lineWidth = line_width
        self.circle_stim.draw()

    def draw_line(self, sx, sy, ex, ey, color, line_width):
        start = self.pixel_to_psychopy_coordinate(sx, sy)
        end = self.pixel_to_psychopy_coordinate(ex, ey)
        self.line_stim.vertices = [start, end]
        self.line_stim.lineColor = color
        self.line_stim.lineWidth = line_width
        self.line_stim.draw()

    def draw_image(self, img_path: str, rect: Tuple[int, int, int, int]):
        x, y, w, h = rect
        p_x, p_y = x + w // 2, y + h // 2
        self.image_stim.pos = self.pixel_to_psychopy_coordinate(p_x, p_y)
        self.image_stim.size = (w, h)
        self.image_stim.image = img_path
        self.image_stim.draw()

    def draw_texture(self, img: np.ndarray, rect: Tuple[int, int, int, int]):
        if rect not in self.texture_cache:
            x, y, w, h = rect
            p_x, p_y = x + w // 2, y + h // 2
            stim = self.visual.GratingStim(
                win=self.win, tex=None, mask=None,
                pos=self.pixel_to_psychopy_coordinate(p_x, p_y),
                size=(w, h), colorSpace='rgb', units='pix'
            )
            self.texture_cache[rect] = stim
        else:
            stim = self.texture_cache[rect]
        img = cv2.rotate(img, cv2.ROTATE_180)
        img = cv2.flip(img, 1)
        # PsychoPy colorSpace='rgb' 需要将 0-255 转为 -1.0 到 1.0
        norm_img = (img / 127.5) - 1.0
        stim.tex = norm_img
        stim.draw()

    def draw_rect(self, rect, color, line_width):
        self.rect_stim.pos = self.pixel_to_psychopy_coordinate(rect[0], rect[1])
        self.rect_stim.size = (rect[2], rect[3])
        self.rect_stim.lineColor = color if line_width > 0 else None
        self.rect_stim.fillColor = color if line_width == 0 else None
        self.rect_stim.lineWidth = line_width
        self.rect_stim.draw()

    def draw_text(self, text, font_name, font_size, text_color, rect, align='center'):
        self.text_stim.text = text
        self.text_stim.font = font_name
        self.text_stim.height = font_size
        self.text_stim.color = text_color
        
        if align == 'left' or align == 'left-top':
            p_x = rect[0]
            p_y = rect[1] + rect[3] // 2
            if align == 'left-top':
                p_y = rect[1]
                if hasattr(self.text_stim, 'anchorVert'):
                     self.text_stim.anchorVert = 'top'
        elif align == 'right':
            p_x = rect[0] + rect[2]
            p_y = rect[1] + rect[3] // 2
        else:
            p_x = rect[0] + rect[2] // 2
            p_y = rect[1] + rect[3] // 2
            
        self.text_stim.pos = self.pixel_to_psychopy_coordinate(p_x, p_y)
        
        if hasattr(self.text_stim, 'anchorHoriz'):
            self.text_stim.anchorHoriz = 'left' if align in ['left', 'left-top'] else align
        if hasattr(self.text_stim, 'alignText'):
            self.text_stim.alignText = 'left' if align in ['left', 'left-top'] else 'center'
        if hasattr(self.text_stim, 'alignHoriz'):    
            self.text_stim.alignHoriz = 'left' if align in ['left', 'left-top'] else align
            
        try:
            self.text_stim.draw()
        except Exception:
            # Fallback to default font if the specified font fails
            self.text_stim.font = "Arial"
            try:
                self.text_stim.draw()
            except Exception:
                pass # Last resort, ignore if still fails

    def get_screen_size(self):
        return self.win.size

    def before_draw(self, bg_color):
        # 转换背景色 0-255 到 -1 到 1
        r = (bg_color[0] / 127.5) - 1.0
        g = (bg_color[1] / 127.5) - 1.0
        b = (bg_color[2] / 127.5) - 1.0
        self.win.color = (r, g, b)

    def after_draw(self):
        self.win.flip()

    def check_action(self):
        keys = self.event.getKeys(keyList=['return', 'space', 'r', 'q', 'escape', 'p'])
        if 'q' in keys or 'escape' in keys: return 'quit'
        if 'return' in keys or 'space' in keys: return 'continue'
        if 'r' in keys: return 'recali'
        if 'p' in keys: return 'toggle_preview'

        mouse_pressed = self.mouse.getPressed()
        
        # Edge detection for mouse clicks (getPressed returns continuous state)
        if not hasattr(self, '_last_mouse_pressed'):
            self._last_mouse_pressed = [0, 0, 0]
            
        clicked_left = mouse_pressed[0] and not self._last_mouse_pressed[0]
        clicked_right = mouse_pressed[2] and not self._last_mouse_pressed[2]
        self._last_mouse_pressed = list(mouse_pressed)

        if clicked_left:
            self.event.clearEvents()
            return 'continue'
        if clicked_right:
            self.event.clearEvents()
            return 'recali'
        return None

    def clear_events(self):
        self.event.clearEvents()
        self.mouse.clickReset()


class PyGameUIBackend(UIBackend):
    """
    :class:`UIBackend` implementation for a Pygame ``Surface``.

    Pygame already uses top-left pixel coordinates, so no conversion is needed. Loaded
    images are cached by path because the calibration target is redrawn every frame.
    """

    def __init__(self, win):
        """
        Args:
            win (pygame.Surface): Display surface to draw on.
        """
        super().__init__(win)

        import pygame
        self.pygame = pygame
        self._image_cache = {}

        # [修复] 强制声明 DPI，解决 Windows 自带 125% 等缩放导致校准框失真/偏移的问题
        if platform.system().lower() == 'windows':
            import ctypes
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(2)
            except Exception:
                try:
                    ctypes.windll.user32.SetProcessDPIAware()
                except Exception:
                    pass

        self.pygame.font.init()

    def draw_circle(self, x, y, radius, color, line_width=0):
        self.pygame.draw.circle(self.win, color, (int(x), int(y)), int(radius), line_width)

    def draw_line(self, sx, sy, ex, ey, color, line_width):
        self.pygame.draw.line(self.win, color, (sx, sy), (ex, ey), line_width)

    def draw_image(self, img_path: str, rect: Tuple[int, int, int, int]):
        if img_path not in self._image_cache:
            self._image_cache[img_path] = self.pygame.image.load(img_path).convert_alpha()

        image = self._image_cache[img_path]
        scaled_image = self.pygame.transform.smoothscale(image, (int(rect[2]), int(rect[3])))
        self.win.blit(scaled_image, (int(rect[0]), int(rect[1])))

    def draw_texture(self, img: np.ndarray, rect: Tuple[int, int, int, int]):
        # img 形状为 (H, W, 3) RGB，Pygame 的 surfarray 需要 (W, H, 3)
        transposed_img = np.transpose(img, (1, 0, 2))
        surface = self.pygame.surfarray.make_surface(transposed_img)
        scaled_surface = self.pygame.transform.scale(surface, (int(rect[2]), int(rect[3])))
        self.win.blit(scaled_surface, (int(rect[0]), int(rect[1])))

    def draw_rect(self, rect, color, line_width):
        self.pygame.draw.rect(self.win, color, rect, line_width)

    def _get_font(self, font_name, font_size):
        try:
            font = self.pygame.font.SysFont(font_name, font_size)
            if font:
                return font
        except Exception:
            pass
        
        # Fallback to direct Windows font paths if on Windows
        import platform, os
        if platform.system().lower() == 'windows':
            windir = os.environ.get('WINDIR', 'C:\\Windows')
            font_paths = [
                os.path.join(windir, 'Fonts', 'msyh.ttc'),
                os.path.join(windir, 'Fonts', 'msyh.ttf'),
                os.path.join(windir, 'Fonts', 'simhei.ttf'),
                os.path.join(windir, 'Fonts', 'simsun.ttc'),
                os.path.join(windir, 'Fonts', 'msgothic.ttc'),
                os.path.join(windir, 'Fonts', 'malgun.ttf')
            ]
            for fp in font_paths:
                if os.path.exists(fp):
                    try:
                        return self.pygame.font.Font(fp, font_size)
                    except Exception:
                        pass
                        
        return self.pygame.font.Font(None, font_size)

    def draw_text(self, text, font_name, font_size, text_color, rect, align='center'):
        font = self._get_font(font_name, font_size)
            
        try:
            text_surface = font.render(text, True, text_color)
        except Exception:
            try:
                # If rendering fails (e.g. for some missing characters), try default font
                font = self.pygame.font.Font(None, font_size)
                text_surface = font.render(text, True, text_color)
            except Exception:
                return # Give up if even default font rendering fails
        text_rect = text_surface.get_rect()

        if align == 'center':
            text_rect.center = (rect[0] + rect[2] // 2, rect[1] + rect[3] // 2)
        elif align == 'left':
            text_rect.topleft = (rect[0], rect[1])
        elif align == 'right':
            text_rect.topright = (rect[0] + rect[2], rect[1])

        self.win.blit(text_surface, text_rect)

    def get_screen_size(self):
        return self.win.get_size()

    def before_draw(self, bg_color):
        self.win.fill(bg_color)

    def after_draw(self):
        self.pygame.display.flip()

    def check_action(self):
        for event in self.pygame.event.get():
            if event.type == self.pygame.QUIT:
                return 'quit'
            if event.type == self.pygame.KEYDOWN:
                if event.key in [self.pygame.K_q, self.pygame.K_ESCAPE]: return 'quit'
                if event.key in [self.pygame.K_RETURN, self.pygame.K_SPACE]: return 'continue'
                if event.key == self.pygame.K_r: return 'recali'
                if event.key == self.pygame.K_p: return 'toggle_preview'
            if event.type == self.pygame.MOUSEBUTTONUP:
                if event.button == 1: return 'continue'  # 左键
                if event.button == 3: return 'recali'  # 右键
        return None

    def clear_events(self):
        self.pygame.event.clear()