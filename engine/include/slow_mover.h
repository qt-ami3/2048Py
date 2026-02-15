#pragma once

#include "passive.h"

struct SlowMoverState {
    int current_row, current_col;
    int dest_row, dest_col;
    int dr, dc;      // direction step per turn (-1, 0, or +1)
    int value;
    PassiveType passive;
    bool active = true;
};

struct SlowMoverUpdate {
    int old_row, old_col;
    int new_row, new_col;
    int value;
    bool finished;
};
