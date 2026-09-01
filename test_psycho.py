import psychopy.visual
import psychopy.core
import pygame
pygame.font.init()
f = pygame.font.match_font('microsoftyahei')
win = psychopy.visual.Window(size=(400, 400), units='pix')
t = psychopy.visual.TextStim(win, text='测试', font=f, height=50)
t.draw()
win.flip()
psychopy.core.wait(0.5)
win.close()
