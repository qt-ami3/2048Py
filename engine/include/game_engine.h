//2048Squared (title pending) copyright (c) 2026 River Knuuttila, common alias: Annie Valentine or aval. All Rights Reserved.
//Do not redistribute or reuse code without accrediting and explicit permission from author.
//Contact:
//+1 (808) 223 4780
//riverknuuttila2@outlook.com

#pragma once

#include "board.h"
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
    std::set<std::pair<int,int>> snail_bomb_kills;  // snail positions killed by adjacent bomb
    int points_gained = 0;
    std::pair<int,int> spawned_tile = {-1, -1};
    std::pair<int,int> spawned_snail = {-1, -1};
    bool board_changed = false;
    bool should_expand = false;
    std::string expand_direction;
    std::vector<PassiveCandidate> passive_candidates;
    std::vector<SlowMoverUpdate> slow_mover_updates;
    std::vector<RandomMoverUpdate> random_mover_updates;
    std::vector<MoveInfo> slow_tile_moves;    // A_LITTLE_SLOW step-advance moves (step 3.5)
    std::vector<MergeInfo> slow_tile_merges;  // merges from step 3.5
};

class GameEngine {
public:
    GameEngine(int rows, int cols);

    TurnResult process_move(const std::string& direction);

    void set_tile(int row, int col, int value, int passive_type = 0);
    void assign_passive(int row, int col, int passive_type);

    void place_bomb(int row, int col);
    void place_freeze(int row, int col);
    void clear_freeze(int row, int col);

    std::vector<int> get_grid_values() const;
    std::vector<std::tuple<int,int,int>> get_passive_map() const;
    std::vector<SlowMoverState> get_slow_movers() const;
    std::vector<RandomMoverState> get_random_movers() const;

    int rows() const { return board_.rows(); }
    int cols() const { return board_.cols(); }
    int score() const { return score_; }
    int tar_expand() const { return tar_expand_; }

    void complete_expansion(const std::string& direction);

private:
    Board board_;
    int score_;
    int tar_expand_;
    std::set<std::pair<int,int>> frozen_tiles_;
    std::vector<SlowMoverState> slow_movers_;
    std::vector<RandomMoverState> random_movers_;
    PassiveRoller passive_roller_;
    std::mt19937 rng_;
    int snail_respawn_timer_ = 0;

    std::vector<SlowMoverUpdate> advance_slow_movers();
    std::vector<RandomMoverUpdate> advance_random_movers(std::set<std::pair<int,int>>& bomb_destroyed);
    std::set<std::pair<int,int>> get_effective_frozen() const;
    void detonate_adjacent_bombs(TurnResult& result, std::set<std::pair<int,int>>& effective_frozen, bool check_frozen_tiles = false);
};
