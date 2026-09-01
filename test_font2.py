import os

try:
    from psychopy import visual, core
    from psychopy.visual.textbox2.fontmanager import FontManager
    f = FontManager()
    
    print("PsychoPy fonts query Microsoft YaHei:", f.getFontFamily('Microsoft YaHei'))
    print("PsychoPy fonts query microsoftyaheiui:", f.getFontFamily('microsoftyaheiui'))
    
except Exception as e:
    print("Error:", e)
