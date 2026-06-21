# _*_ coding: utf-8 _*_

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
# Eye Movement Data Analysis Script
# This script processes eye tracking data files by:
# 1. Detecting fixations, saccades, and blinks using the Pupilio EventDetection library
# 2. Visualizing gaze position over time with saccade periods highlighted
# 3. Saving the results to an output directory

# Author: Gancheng Zhu
# Last updated: 6/21/2026 by Zhiguo Wang

import os
import pandas as pd
import matplotlib.pyplot as plt
from pupilio import EventDetection
import glob

# ---- Initialize the event detector ----
ed = EventDetection()

# ---- Define input and output directories ----
input_dir = 'data'
output_dir = 'output'
os.makedirs(output_dir, exist_ok=True)

# ---- Process each CSV file in the input directory ----
for input_path in glob.glob(os.path.join(input_dir, '*.csv')):
    print(f"\nProcessing: {input_path}")

    # Get the base filename without extension for naming outputs
    base_filename = os.path.splitext(os.path.basename(input_path))[0]

    # ---- Run eye movement event detection ----
    # This generates files: BLK_ (blinks), FIX_ (fixations), SAC_ (saccades)
    ed.detect(input_path, output_dir=output_dir, which_eye='right')

    # ---- Load saccade results ----
    # The SAC_ file naming convention: SAC_{original_filename}.csv
    sac_filename = f"SAC_{base_filename}.csv"
    sac_file = os.path.join(output_dir, sac_filename)

    if not os.path.exists(sac_file):
        print(f"Warning: Saccade file not found: {sac_file}")
        continue

    saccades = pd.read_csv(sac_file)
    print(f"Detected {len(saccades)} saccades")

    # ---- Load original raw eye tracking data ----
    raw_data = pd.read_csv(input_path)
    print(f"Total samples: {len(raw_data)}")

    # ---- Prepare gaze data for plotting ----
    # Set invalid gaze points to NaN so matplotlib will break the line
    x_col = 'left_eye_gaze_position_x'
    y_col = 'left_eye_gaze_position_y'
    valid_col = 'left_eye_valid'

    raw_full = raw_data.copy()

    # Replace invalid gaze positions with NaN to create gaps in the plot
    raw_full.loc[raw_full[valid_col] != 1, x_col] = float('nan')
    raw_full.loc[raw_full[valid_col] != 1, y_col] = float('nan')

    # Create x-axis: sample indices (each row = one timestamp)
    sample_idx = range(len(raw_full))

    # ---- Create the visualization ----
    # Two subplots: top for X position, bottom for Y position
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), sharex=True)

    # Plot X gaze position over time
    ax1.plot(sample_idx, raw_full[x_col], 'b-', linewidth=0.8, alpha=0.7, label='Gaze X')
    ax1.set_ylabel('Gaze X (pixels)')
    ax1.legend(loc='upper right')
    ax1.grid(alpha=0.3)

    # Plot Y gaze position over time
    ax2.plot(sample_idx, raw_full[y_col], 'g-', linewidth=0.8, alpha=0.7, label='Gaze Y')
    ax2.set_ylabel('Gaze Y (pixels)')
    ax2.set_xlabel('Sample index (each row = one timestamp)')
    ax2.legend(loc='upper right')
    ax2.grid(alpha=0.3)

    # ---- Add vertical shaded regions for saccade periods ----
    for idx, saccade in saccades.iterrows():
        onset = saccade['onset_i']   # Start index (based on original data row)
        offset = saccade['offset_i'] # End index

        # Add shaded region on both subplots
        ax1.axvspan(onset, offset, alpha=0.2, color='orange',
                    label='Saccade' if idx == 0 else "")
        ax2.axvspan(onset, offset, alpha=0.2, color='orange')

        # Annotate with saccade number
        mid_point = (onset + offset) / 2
        ax1.annotate(str(idx + 1),
                     xy=(mid_point, ax1.get_ylim()[1] * 0.95),
                     ha='center', fontsize=8, color='darkorange')

    # ---- Save the figure ----
    ax1.set_title(f'Gaze X and Y over time with saccade periods\nFile: {base_filename}')
    plt.tight_layout()

    # Save the plot with a clean filename (without the SAC_ prefix)
    # output_plot = os.path.join(output_dir, f'saccade_trace_{base_filename}.png')
    # plt.savefig(output_plot, dpi=150, bbox_inches='tight')
    # print(f"Plot saved to: {output_plot}")

    # Display the plot (uncomment if you want to see it interactively)
    plt.show()

    # Close the figure to free memory
    plt.close(fig)