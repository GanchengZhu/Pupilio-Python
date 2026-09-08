# LabStreamingLayer (LSL) Integration Guide

## Overview

**LabStreamingLayer (LSL)** is the research standard for unified, time-synchronized data streaming and recording across multiple modalities in cognitive science, neuroscience, and human-computer interaction.

The **Pupilio Python SDK** provides native support for LSL, enabling real-time, low-latency broadcasting of eye-tracking data and experimental triggers over local networks. Researchers can seamlessly co-register Pupilio eye-tracking data with:
- **Electroencephalography (EEG)** (e.g., BrainProducts, ANT Neuro, Biosemi, OpenBCI)
- **Functional Near-Infrared Spectroscopy (fNIRS)**
- **Physiological Sensors (EMG, ECG, GSR)**
- **Stimulus Presentation Engines** (PsychoPy, Pygame, E-Prime)

Pupilio LSL data can be captured synchronously into unified `.xdf` files using [LabRecorder](https://github.com/labstreaminglayer/App-LabRecorder).

---

## Installation & Prerequisites

LSL support relies on the official `pylsl` Python library. It is an optional dependency for Pupilio. If not already installed, install it via:

```bash
pip install pylsl
```

---

## Quick Start

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

# Optional: Run calibration and validation
# pupil_io.calibration_draw(validate=True)

# 3. Start sampling (LSL starts broadcasting automatically)
pupil_io.start_sampling()

# Send experimental triggers (automatically forwarded to LSL Marker stream & Gaze channel 11)
pupil_io.set_trigger(101)  # Target onset

# Send semantic text annotations
pupil_io.send_lsl_marker("FIXATION_CROSS_ONSET")

# 4. Stop sampling (LSL streaming stops automatically)
pupil_io.stop_sampling()
pupil_io.release()
```

---

## Stream Architecture

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

### 1. Continuous Gaze Stream (`Pupilio_Gaze`)
- **Stream Type**: `"Gaze"`
- **Sampling Rate**: `200.0` or `400.0` Hz (matches hardware camera rate)
- **Data Type**: `float32`

#### Standard Mode (`standard`, 12 Channels - Recommended)
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

#### Full Mode (`full`, 39 Channels)
Configured via `config.lsl_stream_mode = "full"`. Exports all 38 parameters computed by the neural gaze estimation model plus the trigger channel:
- **Channels 0–13 (Left Eye)**: `gaze_x`, `gaze_y`, `pupil_dia`, `pupil_pos_x`, `pupil_pos_y`, `pupil_pos_z`, `visual_angle_theta`, `visual_angle_phi`, `visual_vector_x`, `visual_vector_y`, `visual_vector_z`, `pix_per_degree_x`, `pix_per_degree_y`, `valid`.
- **Channels 14–27 (Right Eye)**: Same 14 parameters for the right eye.
- **Channels 28–37 (Binocular Fused)**: `bino_gaze_x`, `bino_gaze_y`, `bino_valid`, and reserved estimation metrics.
- **Channel 38**: `trigger`.

### 2. Discrete Marker Stream (`Pupilio_Markers`)
- **Stream Type**: `"Markers"`
- **Sampling Rate**: `0.0` (`IRREGULAR_RATE`)
- **Data Type**: `string`
- **Channel Count**: 1

Broadcasts discrete experiment events:
- Numeric triggers sent via `pupil_io.set_trigger(code)` (e.g., `"101"`).
- Text labels sent via `pupil_io.send_lsl_marker("TRIAL_START")`.

---

## Precise Clock Synchronization

In multimodal recording (such as EEG + Eye Tracking), software-level transmission latency and operating system scheduling jitter can corrupt millisecond-level alignment.

Pupilio implements a dedicated **`ClockSync`** algorithm:
1. When streaming begins, Pupilio measures the offset between the camera's hardware exposure time ($t_{\text{cam}}$ in ms) and the high-precision `pylsl.local_clock()` ($t_{\text{lsl}}$ in seconds).
2. Every sample is stamped with:
   $$t_{\text{sample}} = \frac{t_{\text{cam}}}{1000.0} + \Delta t_{\text{offset}}$$
3. This ensures that the LSL timestamps strictly represent the optical camera exposure moment, eliminating operating system scheduling jitter.

---

## Configuration Reference

The following settings are available on [`DefaultConfig`](file:///d:/DeepGazeCodeBackup/Pupilio/pupilio/default_config.py):

| Attribute | Type | Default | Description |
| :--- | :---: | :---: | :--- |
| `enable_lsl` | `bool` | `False` | Master switch to enable/disable LSL streaming. |
| `lsl_stream_mode` | `str` | `"standard"` | Gaze stream layout: `"standard"` (12 ch) or `"full"` (39 ch). |
| `lsl_gaze_stream_name` | `str` | `"Pupilio_Gaze"` | Name of the broadcasted continuous gaze stream. |
| `lsl_marker_stream_name` | `str` | `"Pupilio_Markers"`| Name of the broadcasted discrete event stream. |

---

## Recording with LabRecorder

1. Open **LabRecorder**.
2. Click **Update** to refresh network streams.
3. Under **Record from Streams**, select:
   - `Pupilio_Gaze (Gaze)`
   - `Pupilio_Markers (Markers)`
   - Your EEG / fNIRS streams (e.g., `BrainVision RDA`, `OpenBCI_EEG`)
4. Choose the output `.xdf` file path and click **Start**.
5. When the trial finishes, click **Stop**. All modalities are saved with synchronized timestamps.

---

## Offline Analysis in Python (`pyxdf`)

Load and inspect the recorded `.xdf` file using `pyxdf`:

```python
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
timestamps = gaze_stream["time_stamps"]
time_series = gaze_stream["time_series"]

# Channel 0: bino_gaze_x, Channel 1: bino_gaze_y, Channel 11: trigger
bino_x = time_series[:, 0]
bino_y = time_series[:, 1]
triggers = time_series[:, 11]

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
