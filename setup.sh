#!/usr/bin/env bash
# Install everything the pipeline needs. Idempotent -- safe to re-run.
#
# Written because the toolchain is four separate things from four places, one of
# which has to be built from source, and a fresh checkout can otherwise not run
# a single command in the README.
set -euo pipefail

say() { printf '  %-28s %s\n' "$1" "$2"; }
ESPRESSO_SRC="${ESPRESSO_SRC:-$HOME/.local/src/espresso-logic}"
PREFIX="${PREFIX:-/usr/local/bin}"

# root needs no sudo; non-root needs it and may not have it passwordless
if [ "$(id -u)" = 0 ]; then SUDO=""
elif command -v sudo >/dev/null 2>&1; then SUDO="sudo"
else SUDO=""; fi

echo "ECESRIP toolchain setup"
echo

# --- system packages -------------------------------------------------------
NEED=()
command -v iverilog >/dev/null || NEED+=(iverilog)
command -v yosys    >/dev/null || NEED+=(yosys)
command -v git      >/dev/null || NEED+=(git)
command -v make     >/dev/null || NEED+=(build-essential)

if [ ${#NEED[@]} -gt 0 ]; then
  say "installing" "${NEED[*]}"
  if command -v apt-get >/dev/null; then
    $SUDO apt-get update -qq
    $SUDO apt-get install -y -qq "${NEED[@]}"
  elif command -v brew >/dev/null; then
    brew install "${NEED[@]}"
  else
    echo "  no apt-get or brew; install manually: ${NEED[*]}" >&2; exit 1
  fi
fi
say "iverilog" "$(command -v iverilog || echo MISSING)"
say "yosys"    "$(command -v yosys    || echo MISSING)"

# --- python ---------------------------------------------------------------
# pip considers a requirement satisfied if a package of the right version is
# merely PRESENT. A distro numpy that cannot be imported still counts, so this
# tests the import and force-reinstalls on failure rather than trusting pip.
python3 -m pip install --quiet --disable-pip-version-check -r requirements.txt || true
if ! python3 -c 'import numpy, matplotlib' 2>/dev/null; then
  say "python deps" "broken install detected, reinstalling"
  python3 -m pip install --quiet --disable-pip-version-check \
      --ignore-installed --no-cache-dir -r requirements.txt
fi
python3 -c 'import numpy, matplotlib' 2>/dev/null \
  && say "python deps" "numpy $(python3 -c 'import numpy;print(numpy.__version__)')" \
  || { echo "  python deps still broken" >&2; exit 1; }

# --- espresso (no distro package; must be built) ---------------------------
if ! command -v espresso >/dev/null; then
  say "espresso" "building from source"
  mkdir -p "$(dirname "$ESPRESSO_SRC")"
  [ -d "$ESPRESSO_SRC" ] || git clone --depth 1 -q \
      https://github.com/classabbyamp/espresso-logic.git "$ESPRESSO_SRC"
  make -C "$ESPRESSO_SRC/espresso-src" -j"$(nproc 2>/dev/null || echo 2)" >/dev/null 2>&1
  $SUDO install -m755 "$ESPRESSO_SRC/bin/espresso" "$PREFIX/espresso"
fi
say "espresso" "$(command -v espresso || echo MISSING)"

echo
echo "Done. Run 'make check' to verify the toolchain end to end."
