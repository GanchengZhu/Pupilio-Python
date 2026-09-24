# -*- coding: utf-8 -*-

# Copyright (c) 2026, Hangzhou DeepGaze Science and Technology Co., Ltd
# All Rights Reserved
#
# For use by Hangzhou DeepGaze Science and Technology Co., Ltd licensees only.
# Redistribution and use in source and binary forms, with or without
# modification, are NOT permitted.
#
# Redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in
# the documentation and/or other materials provided with the distribution.
#
# Neither name of Hangzhou DeepGaze Sci & Tech Ltd nor the name of
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
# This demo shows how to send real-time face and eye preview images over a UDP connection.
# Demonstrates setting target streaming frame rates (30, 60, 100, 200, 400 FPS) and dynamic adjustment.

# Author: Gancheng Zhu
# Email: zhugc2016@gmail.com
# Last updated: 2026-09-24 by Zhiguo Wang

from pupilio import Pupilio, DefaultConfig

# Initialize the tracker (auto-fallback to simulation mode if hardware is not connected)
try:
    pupil_io = Pupilio()
except RuntimeError as err:
    print(f"[WARN] Eye tracker hardware initialization failed: {err}")
    print("[INFO] Falling back to simulation mode for demonstration...")
    DefaultConfig.simulation_mode = True
    pupil_io = Pupilio()

# UDP preview destination address and port
udp_ip = '127.0.0.1'
udp_port = 8848

# Target streaming frame rate (default: 30 FPS; supports 30, 60, 100, 200, 400 FPS)
# Set fps <= 0 for uncapped rate (synced with camera hardware rate)
initial_fps = 30

try:
    # Start the preview streaming server
    pupil_io.previewer_start(udp_ip, udp_port, draw_preview_annotations=True, fps=initial_fps)
    current_fps = pupil_io.previewer_get_fps()
    print(f"[INFO] UDP preview server started at {udp_ip}:{udp_port}")
    print(f"[INFO] Current target frame rate: {current_fps} FPS")
    print("-" * 65)
    print("Controls:")
    print("  - Enter a number (e.g. 30, 60, 100, 200, 400) to adjust FPS dynamically.")
    print("  - Press ENTER or type 'q' / 'exit' to stop the preview server.")
    print("-" * 65)

    # Interactive loop for runtime dynamic frame rate adjustment
    while True:
        try:
            user_input = input(f"Enter target FPS [current: {pupil_io.previewer_get_fps()} FPS] or 'q' to stop: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[INFO] Interrupt received, exiting...")
            break

        if not user_input or user_input.lower() in ('q', 'quit', 'exit', 'stop'):
            break

        try:
            target_fps = int(user_input)
            pupil_io.previewer_set_fps(target_fps)
            print(f"[SUCCESS] Target FPS updated to: {pupil_io.previewer_get_fps()} FPS")
        except ValueError:
            print("[ERROR] Please enter a valid integer (e.g. 30, 60, 100, 200, 400) or 'q' to stop.")
        except RuntimeError as err:
            print(f"[ERROR] Failed to set FPS: {err}")

finally:
    # Clean up and release native resources
    print("[INFO] Stopping preview server...")
    pupil_io.previewer_stop()
    print("[INFO] Releasing Pupilio instance...")
    pupil_io.release()
    print("[INFO] Preview server stopped successfully.")