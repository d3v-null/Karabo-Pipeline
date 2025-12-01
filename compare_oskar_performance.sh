#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_SCRIPT="$SCRIPT_DIR/test_oskar_performance.py"

echo "============================================================"
echo "OSKAR Performance Comparison: OpenCL vs CPU-only"
echo "============================================================"
echo ""

# Check if test script exists
if [ ! -f "$TEST_SCRIPT" ]; then
    echo "Error: Test script not found: $TEST_SCRIPT"
    exit 1
fi

# Check if both images exist
echo "Checking Docker images..."
if ! docker image inspect oskar:2.11.1 >/dev/null 2>&1; then
    echo "Error: Image 'oskar:2.11.1' not found"
    echo "Please build with: docker build -f oskar.Dockerfile -t oskar:2.11.1 ."
    exit 1
fi

if ! docker image inspect oskar:2.11.1_opencl >/dev/null 2>&1; then
    echo "Error: Image 'oskar:2.11.1_opencl' not found"
    echo "Please build with OpenCL variant first"
    exit 1
fi

echo "✓ Both images found"
echo "✓ Test script: $TEST_SCRIPT"
echo ""

# Create temporary directory for results
RESULTS_DIR="/tmp/oskar_perf_test_$(date +%s)"
mkdir -p "$RESULTS_DIR"
echo "Results will be saved to: $RESULTS_DIR"
echo ""

# Test 1: CPU-only version
echo "============================================================"
echo "TEST 1: CPU-only (oskar:2.11.1)"
echo "============================================================"
START_CPU=$(date +%s)

docker run --rm \
    --user root \
    -v "$TEST_SCRIPT:/workspace/test_oskar_performance.py:ro" \
    -v "$RESULTS_DIR:/results" \
    -w /results \
    oskar:2.11.1 \
    bash -c '
        . /opt/spack/share/spack/setup-env.sh
        spack env activate /opt/spack_env

        # Run the test with CPU-specific MS name
        python3 /workspace/test_oskar_performance.py cpu_test.ms

        # Check if MS was created
        if [ -d cpu_test.ms ]; then
            echo "CPU_TEST_COMPLETED" > cpu_success.flag
        fi
    ' 2>&1 | tee "$RESULTS_DIR/cpu_log.txt"

END_CPU=$(date +%s)
CPU_WALL_TIME=$((END_CPU - START_CPU))

# Extract simulation time from log (portable version without -P)
CPU_SIM_TIME=$(grep "SIMULATION TIME:" "$RESULTS_DIR/cpu_log.txt" | grep -oE '[0-9]+\.[0-9]+' | head -1 || echo "0")

echo ""
echo "CPU-only test completed in ${CPU_WALL_TIME}s (wall time)"
echo ""

# Test 2: OpenCL version
echo "============================================================"
echo "TEST 2: OpenCL-enabled (oskar:2.11.1_opencl)"
echo "============================================================"
START_OPENCL=$(date +%s)

docker run --rm \
    --user root \
    -v "$TEST_SCRIPT:/workspace/test_oskar_performance.py:ro" \
    -v "$RESULTS_DIR:/results" \
    -w /results \
    oskar:2.11.1_opencl \
    bash -c '
        . /opt/spack/share/spack/setup-env.sh
        spack env activate /opt/spack_env

        # Run the test with OpenCL-specific MS name
        python3 /workspace/test_oskar_performance.py opencl_test.ms

        # Check if MS was created
        if [ -d opencl_test.ms ]; then
            echo "OPENCL_TEST_COMPLETED" > opencl_success.flag
        fi
    ' 2>&1 | tee "$RESULTS_DIR/opencl_log.txt"

END_OPENCL=$(date +%s)
OPENCL_WALL_TIME=$((END_OPENCL - START_OPENCL))

# Extract simulation time from log (portable version without -P)
OPENCL_SIM_TIME=$(grep "SIMULATION TIME:" "$RESULTS_DIR/opencl_log.txt" | grep -oE '[0-9]+\.[0-9]+' | head -1 || echo "0")

echo ""
echo "OpenCL test completed in ${OPENCL_WALL_TIME}s (wall time)"
echo ""

# Display results
echo "============================================================"
echo "PERFORMANCE COMPARISON RESULTS"
echo "============================================================"
echo ""
echo "CPU-only (oskar:2.11.1):"
echo "  Simulation time: ${CPU_SIM_TIME}s"
echo "  Wall time:       ${CPU_WALL_TIME}s"
if [ -f "$RESULTS_DIR/cpu_success.flag" ]; then
    echo "  Status:          ✓ SUCCESS"
else
    echo "  Status:          ✗ FAILED"
fi
echo ""
echo "OpenCL-enabled (oskar:2.11.1_opencl):"
echo "  Simulation time: ${OPENCL_SIM_TIME}s"
echo "  Wall time:       ${OPENCL_WALL_TIME}s"
if [ -f "$RESULTS_DIR/opencl_success.flag" ]; then
    echo "  Status:          ✓ SUCCESS"
else
    echo "  Status:          ✗ FAILED"
fi
echo ""

# Calculate speedup if both completed
if [ -f "$RESULTS_DIR/cpu_success.flag" ] && [ -f "$RESULTS_DIR/opencl_success.flag" ]; then
    if command -v python3 >/dev/null 2>&1 && [ "$CPU_SIM_TIME" != "0" ] && [ "$OPENCL_SIM_TIME" != "0" ]; then
        SPEEDUP=$(python3 -c "print(f'{float($CPU_SIM_TIME) / float($OPENCL_SIM_TIME):.2f}')" 2>/dev/null || echo "N/A")

        if [ "$SPEEDUP" != "N/A" ]; then
            echo "Performance comparison:"
            if python3 -c "exit(0 if float($SPEEDUP) > 1.05 else 1)" 2>/dev/null; then
                PERCENT=$(python3 -c "print(f'{(1 - float($OPENCL_SIM_TIME) / float($CPU_SIM_TIME)) * 100:.1f}')")
                echo "  ⚡ OpenCL is ${SPEEDUP}x faster (${PERCENT}% time reduction)"
            elif python3 -c "exit(0 if float($SPEEDUP) < 0.95 else 1)" 2>/dev/null; then
                SLOWDOWN=$(python3 -c "print(f'{float($OPENCL_SIM_TIME) / float($CPU_SIM_TIME):.2f}')")
                PERCENT_SLOWER=$(python3 -c "print(f'{(float($OPENCL_SIM_TIME) / float($CPU_SIM_TIME) - 1) * 100:.1f}')")
                echo "  ⚠️  OpenCL is ${SLOWDOWN}x slower (${PERCENT_SLOWER}% time increase)"
            else
                echo "  ≈ Performance is equivalent (within 5%)"
            fi
        fi
    fi
fi

echo ""
echo "Output files saved to: $RESULTS_DIR"
echo "  Logs:"
echo "    CPU:    cpu_log.txt"
echo "    OpenCL: opencl_log.txt"
echo "  Measurement Sets:"
if [ -d "$RESULTS_DIR/cpu_test.ms" ]; then
    CPU_SIZE=$(du -sh "$RESULTS_DIR/cpu_test.ms" 2>/dev/null | cut -f1)
    echo "    CPU:    cpu_test.ms (${CPU_SIZE})"
else
    echo "    CPU:    cpu_test.ms (not created)"
fi
if [ -d "$RESULTS_DIR/opencl_test.ms" ]; then
    OPENCL_SIZE=$(du -sh "$RESULTS_DIR/opencl_test.ms" 2>/dev/null | cut -f1)
    echo "    OpenCL: opencl_test.ms (${OPENCL_SIZE})"
else
    echo "    OpenCL: opencl_test.ms (not created)"
fi
echo "============================================================"
