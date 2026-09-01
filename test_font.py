import pygame
pygame.font.init()

fonts = pygame.font.get_fonts()
if 'microsoftyaheiui' in fonts:
    print("Pygame found 'microsoftyaheiui'")
else:
    print("Pygame DID NOT find 'microsoftyaheiui'")

try:
    from psychopy import visual, core
    from psychopy.visual.textbox2.fontmanager import FontManager
    f = FontManager()
    print("PsychoPy fonts:", f.getFontFamily('microsoftyaheiui'))
except ImportError:
    print("No psychopy")
except Exception as e:
    print("Error:", e)
