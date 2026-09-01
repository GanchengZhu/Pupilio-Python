from psychopy import visual, core

win = visual.Window([400,400], monitor="testMonitor", units="pix")
try:
    txt = visual.TextStim(win, text="中文测试", font="microsoftyaheiui")
    txt.alignHoriz = 'left' # Check if this raises a warning or error
    txt.draw()
    win.flip()
    print("Psychopy text test OK")
except Exception as e:
    print("Psychopy text test Failed:", e)
finally:
    win.close()
