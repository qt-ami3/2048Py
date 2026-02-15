#pragma once

#include "passive.h"

struct Tile {
    int value = 0;
    PassiveType passive = PassiveType::NONE;

    bool is_empty() const { return value == 0; }
    bool is_bomb() const { return value == -1; }
    bool is_numbered() const { return value > 0; }
    bool has_passive() const { return passive != PassiveType::NONE; }
};
