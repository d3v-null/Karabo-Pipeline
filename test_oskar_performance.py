#!/usr/bin/env python3
"""Simple OSKAR simulation to test performance with/without OpenCL."""

import os
import sys
import time
import shutil
import oskar

print("=" * 60)
print("OSKAR Performance Test")
print("=" * 60)
print(f"OSKAR version: {oskar.__version__}")
print(f"Python version: {sys.version}")
print("=" * 60)

# Get output MS name from command line or use default
output_ms = sys.argv[1] if len(sys.argv) > 1 else "test_simulation.ms"
ra_deg = 20.0
dec_deg = -30.0
start_freq_hz = 100e6  # 100 MHz
freq_inc_hz = 1e6      # 1 MHz channel width
num_channels = 16
num_time_steps = 60
obs_length_sec = 3600.0  # 1 hour
num_stations = 30

print("\nSimulation Parameters:")
print(f"  Output MS: {output_ms}")
print(f"  Phase centre: RA={ra_deg}°, Dec={dec_deg}°")
print(f"  Frequency: {start_freq_hz/1e6:.1f} MHz")
print(f"  Channels: {num_channels}")
print(f"  Time steps: {num_time_steps}")
print(f"  Observation length: {obs_length_sec/3600:.1f} hours")
print(f"  Stations: {num_stations}")
print("=" * 60)

# Clean up any existing output (measurement sets are directories)
if os.path.exists(output_ms):
    print(f"\nRemoving existing {output_ms}...")
    if os.path.isdir(output_ms):
        shutil.rmtree(output_ms)
    else:
        os.remove(output_ms)
    print(f"  ✓ Cleaned up existing output")

# Create simple sky model (3x3 grid = 9 point sources)
print("\n[1/5] Creating sky model...")
sky = oskar.Sky.generate_grid(ra_deg, dec_deg, 3, 1, 3.0, 1.0)
print(f"  Created {sky.num_sources} sources")

# Create telescope model (simple circular array)
print("\n[2/5] Creating telescope model...")
tel = oskar.Telescope()
tel.set_channel_bandwidth(freq_inc_hz)
tel.set_time_average(obs_length_sec / num_time_steps)
tel.set_pol_mode("Scalar")

# Generate station positions in a circle
print(f"  Generating {num_stations} stations in circular configuration...")
import numpy as np
radius_m = 1000.0  # 1 km radius
angles = np.linspace(0, 2 * np.pi, num_stations, endpoint=False)
x = radius_m * np.cos(angles)
y = radius_m * np.sin(angles)
z = np.zeros_like(x)
# Set reference position (Perth, Australia as example)
tel.set_position(116.764, -26.703, 0.0)  # lon, lat, alt
tel.set_station_coords_enu(0.0, 0.0, 0.0, x, y, z)
print(f"  Array diameter: {2*radius_m/1000:.2f} km")

# Create interferometer simulator
print("\n[3/5] Setting up interferometer simulator...")
sim = oskar.Interferometer()
sim.set_sky_model(sky)
sim.set_telescope_model(tel)
sim.set_observation_frequency(start_freq_hz, freq_inc_hz, num_channels)
sim.set_observation_time(57000.0, obs_length_sec, num_time_steps)
# Set the phase center for the observation
tel.set_phase_centre(ra_deg, dec_deg)
sim.set_output_measurement_set(output_ms)

print(f"  ✓ Interferometer configured")

# Run simulation with timing
print("\n[4/5] Running simulation...")
start_timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
print(f"  Started at: {start_timestamp}")
start_time = time.time()

try:
    sim.run()
    elapsed = time.time() - start_time

    end_timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    print(f"  Completed at: {end_timestamp}")
    print(f"\n{'=' * 60}")
    print(f"SIMULATION TIME: {elapsed:.2f} seconds ({elapsed/60:.2f} minutes)")
    print(f"{'=' * 60}")

    # Verify output
    print("\n[5/5] Verifying output...")
    if os.path.exists(output_ms):
        if os.path.isdir(output_ms):
            import subprocess
            try:
                result = subprocess.run(
                    ["du", "-sh", output_ms],
                    capture_output=True,
                    text=True,
                    check=True
                )
                size = result.stdout.split()[0]
                print(f"  ✓ Measurement Set created successfully")
                print(f"  Size: {size}")
                print(f"  Location: {os.path.abspath(output_ms)}")

                # Count files in MS to verify it's complete
                num_files = sum(len(files) for _, _, files in os.walk(output_ms))
                print(f"  Files: {num_files}")
            except Exception as e:
                print(f"  ✓ Measurement Set created: {output_ms}")
                print(f"  (Could not get detailed stats: {e})")
        else:
            print(f"  ⚠ Output exists but is not a directory: {output_ms}")
    else:
        print(f"  ✗ Output file not found: {output_ms}")
        sys.exit(1)

    print("\n✓ Simulation completed successfully!")
    print(f"✓ Measurement Set written to: {output_ms}")
    sys.exit(0)

except Exception as e:
    elapsed = time.time() - start_time
    print(f"\n✗ Simulation failed after {elapsed:.2f} seconds")
    print(f"  Error: {e}")
    sys.exit(1)

