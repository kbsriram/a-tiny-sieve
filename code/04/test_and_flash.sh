#!/usr/bin/env bash
#
# Flashes the basic diagnostic image to an ATtiny412 card on the jig,
# and then runs the MicroPython electrical validation checks via the Pico.
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AVR_SRC_DIR="${SCRIPT_DIR}/avr/src"
RPI_DIR="${SCRIPT_DIR}/rpi"
PORT="${PORT:-/dev/ttyUSB0}"

echo "=================================================="
echo " Stage 1: Flashing diagnostic image via UPDI"
echo " Port: ${PORT}"
echo "=================================================="

if [ ! -e "${PORT}" ]; then
  echo "Error: UPDI port '${PORT}' not found." >&2
  exit 1
fi

make -C "${AVR_SRC_DIR}" flash PORT="${PORT}"

echo ""
echo "=================================================="
echo " Stage 2: Running electrical self-test via Pico"
echo "=================================================="

# Brief settle time after reset
sleep 0.2

(
  cd "${RPI_DIR}"
  mpremote mount . run main.py "$@"
)
