# _*_ coding: utf-8 _*_
# Copyright (c) 2026, Hangzhou DeepGaze Science and Technology Co., Ltd
# All Rights Reserved
#
# DESCRIPTION:
# This demo shows how to enable LabStreamingLayer (LSL) in Pupilio.
# It broadcasts continuous eye-tracking samples (12 channels) and discrete markers/triggers
# to the local network for synchronized recording with EEG, fNIRS, etc. via LabRecorder.

import os
import time
from pupilio import Pupilio, DefaultConfig

def main():
    print("=== Pupilio LSL Sending Demo ===")

    # 1. Configure Pupilio with LSL enabled
    config = DefaultConfig()
    config.enable_lsl = True
    config.lsl_stream_mode = "standard"  # 12 channels (binocular, left, right, trigger)
    config.lsl_gaze_stream_name = "Pupilio_Gaze"
    config.lsl_marker_stream_name = "Pupilio_Markers"

    # Set to True if testing on a PC without physical eye-tracker hardware
    # config.simulation_mode = True

    # 2. Instantiate Pupilio and create experiment session
    pupil_io = Pupilio(config=config)
    pupil_io.create_session("lsl_demo_session")

    print(f"LSL Outlets created:")
    print(f"  - Gaze Stream: '{config.lsl_gaze_stream_name}' (Mode: {config.lsl_stream_mode}, 12 channels)")
    print(f"  - Marker Stream: '{config.lsl_marker_stream_name}'")

    try:
        # 3. Start sampling (this automatically starts LSL streaming in the background)
        print("\nStarting sampling and LSL streaming...")
        pupil_io.start_sampling()

        # 4. Simulate a 5-second experimental trial with triggers and annotations
        print("\nStreaming active for 5 seconds...")
        
        # Send an experiment start annotation
        pupil_io.send_lsl_marker("EXPERIMENT_START")
        time.sleep(1.0)

        # Send trigger code 101 (e.g. Target Stimulus Onset)
        print("Sending trigger 101 (Target Onset)...")
        pupil_io.set_trigger(101)
        time.sleep(1.5)

        # Send trigger code 201 (e.g. Participant Response)
        print("Sending trigger 201 (Response)...")
        pupil_io.set_trigger(201)
        time.sleep(1.5)

        # Send an experiment end annotation
        pupil_io.send_lsl_marker("EXPERIMENT_END")
        time.sleep(1.0)

    finally:
        # 5. Stop sampling (automatically stops LSL streaming)
        print("\nStopping sampling and LSL stream...")
        pupil_io.stop_sampling()

        # 6. Save local CSV data
        out_dir = "./data"
        os.makedirs(out_dir, exist_ok=True)
        csv_file = os.path.join(out_dir, "lsl_demo_gaze.csv")
        pupil_io.save_data(csv_file)
        print(f"Saved local data to: {csv_file}")

        # 7. Clean up resources
        pupil_io.release()
        print("Pupilio tracker released. Done.")


if __name__ == "__main__":
    main()
