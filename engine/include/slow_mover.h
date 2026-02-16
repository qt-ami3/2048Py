//2048Squared (title pending) copyright (c) 2026 River Knuuttila, common alias: Annie Valentine or aval. All Rights Reserved.
//Do not redistribute or reuse code without accrediting and explicit permission from author.
//Contact:
//+1 (808) 223 4780
//riverknuuttila2@outlook.com

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
