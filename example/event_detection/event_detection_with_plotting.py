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
# Eye movement data analysis script.
# This script processes eye tracking data files by:
#   1. Detecting fixations, saccades, and blinks using the Pupilio
#      EventDetection library.
#   2. Visualizing gaze position over time with saccade periods highlighted.
#   3. Saving the plots to an output directory.
#   4. Optionally displaying each plot in a pop-up window.
#
# Author: Gancheng Zhu
# Email: zhugc2016@gmail.com
# Last updated: 2026-06-21 by Zhiguo Wang

import glob
import os

import matplotlib.pyplot as plt
import pandas as pd

from pupilio import EventDetection

# ---- Configuration ----
# Input and output directories.
input_dir = 'data'
output_dir = 'output'

# Which eye to detect and plot.
# Supported values here: 'left' or 'right'.
# The plot columns follow the pattern
#   '{which_eye}_eye_gaze_position_x' / '_y' / '_valid',
# so 'both' would need different column names and is not handled here.
which_eye = 'right'

# Column name for the gaze timestamp in the raw CSV.
# Change this if your recording uses a different column name.
timestamp_col = 'timestamp'

# Gaze timestamps in the raw CSV are stored in nanoseconds.
# They are converted to seconds for plotting.
NS_PER_S = 1e9

# Set to False to run the batch without pop-up windows (useful for
# unattended processing of many files).
show_plots = True


def process_file(ed, input_path, output_dir, which_eye,
                 timestamp_col, ns_per_s, show_plots):
    """Detect events and plot gaze traces for a single CSV file.

    Returns True on success, False if the file was skipped for a
    recoverable reason (missing columns, missing saccade output).
    """
    print(f"\nProcessing: {input_path}")

    # Base filename without extension, used to name the outputs.
    base_filename = os.path.splitext(os.path.basename(input_path))[0]

    # Column names for the chosen eye.
    x_col = f'{which_eye}_eye_gaze_position_x'
    y_col = f'{which_eye}_eye_gaze_position_y'
    valid_col = f'{which_eye}_eye_valid'

    # ---- Load the raw CSV first so we can validate columns before
    # ---- running the (potentially slow) event detector.
    raw_data = pd.read_csv(input_path)
    print(f"  Total samples: {len(raw_data)}")

    required_cols = [timestamp_col, x_col, y_col, valid_col]
    missing = [c for c in required_cols if c not in raw_data.columns]
    if missing:
        print(f"  Warning: missing columns {missing}; skipping.")
        print(f"  Available columns: {list(raw_data.columns)}")
        return False

    # ---- Run eye movement event detection ----
    # This generates BLK_ (blinks), FIX_ (fixations) and SAC_ (saccades)
    # files in the output directory.
    ed.detect(input_path, output_dir=output_dir, which_eye=which_eye)

    # ---- Load saccade results ----
    sac_file = os.path.join(output_dir, f"SAC_{base_filename}.csv")
    if not os.path.exists(sac_file):
        print(f"  Warning: saccade file not found: {sac_file}")
        return False

    saccades = pd.read_csv(sac_file)
    print(f"  Detected {len(saccades)} saccades")

    # ---- Prepare gaze data for plotting ----
    # Convert timestamps from nanoseconds to seconds.
    time_s = raw_data[timestamp_col] / ns_per_s

    # Replace invalid gaze positions with NaN so matplotlib breaks the
    # line at those samples instead of drawing across them.
    raw_full = raw_data.copy()
    raw_full.loc[raw_full[valid_col] != 1, x_col] = float('nan')
    raw_full.loc[raw_full[valid_col] != 1, y_col] = float('nan')

    # ---- Create the visualization ----
    fig, ax = plt.subplots(figsize=(14, 6))

    # Gaze X and Y over time on the same axes.
    ax.plot(time_s, raw_full[x_col],
            color='#0072BD', linewidth=2.8, alpha=0.9,
            label='Gaze X', zorder=3)
    ax.plot(time_s, raw_full[y_col],
            color='#D95319', linewidth=2.8, alpha=0.9,
            label='Gaze Y', zorder=3)

    ax.set_ylabel('Gaze position (pixels)', fontsize=12)
    ax.set_xlabel('Time (s)', fontsize=12)
    ax.grid(alpha=0.3)

    # ---- Highlight saccade periods with shaded vertical strips ----
    # onset_i and offset_i are sample indices into the raw data. They are
    # looked up in the time_s series to obtain the corresponding times in
    # seconds, so the strips align with the x-axis. zorder=2 keeps the
    # strips behind the gaze traces (zorder=3) so the traces stay visible.
    #
    # A flag is used instead of "idx == 0" so the legend entry is still
    # created if the first saccade happens to be skipped for
    # out-of-range indices.
    saccade_label_added = False

    for saccade_number, (_, saccade) in enumerate(saccades.iterrows(), start=1):
        onset_i = int(saccade['onset_i'])
        offset_i = int(saccade['offset_i'])

        # Guard against out-of-range indices in case of a corrupt file.
        if not (0 <= onset_i < len(time_s) and 0 <= offset_i < len(time_s)):
            print(f"  Warning: saccade {saccade_number} has out-of-range "
                  f"indices (onset_i={onset_i}, offset_i={offset_i}); "
                  f"skipping.")
            continue

        onset_s = time_s.iloc[onset_i]
        offset_s = time_s.iloc[offset_i]

        ax.axvspan(onset_s, offset_s,
                   alpha=0.3, color='orange',
                   edgecolor='darkorange', linewidth=0.8,
                   zorder=2,
                   label='Saccade' if not saccade_label_added else "")
        saccade_label_added = True

        # Annotate with the saccade number near the top of the plot,
        # centred between the strip's edges.
        mid_point = (onset_s + offset_s) / 2
        ax.annotate(str(saccade_number),
                    xy=(mid_point, ax.get_ylim()[1] * 0.95),
                    ha='center', fontsize=9, color='darkorange',
                    fontweight='bold', zorder=4)

    # Legend must be added after the saccade strips so it picks up the
    # 'Saccade' entry created inside the loop.
    ax.legend(loc='upper right', fontsize=11, framealpha=0.9)

    ax.set_title(
        f'Gaze X and Y over time with saccade periods\n'
        f'File: {base_filename}',
        fontsize=13,
    )
    plt.tight_layout()

    # ---- Save the figure ----
    output_plot = os.path.join(
        output_dir, f'saccade_trace_{base_filename}.png'
    )
    plt.savefig(output_plot, dpi=150, bbox_inches='tight')
    print(f"  Plot saved to: {output_plot}")

    # ---- Show the plot in a pop-up window ----
    # block=True makes the call block until the window is closed, so each
    # file is reviewed one at a time before the loop continues.
    if show_plots:
        plt.show(block=True)

    # Close the figure to free memory before processing the next file.
    plt.close(fig)
    return True


def main():
    if not os.path.isdir(input_dir):
        print(f"Input directory not found: '{input_dir}'")
        return

    os.makedirs(output_dir, exist_ok=True)

    csv_files = sorted(glob.glob(os.path.join(input_dir, '*.csv')))
    if not csv_files:
        print(f"No CSV files found in '{input_dir}'.")
        return

    # Initialize the event detector once and reuse it across files.
    ed = EventDetection()

    succeeded = 0
    failed = 0

    for input_path in csv_files:
        try:
            if process_file(ed, input_path, output_dir, which_eye,
                            timestamp_col, NS_PER_S, show_plots):
                succeeded += 1
            else:
                failed += 1
        except Exception as err:
            print(f"  Error processing {input_path}: {err}")
            failed += 1

    # ---- Summary ----
    print()
    print("=" * 60)
    print(f"Processed {len(csv_files)} file(s): "
          f"{succeeded} succeeded, {failed} failed.")


if __name__ == '__main__':
    main()

