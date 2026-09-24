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
# This demo shows how to send real-time face images over a UDP connection.

# Author: Gancheng Zhu
# Email: zhugc2016@gmail.com
# Last updated: 2026-06-21 by Zhiguo Wang

from pupilio import Pupilio

# Initialize the tracker and start the UDP preview server.
pupil_io = Pupilio()
pupil_io.previewer_start('127.0.0.1', 8848)

# Run the main loop until the user presses ENTER.
while True:
    _key = input('Type anything here, then press ENTER to stop the previewing UDP server:\n')
    if _key:
        break

# Stop the previewing thread.
pupil_io.previewer_stop()

# Release the tracker.
pupil_io.release()