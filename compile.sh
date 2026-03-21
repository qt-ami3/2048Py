#!/bin/bash
#2048Squared (title pending) copyright (c) 2026 River Knuuttila, common alias: Annie Valentine or aval. All Rights Reserved.
#Do not redistribute or reuse code without accrediting and explicit permission from author.
#Contact:
#+1 (808) 223 4780
#riverknuuttila2@outlook.com

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON="$SCRIPT_DIR/src/venv/bin/python3"
BUILD_DIR="$SCRIPT_DIR/build"

rm -f "$BUILD_DIR/CMakeCache.txt"
cd "$BUILD_DIR" \
  && cmake ../src/engine -Dpybind11_DIR=$("$PYTHON" -m pybind11 --cmakedir) \
  && make -j$(nproc) \
  && cp game2048_engine*.so ../src/
