#!/usr/bin/env python3
"""
Minimalist hyperbeam GPU test script.

docker build -t hyperbeam_cuda_86 -f hyperbeam.Dockerfile .
docker run --gpus all --rm -v /home/dev/src/Karabo-Pipeline/test_hyperbeam_gpu.py:/test_hyperbeam_gpu.py hyperbeam_cuda_86 python /test_hyperbeam_gpu.py
"""

import time
import numpy as np
import mwa_hyperbeam
import os

# Setup
beam_file = os.environ.get('MWA_BEAM_FILE', '/opt/mwa_full_embedded_element_pattern.h5')
beam = mwa_hyperbeam.FEEBeam(beam_file)

# Test data
n = 10000
az = np.linspace(0, 0.9 * np.pi, n)
za = np.linspace(0.1, 0.9 * np.pi / 2, n)
freq = [167000000]
delays = np.zeros(16, dtype=np.uint32)
amps = np.ones(16, dtype=np.float64)

# CPU test
start = time.time()
jones_cpu = beam.calc_jones_array(az, za, freq[0], delays, amps, True)
cpu_time = time.time() - start

# GPU test
delays_gpu = np.zeros((1, 16), dtype=np.uint).flatten()
amps_gpu = np.ones((1, 16)).flatten()
start = time.time()
jones_gpu = beam.calc_jones_gpu(az, za, freq, delays_gpu, amps_gpu, True, None, False)
gpu_time = time.time() - start

# Results
print(f"CPU: {cpu_time:.3f}s | GPU: {gpu_time:.3f}s | Speedup: {cpu_time/gpu_time:.1f}x")
print(f"GPU shape: {jones_gpu.shape} | ✅ Success!")
