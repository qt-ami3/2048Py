//2048Squared (title pending) copyright (c) 2026 River Knuuttila, common alias: Annie Valentine or aval. All Rights Reserved.
//Do not redistribute or reuse code without accrediting and explicit permission from author.
//Contact:
//+1 (808) 223 4780
//riverknuuttila2@outlook.com

#pragma once

#include "movement.h"
#include "passive_roller.h"
#include "slow_mover.h"
#include "random_mover.h"
#include <vector>
#include <set>
#include <string>

struct TurnResult {
    std::vector<MoveInfo> moves;
    std::vector<MergeInfo> merges;
    std::set<std::pair<int,int>> bomb_destroyed;
    std::set<std::pair<int,int>> snail_bomb_kills;
    int points_gained = 0;
    std::pair<int,int> spawned_tile = {-1, -1};
    std::pair<int,int> spawned_snail = {-1, -1};
    bool board_changed = false;
    bool should_expand = false;
    std::string expand_direction;
    std::vector<PassiveCandidate> passive_candidates;
    std::vector<SlowMoverUpdate> slow_mover_updates;
    std::vector<RandomMoverUpdate> random_mover_updates;
    std::vector<MoveInfo> slow_tile_moves;
    std::vector<MergeInfo> slow_tile_merges;
};
