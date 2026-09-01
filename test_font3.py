from psychopy import visual, core
from psychopy.visual.text import fontFinder
import json
print("Loaded fontFinder")
fonts = list(fontFinder.fonts.keys())
print("Available fonts:", len(fonts))

print("Is 'Microsoft YaHei' in fonts?", any('yahei' in f.lower() for f in fonts))
print("Is 'Arial' in fonts?", "arial" in fonts)
print("YaHei variations:", [f for f in fonts if 'yahei' in f.lower()])
