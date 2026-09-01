import pygame
try:
    font = pygame.font.SysFont("microsoftyahei", 32)
    print("SysFont OK")
except Exception as e:
    print("SysFont failed:", e)

from psychopy import visual, core
win = visual.Window([400,400], monitor="testMonitor", units="deg")
try:
    txt = visual.TextStim(win, text="中文测试", font="Microsoft YaHei")
    txt.draw()
    win.flip()
    print("TextStim OK (yahei)")
except Exception as e:
    print("TextStim Failed (yahei):", e)
finally:
    win.close()
    
