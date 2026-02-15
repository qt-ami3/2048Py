#pragma once

#include "board.h"
#include "slow_mover.h"
#include <vector>
#include <set>
#include <utility>

struct MoveInfo {
    int start_row, start_col;
    int end_row, end_col;
    int value;
};

struct MergeInfo {
    int row, col;
    int new_value;
};

struct MoveResult {
    std::vector<MoveInfo> moves;
    std::vector<MergeInfo> merges;
    std::set<std::pair<int,int>> bomb_destroyed;
    bool board_changed = false;
};

namespace movement {

MoveResult move_left(Board& board,
                     const std::set<std::pair<int,int>>& frozen,
                     const std::vector<SlowMoverState>& slow_movers);

MoveResult move_right(Board& board,
                      const std::set<std::pair<int,int>>& frozen,
                      const std::vector<SlowMoverState>& slow_movers);

MoveResult move_up(Board& board,
                   const std::set<std::pair<int,int>>& frozen,
                   const std::vector<SlowMoverState>& slow_movers);

MoveResult move_down(Board& board,
                     const std::set<std::pair<int,int>>& frozen,
                     const std::vector<SlowMoverState>& slow_movers);

} // namespace movement
