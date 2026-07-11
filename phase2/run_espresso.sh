#!/usr/bin/env bash
# run_espresso.sh
# ===============
# Run Espresso on all per-neuron PLA files in an input directory.
#
# Usage:
#   bash phase2/run_espresso.sh <pla_input_dir> <pla_output_dir> [espresso_flags] [espresso_binary]
#
# Examples:
#   # System-installed espresso
#   bash phase2/run_espresso.sh phase2/pla/ phase2/pla_min/
#
#   # Multi-output shared minimization (shared product terms across neurons)
#   bash phase2/run_espresso.sh phase2/pla/ phase2/pla_min/ -Dso_both
#
#   # UCSD server: espresso binary in home directory
#   bash phase2/run_espresso.sh phase2/pla/ phase2/pla_min/ "" ~/espresso
#   bash phase2/run_espresso.sh phase2/pla/ phase2/pla_min/ -Dso_both ~/espresso
#
#   # Also works via ESPRESSO env var:
#   ESPRESSO=~/espresso bash phase2/run_espresso.sh phase2/pla/ phase2/pla_min/

set -euo pipefail

INPUT_DIR="${1:?Usage: $0 <input_dir> <output_dir> [espresso_flags] [espresso_binary]}"
OUTPUT_DIR="${2:?Usage: $0 <input_dir> <output_dir> [espresso_flags] [espresso_binary]}"
ESPRESSO_FLAGS="${3:-}"
# Binary: arg 4 > ESPRESSO env var > 'espresso' in PATH
ESPRESSO_BIN="${4:-${ESPRESSO:-espresso}}"

# Resolve ~ in path if present
ESPRESSO_BIN="${ESPRESSO_BIN/#\~/$HOME}"

# Verify binary exists and is executable
if ! command -v "$ESPRESSO_BIN" &> /dev/null && [ ! -x "$ESPRESSO_BIN" ]; then
    echo "ERROR: espresso not found: '$ESPRESSO_BIN'"
    echo ""
    echo "Options:"
    echo "  System install:  sudo apt-get install espresso"
    echo "  UCSD server:     bash $0 <in> <out> \"\" ~/espresso"
    echo "  Env var:         ESPRESSO=~/espresso bash $0 <in> <out>"
    exit 1
fi

mkdir -p "$OUTPUT_DIR"

# Collect PLA files (per-neuron + combined if present)
ALL_PLA_FILES=()
if ls "$INPUT_DIR"/neuron_*.pla &>/dev/null; then
    ALL_PLA_FILES+=("$INPUT_DIR"/neuron_*.pla)
fi
if [ -f "$INPUT_DIR/combined.pla" ]; then
    ALL_PLA_FILES+=("$INPUT_DIR/combined.pla")
fi

if [ ${#ALL_PLA_FILES[@]} -eq 0 ]; then
    echo "No PLA files found in $INPUT_DIR"
    exit 1
fi

echo "Running Espresso on ${#ALL_PLA_FILES[@]} PLA files"
echo "  Binary: $ESPRESSO_BIN"
echo "  Input:  $INPUT_DIR"
echo "  Output: $OUTPUT_DIR"
echo "  Flags:  '${ESPRESSO_FLAGS}'"
echo ""

PASS=0
FAIL=0
TERMS_BEFORE=0
TERMS_AFTER=0

for pla_in in "${ALL_PLA_FILES[@]}"; do
    name=$(basename "$pla_in")
    pla_out="$OUTPUT_DIR/$name"

    n_before=$(grep -c "^[01-]" "$pla_in" 2>/dev/null || echo 0)
    TERMS_BEFORE=$((TERMS_BEFORE + n_before))

    if "$ESPRESSO_BIN" $ESPRESSO_FLAGS "$pla_in" > "$pla_out" 2>/dev/null; then
        n_after=$(grep -c "^[01-]" "$pla_out" 2>/dev/null || echo 0)
        TERMS_AFTER=$((TERMS_AFTER + n_after))
        echo "  $name: $n_before terms → $n_after terms"
        PASS=$((PASS + 1))
    else
        echo "  $name: FAILED"
        FAIL=$((FAIL + 1))
    fi
done

echo ""
echo "Done: $PASS succeeded, $FAIL failed"
if [ $TERMS_BEFORE -gt 0 ]; then
    echo "Total terms: $TERMS_BEFORE → $TERMS_AFTER  ($(( (TERMS_BEFORE - TERMS_AFTER) * 100 / TERMS_BEFORE ))% reduction)"
fi
echo "Minimized PLAs → $OUTPUT_DIR/"
