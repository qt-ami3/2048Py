//2048Squared (title pending) copyright (c) 2026 River Knuuttila, common alias: Annie Valentine or aval. All Rights Reserved.
//Do not redistribute or reuse code without accrediting and explicit permission from author.
//Contact:
//+1 (808) 223 4780
//riverknuuttila2@outlook.com

#include "game_engine.h"
#include <algorithm>
#include <climits>
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

    // Step 0: Record which tiles have A_LITTLE_SLOW before movement
    std::set<std::pair<int,int>> pre_move_slow_positions;
    for (int r = 0; r < board_.rows(); r++) {
        for (int c = 0; c < board_.cols(); c++) {
            if (board_.at(r, c).passive == PassiveType::A_LITTLE_SLOW &&
                board_.at(r, c).is_numbered()) {
                pre_move_slow_positions.insert({r, c});
            }
        }
    }

    // Step 1: Build effective frozen set
    // Freeze: user-frozen tiles + active slow movers + ALL A_LITTLE_SLOW tiles
    // A_LITTLE_SLOW tiles are frozen during normal movement and advanced separately.
    auto effective_frozen = get_effective_frozen();
    for (const auto& pos : pre_move_slow_positions) {
        effective_frozen.insert(pos);
    }

    // Compute movement direction vector
    int move_dr = 0, move_dc = 0;
    if (direction == "up") move_dr = -1;
    else if (direction == "down") move_dr = 1;
    else if (direction == "left") move_dc = -1;
    else if (direction == "right") move_dc = 1;

    // Step 2: Execute movement (all normal tiles move; slow tiles are frozen)
    MoveResult move_result;
    if (direction == "up")
        move_result = movement::move_up(board_, effective_frozen, slow_movers_);
    else if (direction == "down")
        move_result = movement::move_down(board_, effective_frozen, slow_movers_);
    else if (direction == "left")
        move_result = movement::move_left(board_, effective_frozen, slow_movers_);
    else if (direction == "right")
        move_result = movement::move_right(board_, effective_frozen, slow_movers_);

    // Step 3: Advance existing slow movers (after normal tiles have settled)
    result.slow_mover_updates = advance_slow_movers();

    // Step 3.5: Advance A_LITTLE_SLOW tiles that aren't active slow movers.
    // They were frozen during movement; now move them 1 cell in the direction.
    // Also check behind for same-value tiles to merge (they couldn't merge during
    // movement because the slow tile was frozen as a segment boundary).

    // Build set of active slow mover positions to skip them.
    std::set<std::pair<int,int>> active_sm_positions;
    for (const auto& sm : slow_movers_) {
        if (sm.active) active_sm_positions.insert({sm.current_row, sm.current_col});
    }

    // Process in correct order: tiles closest to movement wall first.
    // For left/up: ascending order (default set iteration).
    // For right/down: descending order (reverse iteration).
    std::vector<std::pair<int,int>> slow_order(pre_move_slow_positions.begin(),
                                                pre_move_slow_positions.end());
    if (direction == "right" || direction == "down") {
        std::reverse(slow_order.begin(), slow_order.end());
    }

    for (const auto& [sr, sc] : slow_order) {
        // Skip if this is an active slow mover (handled by advance_slow_movers)
        if (active_sm_positions.count({sr, sc})) continue;

        // Skip if tile is no longer there (consumed by a previous merge this step)
        if (!board_.at(sr, sc).is_numbered()) continue;
        if (board_.at(sr, sc).passive != PassiveType::A_LITTLE_SLOW) continue;

        int tile_value = board_.at(sr, sc).value;

        // Check behind (opposite to movement direction) for same-value merge.
        // A tile may have compacted next to this frozen slow tile during movement.
        int behind_r = sr - move_dr;
        int behind_c = sc - move_dc;

        if (behind_r >= 0 && behind_r < board_.rows() &&
            behind_c >= 0 && behind_c < board_.cols() &&
            board_.at(behind_r, behind_c).is_numbered() &&
            board_.at(behind_r, behind_c).value == tile_value) {

            int new_value = tile_value * 2;

            // Record move and merge
            move_result.moves.push_back({behind_r, behind_c, sr, sc, tile_value});
            move_result.merges.push_back({sr, sc, new_value});

            // Consume behind tile
            board_.at(behind_r, behind_c).value = 0;
            board_.at(behind_r, behind_c).passive = PassiveType::NONE;

            // Update slow tile value
            board_.at(sr, sc).value = new_value;
            tile_value = new_value;
            move_result.board_changed = true;
        }

        // If this tile is user-frozen, don't advance it (freeze holds for 1 turn).
        // The behind merge above still applies since tiles slid next to it.
        if (frozen_tiles_.count({sr, sc})) continue;

        // Scan ahead in movement direction to find ultimate destination
        int dest_r = sr, dest_c = sc;
        int scan_r = sr + move_dr, scan_c = sc + move_dc;
        bool dest_is_merge = false;

        while (scan_r >= 0 && scan_r < board_.rows() &&
               scan_c >= 0 && scan_c < board_.cols()) {
            if (board_.at(scan_r, scan_c).is_empty()) {
                dest_r = scan_r;
                dest_c = scan_c;
            } else if (board_.at(scan_r, scan_c).value == tile_value &&
                       board_.at(scan_r, scan_c).is_numbered()) {
                dest_r = scan_r;
                dest_c = scan_c;
                dest_is_merge = true;
                break;
            } else {
                break;
            }
            scan_r += move_dr;
            scan_c += move_dc;
        }

        // If destination is same as current position, tile can't advance
        if (dest_r == sr && dest_c == sc) continue;

        int next_r = sr + move_dr;
        int next_c = sc + move_dc;
        int total_dist = std::abs(dest_r - sr) + std::abs(dest_c - sc);

        // Check if the immediate next cell is the merge target
        if (next_r == dest_r && next_c == dest_c && dest_is_merge) {
            // Merge with adjacent tile ahead
            int new_value = tile_value * 2;

            board_.at(sr, sc).value = 0;
            board_.at(sr, sc).passive = PassiveType::NONE;
            board_.at(dest_r, dest_c).value = new_value;
            board_.at(dest_r, dest_c).passive = PassiveType::A_LITTLE_SLOW;

            move_result.moves.push_back({sr, sc, dest_r, dest_c, tile_value});
            move_result.merges.push_back({dest_r, dest_c, new_value});
            move_result.board_changed = true;
        } else {
            // Move 1 cell to empty space
            Tile saved = board_.at(sr, sc);
            board_.at(sr, sc).value = 0;
            board_.at(sr, sc).passive = PassiveType::NONE;
            board_.at(next_r, next_c) = saved;

            move_result.moves.push_back({sr, sc, next_r, next_c, tile_value});
            move_result.board_changed = true;

            // If destination is further than 1 cell, create slow mover
            if (total_dist > 1) {
                SlowMoverState sm;
                sm.current_row = next_r;
                sm.current_col = next_c;
                sm.dest_row = dest_r;
                sm.dest_col = dest_c;
                sm.dr = move_dr;
                sm.dc = move_dc;
                sm.value = saved.value;
                sm.passive = saved.passive;
                sm.active = true;
                slow_movers_.push_back(sm);
            }
        }
    }

    // Step 3.6: Check for merges between tiles and frozen slow movers.
    // A tile may have slid next to a frozen slow mover with the same value.
    for (auto& sm : slow_movers_) {
        if (!sm.active) continue;
        if (!frozen_tiles_.count({sm.current_row, sm.current_col})) continue;

        // Check cell from the approaching direction (opposite of movement)
        int adj_r = sm.current_row - move_dr;
        int adj_c = sm.current_col - move_dc;

        if (adj_r < 0 || adj_r >= board_.rows() ||
            adj_c < 0 || adj_c >= board_.cols()) continue;

        if (!board_.at(adj_r, adj_c).is_numbered()) continue;
        if (board_.at(adj_r, adj_c).value != sm.value) continue;

        // Merge: adjacent tile is absorbed into the frozen slow mover
        int old_adj_value = board_.at(adj_r, adj_c).value;
        int new_value = sm.value * 2;

        board_.at(adj_r, adj_c).value = 0;
        board_.at(adj_r, adj_c).passive = PassiveType::NONE;

        sm.value = new_value;
        board_.at(sm.current_row, sm.current_col).value = new_value;
        // Passive stays A_LITTLE_SLOW

        move_result.moves.push_back({adj_r, adj_c, sm.current_row, sm.current_col, old_adj_value});
        move_result.merges.push_back({sm.current_row, sm.current_col, new_value});
        move_result.board_changed = true;
    }

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

void GameEngine::set_tile(int row, int col, int value, int passive_type) {
    board_.at(row, col).value = value;
    board_.at(row, col).passive = static_cast<PassiveType>(passive_type);
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

        // If this slow mover is frozen, skip its turn but keep it active
        if (frozen_tiles_.count({sm.current_row, sm.current_col})) {
            continue;
        }

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
            // If same value, merge instead of stopping
            if (board_.at(next_r, next_c).is_numbered() &&
                board_.at(next_r, next_c).value == sm.value) {
                int new_value = sm.value * 2;

                // Clear old position
                board_.at(sm.current_row, sm.current_col).value = 0;
                board_.at(sm.current_row, sm.current_col).passive = PassiveType::NONE;

                // Update destination with merged value, keep A_LITTLE_SLOW
                board_.at(next_r, next_c).value = new_value;
                board_.at(next_r, next_c).passive = PassiveType::A_LITTLE_SLOW;

                sm.active = false;
                updates.push_back({sm.current_row, sm.current_col,
                                  next_r, next_c,
                                  new_value, true});
                continue;
            }

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
