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
# This demo shows how to receive real-time face and eye preview images over a UDP connection.
# Features:
#   - Decodes images in full color (preserves pupil, glint, and eye-box annotations).
#   - Real-time FPS calculation and on-screen overlay.
#   - Enlarged socket buffer (4 MB) to prevent OS UDP packet drops under high frame rates.
#   - Responsive UI handling and graceful exit on 'q' or window close.

# Author: Gancheng Zhu
# Email: zhugc2016@gmail.com
# Last updated: 2026-09-24 by Zhiguo Wang

import socket
import time

import cv2
import numpy as np

# Server address and port to listen on (local connection in this example).
server_address = ('127.0.0.1', 8848)

# Maximum buffer size for a single UDP datagram.
buffer_size = 65536

# Open a UDP socket and bind it to the server address.
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Increase socket receive buffer size (4 MB) to prevent packet loss under high FPS (e.g. 100/200/400 FPS).
sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4 * 1024 * 1024)

# Set a timeout so recvfrom doesn't block indefinitely when the stream stops.
sock.settimeout(1.0)
sock.bind(server_address)

# Open an OpenCV window to display the received preview frames.
window_name = 'Pupilio Face Previewer (UDP)'
cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

print(f"[INFO] Listening for UDP preview stream on {server_address[0]}:{server_address[1]}...")
print("[INFO] Press 'q' or ESC in the preview window (or close the window) to exit.")

# Variables for real-time FPS calculation
fps = 0.0
frame_count = 0
fps_timer = time.perf_counter()
last_console_log = time.perf_counter()

try:
    while True:
        try:
            # Receive UDP datagram.
            data, addr = sock.recvfrom(buffer_size)
        except socket.timeout:
            # Check if user closed the window or wants to exit
            if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
                break
            key = cv2.waitKey(10) & 0xFF
            if key in (ord('q'), ord('Q'), 27):
                break
            continue

        if not data:
            break

        # Decode the received JPEG bytes into a color BGR image (preserves colored annotations).
        np_data = np.frombuffer(data, np.uint8)
        frame = cv2.imdecode(np_data, cv2.IMREAD_COLOR)

        if frame is None:
            print("[WARN] Received invalid or corrupted frame.")
            continue

        # Calculate received FPS every 0.5 seconds
        frame_count += 1
        now = time.perf_counter()
        elapsed = now - fps_timer
        if elapsed >= 0.5:
            fps = frame_count / elapsed
            frame_count = 0
            fps_timer = now

        # Periodically log reception statistics to console (every 2 seconds)
        if now - last_console_log >= 2.0:
            print(f"[INFO] Receiving UDP preview: {frame.shape[1]}x{frame.shape[0]} | {fps:.1f} FPS | Datagram: {len(data)} bytes")
            last_console_log = now

        # Overlay real-time FPS on the frame
        fps_text = f"FPS: {fps:.1f}"
        cv2.putText(frame, fps_text, (15, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(frame, fps_text, (15, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2, cv2.LINE_AA)

        # Update window title with FPS
        cv2.setWindowTitle(window_name, f"{window_name} - {fps:.1f} FPS")

        # Show the captured frame.
        cv2.imshow(window_name, frame)

        # Exit on 'q', 'Q', or ESC key
        key = cv2.waitKey(1) & 0xFF
        if key in (ord('q'), ord('Q'), 27):
            break

        # Exit if the window was closed via the [X] button
        if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
            break

finally:
    # Clean up resources
    print("[INFO] Closing socket and OpenCV windows...")
    sock.close()
    cv2.destroyAllWindows()
    print("[INFO] Receiver stopped.")
