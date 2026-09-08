# Frequently Asked Questions (FAQ) & Troubleshooting

This document addresses common questions, best practices, and troubleshooting tips for developing experiments and collecting research data with the Pupilio SDK.

---

## 1. General & Hardware Setup

### Q: Can I develop and debug my experiment scripts on a PC without the eye tracker connected?
**A: Yes.** Set `config.simulation_mode = True` when initializing `Pupilio`:

```python
from pupilio import Pupilio, DefaultConfig

config = DefaultConfig()
config.simulation_mode = True  # Uses mouse cursor as gaze input
pupil_io = Pupilio(config=config)
```
In simulation mode, the mouse position is mapped to real-time gaze coordinates, allowing you to test calibration UI, experimental logic, trigger synchronization, and LSL streaming on any Windows computer.

### Q: What operating systems and Python versions are supported?
**A:** Pupilio is officially tested and optimized for **Windows 10 and Windows 11 (64-bit)** with **Python 3.8 through 3.12**.

### Q: How do I switch between 200 Hz and 400 Hz sampling rates?
**A:** On devices equipped with 400 Hz capable cameras, you can configure the sampling rate through `DefaultConfig`:

```python
config = DefaultConfig()
config.sampling_rate = 400  # or 200
pupil_io = Pupilio(config=config)
```
Pupilio automatically verifies hardware camera modes upon initialization. If a requested rate is unsupported by the connected camera, it will gracefully fall back to the maximum supported rate with a warning.

---

## 2. Calibration & Data Accuracy

### Q: Why does calibration fail or yield low accuracy?
**A:** Check the following physical and environmental factors:
1. **Subject Distance**: Ensure the subject sits between **50 cm and 90 cm** from the eye tracker (optimal distance is around 65–70 cm).
2. **Head Alignment**: Use `pupil_io.face_position()` or enable `config.face_previewing = 1` during calibration to ensure the participant's head is centered in the tracking box.
3. **Lighting Conditions**: Avoid direct sunlight or strong infrared light sources shining directly onto the participant's face or cameras.
4. **Participants with Strabismus**: By default, Pupilio verifies the kappa angle. For subjects with strabismus or eccentric fixation, set:
   ```python
   config.enable_kappa_verification = 0
   ```

### Q: How do I choose between 2-point, 4-point, and 5-point calibration?
**A:** Configured via `config.cali_mode`:
- `CalibrationMode.TWO_POINTS`: Fastest calibration routine, ideal for quick screening, young children, or clinical cohorts.
- `CalibrationMode.FIVE_POINTS` (Recommended): Standard 5-point geometry offering optimal visual angle accuracy across the entire display.
- `CalibrationMode.FOUR_POINTS`: Corner-oriented 4-point calibration.

```python
from pupilio import CalibrationMode
config.cali_mode = CalibrationMode.FIVE_POINTS
```

---

## 3. LabStreamingLayer (LSL) & Multi-modal Integration

### Q: Why doesn't LabRecorder discover `Pupilio_Gaze` or `Pupilio_Markers`?
**A:**
1. **Verify LSL is enabled in config**:
   ```python
   config.enable_lsl = True
   ```
2. **Ensure sampling has started**:
   LSL streaming starts when `pupil_io.start_sampling()` is called.
3. **Check Windows Firewall**:
   LSL uses UDP multicast on local networks. Ensure that Python (or your IDE) is granted permission through Windows Firewall for Private networks.
4. **Multiple Network Adapters**:
   If your machine has multiple active network interfaces (e.g. Wi-Fi, Ethernet, VPN), LSL might bind to a secondary adapter. Create or edit `lsl_api.cfg` in the application directory to specify your target network interface IP.

### Q: What is the difference between `standard` and `full` LSL modes?
**A:**
- **`standard` (12 channels, Default)**: Contains binocular `(x, y, valid)`, left eye `(x, y, pupil_dia, valid)`, right eye `(x, y, pupil_dia, valid)`, and `trigger`. This satisfies 95% of cognitive and EEG co-registration studies with minimal network bandwidth.
- **`full` (39 channels)**: Broadcasts all 38 deep neural network estimation metrics (including 3D pupil coordinate $x, y, z$, visual angles $\theta, \phi$, visual direction vectors, and pixels per degree) + the `trigger` channel.

### Q: How are triggers synchronized across LSL?
**A:** Calling `pupil_io.set_trigger(code)` performs two synchronized actions:
1. It injects the trigger integer code into the continuous Gaze stream (Channel 11 in standard mode) for that exact frame.
2. It simultaneously broadcasts the trigger code as an event string to the discrete Marker stream (`Pupilio_Markers`).

---

## 4. Data Recording & Coordinate Systems

### Q: Why do Pygame and PsychoPy display different gaze coordinates?
**A:**
- **Pygame**: The origin `(0, 0)` is at the **top-left** corner of the display. Screen width and height span `[0, 1920]` and `[0, 1080]`.
- **PsychoPy**: By default, in `units='pix'`, the origin `(0, 0)` is at the **center** of the window:
  - $x \in [-960, +960]$
  - $y \in [-540, +540]$
  - To convert Pupilio pixel coordinates `(gx, gy)` to PsychoPy coordinates:
    ```python
    psychopy_x = gx - (screen_width / 2)
    psychopy_y = (screen_height / 2) - gy
    ```

### Q: Why do I get an error when saving data with `save_data()`?
**A:** `pupil_io.save_data(path)` requires that the destination directory exists and is writable:
```python
import os
data_dir = "./data"
os.makedirs(data_dir, exist_ok=True)
pupil_io.save_data(os.path.join(data_dir, "trial_data.csv"))
```

### Q: How do I perform fixation and saccade detection?
**A:** Use the built-in `EventDetection` module, which implements the standard I-DT (Identification by Dispersion Threshold) algorithm:

```python
from pupilio import EventDetection

ed = EventDetection()
# Analyzes recorded CSV and writes event reports to output_dir
ed.detect(
    "trial_data.csv",
    output_dir="./analysis_output",
    which_eye="bino",
    minimum_duration=30,      # Minimum fixation duration in ms
    dispersion_threshold=1.0  # Dispersion threshold in visual degrees
)
```