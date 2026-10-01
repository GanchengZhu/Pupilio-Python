---
title: "Pupilio LabStreamingLayer (LSL) Integration Guide"
subtitle: "Real-time, time-synchronized eye-tracking for multi-modal research"
author: "Pupilio"
date: "2026-10-01"
---

# LabStreamingLayer (LSL) Integration Guide

## Overview

**LabStreamingLayer (LSL)** is the research standard for unified, time-synchronized data streaming and recording across multiple modalities in cognitive science, neuroscience, and human-computer interaction.

The **Pupilio Python SDK** provides native support for LSL, enabling real-time, low-latency broadcasting of eye-tracking data and experimental triggers over local networks. Researchers can seamlessly co-register Pupilio eye-tracking data with:

- **Electroencephalography (EEG)** (e.g., BrainProducts, ANT Neuro, Biosemi, OpenBCI)
- **Functional Near-Infrared Spectroscopy (fNIRS)**
- **Physiological Sensors (EMG, ECG, GSR)**
- **Stimulus Presentation Engines** (PsychoPy, Pygame, E-Prime)

Pupilio LSL data can be captured synchronously into unified `.xdf` files using [LabRecorder](https://github.com/labstreaminglayer/App-LabRecorder).

### Compatibility

| Component | Tested / required version |
| :--- | :--- |
| Pupilio Python SDK | ≥ 1.0 |
| `pylsl` (liblsl Python bindings) | ≥ 1.16 (LSL protocol 1.1) |
| LabRecorder | ≥ 1.16 |
| `pyxdf` (analysis) | ≥ 1.16 |
| MNE-Python (optional) | ≥ 1.0 (required for `eyegaze` / `pupil` channel types) |

---

## Table of Contents

1. [Installation & Prerequisites](#1-installation--prerequisites)
2. [Quick Start](#2-quick-start)
3. [Stream Architecture](#3-stream-architecture)
4. [Precise Clock Synchronization](#4-precise-clock-synchronization)
5. [Configuration Reference](#5-configuration-reference)
6. [Recording with LabRecorder](#6-recording-with-labrecorder)
7. [Offline Analysis in Python](#7-offline-analysis-in-python-pyxdf)
8. [Troubleshooting & FAQs](#8-troubleshooting--faqs)
9. [Glossary](#9-glossary)

> **Note for Word conversion.** If you convert this file with `pandoc --toc`, delete this hand-written table of contents first — Pandoc generates a native Word TOC and you would otherwise end up with two.

---

## 1. Installation & Prerequisites

LSL support relies on the official `pylsl` Python library. It is an optional dependency for Pupilio. If not already installed, install it via:

```bash
pip install pylsl
```

> **If `pylsl` is missing.** When `enable_lsl = True` but `pylsl` cannot be imported, Pupilio logs a warning and continues sampling **without** LSL streaming. Local CSV output via `save_data()` is unaffected, so a misconfigured LSL environment will not lose your data — but no streams will be visible to LabRecorder.

---

## 2. Quick Start

Enabling LSL streaming in your existing Pupilio script requires just two lines of configuration:

```python
from pupilio import Pupilio, DefaultConfig

# 1. Enable LSL in the configuration
config = DefaultConfig()
config.enable_lsl = True
config.lsl_stream_mode = "standard"  # 12 channels (default)

# 2. Instantiate Pupilio
pupil_io = Pupilio(config=config)
pupil_io.create_session("eeg_multimodal_study")

# Optional: run calibration and validation
# (pass your presentation window; the argument name matches your GUI backend)
# pupil_io.calibration_draw(screen=win, validate=True)

# 3. Start sampling (LSL starts broadcasting automatically)
pupil_io.start_sampling()

# Send experimental triggers (forwarded to both the Marker stream and gaze channel 11)
pupil_io.set_trigger(101)  # Target onset

# Send semantic text annotations
pupil_io.send_lsl_marker("FIXATION_CROSS_ONSET")

# 4. Stop sampling (LSL streaming stops automatically)
pupil_io.stop_sampling()

# Local backup (independent of LSL)
pupil_io.save_data("./data/session.csv")
pupil_io.release()
```

---

## 3. Stream Architecture

Pupilio publishes two independent, synchronized LSL streams:

```
+-------------------------------------------------------------------------+
|                              Pupilio SDK                                |
+-------------------------------------------------------------------------+
       |                                                 |
       v (High-frequency, 200/400 Hz)                    v (Irregular rate)
+------------------------------------+        +---------------------------+
| Gaze Stream: 'Pupilio_Gaze'        |        | Marker Stream:            |
| (Continuous: 12 or 39 channels)    |        | 'Pupilio_Markers' (string)|
+------------------------------------+        +---------------------------+
       |                                                 |
       +------------------------+------------------------+
                                |
                                v
                   LabStreamingLayer Network (LSL)
                                |
                                v
               [LabRecorder / EEGLAB / MNE / OpenViBE]
```

> **Font note (Word).** The diagram above uses box-drawing characters. After converting to Word, select the diagram and set its font to a monospace face that contains them — **Consolas** or **Cascadia Mono**. Calibri and Cambria will render gaps.

### 3.1 Continuous Gaze Stream (`Pupilio_Gaze`)

- **Stream Type**: `"Gaze"`
- **Sampling Rate**: `200.0` or `400.0` Hz (matches hardware camera rate)
- **Data Type**: `float32`

#### Standard Mode (`standard`, 12 Channels — Recommended)

Configured via `config.lsl_stream_mode = "standard"`. Ideal for most cognitive and EEG co-registration studies:

| Index | Channel Label | Description | Units | Eye |
| :---: | :--- | :--- | :---: | :---: |
| 0 | `bino_gaze_x` | Binocular fused gaze horizontal coordinate (0 ~ 1920) | pixels | both |
| 1 | `bino_gaze_y` | Binocular fused gaze vertical coordinate (0 ~ 1080) | pixels | both |
| 2 | `bino_valid` | Binocular gaze validity (1: valid, 0: invalid) | binary | both |
| 3 | `left_gaze_x` | Left eye gaze horizontal coordinate (0 ~ 1920) | pixels | left |
| 4 | `left_gaze_y` | Left eye gaze vertical coordinate (0 ~ 1080) | pixels | left |
| 5 | `left_pupil_dia` | Left eye pupil diameter | mm | left |
| 6 | `left_valid` | Left eye gaze validity (1: valid, 0: invalid) | binary | left |
| 7 | `right_gaze_x` | Right eye gaze horizontal coordinate (0 ~ 1920) | pixels | right |
| 8 | `right_gaze_y` | Right eye gaze vertical coordinate (0 ~ 1080) | pixels | right |
| 9 | `right_pupil_dia` | Right eye pupil diameter | mm | right |
| 10 | `right_valid` | Right eye gaze validity (1: valid, 0: invalid) | binary | right |
| 11 | `trigger` | Active integer trigger code for this sample (0 if none) | integer | none |

> **Pixel units.** Gaze coordinates are in **screen pixels** in the coordinate system of the display configured at session creation. If your experiment uses a different resolution or an offset window, transform the values downstream rather than changing the stream geometry.

#### Full Mode (`full`, 39 Channels)

Configured via `config.lsl_stream_mode = "full"`. Exports all 38 parameters computed by the neural gaze estimation model plus the trigger channel.

**Channels 0–13 (Left Eye)**

| Index | Parameter | Units |
| :---: | :--- | :---: |
| 0 | `gaze_x` | pixels |
| 1 | `gaze_y` | pixels |
| 2 | `pupil_dia` | mm |
| 3 | `pupil_pos_x` | mm |
| 4 | `pupil_pos_y` | mm |
| 5 | `pupil_pos_z` | mm |
| 6 | `visual_angle_theta` | radians |
| 7 | `visual_angle_phi` | radians |
| 8 | `visual_vector_x` | unit vector |
| 9 | `visual_vector_y` | unit vector |
| 10 | `visual_vector_z` | unit vector |
| 11 | `pix_per_degree_x` | px/deg |
| 12 | `pix_per_degree_y` | px/deg |
| 13 | `valid` | binary |

**Channels 14–27 (Right Eye)**: the same 14 parameters for the right eye.

**Channels 28–37 (Binocular Fused)**

| Index | Parameter | Units | Notes |
| :---: | :--- | :---: | :--- |
| 28 | `bino_gaze_x` | pixels | |
| 29 | `bino_gaze_y` | pixels | |
| 30 | `bino_valid` | binary | |
| 31–37 | `bino_reserved_0` … `bino_reserved_6` | — | Reserved estimation metrics. Emitted as `0.0` in current firmware; names and semantics are not yet stable and may change between SDK releases. Do not depend on these channels in production analysis. |

**Channel 38**: `trigger`.

### 3.2 Discrete Marker Stream (`Pupilio_Markers`)

- **Stream Type**: `"Markers"`
- **Sampling Rate**: `0.0` (`IRREGULAR_RATE`)
- **Data Type**: `string` (LSL `cf_string`)
- **Channel Count**: 1

Broadcasts discrete experiment events:

- Numeric triggers sent via `pupil_io.set_trigger(code)` (e.g., `"101"`).
- Text labels sent via `pupil_io.send_lsl_marker("TRIAL_START")`.

**Behavior notes**

- `set_trigger(code)` writes the `trigger` channel in the **gaze** stream *and* pushes a stringified marker (`"101"`) to the **marker** stream — so the same event appears in both places.
- The trigger channel uses **sample-and-hold** semantics: the value persists until the next `set_trigger()` call. If your analysis treats any non-zero sample as an event, call `set_trigger(0)` explicitly after the event window closes, or detect *transitions* rather than absolute values.
- `send_lsl_marker(text)` pushes to the marker stream **only** — it does not touch the trigger channel.
- Both methods are non-blocking and thread-safe with respect to the LSL worker, so they are safe to call from a render loop without stalling presentation.
- Marker strings are truncated at **64 bytes** (the LSL string limit). Keep annotations short.

---

## 4. Precise Clock Synchronization

In multimodal recording (such as EEG + Eye Tracking), software-level transmission latency and operating system scheduling jitter can corrupt millisecond-level alignment.

Pupilio implements a dedicated **`ClockSync`** algorithm:

1. When streaming begins, Pupilio measures the offset between the camera's hardware exposure time ($t_{\text{cam}}$, in ms) and the high-precision `pylsl.local_clock()` ($t_{\text{lsl}}$, in seconds).
2. Every sample is stamped with:

   $$t_{\text{sample}} = \frac{t_{\text{cam}}}{1000.0} + \Delta t_{\text{offset}}$$

3. This ensures that LSL timestamps strictly represent the optical camera exposure moment, eliminating operating system scheduling jitter.

At a nominal 200 Hz camera rate, this yields gaze timestamps aligned to the **acquisition clock** rather than the consumer's arrival clock — so the residual offset between gaze samples and EEG samples is dominated by camera exposure jitter (≪ 1 ms), not by Python or network latency.

---

## 5. Configuration Reference

The following settings are available on `DefaultConfig` (see `pupilio/default_config.py`).

### Documented settings

| Attribute | Type | Default | Description |
| :--- | :---: | :---: | :--- |
| `enable_lsl` | `bool` | `False` | Master switch to enable/disable LSL streaming. |
| `lsl_stream_mode` | `str` | `"standard"` | Gaze stream layout: `"standard"` (12 ch) or `"full"` (39 ch). |
| `lsl_gaze_stream_name` | `str` | `"Pupilio_Gaze"` | Name of the broadcasted continuous gaze stream. |
| `lsl_marker_stream_name` | `str` | `"Pupilio_Markers"` | Name of the broadcasted discrete event stream. |

### Advanced settings

> Verify these against your installed `default_config.py` before relying on them — they are not part of the primary public surface.

| Attribute | Type | Default | Description |
| :--- | :---: | :---: | :--- |
| `lsl_source_id` | `str` | auto (UUID) | LSL `source_id`. Set explicitly if you need a stable identifier across sessions. |
| `lsl_chunk_size` | `int` | `1` | Samples per `push_sample` call. Increase to reduce per-sample Python overhead at high rates. |
| `lsl_max_buffered` | `int` | `360` | Outlet-side buffer depth (samples). Increase if consumers join late or stall. |
| `lsl_nominal_srate` | `float` | derived | Overrides the advertised gaze rate. Normally auto-populated from the active camera rate. |

---

## 6. Recording with LabRecorder

1. Open **LabRecorder**.
2. Click **Update** to refresh network streams.
3. Under **Record from Streams**, select:
   - `Pupilio_Gaze (Gaze)`
   - `Pupilio_Markers (Markers)`
   - Your EEG / fNIRS streams (e.g., `BrainVision RDA`, `OpenBCI_EEG`)
4. Choose the output `.xdf` file path and click **Start**.
5. When the trial finishes, click **Stop**. All modalities are saved with synchronized timestamps.

> **Ordering matters.** Start LabRecorder **before** your task begins, and stop it **after** `stop_sampling()` returns. Recording that begins mid-session will miss the stream's opening samples; recording that ends after the outlets close will produce a truncated tail.

---

## 7. Offline Analysis in Python (`pyxdf`)

Load and inspect the recorded `.xdf` file using `pyxdf`:

```python
import numpy as np
import pyxdf
import matplotlib.pyplot as plt

# Load multi-modal XDF file
streams, header = pyxdf.load_xdf("experiment_data.xdf")

gaze_stream = None
marker_stream = None

for s in streams:
    if s["info"]["name"][0] == "Pupilio_Gaze":
        gaze_stream = s
    elif s["info"]["name"][0] == "Pupilio_Markers":
        marker_stream = s

# Extract gaze samples and timestamps
timestamps = np.array(gaze_stream["time_stamps"])
time_series = np.array(gaze_stream["time_series"])

# Channel 0: bino_gaze_x, Channel 1: bino_gaze_y, Channel 11: trigger
bino_x = time_series[:, 0]
bino_y = time_series[:, 1]
triggers = time_series[:, 11]

# Markers arrive as single-element string lists
marker_time = np.array(marker_stream["time_stamps"])
marker_labels = [m[0] for m in marker_stream["time_series"]]
print(f"{len(timestamps)} gaze samples, {len(marker_labels)} markers")
print(f"First markers: {marker_labels[:5]}")

# Sanity check: both streams share one LSL clock domain
print(f"First gaze ts  : {timestamps[0]:.6f}")
print(f"First marker ts: {marker_time[0]:.6f}")

# Plot gaze trajectory
plt.figure(figsize=(10, 6))
plt.plot(timestamps, bino_x, label="Bino Gaze X")
plt.plot(timestamps, bino_y, label="Bino Gaze Y")
plt.xlabel("LSL Time (seconds)")
plt.ylabel("Screen Coordinates (pixels)")
plt.title("Synchronized Eye Movement Data")
plt.legend()
plt.show()
```

---

## 8. Troubleshooting & FAQs

### Q1: LabRecorder does not discover `Pupilio_Gaze` or `Pupilio_Markers`

- **Cause**: Firewall blocking UDP multicast packets, or multiple network adapters (e.g. Wi-Fi + VPN + Ethernet) causing LSL to bind to the wrong interface.
- **Solution**:
  1. **Windows**: open Windows Firewall Settings and ensure Python (or your IDE) is allowed for both Private and Public networks. **macOS**: allow incoming connections when prompted, or add the interpreter to *System Settings → Network → Firewall → Options*. **Linux**: check `ufw`/`firewalld` rules for UDP multicast (`239.255.172.215` and the LSL port range).
  2. If using multiple network adapters, specify the binding interface in your LSL configuration file (`lsl_api.cfg`), or set the environment variable `LSLAPICFG` to point at a config that pins `MulticastAddress` / `KnownPeers`.

### Q2: I set `enable_lsl = True` but no streams appear

Check the console for a `pylsl` import warning. If `pylsl` is not installed, Pupilio disables streaming and continues with local recording only (see §1). Install with `pip install pylsl` and re-run.

### Q3: My markers show up but have no matching gaze samples

This almost always means LabRecorder started **after** `start_sampling()` or stopped **before** `stop_sampling()`. See the ordering note in §6. It can also occur if the marker stream is added to LabRecorder but the gaze stream is not — both must be checked.

### Q4: My `trigger` channel is stuck at a non-zero value

`set_trigger()` uses sample-and-hold semantics (see §3.2). Call `set_trigger(0)` after the event window closes, or detect transitions rather than absolute values in your analysis.

### Q5: Can I run multiple Pupilio eye trackers on the same network?

**Yes**, but each device needs unique stream names — two outlets with the same `name` are ambiguous for consumers and appear as duplicate entries in LabRecorder.

```python
# Device A
config.lsl_gaze_stream_name = "Pupilio_SubjectA_Gaze"
config.lsl_marker_stream_name = "Pupilio_SubjectA_Markers"

# Device B
config.lsl_gaze_stream_name = "Pupilio_SubjectB_Gaze"
config.lsl_marker_stream_name = "Pupilio_SubjectB_Markers"
```

For robust grouping across sessions, also set a stable `lsl_source_id` per device (e.g. `"pupilio-subjectA"`).

### Q6: How do I verify my channel order without recording?

Resolve the stream and print its metadata XML — the channel labels and units are published there:

```python
import pylsl
streams = pylsl.resolve_byprop("name", "Pupilio_Gaze", timeout=5.0)
print(streams[0].as_xml())
```

---

## 9. Glossary

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

## Converting this Document to Word

```bash
pandoc lsl-integration.md -o lsl-integration.docx \
  --toc --toc-depth=2 \
  --highlight-style=tango
```

Pandoc maps headings, tables, and fenced code blocks to native Word styles, and converts the LaTeX equations in §4 into real Word equations. If you use `--toc`, delete the hand-written table of contents first.

*End of document.*