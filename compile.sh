#!/bin/bash
cd "$(dirname "$0")/build" \
  && cmake ../engine -Dpybind11_DIR=$(python3 -m pybind11 --cmakedir) \
  && make -j$(nproc) \
  && cp game2048_engine*.so ../
