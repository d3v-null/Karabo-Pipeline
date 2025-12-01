# OSKAR Performance Testing: OpenCL vs CPU-only

This directory contains scripts to benchmark OSKAR performance with and without OpenCL support.

## Quick Start

### Option 1: Automated Comparison (Recommended)

Run both tests and compare results automatically:

```bash
./compare_oskar_performance.sh
```

This will:
1. Run the simulation in CPU-only mode (`oskar:2.11.1`)
2. Run the same simulation with OpenCL (`oskar:2.11.1_opencl`)
3. Compare the results and show speedup/slowdown

### Option 2: Manual Testing

Test individual images with the standalone script:

**CPU-only version:**
```bash
docker run --rm -it \
  -v "$(pwd)/test_oskar_performance.py:/workspace/test_oskar_performance.py:ro" \
  -v "/tmp/oskar_results:/results" \
  -w /results \
  oskar:2.11.1 bash -c '
    . /opt/spack/share/spack/setup-env.sh && \
    spack env activate /opt/spack_env && \
    python3 /workspace/test_oskar_performance.py my_simulation.ms
  '
```

**OpenCL version:**
```bash
docker run --rm -it \
  -v "$(pwd)/test_oskar_performance.py:/workspace/test_oskar_performance.py:ro" \
  -v "/tmp/oskar_results:/results" \
  -w /results \
  oskar:2.11.1_opencl bash -c '
    . /opt/spack/share/spack/setup-env.sh && \
    spack env activate /opt/spack_env && \
    python3 /workspace/test_oskar_performance.py my_simulation.ms
  '
```

**Run locally (outside Docker):**
```bash
./test_oskar_performance.py output_name.ms
```

## Test Simulation Parameters

The test creates a simple but realistic simulation:

- **Sky Model**: 9 point sources in a grid (3×3)
- **Telescope**: 30 stations in a circular array (1 km radius)
- **Observation**: 1 hour, 60 time steps
- **Frequency**: 100 MHz with 16 × 1 MHz channels
- **Output**: Measurement Set format

## Expected Results

Performance will vary based on:
- CPU architecture (x86_64 vs ARM)
- Number of CPU cores
- OpenCL implementation (pocl, vendor drivers)
- Memory bandwidth

### Typical Performance

**On ARM with pocl (software OpenCL):**
- CPU-only: May be faster for small simulations
- OpenCL: May have initialization overhead but scale better

**On x86_64 with GPU OpenCL:**
- CPU-only: Baseline performance
- OpenCL with GPU: Significant speedup (2-10x)

## Files

- `test_oskar_performance.py` - Standalone Python test script
  - Usage: `./test_oskar_performance.py [output_ms_name]`
  - Default output: `test_simulation.ms`
  - Automatically cleans up existing output before running
- `compare_oskar_performance.sh` - Automated comparison script
  - Creates separate measurement sets: `cpu_test.ms` and `opencl_test.ms`
  - Saves results to `/tmp/oskar_perf_test_*`
- `OSKAR_PERFORMANCE_TEST.md` - This file

## Troubleshooting

### OpenCL image not built yet

If you get "Image not found" error for `oskar:2.11.1_opencl`:

```bash
# Build OpenCL-enabled image
docker build -f oskar.Dockerfile \
  --build-arg OSKAR_VERSION=2.11.1 \
  -t oskar:2.11.1_opencl .
```

Make sure the Dockerfile specifies `+opencl` variant:
```dockerfile
spack add 'oskar@2.11.1+opencl+casacore+python+hdf5~cuda~openmp~mpi'
```

### Permission errors

The script uses `/tmp` for results. If you have permission issues:

```bash
# Edit compare_oskar_performance.sh and change:
RESULTS_DIR="/tmp/oskar_perf_test_$(date +%s)"
# to your preferred directory
```

### Out of memory

Reduce the simulation size by editing the test script:
- Reduce `num_stations` (currently 30)
- Reduce `num_time_steps` (currently 60)
- Reduce `num_channels` (currently 16)

## Notes

- The first run may be slower due to Docker image pull/cache
- Results are saved to `/tmp/oskar_perf_test_*` directories
- Both simulations use identical parameters for fair comparison
- Measurement Sets are written to verify full pipeline functionality

