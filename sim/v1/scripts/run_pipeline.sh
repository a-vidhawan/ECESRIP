#!/usr/bin/env bash
# =============================================================================
# run_pipeline.sh
# =============================================================================
# End-to-end Hopfield pipeline:  patterns → weights → truth tables → SV RTL
#
# Usage
# -----
#   ./scripts/run_pipeline.sh [OPTIONS]
#
# Options
#   --neurons  N      Number of neurons (default: 8)
#   --patterns FILE   Pattern file (default: generate N random ones)
#   --P        P      Number of random patterns to generate (default: 3)
#   --rule     RULE   hebbian | storkey (default: hebbian)
#   --seed     SEED   RNG seed (default: 42)
#   --out      DIR    Output directory (default: build_<N>)
#   --no-hf           Disable hazard-free augmentation
#   --help            Print this help
#
# Dependencies
# ------------
#   Python 3.9+ with numpy  (pip install numpy)
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_DIR="$SCRIPT_DIR/../python"

# --- Defaults ----------------------------------------------------------------
N=8
P=3
RULE=hebbian
SEED=42
PATTERN_FILE=""
OUT_DIR=""
HAZARD_FREE="--hazard-free"

# --- Argument parsing --------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        --neurons)  N="$2";            shift 2 ;;
        --patterns) PATTERN_FILE="$2"; shift 2 ;;
        --P)        P="$2";            shift 2 ;;
        --rule)     RULE="$2";         shift 2 ;;
        --seed)     SEED="$2";         shift 2 ;;
        --out)      OUT_DIR="$2";      shift 2 ;;
        --no-hf)    HAZARD_FREE="--no-hazard-free"; shift ;;
        --help)
            sed -n '3,30p' "$0"
            exit 0
            ;;
        *) echo "Unknown option: $1" >&2; exit 1 ;;
    esac
done

[[ -z "$OUT_DIR" ]] && OUT_DIR="build_${N}"

# --- Run pipeline ------------------------------------------------------------
echo "============================================"
echo " Hopfield Hardware Pipeline"
echo " N=$N  P=$P  rule=$RULE  seed=$SEED"
echo " output dir: $OUT_DIR"
echo "============================================"

EXTRA=""
[[ -n "$PATTERN_FILE" ]] && EXTRA="--patterns $PATTERN_FILE"

python3 "$PYTHON_DIR/pipeline.py" \
    --N       "$N"        \
    --P       "$P"        \
    --rule    "$RULE"     \
    --seed    "$SEED"     \
    --out     "$OUT_DIR"  \
    $EXTRA                \
    $HAZARD_FREE

echo ""
echo "Pipeline complete.  Artefacts in: $OUT_DIR"
echo ""
echo "Next steps:"
echo "  1. Copy generated SV to RTL:  cp $OUT_DIR/rtl/neuron_logic_generated.sv rtl/"
echo "  2. Simulate:  cd rtl && vsim -do 'do tb/tb_neuron_update.sv'"
echo "  3. Synthesize: vivado -mode batch -source scripts/synth_vivado.tcl"
