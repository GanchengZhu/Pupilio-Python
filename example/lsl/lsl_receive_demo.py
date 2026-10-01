# -*- coding: utf-8 -*-
# Copyright (c) 2026, Hangzhou DeepGaze Science and Technology Co., Ltd
# All Rights Reserved
#
# DESCRIPTION:
# Receiver and verification tool for Pupilio LabStreamingLayer (LSL) streams.
# Discovers 'Pupilio_Gaze' and 'Pupilio_Markers' streams on the local network,
# parses XML metadata (channels, units), and prints incoming samples in real time.
#
# Requires: pip install pylsl
#
# Author: Gancheng Zhu
# Last updated: 6/21/2026 by Zhiguo Wang

import sys
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
    if channels_node.empty():
        return

    print("Channel Specifications:")
    ch = channels_node.child("channel")
    idx = 0
    while not ch.empty():
        label = ch.child_value("label")
        eye = ch.child_value("eye")
        unit = ch.child_value("unit")
        ch_type = ch.child_value("type")
        print(f"  [{idx:02d}] {label:<16} "
              f"(eye: {eye:<5}, type: {ch_type:<14}, unit: {unit})")
        ch = ch.next_sibling("channel")
        idx += 1


def format_gaze_sample(sample, timestamp, counter, start_time):
    """Format one gaze sample for terminal output."""
    elapsed = timestamp - start_time
    n = len(sample)

    if n == 12:
        bino_x, bino_y, _b_val = sample[0], sample[1], sample[2]
        l_x, l_y, l_pupil, _l_val = sample[3], sample[4], sample[5], sample[6]
        r_x, r_y, r_pupil, _r_val = sample[7], sample[8], sample[9], sample[10]
        trig = int(sample[11])
        return (
            f"[Gaze #{counter:05d} @ +{elapsed:7.3f}s] "
            f"Bino: ({bino_x:7.1f}, {bino_y:7.1f}) | "
            f"L: ({l_x:7.1f}, {l_y:7.1f}, d={l_pupil:5.2f}mm) | "
            f"R: ({r_x:7.1f}, {r_y:7.1f}, d={r_pupil:5.2f}mm) | "
            f"Trig: {trig}"
        )

    # Non-standard channel count (e.g. full mode): print a compact line
    trig = sample[-1] if n > 0 else "?"
    return (
        f"[Gaze #{counter:05d} @ +{elapsed:7.3f}s] "
        f"Channels={n}, Trig={trig}"
    )


def main():
    print("=== Pupilio LSL Stream Receiver & Verification ===")
    print("Searching for Pupilio LSL streams on the network...")

    # 1. Resolve Gaze Stream
    gaze_streams = pylsl.resolve_byprop("type", "Gaze", timeout=5.0)
    if not gaze_streams:
        print("No 'Gaze' stream found! "
              "Make sure Pupilio with LSL enabled is running.")
        sys.exit(1)

    gaze_info = gaze_streams[0]
    print(f"\nFound Gaze Stream: '{gaze_info.name()}' "
          f"on host: {gaze_info.hostname()}")
    print_stream_metadata(gaze_info)
    gaze_inlet = pylsl.StreamInlet(gaze_info)
    gaze_inlet.open_stream(timeout=2.0)

    # 2. Resolve Marker Stream (optional)
    marker_streams = pylsl.resolve_byprop("type", "Markers", timeout=2.0)
    marker_inlet = None
    if marker_streams:
        marker_info = marker_streams[0]
        print(f"\nFound Marker Stream: '{marker_info.name()}'")
        marker_inlet = pylsl.StreamInlet(marker_info)
        marker_inlet.open_stream(timeout=2.0)
    else:
        print("\nNo 'Markers' stream found (optional, continuing without it).")

    print("\nListening for data (press Ctrl+C to stop)...")
    print("-" * 75)

    sample_counter = 0
    marker_counter = 0
    wall_start = time.time()
    lsl_start = None

    try:
        while True:
            # --- Pull gaze: block briefly, then drain all queued samples ---
            sample, timestamp = gaze_inlet.pull_sample(timeout=0.05)
            while sample is not None:
                if lsl_start is None:
                    lsl_start = timestamp
                sample_counter += 1

                # Print every 20th sample (~10 Hz in terminal at 200 Hz input)
                if sample_counter % 20 == 0:
                    print(format_gaze_sample(
                        sample, timestamp, sample_counter, lsl_start
                    ))

                sample, timestamp = gaze_inlet.pull_sample(timeout=0.0)

            # --- Pull markers: drain all queued events every iteration ---
            if marker_inlet is not None:
                m_sample, m_ts = marker_inlet.pull_sample(timeout=0.0)
                while m_sample is not None:
                    marker_counter += 1
                    print(f"\n>>> [MARKER #{marker_counter} "
                          f"@ {m_ts:.3f}s] Tag = '{m_sample[0]}' <<<\n")
                    m_sample, m_ts = marker_inlet.pull_sample(timeout=0.0)

    except KeyboardInterrupt:
        pass
    finally:
        elapsed = time.time() - wall_start
        print("\n" + "=" * 75)
        print(f"Session finished after {elapsed:.2f} seconds.")
        print(f"  Gaze samples:  {sample_counter}")
        print(f"  Marker events: {marker_counter}")
        if elapsed > 0:
            print(f"  Average gaze throughput: "
                  f"{sample_counter / elapsed:.1f} samples/sec")
        gaze_inlet.close_stream()
        if marker_inlet:
            marker_inlet.close_stream()


if __name__ == "__main__":
    main()
