# C/C++ API

This document describes the native API of the Pupil.IO eye tracker, generated from the
shipped headers `pupil_io_et.h` and `deep_gaze_et.h`.

If you want to develop with C++, please contact zhugc2016#gmail.com (replace # with @) for
the C++ libraries and headers.

## Two API layers

The DLL exports two families of functions, and it matters which one you use:

| Layer | Prefix | Header | Purpose |
|---|---|---|---|
| Application | `pupil_io_*` | `pupil_io_et.h` | Recording sessions, background sampling, triggers, data export. This is what the Python package binds. |
| Core | `deep_gaze_*` | `deep_gaze_et.h` | Device control and per-frame gaze estimation, with no recording or session management. |

Prefer the `pupil_io_*` layer. It wraps the core layer and adds everything an experiment
needs: a background sampling thread, trigger codes aligned to samples, and CSV export. Drop
to the `deep_gaze_*` layer only when you are building your own recording pipeline.

A third family, `mlif_pupil_io_*`, mirrors the `pupil_io_*` functions but returns plain
`int` instead of the `PupilioReturn` enum. It exists for foreign-function interfaces such as
MATLAB that cannot bind a C++ enum. The behaviour is otherwise identical.

Python users do not call any of this directly — see the
[Modules](modules.rst) documentation for the `pupilio.core.Pupilio` wrapper.

## Return codes

Both layers return the same numeric codes. `pupil_io_et.h` names them `PupilioReturn`,
`deep_gaze_et.h` names them `ET_ReturnCode`, and the Python package exposes them as
`pupilio.ET_ReturnCode`.

| Value | Name | Meaning |
|---|---|---|
| 0 | `PUPILIO_ET_SUCCESS` | Success; proceed to the next step. |
| 1 | `PUPILIO_ET_CALI_CONTINUE` | Calibration in progress; keep sampling the current point. |
| 2 | `PUPILIO_ET_CALI_NEXT_POINT` | Calibration in progress; advance to the next point. |
| 3 | `PUPILIO_ET_INVALID_PATH` | A supplied file or directory path is invalid. |
| 4 | `PUPILIO_ET_INVALID_PARAM` | A supplied argument is out of range or malformed. |
| 8 | `PUPILIO_ET_ALREADY_SET` | The requested value was already applied. Not an error. |
| 9 | `PUPILIO_ET_FAILED` | The operation failed. |
| 10 | `PUPILIO_ET_EXCEPTION` | An exception was raised inside the library. |

The core layer's `ET_ReturnCode` declares only 0, 1, 2, and 9, but the library may return
any of the values above. Always compare against the full set.

## Camera modes

The frame rate mode is decided at runtime by the `camera_mode` field of
`dp_camera_tunning.bin`. **The library is the single source of truth** — do not hard-code
ROI sizes or offsets in client code; read them back with `pupil_io_get_camera_mode`.

| Value | Name | Sampling rates |
|---|---|---|
| 0 | `CAMERA_MODE_SYNC_400` | 200 Hz, 400 Hz |
| 1 | `CAMERA_MODE_SYNC_800` | 200 Hz, 400 Hz, 800 Hz |
| 2 | `CAMERA_MODE_SYNC_1000` | 200 Hz, 400 Hz, 800 Hz, 1000 Hz |
| 3 | `CAMERA_MODE_SYNC_200` | 200 Hz |
| 4 | `CAMERA_MODE_ASYNC_400` | 200 Hz, 400 Hz |

## Data layouts

These arrays are shared by several functions, so they are defined once here.

### Per-eye sample — 14 floats

| Index | Field |
|---|---|
| 0 | Gaze position x, 0–1920 |
| 1 | Gaze position y, 0–1080 |
| 2 | Pupil diameter, 0–10 mm |
| 3–5 | Pupil position in 3-D: x, y, z |
| 6 | Gaze angle theta, radians |
| 7 | Gaze angle phi, radians |
| 8–10 | Gaze direction vector: x, y, z |
| 11–12 | Monocular gaze point: x, y |
| 13 | Validity flag: 0 invalid, 1 valid |

Always check index 13 before using a sample.

### Binocular sample — 10 floats

| Index | Field |
|---|---|
| 0 | Fused gaze position x, 0–1920 |
| 1 | Fused gaze position y, 0–1080 |
| 2 | Validity flag: 0 invalid, 1 valid |
| 3–9 | Reserved |

### Eye position — 3 floats

Millimetres, relative to the tracker.

- Screen centre is `(172.08, 96.795)`; the screen spans `[344.16, 193.59]`.
- Recommended operating ranges: `x` within `172.08 - 32 ± 30`, `y` within `96.795 - 40 ± 30`,
  and `z` within `-580 ± 50`.

---

# Application API (`pupil_io_et.h`)

## Lifecycle

### `pupil_io_init`

```cpp
PupilioReturn pupil_io_init();
```

Initialises the tracker and opens the cameras. Call the configuration functions that must
precede initialisation — `pupil_io_set_camera_mode`, `pupil_io_set_eye_mode`,
`pupil_io_set_log` — before this, and query `pupil_io_get_camera_mode` after it.

### `pupil_io_release`

```cpp
PupilioReturn pupil_io_release();
```

Releases every resource held by the library. Must be called before the program exits.

### `pupil_io_get_version`

```cpp
const char *pupil_io_get_version();
```

Returns the library version string. The buffer is owned by the library; do not free it.

## Configuration

### `pupil_io_set_eye_mode`

```cpp
PupilioReturn pupil_io_set_eye_mode(int mode);
```

Selects which eyes to track: `0` binocular (default), `-1` left only, `1` right only.

### `pupil_io_set_camera_mode`

```cpp
PupilioReturn pupil_io_set_camera_mode(int* mode);
```

Requests a frame rate mode. Accepts only `CAMERA_MODE_SYNC_400` (0) and
`CAMERA_MODE_SYNC_200` (3), and only on devices whose `dp_camera_tunning.bin` is marked
`sync_400` — such devices run natively at 400 Hz and can be down-clocked to 200 Hz.

**Must be called before `pupil_io_init`.** Initialisation applies the mode once when opening
the cameras; an already-open camera is never reconfigured. To change rate afterwards, call
`pupil_io_release`, set the mode, then `pupil_io_init` again.

Returns `PUPILIO_ET_FAILED` if `mode` is null or invalid, or the device is not a `sync_400`
device.

### `pupil_io_get_camera_mode`

```cpp
PupilioReturn pupil_io_get_camera_mode(int* mode, int* left_roi, int* right_roi);
```

Reports the active frame rate mode and the camera ROI geometry. Call it after
`pupil_io_init` succeeds, and use the result to size preview buffers and place preview
rectangles.

- `mode` — receives the camera mode. May be null.
- `left_roi`, `right_roi` — receive 4 ints, `{x, y, w, h}`, in full-sensor (1280x1024)
  coordinates. `w`/`h` are the ROI buffer size and `x`/`y` its position on the full frame.
  May be null.

### `pupil_io_set_look_ahead`

```cpp
PupilioReturn pupil_io_set_look_ahead(int look_ahead);
```

Sets how many frames ahead the filter predicts, trading latency against smoothness. The
Python wrapper restricts this to 1–4.

### `pupil_io_set_kappa_filter`

```cpp
PupilioReturn pupil_io_set_kappa_filter(int kappa_filter);
```

Enables (`1`, default) or disables (`0`) kappa-angle verification after calibration. Disable
it to allow calibration for participants with strabismus.

### `pupil_io_set_filter_enable`

```cpp
PupilioReturn pupil_io_set_filter_enable(bool status);
```

Enables or disables gaze smoothing. Disable it when you need raw, unfiltered estimates.

### `pupil_io_set_log`

```cpp
PupilioReturn pupil_io_set_log(int valid, char *log_Path);
```

Enables (`1`) or disables (`0`) native logging, writing to the directory `log_Path`.

## Calibration

### `pupil_io_set_cali_mode`

```cpp
PupilioReturn pupil_io_set_cali_mode(int mode, float *cali_points);
```

Chooses the calibration layout: `mode` must be 2, 4, or 5. `cali_points` must have room for
`2 * mode` floats and **receives** the target coordinates the library selected, as
alternating x and y values.

### `pupil_io_cali`

```cpp
PupilioReturn pupil_io_cali(const int cali_point_id);
```

Feeds one frame of calibration data for the target `cali_point_id` (zero-based). Call it
repeatedly while that target is displayed and dispatch on the result:

- `PUPILIO_ET_CALI_CONTINUE` — keep displaying this target.
- `PUPILIO_ET_CALI_NEXT_POINT` — move to the next target.
- `PUPILIO_ET_SUCCESS` — calibration is complete.

### `pupil_io_recalibrate`

```cpp
PupilioReturn pupil_io_recalibrate();
```

Discards the current calibration so a fresh one can begin.

### `pupil_io_face_pos`

```cpp
PupilioReturn pupil_io_face_pos(float *eyepos);
```

Writes the participant's eye position into `eyepos`, a 3-float array. See
[Eye position](#eye-position--3-floats). Use it to guide head positioning before
calibration.

## Sessions and recording

### `pupil_io_create_session`

```cpp
PupilioReturn pupil_io_create_session(const char *session_name);
```

Starts a named recording session, creating its log files and a temporary directory for
incremental data. Use only letters, digits, and underscores; keep the name unique so data
can be recovered from the temporary directory if a run is interrupted.

### `pupil_io_start_sampling` / `pupil_io_stop_sampling`

```cpp
PupilioReturn pupil_io_start_sampling();
PupilioReturn pupil_io_stop_sampling();
```

Start and stop the background sampling thread. Buffered samples survive a stop, so data can
still be saved afterwards.

> **Important:** call `pupil_io_stop_sampling` only while sampling is actually running.
> Stopping when idle dereferences a null sampling thread and crashes the process. Guard the
> call with `pupil_io_sampling_status`.

### `pupil_io_sampling_status`

```cpp
PupilioReturn pupil_io_sampling_status(bool &status);
```

Sets `status` to whether the sampling thread is currently running.

### `pupil_io_send_trigger`

```cpp
PupilioReturn pupil_io_send_trigger(uint64_t trigger_code);
```

Records a trigger code alongside the current sample, so eye data can be aligned with
experiment events. The Python wrapper restricts codes to 1–65535. Do not call it faster than
the tracker can consume triggers.

### `pupil_io_save_data_to`

```cpp
PupilioReturn pupil_io_save_data_to(char *path);
```

Writes the buffered samples to a CSV file at `path`. The parent directory must exist and be
writable.

### `pupil_io_clear_cache`

```cpp
PupilioReturn pupil_io_clear_cache();
```

Discards buffered samples. Anything not yet saved is lost.

## Gaze estimation

### `pupil_io_estimate_gaze`

```cpp
PupilioReturn pupil_io_estimate_gaze(float *pt_l, float *pt_r, float *bino, long long *timeStamp);
```

The recommended estimation call. Fills `pt_l` and `pt_r` (14 floats each) and `bino`
(10 floats), plus the camera exposure timestamp.

### `pupil_io_est_full`

```cpp
PupilioReturn pupil_io_est_full(float* pt, long long* timestamp);
```

The same data in one 38-float array, laid out as `pt_l(14) + pt_r(14) + bino(10)`. The
layout does not depend on the frame rate mode.

### `pupil_io_est_lr`

```cpp
PupilioReturn pupil_io_est_lr(float *pt_l, float *pt_r, long long *timeStamp);
```

Left and right eye data only, without the fused binocular result.

### `pupil_io_est`

```cpp
PupilioReturn pupil_io_est(float *pt, long long *timeStamp);
```

A compact 11-float summary:

| Index | Field |
|---|---|
| 0–2 | Left eye: gaze x, gaze y, pupil diameter |
| 3–5 | Right eye: gaze x, gaze y, pupil diameter |
| 6–7 | Monocular mean gaze: x, y |
| 8 | Status: 0 normal, 1 left eye lost, 2 right eye lost, 3 both lost |
| 9–10 | Fused binocular gaze: x, y |

### `pupil_io_get_current_gaze`

```cpp
PupilioReturn pupil_io_get_current_gaze(float *left, float *right, float *bino);
```

Returns the latest cached gaze without running a new estimation — the cheap read for
gaze-contingent displays. Each array holds 3 floats: validity flag, x, y.

## Preview

### `pupil_io_previewer_init` / `_start` / `_stop`

```cpp
PupilioReturn pupil_io_previewer_init(const char *udp_address, int port, bool draw_preview_annotation = true);
PupilioReturn pupil_io_previewer_start();
PupilioReturn pupil_io_previewer_stop();
```

Streams the camera preview over UDP to `udp_address:port`. With `draw_preview_annotation`
set, the stream includes eye boxes, pupil markers, and glint markers.

### `pupil_io_get_previewer`

```cpp
PupilioReturn pupil_io_get_previewer(unsigned char **img_1, unsigned char **img2,
                                     float *eye_rects, float *pupil_centers, float *glint_centers);
```

Retrieves the preview images together with the detected features. The images and the feature
coordinates share one coordinate system, so the features can be drawn directly onto the
returned images:

- **SYNC_200:** images are padded back to the full 1280x1024 frame, and the coordinates are
  full-frame.
- **Other modes:** images keep their ROI size, and the coordinates are already offset by the
  ROI origin and clipped to it.

`eye_rects` holds 16 floats (four `{x, y, w, h}` rects), while `pupil_centers` and
`glint_centers` hold 8 floats each (four `{x, y}` points).

## Event detection

### `pupil_io_event_detection`

```cpp
PupilioReturn pupil_io_event_detection(const char *data_path, char *output_dir,
                                       const char *which_eye,
                                       int minimum_duration = 30,
                                       float dispersion_threshold = 1.0);
```

Detects fixations and saccades in a recorded CSV using the I-DT (dispersion threshold)
algorithm, writing results to `output_dir`. `which_eye` is `"left"`, `"right"`, or `"bino"`;
`minimum_duration` is in milliseconds and `dispersion_threshold` in degrees. Both must be
greater than zero.

See Salvucci, D. D., & Goldberg, J. H. (2000). Identifying fixations and saccades in
eye-tracking protocols. *Proceedings of the 2000 Symposium on Eye Tracking Research &
Applications*, 71–78.

---

# Core API (`deep_gaze_et.h`)

The `deep_gaze_*` functions provide device control and gaze estimation without sessions,
background sampling, or data export. Their names, arguments, and semantics mirror the
`pupil_io_*` functions documented above: `deep_gaze_init`, `deep_gaze_release`,
`deep_gaze_get_version`, `deep_gaze_set_log`, `deep_gaze_set_eye_mode`,
`deep_gaze_set_look_ahead`, `deep_gaze_set_kappa_filter`, `deep_gaze_set_camera_mode`,
`deep_gaze_get_camera_mode`, `deep_gaze_set_cali_mode`, `deep_gaze_cali`,
`deep_gaze_recalibrate`, `deep_gaze_face_pos`, `deep_gaze_est`, `deep_gaze_est_lr`,
`deep_gaze_est_full`, and `deep_gaze_get_previewer`.

Two functions exist only at this layer.

### `deep_gaze_face_image`

```cpp
ET_ReturnCode deep_gaze_face_image(char** image_data, int* width, int* height);
```

Retrieves the pre-processed grayscale face image along with its dimensions.

### `deep_gaze_set_camera_param`

```cpp
ET_ReturnCode deep_gaze_set_camera_param(float* camera_param);
```

Overrides the camera parameter array. Intended for calibration and diagnostics.

## Push-based gaze results

Instead of polling, you can register a callback and let the library push results to you.

```cpp
typedef void (*deep_gaze_est_callback)(const float* pt, long long timestamp, void* user_data);

ET_ReturnCode deep_gaze_set_est_callback(deep_gaze_est_callback cb, void* user_data);
```

`pt` is the 38-float array described under `pupil_io_est_full`. `user_data` is the pointer
you registered, passed through untouched.

Registering a callback starts the estimation pipeline automatically — you no longer need to
call `deep_gaze_est_full` yourself. Results are dispatched at a controlled rate: 400 Hz in
synchronous mode, or 800 Hz in asynchronous mode with the left and right cameras
alternating. The timestamp is the camera exposure time; in synchronous mode both cameras
share it, while in asynchronous mode it alternates between them.

Pass `cb = nullptr` to unregister the callback and stop the dispatch thread.
