#!/bin/bash
# Task 3: re-run the (unmodified) gate_level_hazard.py at N=64, M=8, radius 2
# across delay scales 1, 20, 100. The script always writes
# clockless/results/gate_level_hazard.json, so we snapshot it after each run
# into phase8_consolidation/results/ and restore the original at the end.
set -u
CL=/home/user/ECESRIP/phase2/clockless
OUT=/home/user/ECESRIP/phase2/phase8_consolidation/results
export ESPRESSO="${ESPRESSO:-/tmp/claude-0/-home-user-ECESRIP/34c74a44-9001-565a-8629-44b3228b7c84/scratchpad/espresso-logic/bin/espresso}"

cp "$CL/results/gate_level_hazard.json" "$OUT/.gl_orig.json"

for SC in 1 20 100; do
  echo "=============== delay-scale=$SC ==============="
  T0=$SECONDS
  python3 "$CL/gate_level_hazard.py" \
      --N 64 --M 8 --radius 2 --trials 40 --seed 11 --delay-scale "$SC" \
      2>&1 | tee "$OUT/gate_hazard_N64_scale${SC}.log"
  echo "elapsed $((SECONDS-T0))s" | tee -a "$OUT/gate_hazard_N64_scale${SC}.log"
  if [ -f "$CL/results/gate_level_hazard.json" ]; then
    cp "$CL/results/gate_level_hazard.json" "$OUT/gate_hazard_N64_scale${SC}.json"
  fi
done

cp "$OUT/.gl_orig.json" "$CL/results/gate_level_hazard.json"
rm -f "$OUT/.gl_orig.json"
echo "TASK3 DONE"
