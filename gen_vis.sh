#!/bin/bash
# Generate visibility files for various telescope configurations

set -e  # Exit on error

# Create output directory
mkdir -p out

# Common parameters
SCRIPT_PATH="/Users/dev/Code/Karabo-Pipeline/karabo/examples/generate_visibility.py"
MIDPOINT_TIME="2000-01-01T12:00:00"
MID_FREQ="181e6"
FREQ_RES="80e3"

# Telescope configurations: "output_name|telescope|version"
TELESCOPES=(
    "mwa-ph1|MWA|1"
    "mwa-ph2-ext|MWA|2ext"
    "mwa-ph2-cmp|MWA|2"
    "ska-low-aa0.5|SKA-LOW-AA0.5|ska-ost-array-config-2.3.1"
    "ska-low-aa1|SKA-LOW-AA1|ska-ost-array-config-2.3.1"
    "ska-low-aa2|SKA-LOW-AA2|ska-ost-array-config-2.3.1"
    "ska-low-aastar|SKA-LOW-AAstar|ska-ost-array-config-2.3.1"
)

echo "Generating visibility files..."
echo "=============================="

TOTAL=${#TELESCOPES[@]}
COUNT=0

for config in "${TELESCOPES[@]}"; do
    COUNT=$((COUNT + 1))
    IFS='|' read -r output_name telescope version <<< "$config"

    echo "$COUNT/$TOTAL Generating $output_name..."
    docker run --rm -v "$PWD/out:/out" -v "$SCRIPT_PATH:/tmp/generate_visibility.py:ro" \
        sp5505:latest bash -lc \
        "python /tmp/generate_visibility.py \
        --telescope=$telescope --telescope-version=$version \
        --midpoint-time=$MIDPOINT_TIME \
        --mid-frequency=$MID_FREQ \
        --frequency-resolution=$FREQ_RES \
        --out=/out/${output_name}.MS" 2>&1 | tail -3
done

echo ""
echo "=============================="
echo "All visibility files generated!"
echo "Output directory: $PWD/out"
echo ""
echo "Generated files:"
ls -lh out/*.MS 2>/dev/null | awk '{print "  " $9 " (" $5 ")"}' || echo "  No files generated"
