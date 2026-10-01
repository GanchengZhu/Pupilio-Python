---
title: "Pupilio LabStreamingLayer (LSL) Integration Guide"
subtitle: "Broadcasting and synchronizing eye-tracking data"
author: "Pupilio"
date: "2026-10-01"
---

# LabStreamingLayer (LSL) Integration

Welcome to the **Pupilio LabStreamingLayer (LSL) Integration Guide**. This document provides a production-grade guide to broadcasting and synchronizing eye-tracking data with multi-modal research equipment (EEG, fNIRS, EMG, Motion Capture, etc.) using the Pupilio Python SDK.

**Document scope & compatibility**

| Component | Tested / required version |
| :--- | :--- |
| Pupilio Python SDK | ≥ 1.0 |
| `pylsl` (liblsl Python bindings) | ≥ 1.16 (LSL protocol 1.1) |
| LabRecorder | ≥ 1.16 |
| `pyxdf` (analysis) | ≥ 1.16 |
| MNE-Python (optional, §6.2) | ≥ 1.0 (required for `eyegaze` / `pupil` channel types) |

---

## Table of Contents

1. [Introduction & Multi-Modal Concept](#1-introduction--multi-modal-concept)
2. [Configuration Reference](#2-configuration-reference)
3. [Channel Specifications & Stream Layout](#3-channel-specifications--stream-layout)
4. [Complete Code Examples](#4-complete-code-examples)
5. [LabRecorder Recording Workflow](#5-labrecorder-recording-workflow)
6. [Post-Processing & Downstream Analysis](#6-post-processing--downstream-analysis)
7. [Troubleshooting & FAQs](#7-troubleshooting--faqs)
8. [Glossary](#8-glossary)

> **Note for Word conversion.** If you convert this file with `pandoc --toc`, delete this hand-written table of contents first — Pandoc generates a native Word TOC and you would otherwise end up with two.

---

## 1. Introduction & Multi-Modal Concept

**LabStreamingLayer (LSL)** is a system for the unified collection of measurement time series in research experiments that handles networking, time-synchronization, and recording.

In multi-modal neuroscience and behavioral experiments (such as Brain-Computer Interfaces, visual evoked potential studies, or co-registered EEG-eye tracking), synchronizing data streams across different devices is critical.

Pupilio natively supports LSL streaming, providing:

- **Zero-Configuration Setup**: Turn on streaming with a single configuration flag (`enable_lsl = True`).
- **Dual-Stream Publishing**: Separates high-frequency continuous gaze data from discrete experimental events.
- **Hardware-Aligned Timestamps**: Sub-millisecond clock synchronization using the camera exposure clock, eliminating OS scheduling and network buffering jitter.
- **Trigger Forwarding**: Automatically synchronizes integer trigger codes and custom text annotations to the LSL network.
- **XDF Metadata Compliance**: Streams are described with full XML metadata detailing channel names, units, eye affiliations, and display geometry.

### Quick Start (TL;DR)

```python
from pupilio import Pupilio, DefaultConfig

config = DefaultConfig()
config.enable_lsl = True                 # everything else uses defaults

pupil_io = Pupilio(config=config)
pupil_io.create_session("my_study")
pupil_io.calibration_draw(screen=win, validate=True)
pupil_io.start_sampling()                # LSL worker thread starts here

pupil_io.send_lsl_marker("TRIAL_START")  # discrete text event
pupil_io.set_trigger(20)                 # integer trigger code

pupil_io.stop_sampling()                 # LSL worker stops, streams close
pupil_io.save_data("./data/session.csv")
pupil_io.release()
```

Then open LabRecorder, click **Update**, and record `Pupilio_Gaze` + `Pupilio_Markers`.

---

## 2. Configuration Reference

All LSL behavior is controlled through `DefaultConfig` attributes. Set them **before** constructing `Pupilio(config=config)`.

| Attribute | Type | Default | Description |
| :--- | :---: | :---: | :--- |
| `enable_lsl` | `bool` | `False` | Master switch. When `True`, the LSL worker thread is created on `start_sampling()`. |
| `lsl_stream_mode` | `str` | `"standard"` | `"standard"` (12 ch) or `"full"` (39 ch). See §3. |
| `lsl_gaze_stream_name` | `str` | `"Pupilio_Gaze"` | LSL `name` property of the continuous gaze outlet. Must be unique per device on the network. |
| `lsl_marker_stream_name` | `str` | `"Pupilio_Markers"` | LSL `name` property of the discrete marker outlet. |
| `lsl_source_id` | `str` | auto (UUID) | LSL `source_id`. Set explicitly if you need a stable identifier across sessions. |
| `lsl_chunk_size` | `int` | `1` | Samples per `push_sample` call. Increase to reduce per-sample Python overhead at high rates. |
| `lsl_max_buffered` | `int` | `360` | Outlet-side buffer depth (samples). Increase if consumers join late or stall. |
| `lsl_nominal_srate` | `float` | derived | Overrides the advertised gaze rate. Normally auto-populated from the active camera rate. |

> **Note on `pylsl` availability.** If `enable_lsl = True` but `pylsl` cannot be imported, Pupilio logs a warning and continues sampling **without** LSL streaming. Local CSV/`save_data()` output is unaffected. Install with `pip install pylsl`.

---

## 3. Channel Specifications & Stream Layout

Pupilio provides two user-selectable stream layouts configured via `config.lsl_stream_mode`.

### 3.1 Standard Mode: `standard` (12 Channels, Recommended)

Optimized for the vast majority of visual cognition, psychophysics, and EEG experiments:

| Channel # | Channel Label | Data Type | Units | Eye | Description |
| :---: | :--- | :---: | :---: | :---: | :--- |
| **0** | `bino_gaze_x` | `float32` | `pixels` | `both` | Binocular fused horizontal gaze point on screen (0 ~ 1920) |
| **1** | `bino_gaze_y` | `float32` | `pixels` | `both` | Binocular fused vertical gaze point on screen (0 ~ 1080) |
| **2** | `bino_valid` | `float32` | `binary` | `both` | Binocular gaze confidence (1: valid, 0: invalid / blink) |
| **3** | `left_gaze_x` | `float32` | `pixels` | `left` | Left eye horizontal gaze point on screen (0 ~ 1920) |
| **4** | `left_gaze_y` | `float32` | `pixels` | `left` | Left eye vertical gaze point on screen (0 ~ 1080) |
| **5** | `left_pupil_dia` | `float32` | `mm` | `left` | Left eye pupil diameter in millimeters (0 ~ 10 mm) |
| **6** | `left_valid` | `float32` | `binary` | `left` | Left eye gaze validity flag (1: valid, 0: invalid) |
| **7** | `right_gaze_x` | `float32` | `pixels` | `right` | Right eye horizontal gaze point on screen (0 ~ 1920) |
| **8** | `right_gaze_y` | `float32` | `pixels` | `right` | Right eye vertical gaze point on screen (0 ~ 1080) |
| **9** | `right_pupil_dia` | `float32` | `mm` | `right` | Right eye pupil diameter in millimeters (0 ~ 10 mm) |
| **10** | `right_valid` | `float32` | `binary` | `right` | Right eye gaze validity flag (1: valid, 0: invalid) |
| **11** | `trigger` | `float32` | `integer` | `none` | Active trigger code (0.0 when idle, > 0 during trigger pulse) |

> **Pixel units.** Gaze coordinates are in **screen pixels** in the coordinate system of the display configured at session creation. If your experiment uses a different resolution or an offset window, transform the values downstream rather than changing the stream geometry.

### 3.2 Research Mode: `full` (39 Channels)

Contains the full 38-parameter estimation output from the underlying deep neural network, followed by the trigger channel.

**Left eye — channels `0..13`**

| # | Label | Units |
| :---: | :--- | :---: |
| 0 | `left_gaze_x` | pixels |
| 1 | `left_gaze_y` | pixels |
| 2 | `left_pupil_dia` | mm |
| 3 | `left_pupil_x` | mm |
| 4 | `left_pupil_y` | mm |
| 5 | `left_pupil_z` | mm |
| 6 | `left_theta` | radians |
| 7 | `left_phi` | radians |
| 8 | `left_dir_x` | unit vector |
| 9 | `left_dir_y` | unit vector |
| 10 | `left_dir_z` | unit vector |
| 11 | `left_pix_per_deg_x` | px/deg |
| 12 | `left_pix_per_deg_y` | px/deg |
| 13 | `left_valid` | binary |

**Right eye — channels `14..27`**: identical layout with the `right_` prefix.

**Binocular fused — channels `28..37`**

| # | Label | Units | Notes |
| :---: | :--- | :---: | :--- |
| 28 | `bino_gaze_x` | pixels | |
| 29 | `bino_gaze_y` | pixels | |
| 30 | `bino_valid` | binary | |
| 31–37 | `bino_reserved_0` … `bino_reserved_6` | — | Reserved estimation metrics. Emitted as `0.0` in current firmware; names and semantics are not yet stable and may change between SDK releases. Do not depend on these channels in production analysis. |

**Trigger — channel `38`**: `trigger` code.

### 3.3 Discrete Marker Stream (`Pupilio_Markers`)

- **Type**: `"Markers"`
- **Rate**: `0.0` (`pylsl.IRREGULAR_RATE`)
- **Format**: `pylsl.cf_string`
- **Payload**: Formatted event strings, including integer trigger codes (e.g. `"101"`, `"200"`) and semantic annotations (e.g. `"STIMULUS_ONSET"`, `"RESPONSE_KEY_SPACE"`).

**Behavior notes**

- `set_trigger(code)` sets the value of the `trigger` channel in the **gaze** stream and, in addition, pushes a stringified marker (`"101"`) to the **marker** stream.
- The trigger channel holds `code` until the next `set_trigger()` call. A subsequent `set_trigger(0)` returns it to idle. If your analysis keys off non-zero trigger values, sample-and-hold semantics mean a trigger remains "on" for many gaze samples.
- `send_lsl_marker(text)` pushes a text annotation to the marker stream **only** — it does not touch the trigger channel.
- Both methods are non-blocking and thread-safe with respect to the LSL worker. Call them from your render loop without fear of stalling presentation.
- Marker strings are truncated at **64 bytes** (the LSL string limit). Keep annotations short.

---

## 4. Complete Code Examples

All examples follow the same lifecycle: **configure → create session → calibrate → start sampling → run task → stop sampling → save → release**. Triggers are issued immediately after the corresponding `flip()` / `display.flip()` so that the marker and the visual onset stay tightly coupled.

### 4.1 Pygame Experiment with Synchronized LSL Streaming

```python
import os
import pygame
from pupilio import Pupilio, DefaultConfig

# Initialize Pygame
pygame.init()
scn_width, scn_height = 1920, 1080
win = pygame.display.set_mode(
    (scn_width, scn_height), pygame.FULLSCREEN | pygame.HWSURFACE
)

# 1. Configure Pupilio with LSL
config = DefaultConfig()
config.enable_lsl = True
config.lsl_stream_mode = "standard"          # 12 channels
config.lsl_gaze_stream_name = "Pupilio_Gaze"
config.lsl_marker_stream_name = "Pupilio_Markers"

pupil_io = Pupilio(config=config)
pupil_io.create_session("pygame_lsl_study")

try:
    # 2. Calibration & Validation
    pupil_io.calibration_draw(screen=win, validate=True)

    # 3. Start Sampling (LSL background worker starts automatically)
    pupil_io.start_sampling()

    # Send trial start annotation
    pupil_io.send_lsl_marker("TRIAL_01_START")

    # --- Fixation ---
    win.fill((128, 128, 128))
    pygame.draw.line(win, (255, 255, 255),
                     (scn_width // 2 - 20, scn_height // 2),
                     (scn_width // 2 + 20, scn_height // 2), 3)
    pygame.draw.line(win, (255, 255, 255),
                     (scn_width // 2, scn_height // 2 - 20),
                     (scn_width // 2, scn_height // 2 + 20), 3)
    pygame.display.flip()
    pupil_io.set_trigger(10)                 # Fixation onset (immediately after flip)

    # Pump events so the window stays responsive during the wait
    t_end = pygame.time.get_ticks() + 1000
    while pygame.time.get_ticks() < t_end:
        for ev in pygame.event.get():
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                raise KeyboardInterrupt
        pygame.time.wait(5)

    # --- Stimulus ---
    win.fill((200, 200, 200))
    pygame.draw.circle(win, (255, 0, 0), (scn_width // 2, scn_height // 2), 50)
    pygame.display.flip()
    pupil_io.set_trigger(20)                 # Stimulus onset (immediately after flip)

    t_end = pygame.time.get_ticks() + 2000
    while pygame.time.get_ticks() < t_end:
        for ev in pygame.event.get():
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                raise KeyboardInterrupt
        pygame.time.wait(5)

    pupil_io.send_lsl_marker("TRIAL_01_END")

finally:
    # 4. Stop Sampling (LSL stops automatically)
    pupil_io.stop_sampling()

    # Save local backup CSV
    os.makedirs("./data", exist_ok=True)
    pupil_io.save_data("./data/trial_01.csv")

    # Clean up
    pupil_io.release()
    pygame.quit()
```

### 4.2 PsychoPy Experiment with LSL Integration

```python
from psychopy import visual, core, event
from pupilio import Pupilio, DefaultConfig

win = visual.Window(size=(1920, 1080), fullscr=True, units="pix", color=(0, 0, 0))

# Configure Pupilio
config = DefaultConfig()
config.enable_lsl = True
pupil_io = Pupilio(config=config)
pupil_io.create_session("psychopy_lsl_experiment")

try:
    # Calibrate
    pupil_io.calibration_draw(screen=win, validate=True)

    # Start LSL Recording
    pupil_io.start_sampling()

    fixation = visual.TextStim(win, text="+", height=40, color="white")
    target = visual.GratingStim(win, tex="sin", mask="circle", size=200)

    for trial in range(5):
        pupil_io.send_lsl_marker(f"TRIAL_{trial + 1}_START")

        # Fixation
        fixation.draw()
        win.flip()
        pupil_io.set_trigger(1)              # immediately after flip
        core.wait(1.0)

        # Target
        target.draw()
        win.flip()
        pupil_io.set_trigger(2)              # immediately after flip

        # Wait for subject keypress
        keys = event.waitKeys(maxWait=2.0, keyList=["space", "escape"])
        if keys:
            pupil_io.set_trigger(99)         # Response trigger
            pupil_io.send_lsl_marker(f"RESPONSE_{keys[0].upper()}")
            if keys[0] == "escape":
                break

        pupil_io.send_lsl_marker(f"TRIAL_{trial + 1}_END")
        core.wait(0.5)

finally:
    pupil_io.stop_sampling()
    pupil_io.save_data("./psychopy_gaze.csv")
    pupil_io.release()
    win.close()
    core.quit()
```

### 4.3 Real-Time LSL Receiver and Data Inspector

Use this script to monitor and verify incoming Pupilio streams from another computer or process on the network.

```python
import time
import pylsl

print("Resolving Pupilio LSL streams...")
gaze_streams = pylsl.resolve_byprop("name", "Pupilio_Gaze", timeout=5.0)
marker_streams = pylsl.resolve_byprop("name", "Pupilio_Markers", timeout=2.0)

if not gaze_streams:
    raise SystemExit("Could not find Pupilio_Gaze stream!")

gaze_inlet = pylsl.StreamInlet(gaze_streams[0])
marker_inlet = pylsl.StreamInlet(marker_streams[0]) if marker_streams else None

print("Connected! Streaming live gaze data (Ctrl-C to stop):")
try:
    while True:
        # --- Drain all available gaze samples ---
        while True:
            sample, ts = gaze_inlet.pull_sample(timeout=0.0)
            if sample is None:
                break
            bino_x, bino_y, b_valid = sample[0], sample[1], sample[2]
            l_pupil = sample[5]
            r_pupil = sample[9]
            trig = int(sample[11])
            print(f"[{ts:.3f}] Gaze: ({bino_x:7.1f}, {bino_y:7.1f}) "
                  f"valid={int(b_valid)} | "
                  f"Pupil: L={l_pupil:5.2f}mm R={r_pupil:5.2f}mm | "
                  f"Trig={trig}")

        # --- Drain all available markers ---
        if marker_inlet:
            while True:
                m_sample, m_ts = marker_inlet.pull_sample(timeout=0.0)
                if m_sample is None:
                    break
                print(f"\n>>> [MARKER @ {m_ts:.3f}] {m_sample[0]} <<<\n")

        # Avoid a busy-spin when both streams are momentarily empty
        time.sleep(0.001)

except KeyboardInterrupt:
    print("\nExiting...")
```

> **Why drain in a `while` loop?** Pulling a single sample per iteration with a short timeout can silently drop markers or gaze samples when the consumer falls behind. Draining to exhaustion (`timeout=0.0` until `None`) guarantees you never skip data, at the cost of a tight loop — hence the small `sleep`.

---

## 5. LabRecorder Recording Workflow

To record synchronized data across Pupilio and your EEG/fNIRS devices:

1. **Install LabRecorder**: Download the latest release from the [LabRecorder GitHub Releases](https://github.com/labstreaminglayer/App-LabRecorder/releases).
2. **Start Your Data Sources**:
   - Start your EEG amplifier acquisition software (e.g. BrainVision RDA, BioSemi ActiView, OpenBCI GUI).
   - Start your Pupilio script (`enable_lsl = True`).
3. **Launch LabRecorder**:
   - Click the **Update** button.
   - LabRecorder will discover all active streams on the network.
   - Check the boxes next to:
     - `Pupilio_Gaze (Gaze)`
     - `Pupilio_Markers (Markers)`
     - Your EEG data stream (e.g. `BrainVision RDA (EEG)`)
     - (Optional) Audio / Video / Keyboard streams
4. **Configure File Storage**:
   - Set the participant ID, session number, and output `.xdf` file destination.
5. **Start Recording**:
   - Click **Start**. The recording indicators will turn green.
   - Execute your experimental task.
   - Click **Stop** when finished.

> **Ordering matters.** Start LabRecorder **before** your task begins, and stop it **after** `stop_sampling()` returns. Recording that begins mid-session will miss the stream's opening samples; recording that ends after the outlets close will produce a truncated tail.

---

## 6. Post-Processing & Downstream Analysis

### 6.1 Loading XDF in Python (`pyxdf`)

```python
import numpy as np
import pyxdf
import matplotlib.pyplot as plt

data, header = pyxdf.load_xdf("sub-01_task-vissearch.xdf")

gaze_stream = None
marker_stream = None
eeg_stream = None

for s in data:
    stream_name = s["info"]["name"][0]
    if stream_name == "Pupilio_Gaze":
        gaze_stream = s
    elif stream_name == "Pupilio_Markers":
        marker_stream = s
    elif s["info"]["type"][0] == "EEG":
        eeg_stream = s

# Inspect Gaze Data
gaze_time = np.array(gaze_stream["time_stamps"])
gaze_samples = np.array(gaze_stream["time_series"])

# Channel mapping (standard mode):
bino_x = gaze_samples[:, 0]
bino_y = gaze_samples[:, 1]
left_pupil = gaze_samples[:, 5]
right_pupil = gaze_samples[:, 9]
triggers = gaze_samples[:, 11]

# Inspect Markers
marker_time = np.array(marker_stream["time_stamps"])
marker_labels = [m[0] for m in marker_stream["time_series"]]

print(f"Loaded {len(gaze_time)} gaze samples.")
print(f"Loaded {len(marker_labels)} event markers: {marker_labels[:5]}...")

# Sanity check: confirm both streams share the same LSL clock domain
print(f"First gaze ts  : {gaze_time[0]:.6f}")
print(f"First marker ts: {marker_time[0]:.6f}")
print(f"Nominal rate   : {gaze_stream['info']['nominal_srate'][0]} Hz")
```

### 6.2 Analysis in MNE-Python

```python
import mne
import numpy as np

# Requires MNE-Python >= 1.0 for the "eyegaze" and "pupil" channel types.
ch_names = [
    "bino_x", "bino_y", "bino_valid",
    "left_x", "left_y", "left_pupil", "left_valid",
    "right_x", "right_y", "right_pupil", "right_valid",
    "STI",  # Trigger channel for MNE
]
ch_types = [
    "eyegaze", "eyegaze", "misc",
    "eyegaze", "eyegaze", "pupil", "misc",
    "eyegaze", "eyegaze", "pupil", "misc",
    "stim",
]

sfreq = float(gaze_stream["info"]["nominal_srate"][0])
info = mne.create_info(ch_names=ch_names, sfreq=sfreq, ch_types=ch_types)

# Set the montage-free coordinate frame so MNE knows these are screen pixels
info["description"] = "Pupilio standard-mode gaze (screen pixels)"

# MNE expects shape (n_channels, n_times)
raw_gaze = mne.io.RawArray(gaze_samples.T, info)

# Optional: derive discrete annotations from the trigger channel
events = mne.find_events(raw_gaze, stim_channel="STI", verbose=False)
raw_gaze.set_annotations(
    mne.annotations_from_events(events, sfreq=sfreq)
)

print(raw_gaze)
```

### 6.3 EEGLAB Integration (MATLAB)

1. In EEGLAB, install the `xdf2eeglab` plugin from the EEGLAB Extension Manager.
2. Go to **File → Import data → Using EEGLAB functions and plugins → From XDF file**.
3. Select your `.xdf` file. EEGLAB will import both EEG and Pupilio Gaze channels onto the same synchronized timeline and automatically convert LSL markers into EEGLAB `EEG.event` structures.

---

## 7. Troubleshooting & FAQs

### Q1: LabRecorder does not discover `Pupilio_Gaze` or `Pupilio_Markers`

- **Cause**: Firewall blocking UDP multicast packets, or multiple network adapters (e.g. Wi-Fi + VPN + Ethernet) causing LSL to bind to the wrong interface.
- **Solution**:
  1. **Windows**: open Windows Firewall Settings and ensure Python (or your IDE) is allowed for both Private and Public networks. **macOS**: allow incoming connections when prompted, or add the interpreter to *System Settings → Network → Firewall → Options*. **Linux**: check `ufw`/`firewalld` rules for UDP multicast (`239.255.172.215` and the LSL port range).
  2. If using multiple network adapters, specify the binding interface in your LSL configuration file (`lsl_api.cfg`), or set the environment variable `LSLAPICFG` to point at a config that pins `MulticastAddress` / `KnownPeers`.

### Q2: How does Pupilio ensure sub-millisecond synchronization?

Pupilio uses a continuous clock synchronization algorithm. Rather than recording the timestamp when the network packet is sent, Pupilio captures the exact camera exposure hardware time (`t_cam`) and offsets it against `pylsl.local_clock()`. This bypasses Python GIL delays and OS thread scheduling jitter.

At a nominal 200 Hz camera rate, this yields gaze timestamps aligned to the **acquisition clock**, not to the consumer's arrival clock — so the residual offset between gaze samples and EEG samples is dominated by the camera exposure jitter (≪ 1 ms), not by Python or network latency.

### Q3: Can I run multiple Pupilio eye trackers on the same network?

- **Yes**. Give each eye tracker unique stream names via configuration. This is required — two outlets with the same `name` on the same network are ambiguous for consumers and LabRecorder will show duplicate entries.

  ```python
  config.lsl_gaze_stream_name = "Pupilio_SubjectA_Gaze"
  config.lsl_marker_stream_name = "Pupilio_SubjectA_Markers"
  ```

  For a second device:

  ```python
  config.lsl_gaze_stream_name = "Pupilio_SubjectB_Gaze"
  config.lsl_marker_stream_name = "Pupilio_SubjectB_Markers"
  ```

  If you want LabRecorder to group them robustly across sessions, also set a stable `lsl_source_id` per device (e.g. `"pupilio-subjectA"`).

### Q4: I set `enable_lsl = True` but no streams appear

Check the console for a `pylsl` import warning. If `pylsl` is not installed, Pupilio silently disables streaming and continues with local recording only. Install with `pip install pylsl` and re-run.

### Q5: My markers show up but have no matching gaze samples

This almost always means LabRecorder started **after** `start_sampling()` or stopped **before** `stop_sampling()`. See the ordering note in §5. It can also occur if the marker stream is added to LabRecorder but the gaze stream is not — both must be checked.

### Q6: My `trigger` channel is stuck at a non-zero value

`set_trigger()` uses sample-and-hold semantics: the value persists until the next call. If your analysis treats any non-zero sample as an event, call `set_trigger(0)` explicitly after the event window closes, or key your detection on transitions rather than absolute values.

---

## 8. Glossary

| Term | Meaning |
| :--- | :--- |
| **LSL** | LabStreamingLayer — a protocol and library for time-synchronized streaming of measurement time series over a network. |
| **Outlet / Inlet** | An LSL *outlet* publishes a stream; an *inlet* subscribes to one. Pupilio creates two outlets. |
| **XDF** | Extensible Data Format — the container LabRecorder writes, holding one or more synchronized streams. |
| **Nominal rate** | The advertised sampling rate of a stream (`nominal_srate`). `0.0` denotes an irregular stream, such as markers. |
| **Trigger** | An integer code carried in the `trigger` channel of the gaze stream, used for epoching in EEG/fNIRS analysis. |
| **Marker** | A discrete string event on the `Pupilio_Markers` stream. Triggers are also echoed as stringified markers. |
| **`t_cam`** | Camera exposure hardware timestamp — the ground-truth acquisition time used for clock alignment. |
| **`local_clock()`** | `pylsl.local_clock()`, the LSL library's own monotonic clock, shared across all streams on a machine. |

---

*End of document.*