# _*_ coding: utf-8 _*_
# Shared pytest fixtures for the Pupilio test suite.

import os
import platform
import sys
from pathlib import Path

import pytest

# Make the repository root importable so `import pupilio` works when pytest is
# invoked from anywhere.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

IS_WINDOWS = platform.system().lower() == "windows"

# The native library is only shipped for Windows, so anything that loads a DLL is
# skipped elsewhere.
windows_only = pytest.mark.skipif(
    not IS_WINDOWS, reason="The Pupilio native library is Windows-only."
)


@pytest.fixture
def simulation_config():
    """A DefaultConfig wired to the dummy tracker, so no hardware is needed."""
    from pupilio import DefaultConfig

    config = DefaultConfig()
    config.simulation_mode = True
    return config


@pytest.fixture
def pupil_io(simulation_config):
    """A live Pupilio backed by the simulation DLL, released on teardown."""
    from pupilio import Pupilio

    tracker = Pupilio(config=simulation_config)
    try:
        yield tracker
    finally:
        tracker.release()


@pytest.fixture
def pygame_screen():
    """An off-screen pygame surface, so UI tests need no real display."""
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    pygame = pytest.importorskip("pygame")

    pygame.display.init()
    pygame.font.init()
    screen = pygame.display.set_mode((800, 600))
    try:
        yield screen
    finally:
        pygame.display.quit()
