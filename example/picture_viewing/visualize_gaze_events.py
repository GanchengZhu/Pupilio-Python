#!/usr/bin/env python
# _*_ coding: utf-8 _*_

# Copyright (c) 2026, Hangzhou DeepGaze Science and Technology Co., Ltd
# All Rights Reserved

"""
Interactive Eye Movement Data Visualization & Event Analysis Tool
Combines Pupilio's EventDetection (I-DT algorithm) with interactive Plotly
dashboards and Matplotlib scanpath/time-series visualizations.

Features:
1. Automatic trial segmentation by triggers (e.g. trigger 202 picture onset).
2. Background stimulus image alignment with gaze coordinates (1920x1080).
3. Eye movement event detection (Fixations, Saccades, Blinks) using Pupilio EventDetection.
4. Interactive 2D Spatial Scanpath with duration-scaled fixation bubbles, saccade vectors,
   and trial-switching dropdown.
5. Synchronized time-series view: Gaze X/Y, Pupil diameter, and Velocity with shaded
   event bands (Fixation, Saccade, Blink) and interactive range slider.
6. Event distribution statistics & Main Sequence analysis.
7. Self-contained standalone HTML report (base64 embedded images) with auto-open in browser,
   plus optional interactive Matplotlib desktop GUI.
"""

import os
import sys
import argparse
import base64
import webbrowser
import numpy as np
import pandas as pd
from PIL import Image

try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox, scrolledtext
    HAS_TKINTER = True
except ImportError:
    tk = None
    HAS_TKINTER = False

# Ensure repository root is on sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    from pupilio import EventDetection
except ImportError:
    EventDetection = None

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


def image_to_base64_uri(image_path: str) -> str:
    """Convert a local image to a base64 Data URI for standalone HTML embedding."""
    if not os.path.exists(image_path):
        return ""
    ext = os.path.splitext(image_path)[1].lower()
    mime = "image/jpeg" if ext in [".jpg", ".jpeg"] else "image/png"
    with open(image_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def fallback_idt_detection(df_valid: pd.DataFrame, which_eye: str = "bino",
                           min_duration_ms: float = 50.0,
                           dispersion_threshold_deg: float = 1.0,
                           sample_interval_ms: float = 5.0) -> tuple:
    """
    Pure Python I-DT (Identification by Dispersion Threshold) fallback
    used if native EventDetection DLL is unavailable.
    """
    x_col = f"{which_eye}_eye_gaze_position_x"
    y_col = f"{which_eye}_eye_gaze_position_y"
    ppd_x_col = f"{which_eye}_eye_pixels_per_degree_x"
    ppd_y_col = f"{which_eye}_eye_pixels_per_degree_y"

    ppd_x = df_valid[ppd_x_col].median() if ppd_x_col in df_valid.columns else 54.0
    ppd_y = df_valid[ppd_y_col].median() if ppd_y_col in df_valid.columns else 54.0
    disp_thresh_px = dispersion_threshold_deg * ((ppd_x + ppd_y) / 2.0)

    min_samples = max(2, int(round(min_duration_ms / sample_interval_ms)))
    xs = df_valid[x_col].values
    ys = df_valid[y_col].values
    ts = df_valid['timestamp'].values
    n = len(xs)

    fixations = []
    i = 0
    while i <= n - min_samples:
        j = i + min_samples
        while j <= n:
            window_x = xs[i:j]
            window_y = ys[i:j]
            dispersion = (np.max(window_x) - np.min(window_x)) + (np.max(window_y) - np.min(window_y))
            if dispersion <= disp_thresh_px:
                j += 1
            else:
                break

        if j - i > min_samples:
            fix_win_x = xs[i:j - 1]
            fix_win_y = ys[i:j - 1]
            onset_ts = ts[i]
            offset_ts = ts[j - 2]
            dur_ms = (offset_ts - onset_ts) / 1e6
            fixations.append({
                'onset': int(onset_ts / 1e6),
                'offset': int(offset_ts / 1e6),
                'duration': max(1, int(dur_ms)),
                'start_x': fix_win_x[0],
                'start_y': fix_win_y[0],
                'end_x': fix_win_x[-1],
                'end_y': fix_win_y[-1],
                'avg_x': np.mean(fix_win_x),
                'avg_y': np.mean(fix_win_y),
                'eye': which_eye,
                'onset_i': i,
                'offset_i': j - 2
            })
            i = j - 1
        else:
            i += 1

    df_fix = pd.DataFrame(fixations)
    df_sac = pd.DataFrame()
    if len(df_fix) > 1:
        saccades = []
        for k in range(len(df_fix) - 1):
            f1 = df_fix.iloc[k]
            f2 = df_fix.iloc[k + 1]
            dx = (f2['start_x'] - f1['end_x']) / ppd_x
            dy = (f2['start_y'] - f1['end_y']) / ppd_y
            amp_deg = np.sqrt(dx ** 2 + dy ** 2)
            sac_dur = max(5, int(f2['onset'] - f1['offset']))
            peak_v = amp_deg / (sac_dur / 1000.0) if sac_dur > 0 else 0
            saccades.append({
                'onset': f1['offset'],
                'offset': f2['onset'],
                'duration': sac_dur,
                'start_x': f1['end_x'],
                'start_y': f1['end_y'],
                'end_x': f2['start_x'],
                'end_y': f2['start_y'],
                'sac_amp': amp_deg,
                'eye': which_eye,
                'peakv': peak_v,
                'onset_i': int(f1['offset_i']),
                'offset_i': int(f2['onset_i'])
            })
        df_sac = pd.DataFrame(saccades)

    # Detect blinks from eye valid flag (valid == 0 or valid != 1)
    df_blk = pd.DataFrame()
    valid_col = f"{which_eye}_eye_valid"
    if valid_col not in df_valid.columns:
        valid_col = 'bino_eye_valid' if 'bino_eye_valid' in df_valid.columns else 'left_eye_valid'
    if valid_col in df_valid.columns:
        blinks = []
        is_invalid = (df_valid[valid_col] != 1).values
        in_blk = False
        blk_start = 0
        for k_idx, val in enumerate(is_invalid):
            if val and not in_blk:
                in_blk = True
                blk_start = k_idx
            elif not val and in_blk:
                in_blk = False
                blk_end = k_idx
                dur_ms = (ts[blk_end - 1] - ts[blk_start]) / 1e6 if blk_end > blk_start else 0
                if dur_ms >= 30:  # Minimum 30ms for blink
                    blinks.append({
                        'onset': int(ts[blk_start] / 1e6),
                        'offset': int(ts[min(n - 1, blk_end)] / 1e6),
                        'duration': max(1, int(dur_ms)),
                        'start_x': xs[max(0, blk_start - 1)],
                        'start_y': ys[max(0, blk_start - 1)],
                        'end_x': xs[min(n - 1, blk_end)],
                        'end_y': ys[min(n - 1, blk_end)],
                        'sac_amp': 0.0,
                        'eye': which_eye,
                        'onset_i': blk_start,
                        'offset_i': blk_end,
                        'peakv': np.nan,
                        'blink': 1
                    })
        if blinks:
            df_blk = pd.DataFrame(blinks)

    return df_fix, df_sac, df_blk


class GazeDataAnalyzer:
    """Loads eye-tracking data, segments trials, runs EventDetection, and provides metrics."""

    def __init__(self, data_path: str, img_dir: str = None, output_dir: str = None,
                 which_eye: str = 'bino', min_duration: int = 50, dispersion: float = 1.0):
        self.data_path = os.path.abspath(data_path)
        self.which_eye = which_eye
        self.min_duration = min_duration
        self.dispersion = dispersion

        if img_dir is None:
            self.img_dir = os.path.join(os.path.dirname(self.data_path), '..', 'images')
        else:
            self.img_dir = os.path.abspath(img_dir)

        if output_dir is None:
            self.output_dir = os.path.join(os.path.dirname(self.data_path), '..', 'output')
        else:
            self.output_dir = os.path.abspath(output_dir)
        os.makedirs(self.output_dir, exist_ok=True)

        self.df_raw = None
        self.df_clean = None
        self.df_fix = pd.DataFrame()
        self.df_sac = pd.DataFrame()
        self.df_blk = pd.DataFrame()
        self.trials = []
        self.sampling_rate = 200

        self._load_and_preprocess()
        self._detect_events()
        self._segment_trials()

    def _load_and_preprocess(self):
        print(f"[1/4] Loading gaze data from: {self.data_path}")
        self.df_raw = pd.read_csv(self.data_path)

        valid_col = f"{self.which_eye}_eye_valid"
        if valid_col not in self.df_raw.columns:
            valid_col = 'bino_eye_valid' if 'bino_eye_valid' in self.df_raw.columns else 'left_eye_valid'

        # Filter out injected / duplicate records where dt <= 2ns
        # Note: In deepgaze/pupilio datasets, triggers and messages can be logged on injected +1ns rows.
        # We propagate any trigger or message back to the preceding genuine frame before filtering.
        is_dup = (self.df_raw['timestamp'].diff() <= 2)
        if is_dup.any():
            dup_trigger_indices = self.df_raw[is_dup & (self.df_raw['trigger'] > 0)].index
            for idx in dup_trigger_indices:
                if idx > 0:
                    self.df_raw.loc[idx - 1, 'trigger'] = self.df_raw.loc[idx, 'trigger']

            if 'message' in self.df_raw.columns:
                dup_msg_indices = self.df_raw[is_dup & self.df_raw['message'].notna()].index
                for idx in dup_msg_indices:
                    if idx > 0:
                        self.df_raw.loc[idx - 1, 'message'] = self.df_raw.loc[idx, 'message']

            self.df_genuine = self.df_raw[~is_dup].copy().reset_index(drop=True)
        else:
            self.df_genuine = self.df_raw.copy().reset_index(drop=True)

        # Baseline timestamp in seconds
        t0 = self.df_genuine['timestamp'].iloc[0]
        self.df_genuine['time_s'] = (self.df_genuine['timestamp'] - t0) / 1e9
        self.df_raw['time_s'] = (self.df_raw['timestamp'] - t0) / 1e9

        # df_clean is df_genuine, preserving valid==0 frames for blink detection
        self.df_clean = self.df_genuine

        total_time_s = self.df_genuine['time_s'].iloc[-1] - self.df_genuine['time_s'].iloc[0] if len(self.df_genuine) > 0 else 0
        self.nominal_rate = int(round(len(self.df_raw) / total_time_s)) if total_time_s > 0 else 200

        # Estimate effective frame rate and interval based on genuine frames
        dt_s = self.df_genuine['time_s'].diff().median()
        if dt_s and dt_s > 0:
            self.sample_interval_ms = dt_s * 1000.0
            self.effective_rate = int(round(1.0 / dt_s))
        else:
            self.sample_interval_ms = 5.0
            self.effective_rate = self.nominal_rate

        self.sampling_rate = self.nominal_rate

        valid_samples = (self.df_genuine[valid_col] == 1).sum() if valid_col in self.df_genuine.columns else len(self.df_genuine)
        print(f"      Total raw rows: {len(self.df_raw)} (Nominal Rate: {self.nominal_rate} Hz), "
              f"Genuine frames: {len(self.df_genuine)} (Effective Rate: ~{self.effective_rate} Hz, Frame Interval: {self.sample_interval_ms:.2f}ms), "
              f"Valid samples: {valid_samples} ({valid_samples/max(1, len(self.df_genuine))*100:.1f}%)")

    def _detect_events(self):
        print(f"[2/4] Running Pupilio Event Detection (Eye: {self.which_eye}, MinDur: {self.min_duration}ms, Disp: {self.dispersion}deg)...")
        temp_clean_path = os.path.join(self.output_dir, "_temp_clean_for_ed.csv")
        self.df_clean.to_csv(temp_clean_path, index=False)

        used_native = False
        if EventDetection is not None:
            try:
                ed = EventDetection()
                ed.detect(temp_clean_path, self.output_dir, which_eye=self.which_eye,
                          minimum_duration=self.min_duration, dispersion_threshold=self.dispersion)
                base_name = os.path.splitext(os.path.basename(temp_clean_path))[0]
                fix_file = os.path.join(self.output_dir, f"FIX_{base_name}.csv")
                sac_file = os.path.join(self.output_dir, f"SAC_{base_name}.csv")
                blk_file = os.path.join(self.output_dir, f"BLK_{base_name}.csv")

                if os.path.exists(fix_file):
                    self.df_fix = pd.read_csv(fix_file)
                if os.path.exists(sac_file):
                    self.df_sac = pd.read_csv(sac_file)
                if os.path.exists(blk_file):
                    self.df_blk = pd.read_csv(blk_file)
                used_native = True
            except Exception as e:
                print(f"      [Notice] Native EventDetection exception ({e}), using fallback I-DT.")

        if not used_native or len(self.df_fix) == 0:
            self.df_fix, self.df_sac, self.df_blk = fallback_idt_detection(
                self.df_clean, which_eye=self.which_eye,
                min_duration_ms=self.min_duration, dispersion_threshold_deg=self.dispersion
            )

        # Map onset_i and offset_i to absolute time in seconds using df_genuine timeline
        t0 = self.df_genuine['timestamp'].iloc[0]
        n_pts = len(self.df_genuine)

        if len(self.df_fix) > 0 and 'onset_i' in self.df_fix.columns:
            # Fixation onset_i: 1-based index in Pupilio DLL output
            self.df_fix['onset_s'] = self.df_fix['onset_i'].apply(
                lambda idx: self.df_genuine.iloc[max(0, min(int(idx) - 1, n_pts - 1))]['time_s']
            )
            self.df_fix['offset_s'] = self.df_fix['offset_i'].apply(
                lambda idx: self.df_genuine.iloc[max(0, min(int(idx), n_pts - 1))]['time_s']
            )

        if len(self.df_sac) > 0 and 'onset_i' in self.df_sac.columns:
            # Saccade onset_i: 0-based index matching start_x/y
            self.df_sac['onset_s'] = self.df_sac['onset_i'].apply(
                lambda idx: self.df_genuine.iloc[max(0, min(int(idx), n_pts - 1))]['time_s']
            )
            # Saccade offset_i: 0-based landing frame on next fixation
            self.df_sac['offset_s'] = self.df_sac['offset_i'].apply(
                lambda idx: self.df_genuine.iloc[max(0, min(int(idx), n_pts - 1))]['time_s']
            )

        if len(self.df_blk) > 0 and 'onset_i' in self.df_blk.columns:
            # Blink onset_i: 0-based index
            self.df_blk['onset_s'] = self.df_blk['onset_i'].apply(
                lambda idx: self.df_genuine.iloc[max(0, min(int(idx), n_pts - 1))]['time_s']
            )
            self.df_blk['offset_s'] = self.df_blk['offset_i'].apply(
                lambda idx: self.df_genuine.iloc[max(0, min(int(idx), n_pts - 1))]['time_s']
            )

        # Cleanup temporary clean file
        if os.path.exists(temp_clean_path):
            try:
                os.remove(temp_clean_path)
            except OSError:
                pass

        print(f"      Detected: {len(self.df_fix)} Fixations, {len(self.df_sac)} Saccades, {len(self.df_blk)} Blinks")

    def _segment_trials(self):
        """Identify experiment trials from trigger events (e.g. trigger 202) and align with images."""
        print(f"[3/4] Segmenting experimental trials...")
        trigger_rows = self.df_genuine[self.df_genuine['trigger'] > 0]

        # Available stimulus images in order
        candidate_images = ['gray_grid.jpg', 'west_lake.jpg', 'old_town.jpg']
        actual_images = [img for img in candidate_images if os.path.exists(os.path.join(self.img_dir, img))]

        if len(trigger_rows) > 0:
            indices = list(trigger_rows.index)
            times = list(trigger_rows['time_s'])

            for i in range(len(indices)):
                start_time = times[i]
                end_time = times[i+1] if i+1 < len(times) else self.df_genuine['time_s'].iloc[-1]
                start_idx = indices[i]
                end_idx = indices[i+1] if i+1 < len(indices) else len(self.df_genuine) - 1

                img_name = actual_images[i] if i < len(actual_images) else f"Stimulus {i+1}"
                img_path = os.path.join(self.img_dir, img_name) if os.path.exists(os.path.join(self.img_dir, img_name)) else None

                self.trials.append({
                    'trial_id': i + 1,
                    'name': f"Trial {i+1}: {img_name}",
                    'image_name': img_name,
                    'image_path': img_path,
                    'start_time': start_time,
                    'end_time': end_time,
                    'start_idx': start_idx,
                    'end_idx': end_idx
                })
        else:
            # Single whole session trial
            img_name = actual_images[0] if actual_images else "Stimulus"
            img_path = os.path.join(self.img_dir, img_name) if actual_images else None
            self.trials.append({
                'trial_id': 1,
                'name': "Full Session",
                'image_name': img_name,
                'image_path': img_path,
                'start_time': self.df_genuine['time_s'].iloc[0],
                'end_time': self.df_genuine['time_s'].iloc[-1],
                'start_idx': 0,
                'end_idx': len(self.df_genuine) - 1
            })

        for tr in self.trials:
            print(f"      {tr['name']} | Time: {tr['start_time']:.2f}s - {tr['end_time']:.2f}s "
                  f"(Duration: {tr['end_time']-tr['start_time']:.2f}s)")

    def get_summary_metrics(self) -> dict:
        total_time_s = self.df_genuine['time_s'].iloc[-1] - self.df_genuine['time_s'].iloc[0] if len(self.df_genuine) > 0 else 0
        valid_col = f"{self.which_eye}_eye_valid"
        if valid_col not in self.df_genuine.columns:
            valid_col = 'bino_eye_valid' if 'bino_eye_valid' in self.df_genuine.columns else 'left_eye_valid'
        valid_samples = (self.df_genuine[valid_col] == 1).sum() if valid_col in self.df_genuine.columns else len(self.df_genuine)
        valid_ratio = valid_samples / max(1, len(self.df_genuine)) * 100.0

        fix_dur_mean = self.df_fix['duration'].mean() if len(self.df_fix) > 0 else 0
        fix_dur_med = self.df_fix['duration'].median() if len(self.df_fix) > 0 else 0
        fix_total_s = self.df_fix['duration'].sum() / 1000.0 if len(self.df_fix) > 0 else 0

        sac_amp_mean = self.df_sac['sac_amp'].mean() if len(self.df_sac) > 0 and 'sac_amp' in self.df_sac else 0
        sac_peakv_mean = self.df_sac['peakv'].dropna().mean() if len(self.df_sac) > 0 and 'peakv' in self.df_sac else 0

        blink_count = len(self.df_blk)
        blink_dur_mean = self.df_blk['duration'].mean() if blink_count > 0 and 'duration' in self.df_blk else 0
        blink_rate_bpm = (blink_count / (total_time_s / 60.0)) if total_time_s > 0 else 0

        return {
            'total_time_s': total_time_s,
            'total_samples': len(self.df_genuine),
            'valid_samples': valid_samples,
            'tracking_ratio': valid_ratio,
            'fixation_count': len(self.df_fix),
            'fix_dur_mean': fix_dur_mean,
            'fix_dur_med': fix_dur_med,
            'fix_total_s': fix_total_s,
            'saccade_count': len(self.df_sac),
            'sac_amp_mean': sac_amp_mean,
            'sac_peakv_mean': sac_peakv_mean,
            'blink_count': blink_count,
            'blink_dur_mean': blink_dur_mean,
            'blink_rate_bpm': blink_rate_bpm,
            'nominal_rate': self.nominal_rate,
            'effective_rate': self.effective_rate,
            'sample_interval_ms': self.sample_interval_ms
        }


def build_plotly_dashboard(analyzer: GazeDataAnalyzer, html_out_path: str):
    """Generates a rich, interactive Plotly dashboard report and saves as HTML."""
    if not HAS_PLOTLY:
        print("[Error] plotly is not installed. Please install plotly.")
        return

    print(f"[4/4] Building interactive HTML dashboard: {html_out_path}")
    metrics = analyzer.get_summary_metrics()

    # Pre-encode all trial images to base64 Data URIs
    trial_images_b64 = {}
    for tr in analyzer.trials:
        if tr['image_path'] and os.path.exists(tr['image_path']):
            trial_images_b64[tr['trial_id']] = image_to_base64_uri(tr['image_path'])
        else:
            trial_images_b64[tr['trial_id']] = ""

    # Gaze and Pupil column names
    eye = analyzer.which_eye
    gx_col = f"{eye}_eye_gaze_position_x" if f"{eye}_eye_gaze_position_x" in analyzer.df_raw else 'bino_eye_gaze_position_x'
    gy_col = f"{eye}_eye_gaze_position_y" if f"{eye}_eye_gaze_position_y" in analyzer.df_raw else 'bino_eye_gaze_position_y'
    pupil_l = 'left_eye_pupil_diameter_mm'
    pupil_r = 'right_eye_pupil_diameter_mm'
    valid_col = f"{eye}_eye_valid" if f"{eye}_eye_valid" in analyzer.df_raw else 'bino_eye_valid'

    # Filtered valid gaze for continuous plotting (with NaNs to break lines during blinks)
    df_plot = analyzer.df_genuine.copy()
    df_plot.loc[df_plot[valid_col] != 1, [gx_col, gy_col]] = np.nan

    # Calculate angular velocity (deg/s) on genuine continuous frames
    ppd = 54.0
    dx = df_plot[gx_col].diff() / ppd
    dy = df_plot[gy_col].diff() / ppd
    dt = df_plot['time_s'].diff()
    speed_deg = np.sqrt(dx ** 2 + dy ** 2) / dt.replace(0, np.nan)
    speed_deg = speed_deg.clip(upper=1000)

    # ==================== Figure 1: Spatial Scanpath ====================
    fig_spatial = go.Figure()

    # Trace 0: Raw Gaze Path
    fig_spatial.add_trace(go.Scatter(
        x=df_plot[gx_col],
        y=df_plot[gy_col],
        mode='lines',
        line=dict(color='rgba(0, 180, 255, 0.35)', width=1.5),
        name='Raw Gaze Path',
        hoverinfo='skip'
    ))

    # Trace 1: Saccade Vectors
    if len(analyzer.df_sac) > 0:
        sac_x = []
        sac_y = []
        for _, sac in analyzer.df_sac.iterrows():
            sac_x.extend([sac['start_x'], sac['end_x'], None])
            sac_y.extend([sac['start_y'], sac['end_y'], None])
        fig_spatial.add_trace(go.Scatter(
            x=sac_x, y=sac_y,
            mode='lines',
            line=dict(color='rgba(255, 140, 0, 0.65)', width=2, dash='solid'),
            name='Saccades',
            hoverinfo='skip'
        ))

    # Trace 2: Blinks (positions where gaze was lost/recovered)
    if len(analyzer.df_blk) > 0:
        blk_text = [
            f"<b>Blink #{i+1}</b><br>"
            f"Duration: {row['duration']} ms<br>"
            f"Time: {row.get('onset_s', 0):.2f}s - {row.get('offset_s', 0):.2f}s<br>"
            f"Start: ({row['start_x']:.1f}, {row['start_y']:.1f})<br>"
            f"End: ({row['end_x']:.1f}, {row['end_y']:.1f})"
            for i, row in analyzer.df_blk.iterrows()
        ]
        fig_spatial.add_trace(go.Scatter(
            x=analyzer.df_blk['start_x'],
            y=analyzer.df_blk['start_y'],
            mode='markers',
            marker=dict(
                size=12,
                symbol='x',
                color='#8338ec',
                line=dict(color='white', width=1.5)
            ),
            hovertext=blk_text,
            hoverinfo='text',
            name='Blinks'
        ))

    # Trace 3: Fixation Bubbles
    if len(analyzer.df_fix) > 0:
        fix_text = [
            f"<b>Fixation #{i+1}</b><br>"
            f"Duration: {row['duration']} ms<br>"
            f"Time: {row.get('onset_s', 0):.2f}s - {row.get('offset_s', 0):.2f}s<br>"
            f"Pos: ({row['avg_x']:.1f}, {row['avg_y']:.1f})"
            for i, row in analyzer.df_fix.iterrows()
        ]
        # Size mapping: duration ms to radius 8-36
        sizes = np.clip(np.sqrt(analyzer.df_fix['duration']) * 1.4, 8, 40)
        colors = np.arange(len(analyzer.df_fix))

        fig_spatial.add_trace(go.Scatter(
            x=analyzer.df_fix['avg_x'],
            y=analyzer.df_fix['avg_y'],
            mode='markers+text',
            marker=dict(
                size=sizes,
                color=colors,
                colorscale='Viridis',
                showscale=True,
                colorbar=dict(title='Fixation Order', thickness=14, len=0.6, y=0.5),
                line=dict(color='white', width=1.5),
                opacity=0.85
            ),
            text=[str(i+1) for i in range(len(analyzer.df_fix))],
            textposition='middle center',
            textfont=dict(size=10, color='white'),
            hovertext=fix_text,
            hoverinfo='text',
            name='Fixations'
        ))

    # Default image background (Trial 1 or first available)
    first_b64 = trial_images_b64.get(1, "") or (list(trial_images_b64.values())[0] if trial_images_b64 else "")
    images_layout = []
    if first_b64:
        images_layout.append(dict(
            source=first_b64,
            xref="x", yref="y",
            x=0, y=0,
            sizex=1920, sizey=1080,
            sizing="stretch",
            opacity=0.85,
            layer="below"
        ))

    # Trial dropdown buttons for Figure 1
    buttons_spatial = []
    # Full session button
    buttons_spatial.append(dict(
        label="Full Session (All Data)",
        method="update",
        args=[
            {"visible": [True] * (3 + (1 if len(analyzer.df_blk) > 0 else 0))},
            {"images": images_layout}
        ]
    ))
    # Trial buttons
    for tr in analyzer.trials:
        tr_id = tr['trial_id']
        tr_b64 = trial_images_b64.get(tr_id, "")
        tr_img_cfg = [dict(
            source=tr_b64,
            xref="x", yref="y",
            x=0, y=0,
            sizex=1920, sizey=1080,
            sizing="stretch",
            opacity=0.85,
            layer="below"
        )] if tr_b64 else []

        buttons_spatial.append(dict(
            label=f"{tr['name']}",
            method="update",
            args=[
                {},  # keep traces
                {"images": tr_img_cfg}
            ]
        ))

    fig_spatial.update_layout(
        title="<b>2D Spatial Scanpath on Stimulus</b> (Hover for Fixation/Blink Details, Click Legend to Toggle)",
        xaxis=dict(range=[0, 1920], title="Screen X (pixels)", showgrid=True, zeroline=False),
        yaxis=dict(range=[1080, 0], title="Screen Y (pixels)", showgrid=True, zeroline=False),
        width=1100,
        height=680,
        images=images_layout,
        template='plotly_white',
        updatemenus=[
            dict(
                buttons=buttons_spatial,
                direction="down",
                showactive=True,
                x=0.0, y=1.14,
                xanchor="left", yanchor="top",
                bgcolor="#f8f9fa",
                bordercolor="#ced4da"
            )
        ],
        margin=dict(l=60, r=40, t=100, b=50)
    )

    # ==================== Figure 2: Synchronized Time-Series ====================
    fig_temporal = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.055,
        subplot_titles=(
            "<b>① Gaze Position (X & Y, Screen Pixels) & Event Intervals</b>",
            "<b>② Pupil Diameter (Left & Right Eye, mm)</b>",
            "<b>③ Angular Gaze Velocity (deg/s)</b>"
        ),
        row_heights=[0.42, 0.28, 0.30]
    )

    # Row 1: Gaze X & Y
    fig_temporal.add_trace(go.Scatter(
        x=df_plot['time_s'], y=df_plot[gx_col],
        name="Gaze X (px)", line=dict(color='#0077b6', width=1.4)
    ), row=1, col=1)

    fig_temporal.add_trace(go.Scatter(
        x=df_plot['time_s'], y=df_plot[gy_col],
        name="Gaze Y (px)", line=dict(color='#7209b7', width=1.4)
    ), row=1, col=1)

    # Row 2: Pupil diameter
    has_pupil = False
    if pupil_l in analyzer.df_genuine.columns:
        valid_pupil_l = analyzer.df_genuine[pupil_l].replace(0, np.nan)
        if valid_pupil_l.notna().sum() > 0:
            has_pupil = True
            fig_temporal.add_trace(go.Scatter(
                x=analyzer.df_genuine['time_s'], y=valid_pupil_l,
                name="Left Pupil (mm)", line=dict(color='#2a9d8f', width=1.4)
            ), row=2, col=1)

    if pupil_r in analyzer.df_genuine.columns:
        valid_pupil_r = analyzer.df_genuine[pupil_r].replace(0, np.nan)
        if valid_pupil_r.notna().sum() > 0:
            has_pupil = True
            fig_temporal.add_trace(go.Scatter(
                x=analyzer.df_genuine['time_s'], y=valid_pupil_r,
                name="Right Pupil (mm)", line=dict(color='#e76f51', width=1.4)
            ), row=2, col=1)

    if not has_pupil:
        fig_temporal.add_annotation(
            text="No pupil diameter data recorded in this session",
            xref="x2", yref="y2", x=df_plot['time_s'].median(), y=0.5,
            showarrow=False, font=dict(color="gray", size=12)
        )

    # Row 3: Velocity
    fig_temporal.add_trace(go.Scatter(
        x=df_plot['time_s'], y=speed_deg,
        name="Gaze Speed (deg/s)", line=dict(color='#e63946', width=1.2),
        fill='tozeroy', fillcolor='rgba(230, 57, 70, 0.15)'
    ), row=3, col=1)

    # Add shaded regions for Events:
    # 1. Fixations: Soft Green on Row 1 (Gaze Position)
    for _, fix in analyzer.df_fix.iterrows():
        onset_s = fix.get('onset_s', None)
        offset_s = fix.get('offset_s', None)
        if onset_s is not None and offset_s is not None:
            fig_temporal.add_vrect(
                x0=onset_s, x1=offset_s,
                fillcolor="rgba(46, 204, 113, 0.16)",
                layer="below", line_width=0,
                row=1, col=1
            )

    # 2. Saccades: Distinct Orange band on Row 1 (Position) and Row 3 (Velocity)
    for _, sac in analyzer.df_sac.iterrows():
        onset_s = sac.get('onset_s', None)
        offset_s = sac.get('offset_s', None)
        if onset_s is not None and offset_s is not None:
            for r in [1, 3]:
                fig_temporal.add_vrect(
                    x0=onset_s, x1=offset_s,
                    fillcolor="rgba(243, 156, 18, 0.35)",
                    line_color="rgba(243, 156, 18, 0.70)",
                    line_width=1,
                    layer="below",
                    row=r, col=1
                )

    # 3. Blinks: Lavender/Purple band across all 3 subplots
    for _, blk in analyzer.df_blk.iterrows():
        onset_s = blk.get('onset_s', None)
        offset_s = blk.get('offset_s', None)
        if onset_s is not None and offset_s is not None:
            for r in [1, 2, 3]:
                fig_temporal.add_vrect(
                    x0=onset_s, x1=offset_s,
                    fillcolor="rgba(155, 89, 182, 0.30)",
                    line_color="rgba(155, 89, 182, 0.70)",
                    line_width=1,
                    layer="below",
                    row=r, col=1
                )

    # Add Vertical dashed lines and aligned trial labels for stimulus images
    for tr in analyzer.trials:
        # Boundary dashed line at stimulus onset across all rows
        fig_temporal.add_vline(
            x=tr['start_time'], line_width=1.5, line_dash="dash", line_color="#495057"
        )
        # Place trial/image label inside its own interval on Row 1 (top-left inside segment)
        dur_s = tr['end_time'] - tr['start_time']
        fig_temporal.add_annotation(
            xref="x", yref="y domain",
            x=tr['start_time'] + 0.12, y=0.98,
            xanchor="left", yanchor="top",
            text=f"🖼️ <b>Trial {tr['trial_id']}: {tr['image_name']}</b> ({dur_s:.1f}s)",
            showarrow=False,
            font=dict(size=11, color="#1d3557"),
            bgcolor="rgba(255, 255, 255, 0.88)",
            bordercolor="rgba(108, 117, 125, 0.45)",
            borderwidth=1,
            borderpad=4
        )

    # Add session terminating boundary line if trials exist
    if analyzer.trials:
        fig_temporal.add_vline(
            x=analyzer.trials[-1]['end_time'], line_width=1.5, line_dash="dash", line_color="#495057"
        )

    fig_temporal.update_layout(
        title=(
            "<b>Synchronized Eye Tracking Time-Series</b> &nbsp;&nbsp;&nbsp;&nbsp; "
            "<span style='font-size:12px; color:#495057; font-weight:normal;'>"
            "[事件阴影: <span style='color:#27ae60;'>■ 注视 Fixation</span> &nbsp;|&nbsp; "
            "<span style='color:#e67e22;'>■ 眼跳 Saccade</span> &nbsp;|&nbsp; "
            "<span style='color:#8e44ad;'>■ 眨眼 Blink</span>]"
            "</span>"
        ),
        height=1120,
        margin=dict(l=60, r=40, t=95, b=50),
        template='plotly_white',
        xaxis3=dict(
            title="Time (seconds)",
            rangeslider=dict(visible=True, thickness=0.05),
            type="linear"
        ),
        yaxis=dict(title="Position (px)"),
        yaxis2=dict(title="Pupil (mm)"),
        yaxis3=dict(title="Speed (deg/s)"),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1.0,
            bgcolor="rgba(255, 255, 255, 0.85)",
            bordercolor="#dee2e6",
            borderwidth=1
        )
    )

    # ==================== Figure 3: Event Statistics ====================
    fig_stats = make_subplots(
        rows=1, cols=3,
        subplot_titles=(
            "<b>Fixation Duration Distribution</b>",
            "<b>Saccade Main Sequence (Amp vs Peak Vel)</b>",
            "<b>Blink Duration Distribution</b>"
        )
    )

    if len(analyzer.df_fix) > 0:
        fig_stats.add_trace(go.Histogram(
            x=analyzer.df_fix['duration'],
            nbinsx=20,
            marker_color='#457b9d',
            name='Fixation Duration (ms)'
        ), row=1, col=1)

    if len(analyzer.df_sac) > 0 and 'sac_amp' in analyzer.df_sac and 'peakv' in analyzer.df_sac:
        valid_sac = analyzer.df_sac.dropna(subset=['sac_amp', 'peakv'])
        fig_stats.add_trace(go.Scatter(
            x=valid_sac['sac_amp'],
            y=valid_sac['peakv'],
            mode='markers',
            marker=dict(size=9, color='#e76f51', opacity=0.75, line=dict(color='black', width=0.8)),
            hovertext=[f"Amp: {r['sac_amp']:.2f}°<br>Peak: {r['peakv']:.1f}°/s<br>Dur: {r['duration']}ms" for _, r in valid_sac.iterrows()],
            hoverinfo='text',
            name='Saccade'
        ), row=1, col=2)

    if len(analyzer.df_blk) > 0:
        fig_stats.add_trace(go.Histogram(
            x=analyzer.df_blk['duration'],
            nbinsx=15,
            marker_color='#9d4edd',
            name='Blink Duration (ms)'
        ), row=1, col=3)

    fig_stats.update_layout(
        title="<b>Eye Movement Event Statistics</b>",
        template='plotly_white',
        height=380,
        showlegend=False
    )
    fig_stats.update_xaxes(title_text="Duration (ms)", row=1, col=1)
    fig_stats.update_yaxes(title_text="Count", row=1, col=1)
    fig_stats.update_xaxes(title_text="Amplitude (deg)", row=1, col=2)
    fig_stats.update_yaxes(title_text="Peak Velocity (deg/s)", row=1, col=2)
    fig_stats.update_xaxes(title_text="Duration (ms)", row=1, col=3)
    fig_stats.update_yaxes(title_text="Count", row=1, col=3)

    # Convert figures to standalone HTML divs
    div_spatial = fig_spatial.to_html(full_html=False, include_plotlyjs='cdn')
    div_temporal = fig_temporal.to_html(full_html=False, include_plotlyjs=False)
    div_stats = fig_stats.to_html(full_html=False, include_plotlyjs=False)

    # Assemble HTML Report
    html_template = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pupilio Eye Tracking & Event Detection Interactive Report</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background-color: #f4f6f9;
            color: #2c3e50;
            margin: 0;
            padding: 24px;
        }}
        .container {{
            max-width: 1280px;
            margin: 0 auto;
        }}
        .header {{
            background: linear-gradient(135deg, #1f2937 0%, #111827 100%);
            color: white;
            padding: 28px 36px;
            border-radius: 12px;
            margin-bottom: 24px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }}
        .header h1 {{
            margin: 0 0 8px 0;
            font-size: 26px;
            letter-spacing: -0.5px;
        }}
        .header p {{
            margin: 0;
            opacity: 0.8;
            font-size: 14px;
        }}
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }}
        .kpi-card {{
            background: white;
            padding: 18px 22px;
            border-radius: 10px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            border-left: 4px solid #3b82f6;
        }}
        .kpi-card.green {{ border-left-color: #10b981; }}
        .kpi-card.purple {{ border-left-color: #8b5cf6; }}
        .kpi-card.amber {{ border-left-color: #f59e0b; }}
        .kpi-card.rose {{ border-left-color: #f43f5e; }}
        .kpi-title {{
            font-size: 13px;
            color: #6b7280;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 6px;
        }}
        .kpi-value {{
            font-size: 24px;
            font-weight: 700;
            color: #111827;
        }}
        .kpi-sub {{
            font-size: 12px;
            color: #9ca3af;
            margin-top: 4px;
        }}
        .card {{
            background: white;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 24px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        }}
        .table-responsive {{
            max-height: 280px;
            overflow-y: auto;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }}
        th, td {{
            padding: 8px 12px;
            text-align: left;
            border-bottom: 1px solid #e5e7eb;
        }}
        th {{
            background-color: #f9fafb;
            position: sticky;
            top: 0;
            color: #4b5563;
        }}
        tr:hover {{
            background-color: #f3f4f6;
        }}
        .badge {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 9999px;
            font-size: 11px;
            font-weight: 600;
        }}
        .badge-fix {{ background-color: #d1fae5; color: #065f46; }}
        .badge-sac {{ background-color: #fed7aa; color: #9a3412; }}
        .badge-blk {{ background-color: #f3e8ff; color: #7e22ce; }}
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>Pupilio 眼动数据与事件检测交互式分析报告</h1>
        <p>数据源: <code>{os.path.basename(analyzer.data_path)}</code> | 算法: Pupilio I-DT (分散阈值法) | 采样率: 标称 {analyzer.nominal_rate} Hz (实际有效眼动帧率: ~{analyzer.effective_rate} Hz, 帧间隔 {analyzer.sample_interval_ms:.2f} ms) | 分析眼: {analyzer.which_eye.upper()}</p>
    </div>

    <div class="kpi-grid">
        <div class="kpi-card">
            <div class="kpi-title">总记录时间</div>
            <div class="kpi-value">{metrics['total_time_s']:.2f} s</div>
            <div class="kpi-sub">{metrics['total_samples']:,} 帧 (标称 {metrics['nominal_rate']}Hz / 有效 ~{metrics['effective_rate']}Hz)</div>
        </div>
        <div class="kpi-card green">
            <div class="kpi-title">数据追踪率</div>
            <div class="kpi-value">{metrics['tracking_ratio']:.1f} %</div>
            <div class="kpi-sub">有效帧: {metrics['valid_samples']:,}</div>
        </div>
        <div class="kpi-card purple">
            <div class="kpi-title">注视点 (Fixations)</div>
            <div class="kpi-value">{metrics['fixation_count']} 次</div>
            <div class="kpi-sub">均长: {metrics['fix_dur_mean']:.1f} ms (总 {metrics['fix_total_s']:.1f}s)</div>
        </div>
        <div class="kpi-card amber">
            <div class="kpi-title">眼跳 (Saccades)</div>
            <div class="kpi-value">{metrics['saccade_count']} 次</div>
            <div class="kpi-sub">均幅: {metrics['sac_amp_mean']:.2f}° | 峰速: {metrics['sac_peakv_mean']:.1f}°/s</div>
        </div>
        <div class="kpi-card rose">
            <div class="kpi-title">眨眼 (Blinks)</div>
            <div class="kpi-value">{metrics['blink_count']} 次</div>
            <div class="kpi-sub">频率: {metrics['blink_rate_bpm']:.1f} 次/分 (均长: {metrics['blink_dur_mean']:.1f}ms)</div>
        </div>
    </div>

    <!-- Spatial Scanpath -->
    <div class="card">
        {div_spatial}
    </div>

    <!-- Synchronized Time Series -->
    <div class="card">
        {div_temporal}
    </div>

    <!-- Event Stats -->
    <div class="card">
        {div_stats}
    </div>

    <!-- Event Data Tables -->
    <div class="card">
        <h3>注视、眼跳与眨眼事件明细表 (前 50 项)</h3>
        <div class="table-responsive">
            <table>
                <thead>
                    <tr>
                        <th>类型</th>
                        <th>序号</th>
                        <th>起始时间 (s)</th>
                        <th>持续时间 (ms)</th>
                        <th>坐标 (X, Y)</th>
                        <th>幅值 / 峰值速度 / 备注</th>
                    </tr>
                </thead>
                <tbody>
"""

    event_rows = []
    for i, r in analyzer.df_fix.iterrows():
        event_rows.append({
            'type': '<span class="badge badge-fix">注视 Fixation</span>',
            'seq': i + 1,
            'time': r.get('onset_s', 0),
            'dur': r['duration'],
            'pos': f"({r['avg_x']:.1f}, {r['avg_y']:.1f})",
            'extra': '-'
        })

    for i, r in analyzer.df_sac.iterrows():
        event_rows.append({
            'type': '<span class="badge badge-sac">眼跳 Saccade</span>',
            'seq': i + 1,
            'time': r.get('onset_s', 0),
            'dur': r['duration'],
            'pos': f"({r['start_x']:.1f}, {r['start_y']:.1f}) → ({r['end_x']:.1f}, {r['end_y']:.1f})",
            'extra': f"幅值: {r.get('sac_amp', 0):.2f}° | 峰速: {r.get('peakv', 0):.1f}°/s"
        })

    for i, r in analyzer.df_blk.iterrows():
        event_rows.append({
            'type': '<span class="badge badge-blk">眨眼 Blink</span>',
            'seq': i + 1,
            'time': r.get('onset_s', 0),
            'dur': r['duration'],
            'pos': f"({r['start_x']:.1f}, {r['start_y']:.1f}) → ({r['end_x']:.1f}, {r['end_y']:.1f})",
            'extra': f"闭眼/失锁: {r['duration']} ms"
        })

    event_rows.sort(key=lambda x: x['time'])
    for row in event_rows[:50]:
        html_template += f"""
                    <tr>
                        <td>{row['type']}</td>
                        <td>#{row['seq']}</td>
                        <td>{row['time']:.3f} s</td>
                        <td>{row['dur']} ms</td>
                        <td>{row['pos']}</td>
                        <td>{row['extra']}</td>
                    </tr>
"""

    html_template += """
                </tbody>
            </table>
        </div>
    </div>
</div>
</body>
</html>
"""

    with open(html_out_path, "w", encoding="utf-8") as f:
        f.write(html_template)
    print(f"      Dashboard successfully saved: {html_out_path}")


def run_matplotlib_interactive_gui(analyzer: GazeDataAnalyzer):
    """Fallback / secondary interactive Matplotlib viewer."""
    if not HAS_MATPLOTLIB:
        print("[Error] matplotlib is not installed.")
        return

    print("Launching Matplotlib interactive inspection...")
    eye = analyzer.which_eye
    gx_col = f"{eye}_eye_gaze_position_x" if f"{eye}_eye_gaze_position_x" in analyzer.df_raw else 'bino_eye_gaze_position_x'
    gy_col = f"{eye}_eye_gaze_position_y" if f"{eye}_eye_gaze_position_y" in analyzer.df_raw else 'bino_eye_gaze_position_y'
    valid_col = f"{eye}_eye_valid" if f"{eye}_eye_valid" in analyzer.df_raw else 'bino_eye_valid'

    df_plot = analyzer.df_genuine.copy()
    df_plot.loc[df_plot[valid_col] != 1, [gx_col, gy_col]] = np.nan

    fig = plt.figure(figsize=(15, 9))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.2, 1.0], width_ratios=[1.3, 1.0])

    ax_scanpath = fig.add_subplot(gs[0, :])
    ax_time_x = fig.add_subplot(gs[1, 0])
    ax_time_y = fig.add_subplot(gs[1, 1], sharex=ax_time_x)

    # 1. Scanpath
    trial1 = analyzer.trials[0] if analyzer.trials else None
    if trial1 and trial1['image_path'] and os.path.exists(trial1['image_path']):
        im = Image.open(trial1['image_path'])
        ax_scanpath.imshow(im, extent=[0, 1920, 1080, 0], aspect='auto', alpha=0.75)
    else:
        ax_scanpath.set_facecolor('#f0f0f0')

    ax_scanpath.plot(df_plot[gx_col], df_plot[gy_col], color='cyan', alpha=0.4, linewidth=1, label='Raw Gaze')

    if len(analyzer.df_fix) > 0:
        sizes = np.clip(np.sqrt(analyzer.df_fix['duration']) * 2.0, 10, 45)
        scatter = ax_scanpath.scatter(
            analyzer.df_fix['avg_x'], analyzer.df_fix['avg_y'],
            s=sizes**2, c=range(len(analyzer.df_fix)), cmap='viridis',
            alpha=0.8, edgecolors='white', zorder=5, label='Fixations'
        )
        plt.colorbar(scatter, ax=ax_scanpath, label='Fixation Index', pad=0.01)

    if len(analyzer.df_blk) > 0:
        ax_scanpath.scatter(
            analyzer.df_blk['start_x'], analyzer.df_blk['start_y'],
            marker='x', s=60, color='purple', linewidths=2, zorder=6, label='Blinks'
        )

    ax_scanpath.set_xlim(0, 1920)
    ax_scanpath.set_ylim(1080, 0)
    ax_scanpath.set_title("2D Scanpath Overlay (Screen Coordinates 1920x1080)")
    ax_scanpath.set_xlabel("X (px)")
    ax_scanpath.set_ylabel("Y (px)")
    ax_scanpath.legend(loc='upper right')

    # 2. Time-series X
    ax_time_x.plot(df_plot['time_s'], df_plot[gx_col], color='royalblue', label='Gaze X')
    ax_time_x.set_ylabel("X (pixels)")
    ax_time_x.set_xlabel("Time (s)")
    ax_time_x.grid(alpha=0.3)

    # 3. Time-series Y
    ax_time_y.plot(df_plot['time_s'], df_plot[gy_col], color='darkmagenta', label='Gaze Y')
    ax_time_y.set_ylabel("Y (pixels)")
    ax_time_y.set_xlabel("Time (s)")
    ax_time_y.grid(alpha=0.3)

    # Shade events
    for i, fix in analyzer.df_fix.iterrows():
        ons = fix.get('onset_s', None)
        offs = fix.get('offset_s', None)
        if ons is not None and offs is not None:
            lbl = 'Fixation' if i == 0 else None
            ax_time_x.axvspan(ons, offs, color='lightgreen', alpha=0.25, label=lbl)
            ax_time_y.axvspan(ons, offs, color='lightgreen', alpha=0.25)

    for i, sac in analyzer.df_sac.iterrows():
        ons = sac.get('onset_s', None)
        offs = sac.get('offset_s', None)
        if ons is not None and offs is not None:
            lbl = 'Saccade' if i == 0 else None
            ax_time_x.axvspan(ons, offs, color='orange', alpha=0.35, label=lbl)
            ax_time_y.axvspan(ons, offs, color='orange', alpha=0.35)

    for i, blk in analyzer.df_blk.iterrows():
        ons = blk.get('onset_s', None)
        offs = blk.get('offset_s', None)
        if ons is not None and offs is not None:
            lbl = 'Blink' if i == 0 else None
            ax_time_x.axvspan(ons, offs, color='mediumpurple', alpha=0.35, label=lbl)
            ax_time_y.axvspan(ons, offs, color='mediumpurple', alpha=0.35)

    # Add trial boundaries to Matplotlib time-series
    for tr in analyzer.trials:
        ax_time_x.axvline(tr['start_time'], color='#495057', linestyle='--', linewidth=1.2, alpha=0.7)
        ax_time_y.axvline(tr['start_time'], color='#495057', linestyle='--', linewidth=1.2, alpha=0.7)
        dur_s = tr['end_time'] - tr['start_time']
        ax_time_x.text(
            tr['start_time'] + 0.15, 0.95, f"T{tr['trial_id']}: {tr['image_name']} ({dur_s:.1f}s)",
            transform=ax_time_x.get_xaxis_transform(),
            fontsize=8.5, color='#1d3557', weight='bold',
            verticalalignment='top', bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.85, edgecolor='#ced4da')
        )
    if analyzer.trials:
        ax_time_x.axvline(analyzer.trials[-1]['end_time'], color='#495057', linestyle='--', linewidth=1.2, alpha=0.7)
        ax_time_y.axvline(analyzer.trials[-1]['end_time'], color='#495057', linestyle='--', linewidth=1.2, alpha=0.7)

    ax_time_x.legend(loc='upper right')
    ax_time_y.legend(loc='upper right')

    plt.tight_layout()
    plt.show()


class GazeAnalysisGUI:
    """Tkinter-based GUI for Pupilio gaze analysis & event detection."""

    def __init__(self, root: tk.Tk, default_data: str, default_images: str, default_output: str):
        self.root = root
        self.root.title("Pupilio 眼动数据分析与事件检测 GUI")
        self.root.geometry("860x860")
        self.root.minsize(780, 720)

        self.var_data_path = tk.StringVar(value=default_data)
        self.var_img_dir = tk.StringVar(value=default_images)
        self.var_output_dir = tk.StringVar(value=default_output)
        self.var_eye = tk.StringVar(value="bino")
        self.var_min_dur = tk.IntVar(value=50)
        self.var_disp = tk.DoubleVar(value=1.0)
        self.var_mode = tk.StringVar(value="html")
        self.var_auto_open = tk.BooleanVar(value=True)

        self.last_html_path = os.path.join(default_output, "gaze_event_analysis_dashboard.html")
        self.analyzer = None

        self._configure_styles()
        self._build_ui()

    def _configure_styles(self):
        style = ttk.Style(self.root)
        available_themes = style.theme_names()
        if "vista" in available_themes:
            style.theme_use("vista")
        elif "clam" in available_themes:
            style.theme_use("clam")

        style.configure("Title.TLabel", font=("Microsoft YaHei UI", 15, "bold"), foreground="#1e293b")
        style.configure("Subtitle.TLabel", font=("Microsoft YaHei UI", 9), foreground="#64748b")
        style.configure("Header.TLabelframe.Label", font=("Microsoft YaHei UI", 10, "bold"), foreground="#0f172a")
        style.configure("Primary.TButton", font=("Microsoft YaHei UI", 11, "bold"), padding=6)
        style.configure("KPIValue.TLabel", font=("Segoe UI", 13, "bold"), foreground="#0284c7")
        style.configure("KPITitle.TLabel", font=("Microsoft YaHei UI", 8), foreground="#64748b")

    def _build_ui(self):
        main_container = ttk.Frame(self.root, padding="16 12 16 12")
        main_container.pack(fill=tk.BOTH, expand=True)

        # 1. Header Frame
        header_frame = ttk.Frame(main_container)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(header_frame, text="👁️ Pupilio 眼动事件检测与交互式可视化", style="Title.TLabel").pack(anchor=tk.W)
        ttk.Label(header_frame, text="结合 Pupilio I-DT 分散阈值算法 | 自动 Trial 划分与刺激图片对齐 | 网页与桌面双模态", style="Subtitle.TLabel").pack(anchor=tk.W, pady=(2, 0))

        # 2. Path Settings Frame
        path_frame = ttk.LabelFrame(main_container, text="📁 数据与刺激图路径设置", style="Header.TLabelframe", padding="10")
        path_frame.pack(fill=tk.X, pady=(0, 10))
        path_frame.columnconfigure(1, weight=1)

        # Data file
        ttk.Label(path_frame, text="眼动 CSV 数据:").grid(row=0, column=0, sticky=tk.W, pady=4)
        ttk.Entry(path_frame, textvariable=self.var_data_path).grid(row=0, column=1, sticky=tk.EW, padx=8, pady=4)
        ttk.Button(path_frame, text="浏览...", command=self._browse_data).grid(row=0, column=2, pady=4)

        # Images dir
        ttk.Label(path_frame, text="刺激图片目录:").grid(row=1, column=0, sticky=tk.W, pady=4)
        ttk.Entry(path_frame, textvariable=self.var_img_dir).grid(row=1, column=1, sticky=tk.EW, padx=8, pady=4)
        ttk.Button(path_frame, text="浏览...", command=self._browse_img_dir).grid(row=1, column=2, pady=4)

        # Output dir
        ttk.Label(path_frame, text="输出报告目录:").grid(row=2, column=0, sticky=tk.W, pady=4)
        ttk.Entry(path_frame, textvariable=self.var_output_dir).grid(row=2, column=1, sticky=tk.EW, padx=8, pady=4)
        ttk.Button(path_frame, text="浏览...", command=self._browse_output_dir).grid(row=2, column=2, pady=4)

        # 3. Parameters Frame
        param_frame = ttk.LabelFrame(main_container, text="⚙️ 事件检测参数 (I-DT Algorithm)", style="Header.TLabelframe", padding="10")
        param_frame.pack(fill=tk.X, pady=(0, 10))
        param_frame.columnconfigure(1, weight=1)

        # Eye selection
        ttk.Label(param_frame, text="分析眼别 (Eye):").grid(row=0, column=0, sticky=tk.W, pady=4)
        eye_box = ttk.Frame(param_frame)
        eye_box.grid(row=0, column=1, sticky=tk.W, padx=8, pady=4)
        ttk.Radiobutton(eye_box, text="双眼 (bino)", variable=self.var_eye, value="bino").pack(side=tk.LEFT, padx=(0, 16))
        ttk.Radiobutton(eye_box, text="左眼 (left)", variable=self.var_eye, value="left").pack(side=tk.LEFT, padx=(0, 16))
        ttk.Radiobutton(eye_box, text="右眼 (right)", variable=self.var_eye, value="right").pack(side=tk.LEFT)

        # Min fixation duration
        ttk.Label(param_frame, text="最小注视时长 (ms):").grid(row=1, column=0, sticky=tk.W, pady=6)
        dur_box = ttk.Frame(param_frame)
        dur_box.grid(row=1, column=1, sticky=tk.EW, padx=8, pady=6)
        dur_box.columnconfigure(0, weight=1)
        dur_scale = ttk.Scale(dur_box, from_=20, to=200, variable=self.var_min_dur, orient=tk.HORIZONTAL)
        dur_scale.grid(row=0, column=0, sticky=tk.EW, padx=(0, 8))
        dur_spin = ttk.Spinbox(dur_box, from_=10, to=500, textvariable=self.var_min_dur, width=6)
        dur_spin.grid(row=0, column=1)
        ttk.Label(param_frame, text="建议 40~100 ms (默认 50)").grid(row=1, column=2, sticky=tk.W, padx=(6, 0))

        # Dispersion threshold
        ttk.Label(param_frame, text="分散度阈值 (deg):").grid(row=2, column=0, sticky=tk.W, pady=6)
        disp_box = ttk.Frame(param_frame)
        disp_box.grid(row=2, column=1, sticky=tk.EW, padx=8, pady=6)
        disp_box.columnconfigure(0, weight=1)
        disp_scale = ttk.Scale(disp_box, from_=0.2, to=3.0, variable=self.var_disp, orient=tk.HORIZONTAL)
        disp_scale.grid(row=0, column=0, sticky=tk.EW, padx=(0, 8))
        disp_spin = ttk.Spinbox(disp_box, from_=0.1, to=10.0, increment=0.1, textvariable=self.var_disp, width=6)
        disp_spin.grid(row=0, column=1)
        ttk.Label(param_frame, text="建议 0.5~1.5° (默认 1.0)").grid(row=2, column=2, sticky=tk.W, padx=(6, 0))

        # 4. Visualization Mode
        mode_frame = ttk.LabelFrame(main_container, text="📊 可视化与导出选项", style="Header.TLabelframe", padding="10")
        mode_frame.pack(fill=tk.X, pady=(0, 10))

        mode_box = ttk.Frame(mode_frame)
        mode_box.pack(fill=tk.X, pady=2)
        ttk.Radiobutton(mode_box, text="交互式网页仪表盘 (Plotly HTML - 推荐)", variable=self.var_mode, value="html").pack(side=tk.LEFT, padx=(0, 20))
        ttk.Radiobutton(mode_box, text="桌面原生图表窗口 (Matplotlib)", variable=self.var_mode, value="matplotlib").pack(side=tk.LEFT, padx=(0, 20))
        ttk.Radiobutton(mode_box, text="两者同时生成 (Both)", variable=self.var_mode, value="both").pack(side=tk.LEFT)

        ttk.Checkbutton(mode_frame, text="生成完成后自动在默认浏览器中打开 HTML 报告", variable=self.var_auto_open).pack(anchor=tk.W, pady=(6, 2))

        # 5. Action Buttons & Progress
        action_frame = ttk.Frame(main_container)
        action_frame.pack(fill=tk.X, pady=(4, 8))

        self.btn_run = ttk.Button(action_frame, text="🚀 开始分析并生成可视化", style="Primary.TButton", command=self._start_analysis)
        self.btn_run.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))

        self.btn_open_dir = ttk.Button(action_frame, text="📂 打开输出目录", command=self._open_output_dir)
        self.btn_open_dir.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_open_browser = ttk.Button(action_frame, text="🌐 浏览上次报告", command=self._open_last_html)
        self.btn_open_browser.pack(side=tk.LEFT)

        self.progress_bar = ttk.Progressbar(main_container, mode='indeterminate')
        self.progress_bar.pack(fill=tk.X, pady=(0, 8))

        # 6. KPI Summary Frame
        self.kpi_frame = ttk.LabelFrame(main_container, text="📈 关键统计指标概览 (KPI Summary)", style="Header.TLabelframe", padding="8")
        self.kpi_frame.pack(fill=tk.X, pady=(0, 8))

        kpi_grid = ttk.Frame(self.kpi_frame)
        kpi_grid.pack(fill=tk.X)
        for c in range(5):
            kpi_grid.columnconfigure(c, weight=1)

        self.lbl_kpi_track = self._add_kpi_cell(kpi_grid, 0, "数据追踪率", "-- %", "-- 帧")
        self.lbl_kpi_time = self._add_kpi_cell(kpi_grid, 1, "总时长", "-- s", "-- 采样率")
        self.lbl_kpi_fix = self._add_kpi_cell(kpi_grid, 2, "注视点 (Fixation)", "-- 次", "均长 -- ms")
        self.lbl_kpi_sac = self._add_kpi_cell(kpi_grid, 3, "眼跳 (Saccade)", "-- 次", "均幅 --°")
        self.lbl_kpi_blk = self._add_kpi_cell(kpi_grid, 4, "眨眼 (Blink)", "-- 次", "-- 次/分")

        # 7. Log Window
        log_frame = ttk.LabelFrame(main_container, text="📝 运行日志 (Execution Log)", style="Header.TLabelframe", padding="6")
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.txt_log = scrolledtext.ScrolledText(log_frame, height=7, font=("Consolas", 9), wrap=tk.WORD)
        self.txt_log.pack(fill=tk.BOTH, expand=True)
        self._log("就绪。请确认配置后点击【🚀 开始分析并生成可视化】。")

    def _add_kpi_cell(self, parent, col, title, initial_val, initial_sub):
        frame = ttk.Frame(parent, padding=4)
        frame.grid(row=0, column=col, sticky=tk.NSEW, padx=4)
        ttk.Label(frame, text=title, style="KPITitle.TLabel").pack(anchor=tk.W)
        val_lbl = ttk.Label(frame, text=initial_val, style="KPIValue.TLabel")
        val_lbl.pack(anchor=tk.W)
        sub_lbl = ttk.Label(frame, text=initial_sub, style="KPITitle.TLabel")
        sub_lbl.pack(anchor=tk.W)
        return (val_lbl, sub_lbl)

    def _browse_data(self):
        f = filedialog.askopenfilename(
            title="选择眼动 CSV 数据文件",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
            initialdir=os.path.dirname(self.var_data_path.get()) if os.path.exists(self.var_data_path.get()) else SCRIPT_DIR
        )
        if f:
            self.var_data_path.set(os.path.abspath(f))

    def _browse_img_dir(self):
        d = filedialog.askdirectory(
            title="选择刺激图片目录",
            initialdir=self.var_img_dir.get() if os.path.exists(self.var_img_dir.get()) else SCRIPT_DIR
        )
        if d:
            self.var_img_dir.set(os.path.abspath(d))

    def _browse_output_dir(self):
        d = filedialog.askdirectory(
            title="选择输出目录",
            initialdir=self.var_output_dir.get() if os.path.exists(self.var_output_dir.get()) else SCRIPT_DIR
        )
        if d:
            self.var_output_dir.set(os.path.abspath(d))

    def _open_output_dir(self):
        out_dir = self.var_output_dir.get()
        if os.path.exists(out_dir):
            if sys.platform == "win32":
                os.startfile(out_dir)
            else:
                import subprocess
                subprocess.Popen(["xdg-open", out_dir])
        else:
            messagebox.showinfo("提示", f"输出目录尚不存在:\n{out_dir}")

    def _open_last_html(self):
        if os.path.exists(self.last_html_path):
            webbrowser.open(f"file://{os.path.abspath(self.last_html_path)}")
        else:
            messagebox.showinfo("提示", "尚未生成报告，请先点击【开始分析】。")

    def _log(self, text: str):
        self.txt_log.insert(tk.END, text + "\n")
        self.txt_log.see(tk.END)

    def _log_safe(self, text: str):
        self.root.after(0, lambda: self._log(text))

    def _start_analysis(self):
        data_path = self.var_data_path.get().strip()
        if not os.path.exists(data_path):
            messagebox.showerror("错误", f"找不到数据文件：\n{data_path}")
            return

        self.btn_run.config(state=tk.DISABLED)
        self.progress_bar.start(10)
        self.txt_log.delete("1.0", tk.END)
        from datetime import datetime
        self._log(f"[{datetime.now().strftime('%H:%M:%S')}] 开始执行眼动分析...")

        import threading
        threading.Thread(target=self._run_analysis_worker, daemon=True).start()

    def _run_analysis_worker(self):
        try:
            data_path = self.var_data_path.get().strip()
            img_dir = self.var_img_dir.get().strip()
            out_dir = self.var_output_dir.get().strip()
            eye = self.var_eye.get()
            min_dur = int(self.var_min_dur.get())
            disp = float(self.var_disp.get())
            mode = self.var_mode.get()
            auto_open = self.var_auto_open.get()

            os.makedirs(out_dir, exist_ok=True)
            self._log_safe(f"正在加载数据: {data_path}")
            analyzer = GazeDataAnalyzer(
                data_path=data_path,
                img_dir=img_dir,
                output_dir=out_dir,
                which_eye=eye,
                min_duration=min_dur,
                dispersion=disp
            )
            self.analyzer = analyzer

            metrics = analyzer.get_summary_metrics()
            self._log_safe(f"数据加载完成: 共 {metrics['total_samples']} 帧, 追踪率 {metrics['tracking_ratio']:.1f}%")
            self._log_safe(f"事件检测完成: {metrics['fixation_count']} 个注视点 (均长 {metrics['fix_dur_mean']:.1f}ms), {metrics['saccade_count']} 次眼跳, {metrics['blink_count']} 次眨眼")

            html_path = os.path.join(out_dir, "gaze_event_analysis_dashboard.html")
            self.last_html_path = html_path

            if mode in ["html", "both"]:
                self._log_safe(f"正在生成交互式 HTML 仪表盘...")
                build_plotly_dashboard(analyzer, html_path)
                self._log_safe(f"仪表盘已保存: {html_path}")
                if auto_open:
                    self._log_safe(f"正在默认浏览器中打开仪表盘...")
                    webbrowser.open(f"file://{os.path.abspath(html_path)}")

            self.root.after(0, lambda: self._update_kpi(metrics))

            if mode in ["matplotlib", "both"]:
                self.root.after(100, lambda: run_matplotlib_interactive_gui(analyzer))

            self._log_safe("✅ 全部分析已顺利完成！")
            self.root.after(0, lambda: messagebox.showinfo("成功", f"分析完成！\n已检测出 {metrics['fixation_count']} 个注视点与 {metrics['saccade_count']} 次眼跳。\n报告已生成至:\n{html_path}"))
        except Exception as e:
            self._log_safe(f"❌ 分析出错: {str(e)}")
            self.root.after(0, lambda: messagebox.showerror("错误", f"分析过程中发生错误:\n{str(e)}"))
        finally:
            self.root.after(0, self._finish_analysis)

    def _update_kpi(self, metrics: dict):
        self.lbl_kpi_track[0].config(text=f"{metrics['tracking_ratio']:.1f} %")
        self.lbl_kpi_track[1].config(text=f"有效 {metrics['valid_samples']:,} / {metrics['total_samples']:,} 帧")

        self.lbl_kpi_time[0].config(text=f"{metrics['total_time_s']:.2f} s")
        self.lbl_kpi_time[1].config(text=f"标称 {self.analyzer.nominal_rate}Hz (有效 ~{self.analyzer.effective_rate}Hz)")

        self.lbl_kpi_fix[0].config(text=f"{metrics['fixation_count']} 次")
        self.lbl_kpi_fix[1].config(text=f"均长 {metrics['fix_dur_mean']:.1f} ms")

        self.lbl_kpi_sac[0].config(text=f"{metrics['saccade_count']} 次")
        self.lbl_kpi_sac[1].config(text=f"均幅 {metrics['sac_amp_mean']:.2f}° | 峰速 {metrics['sac_peakv_mean']:.0f}°/s")

        self.lbl_kpi_blk[0].config(text=f"{metrics['blink_count']} 次")
        self.lbl_kpi_blk[1].config(text=f"{metrics['blink_rate_bpm']:.1f} 次/分")

    def _finish_analysis(self):
        self.progress_bar.stop()
        self.btn_run.config(state=tk.NORMAL)


def launch_gui(default_data="", default_images="", default_output=""):
    """Launch the Python native Tkinter GUI."""
    root = tk.Tk()
    app = GazeAnalysisGUI(root, default_data, default_images, default_output)
    root.mainloop()


def main():
    parser = argparse.ArgumentParser(description="Pupilio Interactive Eye-Tracking & Event Detection Analyzer")
    default_data = os.path.join(SCRIPT_DIR, "data", "deepgaze_demo.csv")
    default_images = os.path.join(SCRIPT_DIR, "images")
    default_output = os.path.join(SCRIPT_DIR, "output")

    parser.add_argument("--gui", action="store_true", help="Launch Tkinter GUI interface (default if no args)")
    parser.add_argument("--cli", action="store_true", help="Force command-line mode without GUI")
    parser.add_argument("--data", default=default_data, help="Path to gaze data CSV file")
    parser.add_argument("--img-dir", default=default_images, help="Directory containing stimulus images")
    parser.add_argument("--output-dir", default=default_output, help="Directory to save output and dashboard")
    parser.add_argument("--eye", default="bino", choices=["bino", "left", "right"], help="Eye to analyze (bino, left, right)")
    parser.add_argument("--min-duration", type=int, default=50, help="Minimum fixation duration in ms (default: 50)")
    parser.add_argument("--dispersion", type=float, default=1.0, help="Dispersion threshold in degrees (default: 1.0)")
    parser.add_argument("--mode", default="html", choices=["html", "matplotlib", "both"], help="Output visualization mode")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically open the browser")

    # If launched with no args or --gui, launch the Tkinter GUI!
    if len(sys.argv) == 1 or "--gui" in sys.argv:
        launch_gui(default_data, default_images, default_output)
        return

    args = parser.parse_args()

    if not os.path.exists(args.data):
        print(f"[Error] Data file not found: {args.data}")
        sys.exit(1)

    analyzer = GazeDataAnalyzer(
        data_path=args.data,
        img_dir=args.img_dir,
        output_dir=args.output_dir,
        which_eye=args.eye,
        min_duration=args.min_duration,
        dispersion=args.dispersion
    )

    if args.mode in ["html", "both"]:
        html_path = os.path.join(args.output_dir, "gaze_event_analysis_dashboard.html")
        build_plotly_dashboard(analyzer, html_path)
        if not args.no_browser:
            print(f"Opening report in default browser: {html_path}")
            webbrowser.open(f"file://{os.path.abspath(html_path)}")

    if args.mode in ["matplotlib", "both"]:
        run_matplotlib_interactive_gui(analyzer)


if __name__ == "__main__":
    main()
