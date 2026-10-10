# _*_ coding: utf-8 _*_
# Shared pytest fixtures for the Pupilio test suite.

import os
import platform
import sys
from pathlib import Path

import pytest

# Make the repository root importable so `import pupilio` works when pytest is
# invoked from anywhere. Inserting at position 0 means the checkout under test
# shadows any other installed copy of the package, which is what we want.
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
def real_hardware_config():
    """
    A DefaultConfig wired to the real tracker.

    Requires physical hardware (or the real DLL installed as ``PupilioET.dll``) and a
    Windows host. Request this fixture only in tests that genuinely need the native
    camera pipeline.
    """
    from pupilio import DefaultConfig

    config = DefaultConfig()
    config.simulation_mode = False
    return config


def _make_pupil_io(config):
    """
    Construct a Pupilio, yield it, and release it on teardown.

    ``release()`` is called even if the test itself raised, so a failing test cannot
    leave the DLL in a locked state for the next one. Any exception from ``release``
    is logged rather than propagated, so it does not mask the original test failure.
    """
    from pupilio import Pupilio

    tracker = Pupilio(config=config)
    try:
        yield tracker
    finally:
        try:
            tracker.release()
        except Exception as exc:  # pragma: no cover — teardown robustness only
            import logging
            logging.getLogger(__name__).warning(
                "tracker.release() failed during teardown: %s", exc
            )


@pytest.fixture
def pupil_io(simulation_config):
    """A live Pupilio backed by the simulation DLL, released on teardown."""
    yield from _make_pupil_io(simulation_config)


@pytest.fixture
def pupil_io_real(real_hardware_config):
    """
    A live Pupilio backed by the real tracker, released on teardown.

    Skipped on non-Windows hosts. On Windows, still requires the real DLL and physical
    hardware to be present; a missing DLL or camera will raise from ``Pupilio(...)``,
    which the test should treat as a configuration error rather than a code failure.
    """
    if not IS_WINDOWS:
        pytest.skip("The Pupilio native library is Windows-only.")
    yield from _make_pupil_io(real_hardware_config)


@pytest.fixture
def pygame_screen():
    pygame = pytest.importorskip("pygame")

    saved_video = os.environ.get("SDL_VIDEODRIVER")
    saved_audio = os.environ.get("SDL_AUDIODRIVER")
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ["SDL_AUDIODRIVER"] = "dummy"

    display_inited = font_inited = False
    try:
        pygame.display.init(); display_inited = True
        pygame.font.init();    font_inited = True
        screen = pygame.display.set_mode((800, 600))
        yield screen
    finally:
        if font_inited:    pygame.font.quit()
        if display_inited: pygame.display.quit()
        pygame.quit()

        if saved_video is None:
            os.environ.pop("SDL_VIDEODRIVER", None)
        else:
            os.environ["SDL_VIDEODRIVER"] = saved_video
        if saved_audio is None:
            os.environ.pop("SDL_AUDIODRIVER", None)
        else:
            os.environ["SDL_AUDIODRIVER"] = saved_audio
