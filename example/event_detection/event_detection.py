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
# Batch eye-movement event detection script.
# Processes every CSV file in the 'data' directory and detects:
#   - Fixations (FIX_)
#   - Saccades  (SAC_)
#   - Blinks    (BLK_)
# Results are written to the 'output' directory.
#
# Author: Gancheng Zhu
# Email: zhugc2016@gmail.com

import glob
import os

from pupilio import EventDetection

# ---- Configuration ----
# Directory containing the recorded eye-tracking CSV files.
data_dir = 'data'

# Directory where the detected-event files will be written.
out_dir = 'output'

# Eye to use for event detection.
# Common values: 'left', 'right', 'both'.
which_eye = 'right'


def main():
    if not os.path.isdir(data_dir):
        print(f"Data directory not found: '{data_dir}'")
        return

    # Create the output directory (no-op if it already exists)
    os.makedirs(out_dir, exist_ok=True)

    csv_files = sorted(glob.glob(os.path.join(data_dir, '*.csv')))
    if not csv_files:
        print(f"No CSV files found in '{data_dir}'.")
        return

    # Initialize the event detector once and reuse it across files.
    ed = EventDetection()

    succeeded = 0
    failed = []

    for file_path in csv_files:
        print(f"Processing: {file_path}")
        try:
            ed.detect(file_path, output_dir=out_dir, which_eye=which_eye)
            succeeded += 1
            print(f"Completed:  {file_path}")
        except Exception as err:
            failed.append((file_path, err))
            print(f"Failed:     {file_path} -- {err}")

    # ---- Summary ----
    print()
    print("=" * 60)
    print(f"Processed {len(csv_files)} file(s): "
          f"{succeeded} succeeded, {len(failed)} failed.")
    if failed:
        print("Failures:")
        for file_path, err in failed:
            print(f"  - {file_path}: {err}")


if __name__ == '__main__':
    main()

