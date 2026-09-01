from psychopy import visual, core
win = visual.Window([400,400], monitor="testMonitor", units="deg")
try:
    txt = visual.TextStim(win, text="中文测试 microsoftyaheiui", font="microsoftyaheiui")
    txt.draw()
    win.flip()
    print("TextStim OK (microsoftyaheiui)")
except Exception as e:
    print("TextStim Failed (microsoftyaheiui):", e)
finally:
    win.close()
    
try:
    win = visual.Window([400,400], monitor="testMonitor", units="deg")
    txt = visual.TextStim(win, text="中文测试 Arial", font="Arial")
    txt.draw()
    win.flip()
    print("TextStim OK (Arial)")
except Exception as e:
    pass
finally:
    win.close()
