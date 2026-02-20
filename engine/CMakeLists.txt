#2048Squared (title pending) copyright (c) 2026 River Knuuttila, common alias: Annie Valentine or aval. All Rights Reserved.
#Do not redistribute or reuse code without accrediting and explicit permission from author.
#Contact:
#+1 (808) 223 4780
#riverknuuttila2@outlook.com

cmake_minimum_required(VERSION 3.15)
project(game2048_engine)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(pybind11 REQUIRED)

pybind11_add_module(game2048_engine
    src/bindings.cpp
    src/tile.cpp
    src/board.cpp
    src/passive.cpp
    src/movement.cpp
    src/game_engine.cpp
    src/passive_roller.cpp
    src/slow_mover.cpp
    src/random_mover.cpp
    src/slow_behavior.cpp
    src/contrarian_behavior.cpp
)

target_include_directories(game2048_engine PRIVATE include)

install(TARGETS game2048_engine DESTINATION ${CMAKE_SOURCE_DIR}/..)
