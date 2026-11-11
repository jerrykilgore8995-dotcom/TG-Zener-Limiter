#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p build-tests
for t in basic controls program autotrack detector_clean spectra embedded_memory; do
    g++ -std=c++17 -O3 "tests/test_${t}.cpp" -o "build-tests/test_${t}"
    "build-tests/test_${t}" reference/TGZener4Freq_THD2pct_InputScaled.bin > "build-tests/test_${t}.out"
    echo "PASS: ${t}"
done
