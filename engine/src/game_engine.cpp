//2048Squared (title pending) copyright (c) 2026 River Knuuttila, common alias: Annie Valentine or aval. All Rights Reserved.
//Do not redistribute or reuse code without accrediting and explicit permission from author.
//Contact:
//+1 (808) 223 4780
//riverknuuttila2@outlook.com

#include "game_engine.h"
#include <algorithm>
#include <cmath>

GameEngine::GameEngine(int rows, int cols)
    : board_(rows, cols),
      score_(4500),
      tar_expand_(2048),
      rng_(std::random_device{}())
{
    // Spawn two initial tiles
    board_.spawn_number();
    board_.spawn_number();
}

TurnResult GameEngine::process_move(const std::string& direction) {
    TurnResult result;

    // Step 1: Build effective frozen set (frozen tiles + active slow mover positions)
    auto effective_frozen = get_effective_frozen();

    // Step 2: Execute movement (all normal tiles move first)
    MoveResult move_result;
    if (direction == "up")
        move_result = movement::move_up(board_, effective_frozen, slow_movers_);
    else if (direction == "down")
        move_result = movement::move_down(board_, effective_frozen, slow_movers_);
    else if (direction == "left")
        move_result = movement::move_left(board_, effective_frozen, slow_movers_);
    else if (direction == "right")
        move_result = movement::move_right(board_, effective_frozen, slow_movers_);

    // Step 3: Advance slow movers (after all normal tiles have settled)
    result.slow_mover_updates = advance_slow_movers();

    // Check if anything changed (board or slow movers moved)
    bool slow_movers_moved = !result.slow_mover_updates.empty();
    if (!move_result.board_changed && !slow_movers_moved) {
        result.board_changed = false;
        return result;
    }

    result.board_changed = true;
    result.moves = move_result.moves;
    result.merges = move_result.merges;
    result.bomb_destroyed = move_result.bomb_destroyed;

    // Step 4: Clear freeze (wears off after one move)
    frozen_tiles_.clear();

    // Step 5: Calculate points
    result.points_gained = 0;
    for (const auto& m : result.merges) {
        result.points_gained += m.new_value;
    }
    score_ += result.points_gained;

    // Step 6: Build exclusion set for passive rolling
    std::set<std::pair<int,int>> excluded;
    for (const auto& m : result.merges) {
        excluded.insert({m.row, m.col});
    }
    for (const auto& sm : slow_movers_) {
        if (sm.active) {
            excluded.insert({sm.current_row, sm.current_col});
        }
    }

    // Step 7: Spawn a new tile
    result.spawned_tile = board_.spawn_number(move_result.bomb_destroyed);
    if (result.spawned_tile.first >= 0) {
        excluded.insert(result.spawned_tile);
    }

    // Step 8: Check for slow tiles in moves and convert them
    // After movement, check if any tiles that moved have A_LITTLE_SLOW passive.
    // If so, we need to create slow movers for them.
    // NOTE: The movement already happened instantly on the board. For slow tiles,
    // we need to undo the instant move and set up gradual movement instead.
    // This is done by detecting tiles with A_LITTLE_SLOW at their destination.
    for (const auto& mv : result.moves) {
        // Check if the tile at the destination has A_LITTLE_SLOW
        if (board_.at(mv.end_row, mv.end_col).passive == PassiveType::A_LITTLE_SLOW &&
            board_.at(mv.end_row, mv.end_col).is_numbered()) {

            // Only create slow mover if the tile actually moved more than 1 cell
            int dist_r = std::abs(mv.end_row - mv.start_row);
            int dist_c = std::abs(mv.end_col - mv.start_col);
            int total_dist = dist_r + dist_c;

            if (total_dist > 1) {
                // Direction of movement
                int dr = 0, dc = 0;
                if (mv.end_row > mv.start_row) dr = 1;
                else if (mv.end_row < mv.start_row) dr = -1;
                if (mv.end_col > mv.start_col) dc = 1;
                else if (mv.end_col < mv.start_col) dc = -1;

                // Move tile back to one step from start
                int first_step_r = mv.start_row + dr;
                int first_step_c = mv.start_col + dc;

                // Remove tile from its final destination on the board
                Tile saved = board_.at(mv.end_row, mv.end_col);
                board_.at(mv.end_row, mv.end_col).value = 0;
                board_.at(mv.end_row, mv.end_col).passive = PassiveType::NONE;

                // Place it one step from start
                board_.at(first_step_r, first_step_c) = saved;

                // Create slow mover state
                SlowMoverState sm;
                sm.current_row = first_step_r;
                sm.current_col = first_step_c;
                sm.dest_row = mv.end_row;
                sm.dest_col = mv.end_col;
                sm.dr = dr;
                sm.dc = dc;
                sm.value = saved.value;
                sm.passive = saved.passive;
                sm.active = true;
                slow_movers_.push_back(sm);
            }
        }
    }

    // Step 9: Roll for passive triggers
    result.passive_candidates = passive_roller_.roll(board_, result.merges, excluded);

    // Step 10: Check for expansion trigger
    for (const auto& m : result.merges) {
        if (m.new_value == tar_expand_) {
            result.should_expand = true;
            tar_expand_ *= 2;
            break;
        }
    }

    return result;
}

void GameEngine::assign_passive(int row, int col, int passive_type) {
    board_.at(row, col).passive = static_cast<PassiveType>(passive_type);
}

void GameEngine::place_bomb(int row, int col) {
    if (board_.at(row, col).is_empty()) {
        board_.at(row, col).value = -1;
        board_.at(row, col).passive = PassiveType::NONE;
    }
}

void GameEngine::place_freeze(int row, int col) {
    if (board_.at(row, col).is_numbered()) {
        frozen_tiles_.insert({row, col});
    }
}

void GameEngine::clear_freeze(int row, int col) {
    frozen_tiles_.erase({row, col});
}

std::vector<int> GameEngine::get_grid_values() const {
    return board_.to_flat_values();
}

std::vector<std::tuple<int,int,int>> GameEngine::get_passive_map() const {
    return board_.get_passive_map();
}

std::vector<SlowMoverState> GameEngine::get_slow_movers() const {
    return slow_movers_;
}

void GameEngine::complete_expansion(const std::string& direction) {
    board_.expand(direction);

    // Adjust slow mover positions if expansion shifts the grid
    if (direction == "up") {
        for (auto& sm : slow_movers_) {
            sm.current_row++;
            sm.dest_row++;
        }
    } else if (direction == "left") {
        for (auto& sm : slow_movers_) {
            sm.current_col++;
            sm.dest_col++;
        }
    }
    // "down" and "right" don't shift existing positions
}

std::vector<SlowMoverUpdate> GameEngine::advance_slow_movers() {
    std::vector<SlowMoverUpdate> updates;

    for (auto& sm : slow_movers_) {
        if (!sm.active) continue;

        int next_r = sm.current_row + sm.dr;
        int next_c = sm.current_col + sm.dc;

        // Check if destination reached
        if (sm.current_row == sm.dest_row && sm.current_col == sm.dest_col) {
            sm.active = false;
            updates.push_back({sm.current_row, sm.current_col,
                              sm.current_row, sm.current_col,
                              sm.value, true});
            continue;
        }

        // Check wall (out of bounds)
        if (next_r < 0 || next_r >= board_.rows() ||
            next_c < 0 || next_c >= board_.cols()) {
            sm.active = false;
            updates.push_back({sm.current_row, sm.current_col,
                              sm.current_row, sm.current_col,
                              sm.value, true});
            continue;
        }

        // Check if next cell is occupied
        if (!board_.at(next_r, next_c).is_empty()) {
            sm.active = false;
            updates.push_back({sm.current_row, sm.current_col,
                              sm.current_row, sm.current_col,
                              sm.value, true});
            continue;
        }

        // Move one cell
        SlowMoverUpdate update;
        update.old_row = sm.current_row;
        update.old_col = sm.current_col;
        update.new_row = next_r;
        update.new_col = next_c;
        update.value = sm.value;

        // Update board: clear old position, set new position
        board_.at(sm.current_row, sm.current_col).value = 0;
        board_.at(sm.current_row, sm.current_col).passive = PassiveType::NONE;
        board_.at(next_r, next_c).value = sm.value;
        board_.at(next_r, next_c).passive = sm.passive;

        sm.current_row = next_r;
        sm.current_col = next_c;

        // Check if now at destination
        update.finished = (next_r == sm.dest_row && next_c == sm.dest_col);
        if (update.finished) {
            sm.active = false;
        }

        updates.push_back(update);
    }

    // Remove inactive slow movers
    slow_movers_.erase(
        std::remove_if(slow_movers_.begin(), slow_movers_.end(),
                       [](const SlowMoverState& sm) { return !sm.active; }),
        slow_movers_.end());

    return updates;
}

std::set<std::pair<int,int>> GameEngine::get_effective_frozen() const {
    auto frozen = frozen_tiles_;
    for (const auto& sm : slow_movers_) {
        if (sm.active) {
            frozen.insert({sm.current_row, sm.current_col});
        }
    }
    return frozen;
}
