<div align="left">

# Pupil.IO Python SDK 

</div>

## What is "pupilio"?

**pupilio** is a lightweight Python SDK for the Pupil.IO eye-trackers developed by Hangzhou Shenning Technology Co., Ltd. It offers a user-friendly interface that covers core eye-tracking functions like data recording, calibration,  validation, and real-time access to gaze data. **"pupilio"** seamlessly integrates with popular platforms such as PsychoPy and PyGame, it enables quick development of eye-tracking studies.

## The Pupil.IO eye-tracker

<div align="left">
  <a href="https://raw.githubusercontent.com/GanchengZhu/Pupilio/refs/heads/master/docs/_static/images/intro/about/pupilio_c.PNG">
    <img width="390" height="351" src="https://raw.githubusercontent.com/GanchengZhu/Pupilio/refs/heads/master/docs/_static/images/intro/about/pupilio_c.PNG">
  </a>
</div>

[Pupil.IO](https://www.deep-gaze.com/) is a high-speed, high-precision eye-tracking system featuring an all-in-one (AIO) plug-and-play design that is ideal for both scientific research and clinical applications. With minimal setup (just power on and start tracking), it delivers lab-grade accuracy in a compact, user-friendly form factor.

### Features
- **Precision Tracking**: Capture high-frequency eye movement and pupil dynamics with lab-grade accuracy.
- **Seamless Compatibility**: Native integration with PsychoPy, PyGame, and other Python experimental platforms.
- **Intuitive Workflow**: Simplified calibration, validation, and recording with minimal setup.

### Specifications

| Attribute                | Specification                                 |
|--------------------------|-----------------------------------------------|
| Sample Rate              | 200 Hz        |
| Accuracy                 | 0.5-1°                                          |
| Precision                | 0.03°                                         |
| Blink/Occlusion Recovery | 5 ms @ 200 Hz                |
| Head Box                 | 40 cm x 40 cm @ 70 cm                         |
| Operation Range          | 50 - 90 cm                                    |
| Gaze Signal Delay        | < 25 ms                                       |
| Tracking Technology      | Neural Networks                               |
| Dimension                | 32 cm x 45 cm x 20 cm                         |
| Weight                   | 5 kg [Eye-tracker + Display + Compute Module] |
| Operating System         | Windows 11                                    |
| SDK                      | C/C++/Python/Matlab                           |

## Installation

Currently, all eye trackers shipped with Pupilio are pre-configured with the necessary Pupilio Python packages. If we need to upgrade this package, please enter the following command in the command prompt or PowerShell window:

```bash
pip install -U pupilio
```


## Quick Start
Here is a simple example to get started with Pupilio:

```python
# load PyGame library
import pygame
from pygame.locals import FULLSCREEN, HWSURFACE

# initialize PyGame
pygame.init()
# define the scree size
scn_width, scn_height = (1920, 1080)
# set a fullscreen mode with the above size
win = pygame.display.set_mode((scn_width, scn_height), FULLSCREEN|HWSURFACE)

# load Pupilio library
from pupilio import Pupilio

# instantiate a connection to the tracker
pupil_io = Pupilio()

# create a task session, and set a session name. 
# The session name must contain only letters, digits or underscores without any special characters.
pupil_io.create_session(session_name="quick_start")

# calibration and validation (recommended)
# set 'validate' to True if we would like to verify the calibration results
pupil_io.calibration_draw(screen=win, validate=True)

# start retrieving gaze
pupil_io.start_sampling()

# hang the main thread for 5 seconds by game
# eye tracking sampling are running on the background thread
pygame.time.wait(5 * 1000)

# stop eye tracking sampling
pupil_io.stop_sampling()

# sleep for 100 ms to capture ending samples
pygame.time.wait(100)

# save eye movement data
pupil_io.save_data("eye_movement.csv")

# release the tracker instance
# clean up Pupilio resources
pupil_io.release()

# quit pygame
pygame.quit()
```

## Documentation

Comprehensive documentation is available at Pupilio [Documentation](https://pupilio.readthedocs.io/en/latest/start/demo.html).

## Support

If you encounter any issues or have questions, please open an issue on GitHub or contact [zhugc2016@gmail.com](mailto:zhugc2016@gmail.com).

## License

Pupilio is a proprietary software developed by Hangzhou Shenning Technology Co., Ltd. All rights reserved. Unauthorized use, distribution, or modification is prohibited without explicit permission. For licensing inquiries, please contact [zhugc2016@gmail.com](mailto:zhugc2016@gmail.com).

## Acknowledgments
Pupilio is developed and maintained by Hangzhou Shenning Technology Co., Ltd. Special thanks to the community for their valuable feedback and support.
