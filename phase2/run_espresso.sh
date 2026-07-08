#!/usr/bin/env bash
# run_espresso.sh
# ===============
# Run Espresso on all per-neuron PLA files in an input directory.
#
# Usage:
#   bash phase2/run_espresso.sh <pla_input_dir> <pla_output_dir> [espresso_flags]
#
# Example:
#   bash phase2/run_espresso.sh phase2/pla/ phase2/pla_min/
#   bash phase2/run_espresso.sh phase2/pla/ phase2/pla_min/ -Dso   # single-output exact

set -euo pipefail

INPUT_DIR="${1:?Usage: $0 <input_dir> <output_dir> [espresso_flags]}"
OUTPUT_DIR="${2:?Usage: $0 <input_dir> <output_dir> [espresso_flags]}"
ESPRESSO_FLAGS="${3:-}"       # optional extra flags, e.g. -Dso for exact minimization

# Check Espresso is installed
if ! command -v espresso &> /dev/null; then
    echo "ERROR: espresso not found in PATH."
    echo "Install with:"
    echo "  Ubuntu:  sudo apt-get install espresso"
    echo "  macOS:   brew install espresso"
    echo "  Source:  https://github.com/chipsalliance/espresso"
    exit 1
fi

mkdir -p "$OUTPUT_DIR"

PLA_FILES=("$INPUT_DIR"/neuron_*.pla)
if [ ${#PLA_FILES[@]} -eq 0 ]; then
    echo "No neuron_*.pla files found in $INPUT_DIR"
    exit 1
fi

echo "Running Espresso on ${#PLA_FILES[@]} PLA files"
echo "  Input:  $INPUT_DIR"
echo "  Output: $OUTPUT_DIR"
echo "  Flags:  '${ESPRESSO_FLAGS}'"
echo ""

PASS=0
FAIL=0

for pla_in in "$INPUT_DIR"/neuron_*.pla; do
    name=$(basename "$pla_in")
    pla_out="$OUTPUT_DIR/$name"

    # Count input product terms before minimization
    n_before=$(grep -c "^[01-]" "$pla_in" 2>/dev/null || echo "?")

    if espresso $ESPRESSO_FLAGS "$pla_in" > "$pla_out" 2>/dev/null; then
        n_after=$(grep -c "^[01-]" "$pla_out" 2>/dev/null || echo "?")
        echo "  $name: $n_before terms → $n_after terms"
        PASS=$((PASS + 1))
    else
        echo "  $name: FAILED"
        FAIL=$((FAIL + 1))
    fi
done

echo ""
echo "Done: $PASS succeeded, $FAIL failed"
echo "Minimized PLAs → $OUTPUT_DIR/"
