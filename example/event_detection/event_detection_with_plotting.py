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
# Eye movement data analysis script.
# This script processes eye tracking data files by:
# 1. Detecting fixations, saccades, and blinks using the Pupilio EventDetection library
# 2. Visualizing gaze position over time with saccade periods highlighted
# 3. Saving the results to an output directory
# 4. Displaying each plot in a pop-up window

# Author: Gancheng Zhu
# Email: zhugc2016@gmail.com
# Last updated: 2026-06-21 by Zhiguo Wang

import glob
import os

import matplotlib.pyplot as plt
import pandas as pd

from pupilio import EventDetection

#- Initialize the event detector
ed = EventDetection()

#- Define input and output directories
input_dir = 'data'
output_dir = 'output'
os.makedirs(output_dir, exist_ok=True)

# Which eye to detect and plot: 'left', 'right', or 'both'.
which_eye = 'right'

# Column name for the gaze timestamp in the raw CSV.
# Change this if your recording uses a different column name.
timestamp_col = 'timestamp'

# Gaze timestamps in the raw CSV are stored in nanoseconds.
# They are converted to seconds for plotting.
NS_PER_S = 1e9

#- Process each CSV file in the input directory
for input_path in glob.glob(os.path.join(input_dir, '*.csv')):
    print(f"\nProcessing: {input_path}")

    # Get the base filename without extension for naming outputs.
    base_filename = os.path.splitext(os.path.basename(input_path))[0]

    #- Run eye movement event detection
    # This generates files: BLK_ (blinks), FIX_ (fixations), SAC_ (saccades).
    ed.detect(input_path, output_dir=output_dir, which_eye=which_eye)

    #- Load saccade results
    # The SAC_ file naming convention is: SAC_{base_filename}.csv
    sac_filename = f"SAC_{base_filename}.csv"
    sac_file = os.path.join(output_dir, sac_filename)

    if not os.path.exists(sac_file):
        print(f"Warning: Saccade file not found: {sac_file}")
        continue

    saccades = pd.read_csv(sac_file)
    print(f"Detected {len(saccades)} saccades")

    #- Load original raw eye tracking data
    raw_data = pd.read_csv(input_path)
    print(f"Total samples: {len(raw_data)}")

    if timestamp_col not in raw_data.columns:
        print(f"Warning: Timestamp column '{timestamp_col}' not found. "
              f"Available columns: {list(raw_data.columns)}")
        continue

    #- Prepare gaze data for plotting
    # Set invalid gaze points to NaN so matplotlib will break the line.
    x_col = f'{which_eye}_eye_gaze_position_x'
    y_col = f'{which_eye}_eye_gaze_position_y'
    valid_col = f'{which_eye}_eye_valid'

    raw_full = raw_data.copy()

    # Convert gaze timestamps from nanoseconds to seconds.
    time_s = raw_full[timestamp_col] / NS_PER_S

    # Replace invalid gaze positions with NaN to create gaps in the plot.
    raw_full.loc[raw_full[valid_col] != 1, x_col] = float('nan')
    raw_full.loc[raw_full[valid_col] != 1, y_col] = float('nan')

    #- Create the visualization
    # Single plot with both X and Y on the same axes.
    fig, ax = plt.subplots(figsize=(14, 6))

    # Plot X gaze position over time (thick blue line).
    ax.plot(time_s, raw_full[x_col],
            color='#0072BD', linewidth=2.8, alpha=0.9,
            label='Gaze X', zorder=3)

    # Plot Y gaze position over time (thick orange/red line).
    ax.plot(time_s, raw_full[y_col],
            color='#D95319', linewidth=2.8, alpha=0.9,
            label='Gaze Y', zorder=3)

    ax.set_ylabel('Gaze position (pixels)', fontsize=12)
    ax.set_xlabel('Time (s)', fontsize=12)
    ax.grid(alpha=0.3)

    #- Highlight saccade periods with shaded vertical strips
    # onset_i and offset_i are sample indices into the raw data. They are
    # looked up in the time_s series to obtain the corresponding times in
    # seconds, so the strips align with the x-axis. zorder=2 keeps the
    # strips behind the gaze traces (zorder=3) so the traces stay visible.
    for idx, saccade in saccades.iterrows():
        onset_i = int(saccade['onset_i'])    # sample index of saccade start
        offset_i = int(saccade['offset_i'])  # sample index of saccade end

        # Guard against out-of-range indices in case of a corrupt file.
        if not (0 <= onset_i < len(time_s) and 0 <= offset_i < len(time_s)):
            print(f"Warning: Saccade {idx + 1} has out-of-range indices "
                  f"(onset_i={onset_i}, offset_i={offset_i}); skipping.")
            continue

        onset_s = time_s.iloc[onset_i]    # saccade start time (s)
        offset_s = time_s.iloc[offset_i]  # saccade end time (s)

        # Shaded vertical strip spanning the saccade interval
        # (only the first one carries the legend label).
        ax.axvspan(onset_s, offset_s,
                   alpha=0.3, color='orange',
                   edgecolor='darkorange', linewidth=0.8,
                   zorder=2,
                   label='Saccade' if idx == 0 else "")

        # Annotate with saccade number near the top of the plot, centered
        # between the strip's edges.
        mid_point = (onset_s + offset_s) / 2
        ax.annotate(str(idx + 1),
                    xy=(mid_point, ax.get_ylim()[1] * 0.95),
                    ha='center', fontsize=9, color='darkorange',
                    fontweight='bold', zorder=4)

    # Legend must be added after the saccade strips so it picks up the
    # 'Saccade' entry created inside the loop.
    ax.legend(loc='upper right', fontsize=11, framealpha=0.9)

    #- Save the figure
    ax.set_title(f'Gaze X and Y over time with saccade periods\nFile: {base_filename}',
                 fontsize=13)
    plt.tight_layout()

    # Save the plot using the original filename as a base.
    output_plot = os.path.join(output_dir, f'saccade_trace_{base_filename}.png')
    plt.savefig(output_plot, dpi=150, bbox_inches='tight')
    print(f"Plot saved to: {output_plot}")

    #- Show the plot in a pop-up window
    # block=True makes the call block until the window is closed, so each
    # file is reviewed one at a time before the loop continues.
    plt.show(block=True)

    # Close the figure to free memory before processing the next file.
    plt.close(fig)
