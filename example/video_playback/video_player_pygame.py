# -*- coding: utf-8 -*-

# Copyright (c) 2024, Hangzhou Deep Gaze Science and Technology Co., Ltd
# All Rights Reserved
#
# For use by Hangzhou Deep Gaze Science and Technology Co., Ltd customers
# only. Redistribution and use in source and binary forms, with or without
# modification, are NOT permitted.
#
# Redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in
# the documentation and/or other materials provided with the distribution.
#
# Neither name of Hangzhou Deep Gaze Sci & Tech Ltd nor the name of
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS ``AS
# IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED
# TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
# PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE REGENTS OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# DESCRIPTION:
# This is a demo showing how to play video while recording gaze.
#
# A dual-eye gaze cursor is overlaid on each video frame:
#   - Left  eye: hollow blue  circle, labelled "L"
#   - Right eye: hollow green circle, labelled "R"
# Both are drawn simultaneously, each only when that eye reports a valid,
# finite sample, and only when 'show_gaze' is enabled in the participant
# menu. Colors match the Pygame and PsychoPy quick-start demos.

import json
import logging
import math
import os
import sys
from datetime import datetime
import cv2
import pygame
import webview
from pygame.locals import FULLSCREEN, HWSURFACE, KEYDOWN, K_ESCAPE

from pupilio import Pupilio


def generate_thumbnail(video_path, thumbnail_path):
    """Generate a video thumbnail for display in the selection menu.

    video_path: path to the video file
    thumbnail_path: where to save the thumbnail
    """

    # open the video file with OpenCV
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        logging.warning("could not open video for thumbnail: %s", video_path)
        return

    try:
        # retrieve the frame count for the video
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        # get a frame that is 1/10 into the video
        frame_number = total_frames // 10
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ret, frame = cap.read()
        if not ret:
            logging.warning("could not read frame for thumbnail: %s", video_path)
            return

        # original frame width and height
        height, width = frame.shape[:2]

        # keep the aspect ratio, resize the height to 480
        new_height = 480
        new_width = int(width * (new_height / height))

        # thumbnail
        thumbnail = cv2.resize(
            frame, (new_width, new_height), interpolation=cv2.INTER_LINEAR
        )

        # save the thumbnail
        cv2.imwrite(thumbnail_path, thumbnail)
    finally:
        # release the video capture
        cap.release()


class GazeCursor:
    """Dual-eye gaze cursor overlay for the video-viewing task.

    Draws two hollow circles on top of the current frame:
      - left  eye: blue,  labelled "L"
      - right eye: green, labelled "R"

    Both are drawn simultaneously, each only when that eye reports a
    valid, finite sample. Colors match the Pygame and PsychoPy quick-start
    demos (pure blue and pure green).
    """

    BLUE = (0, 0, 255)
    GREEN = (0, 255, 0)
    RADIUS = 55
    THICKNESS = 5

    def __init__(self, screen):
        self.screen = screen
        self.font = pygame.font.SysFont("Arial", 48, bold=True)
        # Last known positions in screen pixels, or None until a valid
        # sample arrives for that eye.
        self.left_pos = None
        self.right_pos = None

    def update(self, pi):
        """Pull the newest gaze sample and update cursor positions."""
        left, right, _bino = pi.get_current_gaze()

        l_status, lx, ly = left
        if l_status == 1 and math.isfinite(lx) and math.isfinite(ly):
            self.left_pos = (int(lx), int(ly))

        r_status, rx, ry = right
        if r_status == 1 and math.isfinite(rx) and math.isfinite(ry):
            self.right_pos = (int(rx), int(ry))

    def draw(self):
        """Draw both cursors on the current frame."""
        if self.left_pos is not None:
            x, y = self.left_pos
            pygame.draw.circle(
                self.screen, self.BLUE, (x, y), self.RADIUS, self.THICKNESS
            )
            label = self.font.render("L", True, self.BLUE)
            self.screen.blit(label, label.get_rect(center=(x, y)))

        if self.right_pos is not None:
            x, y = self.right_pos
            pygame.draw.circle(
                self.screen, self.GREEN, (x, y), self.RADIUS, self.THICKNESS
            )
            label = self.font.render("R", True, self.GREEN)
            self.screen.blit(label, label.get_rect(center=(x, y)))


def single_line_text(text, size=48, color=(255, 255, 255),
                     bg=(128, 128, 128), screen=None):
    """Render a single line of centered text on the screen."""
    font = pygame.font.SysFont("Arial", size)
    w, h = font.size(text)
    surf = font.render(text, True, color)
    if screen is not None:
        screen.fill(bg)
        screen.blit(surf, ((screen.get_width() - w) // 2,
                           (screen.get_height() - h) // 2))
        pygame.display.flip()


def play_video_with_gaze(screen, pi, gaze_cursor, video_path, show_gaze,
                         quit_keys=(K_ESCAPE,)):
    """Play one video with an optional gaze-cursor overlay.

    Replaces video_player_core_pygame.VideoPlayer.play() so the gaze
    cursor can be drawn on top of each frame. Returns True if the video
    finished normally, False if the user quit early.

    If your VideoPlayer handles per-video data saving or trigger codes,
    merge that logic into this loop.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        logging.warning("could not open video: %s", video_path)
        return False

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    clock = pygame.time.Clock()
    scn_w, scn_h = screen.get_size()

    try:
        while True:
            # check for early quit
            for ev in pygame.event.get():
                if ev.type == KEYDOWN and ev.key in quit_keys:
                    return False

            ret, frame = cap.read()
            if not ret:
                break

            # OpenCV returns BGR; pygame expects RGB
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            # OpenCV frame is (H, W, 3); pygame.surfarray expects (W, H, 3)
            frame = frame.swapaxes(0, 1)
            surf = pygame.surfarray.make_surface(frame)
            surf = pygame.transform.scale(surf, (scn_w, scn_h))

            screen.blit(surf, (0, 0))

            if show_gaze:
                gaze_cursor.update(pi)
                gaze_cursor.draw()

            pygame.display.flip()
            clock.tick(fps)
    finally:
        cap.release()

    return True


class JsBridge:
    """A webpage menu to set participant info."""

    def __init__(self):
        self._window = None
        _current_datetime = datetime.now()
        _current_time = _current_datetime.strftime("%Y_%m_%d_%H_%M_%S")
        self.expInfo = {
            "name": "",
            "age": "18",
            "gender": "male",
            "task": "[]",
            "show_gaze": 0,
            "now": _current_time,
        }
        self.global_quit = False

    def set_window(self, window):
        """Select a window to use."""
        self._window = window

    def set_now(self, now):
        """Retrieve task time."""
        self.expInfo["now"] = now

    def set_test_item(self, item_id):
        """Select the task."""
        self.expInfo["task"] = item_id

    def set_participant_id(self, participant_id):
        """Give the subject a unique id."""
        self.expInfo["name"] = str(participant_id)

    def set_age(self, age):
        """Subject age."""
        self.expInfo["age"] = str(age)

    def set_gender(self, gender):
        """Set the subject gender."""
        self.expInfo["gender"] = gender

    def set_show_gaze(self, show_gaze):
        """Whether the gaze cursor should be displayed."""
        self.expInfo["show_gaze"] = show_gaze

    def quit_all(self):
        """Exit."""
        self.global_quit = True
        self._window.destroy()

    def get_video_dict(self):
        """Return all selected video files as a dictionary."""
        return thumbnail_paths_dict

    def start_task(self):
        """Start the experiment here."""
        try:
            self._window.destroy()
        except Exception as e:
            logging.exception(e)


# the main task loop
if __name__ == '__main__':
    # video file directory
    video_dir = 'video'
    if not os.path.isdir(video_dir):
        raise SystemExit(f"Video directory not found: {video_dir}")

    # thumbnail directory
    thumbnail_dir = 'html/img'
    os.makedirs(thumbnail_dir, exist_ok=True)

    # get all the video files
    video_files = [
        f for f in os.listdir(video_dir)
        if f.endswith(('.mp4', '.avi', '.mov', '.mkv'))
    ]

    # a dictionary mapping video file names to their thumbnail paths
    thumbnail_paths_dict = {}

    # generate video covers
    for video_file in video_files:
        video_path = os.path.join(video_dir, video_file)
        thumbnail_path = os.path.join(
            thumbnail_dir, f'{os.path.splitext(video_file)[0]}.png'
        )

        # use the file name as key to save the thumbnails in a dictionary
        file_name = os.path.basename(thumbnail_path)
        thumbnail_paths_dict[os.path.split(video_path)[-1]] = f'img/{file_name}'

        if not os.path.exists(thumbnail_path):
            generate_thumbnail(video_path, thumbnail_path)

    # check that the filenames and paths are all correct
    for filename, path in thumbnail_paths_dict.items():
        print(f'{filename}: {path}')

    # now show the video selection menu as a webpage
    bridge = JsBridge()
    html_url = 'html/par_info.html'
    window = webview.create_window(
        'Video Viewing Task', html_url, js_api=bridge, fullscreen=True
    )
    bridge.set_window(window)
    webview.start(debug=False, http_server=True)

    _current_datetime = datetime.now()
    _current_time = _current_datetime.strftime("%Y_%m_%d_%H_%M_%S")
    participant_info = bridge.expInfo

    """
    The return value of "participant_info":
    127.0.0.1 - - [26/Nov/2024 19:34:10] "GET /result_show.html HTTP/1.1" 200 5670
    {'name': '11', 'age': '11', 'gender': 'male', 'task': '["DSCF4652 00_00_00-00_00_12.avi",
        "DSCF4696 00_00_06-00_00_28.avi", "DSCF4732 00_00_03-00_00_42.avi", "DSCF5250-1.avi",
        "DSCF5253 00_00_06-00_00_41.avi", "DSCF5268 00_00_00-00_00_16.avi",
        "DSCF5268 00_01_05-00_01_52.avi"]', 'now': '2024_11_26_19_33_53'}
    """

    # create a folder to store data collected from each participant
    subj_folder = f"data/{participant_info['name']}_{participant_info['age']}_{participant_info['gender']}"
    os.makedirs(subj_folder, exist_ok=True)

    # dump the subject information into a json file
    with open(os.path.join(subj_folder, 'subj_info.json'), 'w', encoding='utf-8') as subj:
        json.dump(participant_info, subj, ensure_ascii=False, indent=2)

    # read task parameters
    show_gaze = participant_info['show_gaze']
    video_list = participant_info['task']

    # The bridge sends 'task' as a JSON string, e.g. '["a.avi", "b.avi"]'.
    # Parse it so that len() and iteration operate on filenames, not characters.
    if isinstance(video_list, str):
        video_list = json.loads(video_list)

    if len(video_list) == 0 or bridge.global_quit:
        print("No videos were selected or user pressed the `quit` button!")
        sys.exit(0)

    # ---- Initialize Pygame and open a full-screen window ----
    pygame.init()
    scn_width, scn_height = (1920, 1080)
    screen = pygame.display.set_mode(
        (scn_width, scn_height), FULLSCREEN | HWSURFACE
    )

    # ---- Initialize the tracker and create a session ----
    pi = Pupilio()
    try:
        # calibrate the tracker
        pi.create_session(session_name="video_viewing")
        pi.calibration_draw(validate=True, hands_free=False, screen=screen)

        # ---- Gaze cursor ----
        # Created once; positions are updated each frame from the tracker.
        gaze_cursor = GazeCursor(screen)

        # ---- Play each selected video ----
        for vid in video_list:
            # show a fixation cross for 2 seconds before each video
            single_line_text(u"+", 64, screen=screen)
            pygame.time.wait(2000)

            # play the video with the gaze cursor overlaid
            video_path = os.path.join(video_dir, vid)
            keep_going = play_video_with_gaze(
                screen, pi, gaze_cursor, video_path, show_gaze
            )
            if not keep_going:
                break
    finally:
        # release the tracker instance
        pi.release()

    # show a goodbye message
    single_line_text(u"Playback completed...", 32, screen=screen)
    pygame.time.wait(2000)

    # quit pygame
    pygame.quit()
