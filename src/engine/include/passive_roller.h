//2048Squared (title pending) copyright (c) 2026 River Knuuttila, common alias: Annie Valentine or aval. All Rights Reserved.
//Do not redistribute or reuse code without accrediting and explicit permission from author.
//Contact:
//+1 (808) 223 4780
//riverknuuttila2@outlook.com

#pragma once

#include "board.h"
#include "movement.h"
#include <vector>
#include <set>
#include <random>

struct PassiveCandidate {
    int row, col;
    int tile_value;
};

class PassiveRoller {
public:
    PassiveRoller();

    // Roll for passive triggers based on merge results.
    // excluded_positions = merge destinations + spawned tile + slow mover positions
    std::vector<PassiveCandidate> roll(
        const Board& board,
        const std::vector<MergeInfo>& merges,
        const std::set<std::pair<int,int>>& excluded_positions
    );

private:
    std::mt19937 rng_;
};
