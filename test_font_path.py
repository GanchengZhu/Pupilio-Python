import os, platform

def get_font(name):
    # try pygame
    try:
        import pygame
        pygame.font.init()
        font_path = pygame.font.match_font(name)
        if font_path:
            return font_path
    except Exception as e:
        print("pygame fail", e)
    return name

if __name__ == '__main__':
    print("Yahei path:", get_font('microsoftyahei'))
    print("YaheiUI path:", get_font('microsoftyaheiui'))
