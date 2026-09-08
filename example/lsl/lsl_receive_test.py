# _*_ coding: utf-8 _*_
# Copyright (c) 2026, Hangzhou DeepGaze Science and Technology Co., Ltd
# All Rights Reserved
#
# DESCRIPTION:
# Receiver and verification tool for Pupilio LabStreamingLayer (LSL) streams.
# Discovers 'Pupilio_Gaze' and 'Pupilio_Markers' streams on the local network,
# parses XML metadata (channels, units), and prints incoming samples in real time.

import time
import pylsl


def print_stream_metadata(info: pylsl.StreamInfo):
    print("\n--- Stream Metadata ---")
    print(f"Name: {info.name()}")
    print(f"Type: {info.type()}")
    print(f"Channels: {info.channel_count()}")
    print(f"Sampling Rate: {info.nominal_srate()} Hz")
    print(f"Source ID: {info.source_id()}")

    desc = info.desc()
    channels_node = desc.child("channels")
    if not channels_node.empty():
        print("Channel Specifications:")
        ch = channels_node.child("channel")
        idx = 0
        while not ch.empty():
            label = ch.child_value("label")
            eye = ch.child_value("eye")
            unit = ch.child_value("unit")
            ch_type = ch.child_value("type")
            print(f"  [{idx:02d}] {label:<16} (eye: {eye:<5}, type: {ch_type:<14}, unit: {unit})")
            ch = ch.next_sibling("channel")
            idx += 1


def main():
    print("=== Pupilio LSL Stream Receiver & Verification ===")
    print("Searching for Pupilio LSL streams on the network...")

    # 1. Resolve Gaze Stream
    gaze_streams = pylsl.resolve_byprop("type", "Gaze", timeout=5.0)
    if not gaze_streams:
        print("No 'Gaze' stream found! Make sure Pupilio with LSL enabled is running.")
        return

    gaze_info = gaze_streams[0]
    print(f"\nFound Gaze Stream: '{gaze_info.name()}' on host: {gaze_info.hostname()}")
    print_stream_metadata(gaze_info)
    gaze_inlet = pylsl.StreamInlet(gaze_info)

    # 2. Resolve Marker Stream (optional)
    marker_streams = pylsl.resolve_byprop("type", "Markers", timeout=2.0)
    marker_inlet = None
    if marker_streams:
        marker_info = marker_streams[0]
        print(f"\nFound Marker Stream: '{marker_info.name()}'")
        marker_inlet = pylsl.StreamInlet(marker_info)
        marker_inlet.open_stream(timeout=2.0)

    print("\nListening for data (press Ctrl+C to stop)...")
    print("-" * 75)

    sample_counter = 0
    start_time = time.time()

    try:
        while True:
            # Check for Gaze sample
            sample, timestamp = gaze_inlet.pull_sample(timeout=0.05)
            if sample is not None:
                sample_counter += 1
                # Periodically print every 20 samples (~10 Hz in terminal)
                if sample_counter % 20 == 0:
                    if len(sample) == 12:
                        bino_x, bino_y, b_val = sample[0], sample[1], sample[2]
                        l_x, l_y, l_pupil, l_val = sample[3], sample[4], sample[5], sample[6]
                        r_x, r_y, r_pupil, r_val = sample[7], sample[8], sample[9], sample[10]
                        trig = int(sample[11])

                        print(
                            f"[Gaze #{sample_counter:05d} @ {timestamp:.3f}s] "
                            f"Bino: ({bino_x:.1f}, {bino_y:.1f}) | "
                            f"L: ({l_x:.1f}, {l_y:.1f}, d={l_pupil:.2f}mm) | "
                            f"R: ({r_x:.1f}, {r_y:.1f}, d={r_pupil:.2f}mm) | "
                            f"Trig: {trig}"
                        )
                    else:
                        print(f"[Gaze #{sample_counter:05d} @ {timestamp:.3f}s] Channels={len(sample)}, Trig={sample[-1]}")

            # Check for discrete Marker sample
            if marker_inlet is not None:
                marker_sample, marker_ts = marker_inlet.pull_sample(timeout=0.0)
                if marker_sample is not None:
                    print(f"\n>>> [MARKER EVENT @ {marker_ts:.3f}s] Tag = '{marker_sample[0]}' <<<\n")

    except KeyboardInterrupt:
        pass
    finally:
        elapsed = time.time() - start_time
        print("\n" + "=" * 75)
        print(f"Session finished. Received {sample_counter} gaze samples in {elapsed:.2f} seconds.")
        if elapsed > 0:
            print(f"Average throughput: {sample_counter / elapsed:.1f} samples/sec.")
        gaze_inlet.close_stream()
        if marker_inlet:
            marker_inlet.close_stream()


if __name__ == "__main__":
    main()
