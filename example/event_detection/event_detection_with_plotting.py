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
ed = EventDetection(simulation_mode=1)

# ---- Define input and output directories ----
input_dir = 'data'
output_dir = 'output'
os.makedirs(output_dir, exist_ok=True)

# Which eye to detect and plot: 'left', 'right', or 'bino'
which_eye = 'right'

# ---- Process each CSV file in the input directory ----
for input_path in glob.glob(os.path.join(input_dir, '*.csv')):
    print(f"\nProcessing: {input_path}")

    # Get the base filename without extension for naming outputs
    base_filename = os.path.splitext(os.path.basename(input_path))[0]

    # ---- Run eye movement event detection ----
    # This generates files: BLK_ (blinks), FIX_ (fixations), SAC_ (saccades)
    ed.detect(input_path, output_dir=output_dir, which_eye=which_eye)

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
    x_col = f'{which_eye}_eye_gaze_position_x'
    y_col = f'{which_eye}_eye_gaze_position_y'
    valid_col = f'{which_eye}_eye_valid'

    raw_full = raw_data.copy()

    # Replace invalid gaze positions with NaN to create gaps in the plot
    raw_full.loc[raw_full[valid_col] != 1, x_col] = float('nan')
    raw_full.loc[raw_full[valid_col] != 1, y_col] = float('nan')

    # Create x-axis: sample indices (each row = one timestamp)
    sample_idx = range(len(raw_full))

    # ---- Create the visualization ----
    # Single plot with both X and Y on the same axes
    fig, ax = plt.subplots(figsize=(14, 6))

    # Plot X gaze position over time (thick blue line)
    ax.plot(sample_idx, raw_full[x_col],
            color='#0072BD', linewidth=2.8, alpha=0.9,
            label='Gaze X')

    # Plot Y gaze position over time (thick orange/red line)
    ax.plot(sample_idx, raw_full[y_col],
            color='#D95319', linewidth=2.8, alpha=0.9,
            label='Gaze Y')

    ax.set_ylabel('Gaze position (pixels)', fontsize=12)
    ax.set_xlabel('Sample index (each row = one timestamp)', fontsize=12)
    ax.grid(alpha=0.3)
    ax.legend(loc='upper right', fontsize=11, framealpha=0.9)

    # ---- Add vertical shaded regions for saccade periods ----
    for idx, saccade in saccades.iterrows():
        onset = saccade['onset_i']   # Start index (based on original data row)
        offset = saccade['offset_i'] # End index

        # Add shaded region for saccade period on the single plot
        ax.axvspan(onset, offset, alpha=0.2, color='orange',
                   label='Saccade' if idx == 0 else "")

        # Annotate with saccade number near the top of the plot
        mid_point = (onset + offset) / 2
        ax.annotate(str(idx + 1),
                    xy=(mid_point, ax.get_ylim()[1] * 0.95),
                    ha='center', fontsize=9, color='darkorange',
                    fontweight='bold')

    # ---- Save the figure ----
    ax.set_title(f'Gaze X and Y over time with saccade periods\nFile: {base_filename}',
                 fontsize=13)
    plt.tight_layout()

    # Save the plot with a clean filename (without the SAC_ prefix)
    output_plot = os.path.join(output_dir, f'saccade_trace_{base_filename}.png')
    plt.savefig(output_plot, dpi=150, bbox_inches='tight')
    print(f"Plot saved to: {output_plot}")

    # Display the plot (uncomment if you want to see it interactively)
    plt.show()

    # Close the figure to free memory
    plt.close(fig)