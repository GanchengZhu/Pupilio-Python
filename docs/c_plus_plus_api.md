# Overview

This document provides a detailed description of the API functions provided by the Deep Gaze library. This library allows for the initialization, calibration, and querying of eye gaze information.
If you want to develop with C++, please contact zhugc2016#gmail.com (replace # with @) for C++ libraries and headers.

# Enum Definitions

## `ET_ReturnCode`

The `ET_ReturnCode` enum defines possible return codes for the API functions:

- `ET_SUCCESS` (0): Success; proceed to the next scene.
- `ET_CALI_CONTINUE` (1): Calibration in progress; continue using the current calibration point.
- `ET_CALI_NEXT_POINT` (2): Calibration in progress; switch to the next calibration point.
- `ET_FAILED` (9): Operation failed.


# API Functions

## `pupil_io_init`

```cpp
ET_ReturnCode pupil_io_init();
```

**Description:**

Initializes the Deep Gaze system.

**Returns:**

+   `ET_SUCCESS` on successful initialization.
+   Other `ET_ReturnCode` values indicate failure or special conditions.

* * *

## `pupil_io_face_pos`

```cpp
ET_ReturnCode pupil_io_face_pos(float* eyepos);
```

**Description:**

Retrieves the user's face position.

**Parameters:**

+   `eyepos`: Array of 3 floats representing the eye position in millimeters.
    
    +   `x` and `y` are the coordinates on the screen.
    +   `z` is the depth value.
    
    Screen center: (172.08, 96.795)  
    Screen size: \[344.16, 193.59\]  
    Valid ranges:
    
    +   `x` ∈ \[172.08 - 32 - 30, 172.08 - 32 + 30\]
    +   `y` ∈ \[96.795 - 40 - 30, 96.795 - 40 + 30\]
    +   `z` ∈ \[-580 - 50, -580 + 50\]

**Returns:**

+   `ET_SUCCESS` on success.
+   Other `ET_ReturnCode` values indicate failure or special conditions.

* * *

## `pupil_io_cali`

```cpp
ET_ReturnCode pupil_io_cali(const int cali_point_id);
```

**Description:**

Performs calibration at a specific point.

**Parameters:**

+   `cali_point_id`: Identifier for the calibration point.

**Returns:**

+   `ET_SUCCESS` if calibration is successful.
+   `ET_CALI_CONTINUE` if calibration needs to continue.
+   `ET_CALI_NEXT_POINT` if calibration needs to move to the next point.
+   Other `ET_ReturnCode` values indicate failure or special conditions.

* * *

## `pupil_io_est`

```cpp
ET_ReturnCode pupil_io_est(float* pt, long long* timeStamp);
```

**Description:**

Obtains gaze estimation information.

**Parameters:**

+   `pt`: Array of 11 floats providing gaze information:
    
    +   `pt[0]` - Left eye gaze position x (0~1920)
    +   `pt[1]` - Left eye gaze position y (0~1080)
    +   `pt[2]` - Left eye pupil size (0~10) mm
    +   `pt[3]` - Right eye gaze position x (0~1920)
    +   `pt[4]` - Right eye gaze position y (0~1080)
    +   `pt[5]` - Right eye pupil size (0~10) mm
    +   `pt[6]` - Pixels per degree x
    +   `pt[7]` - Pixels per degree y
    +   `pt[8]` - Return flag (norm: 0; miss left eye: 1; miss right eye: 2; no eyes: 3)
    +   `pt[9]` - Binocular gaze position x (0~1920)
    +   `pt[10]` - Binocular gaze position y (0~1920)
+   `timeStamp`: Timestamp in hours, minutes, seconds, and milliseconds.
    

**Returns:**

+   `ET_SUCCESS` on successful retrieval.
+   Other `ET_ReturnCode` values indicate failure or special conditions.

* * *

## `pupil_io_est_lr`

```cpp
ET_ReturnCode pupil_io_est_lr(float* pt_l, float* pt_r, long long* timeStamp);
```

**Description:**

Obtains separate gaze estimation information for the left and right eyes.

**Parameters:**

+   `pt_l`: Array of 14 floats for left eye gaze information:
    
    +   `pt_l[0]` - Left eye gaze position x (0~1920)
    +   `pt_l[1]` - Left eye gaze position y (0~1080)
    +   `pt_l[2]` - Left eye pupil diameter (0~10) mm
    +   `pt_l[3]` - Left eye pupil position x
    +   `pt_l[4]` - Left eye pupil position y
    +   `pt_l[5]` - Left eye pupil position z
    +   `pt_l[6]` - Left eye visual angle (theta)
    +   `pt_l[7]` - Left eye visual angle (phi)
    +   `pt_l[8]` - Left eye visual angle (x)
    +   `pt_l[9]` - Left eye visual angle (y)
    +   `pt_l[10]` - Left eye visual angle (z)
    +   `pt_l[11]` - Left eye pixels per degree x
    +   `pt_l[12]` - Left eye pixels per degree y
    +   `pt_l[13]` - Left eye valid (0: invalid, 1: valid)
+   `pt_r`: Array of 14 floats for right eye gaze information:
    
    +   `pt_r[0]` - Right eye gaze position x (0~1920)
    +   `pt_r[1]` - Right eye gaze position y (0~1080)
    +   `pt_r[2]` - Right eye pupil diameter (0~10) mm
    +   `pt_r[3]` - Right eye pupil position x
    +   `pt_r[4]` - Right eye pupil position y
    +   `pt_r[5]` - Right eye pupil position z
    +   `pt_r[6]` - Right eye visual angle (theta)
    +   `pt_r[7]` - Right eye visual angle (phi)
    +   `pt_r[8]` - Right eye visual angle (x)
    +   `pt_r[9]` - Right eye visual angle (y)
    +   `pt_r[10]` - Right eye visual angle (z)
    +   `pt_r[11]` - Right eye pixels per degree x
    +   `pt_r[12]` - Right eye pixels per degree y
    +   `pt_r[13]` - Right eye valid (0: invalid, 1: valid)
+   `timeStamp`: Timestamp in hours, minutes, seconds, and milliseconds.
    

**Returns:**

+   `ET_SUCCESS` on successful retrieval.
+   Other `ET_ReturnCode` values indicate failure or special conditions.

* * *

## `pupil_io_release`

```cpp
ET_ReturnCode pupil_io_release();
```

**Description:**

Releases resources and performs cleanup when the program exits.

**Returns:**

+   `ET_SUCCESS` on successful release.
+   Other `ET_ReturnCode` values indicate failure or special conditions.

## `pupil_io_get_version`

```cpp
const char *pupil_io_get_version();
```

**Description:**

Retrieves the version information of the Deep Gaze library.

**Returns:**

+   A const char* representing the version string of the library.

## `pupil_io_set_look_ahead`

```cpp
ET_ReturnCode pupil_io_set_look_ahead(int look_ahead);
```

**Description:**

Sets the look-ahead parameter, which defines the number of future frames the system considers for gaze estimation.

**Parameters:**

+   `look_ahead`: An integer specifying the number of frames to look ahead.

**Returns:**

+   `ET_SUCCESS` on successful parameter update. Other ET_ReturnCode values indicate failure or invalid input.

## `pupil_io_set_log`

```cpp
ET_ReturnCode pupil_io_set_log(int valid, char *log_Path);
```

**Description:**

Configures logging for the Deep Gaze library.

**Parameters:**

+   `valid`: An integer indicating whether logging is enabled (1 for enabled, 0 for disabled).
log_Path: A pointer to a character array specifying the path to the log file.

**Returns:**

+   `ET_SUCCESS` on successful log configuration.
Other ET_ReturnCode values indicate failure or invalid parameters.


## `pupil_io_recalibrate`

```cpp
ET_ReturnCode pupil_io_recalibrate();
```

**Description:**

Triggers recalibration of the gaze tracking system to improve accuracy.

**Returns:**

+   `ET_SUCCESS` if recalibration is completed successfully.
Other ET_ReturnCode values indicate failure or an inability to recalibrate.

## `pupil_io_face_image`

```cpp
ET_ReturnCode pupil_io_face_image(char **image_data, int *width, int *height);
```

**Description:**

Provides the current face image data being processed by the gaze tracking system.

**Parameters:**

+   `image_data`: A double pointer to hold the address of the image data buffer.
width: A pointer to an integer to store the width of the image.
height: A pointer to an integer to store the height of the image.
Returns:

**Returns:**

+   `ET_SUCCESS` on successful retrieval of face image data.
Other ET_ReturnCode values indicate failure or lack of image data.


## `pupil_io_set_cali_mode`

```cpp
ET_ReturnCode pupil_io_set_cali_mode(int mode, float *cali_points);
```

**Description:**

Sets the calibration mode and points for gaze tracking.

**Parameters:**

+   `mode`: An integer representing the calibration mode.
cali_points: A pointer to an array of floats representing calibration points.
Returns:

**Returns:**

+   `ET_SUCCESS` on successful calibration mode configuration.
Other ET_ReturnCode values indicate failure or invalid input