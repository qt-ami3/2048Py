#!/bin/bash
#2048Squared (title pending) copyright (c) 2026 River Knuuttila, common alias: Annie Valentine or aval. All Rights Reserved.
#Do not redistribute or reuse code without accrediting and explicit permission from author.
#Contact:
#+1 (808) 223 4780
#riverknuuttila2@outlook.com

cd "$(dirname "$0")/build" \
  && cmake ../engine -Dpybind11_DIR=$(python3 -m pybind11 --cmakedir) \
  && make -j$(nproc) \
  && cp game2048_engine*.so ../
