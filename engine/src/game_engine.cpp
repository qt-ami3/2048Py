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

    // Step 0: Record which tiles have A_LITTLE_SLOW and which are snails before movement
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
    // Freeze: user-frozen tiles + active slow movers + ALL A_LITTLE_SLOW tiles + ALL snails
    // A_LITTLE_SLOW tiles and snails are frozen during normal movement and advanced separately.
    auto effective_frozen = get_effective_frozen();
    for (const auto& pos : pre_move_slow_positions) {
        effective_frozen.insert(pos);
    }
    // Freeze all snail tiles
    for (int r = 0; r < board_.rows(); r++) {
        for (int c = 0; c < board_.cols(); c++) {
            if (board_.at(r, c).is_snail()) {
                effective_frozen.insert({r, c});
            }
        }
    }
    // Freeze all wall tiles (permanent immovable obstacles)
    for (int r = 0; r < board_.rows(); r++) {
        for (int c = 0; c < board_.cols(); c++) {
            if (board_.at(r, c).is_wall()) {
                effective_frozen.insert({r, c});
            }
        }
    }

    // Count snails before any killing steps (for respawn detection)
    int snails_before = 0;
    for (int r = 0; r < board_.rows(); r++)
        for (int c = 0; c < board_.cols(); c++)
            if (board_.at(r, c).is_snail()) snails_before++;

    // Step 1.5: Pre-movement bomb-snail detonation.
    detonate_adjacent_bombs(result, effective_frozen);

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

    // Step 2.5: Post-movement bomb-snail detonation.
    // A bomb may have slid up to a frozen snail during step 2 — detonate it now.
    // Also check frozen tiles post-movement (not pre-movement, so bombs can
    // participate in normal movement first before detonating frozen tiles).
    detonate_adjacent_bombs(result, effective_frozen, true);

    // Step 2.6: Advance SNAIL tiles (random movers) in a random direction.
    // Snails move after normal tiles and bombs have settled, but before slow tiles.
    result.random_mover_updates = advance_random_movers(result.bomb_destroyed);

    // Track positions vacated by snails this turn (for cascade fill in step 3.5b).
    std::set<std::pair<int,int>> snail_vacated;
    for (const auto& u : result.random_mover_updates) {
        if (u.old_row != u.new_row || u.old_col != u.new_col)
            snail_vacated.insert({u.old_row, u.old_col});
    }

    // Detect snail kills and arm respawn timer (Scary Forest and beyond only)
    if (tar_expand_ > 4096) {
        int snails_after = 0;
        for (int r = 0; r < board_.rows(); r++)
            for (int c = 0; c < board_.cols(); c++)
                if (board_.at(r, c).is_snail()) snails_after++;
        if (snails_after < snails_before)
            snail_respawn_timer_ = 3;
    }

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

            // Record move and merge (deferred to slow-tile animation phase)
            result.slow_tile_moves.push_back({behind_r, behind_c, sr, sc, tile_value});
            result.slow_tile_merges.push_back({sr, sc, new_value});

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

            result.slow_tile_moves.push_back({sr, sc, dest_r, dest_c, tile_value});
            result.slow_tile_merges.push_back({dest_r, dest_c, new_value});
            move_result.board_changed = true;

            // Slow tile vacated (sr, sc) — let regular tiles behind it follow in.
            cascade_fill_behind(sr, sc, move_dr, move_dc, active_sm_positions, result.slow_tile_moves);
        } else {
            // Move 1 cell to empty space
            Tile saved = board_.at(sr, sc);
            board_.at(sr, sc).value = 0;
            board_.at(sr, sc).passive = PassiveType::NONE;
            board_.at(next_r, next_c) = saved;

            result.slow_tile_moves.push_back({sr, sc, next_r, next_c, tile_value});
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

            // Slow tile vacated (sr, sc) — let regular tiles behind it follow in.
            cascade_fill_behind(sr, sc, move_dr, move_dc, active_sm_positions, result.slow_tile_moves);
        }
    }

    // Step 3.5b: Cascade regular tiles into positions vacated by snails this turn.
    // Tiles were blocked by frozen snails during step 2; now that snails have moved
    // (step 2.6), those tiles can slide forward into the vacated cells.
    for (const auto& [vr, vc] : snail_vacated) {
        if (board_.at(vr, vc).is_empty())
            cascade_fill_behind(vr, vc, move_dr, move_dc, active_sm_positions, result.slow_tile_moves);
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

    // Check if anything changed (board or slow movers or random movers moved)
    bool random_movers_moved = !result.random_mover_updates.empty();
    bool slow_movers_moved = !result.slow_mover_updates.empty();
    if (!move_result.board_changed && !slow_movers_moved && !random_movers_moved) {
        result.board_changed = false;
        return result;
    }

    result.board_changed = true;
    result.moves = move_result.moves;
    result.merges = move_result.merges;
    // Merge both bomb_destroyed sets (regular movement + snail-bomb interactions)
    result.bomb_destroyed.insert(move_result.bomb_destroyed.begin(), move_result.bomb_destroyed.end());

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
    for (const auto& rm : random_movers_) {
        excluded.insert({rm.row, rm.col});
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

    // Snail respawn countdown
    if (snail_respawn_timer_ > 0) {
        snail_respawn_timer_--;
        if (snail_respawn_timer_ == 0 && tar_expand_ > 4096) {
            // Only spawn if no snail is already on the board
            bool has_snail = false;
            for (int r = 0; r < board_.rows() && !has_snail; r++)
                for (int c = 0; c < board_.cols() && !has_snail; c++)
                    if (board_.at(r, c).is_snail()) has_snail = true;
            if (!has_snail) {
                auto pos = board_.spawn_snail();
                if (pos.first >= 0) {
                    result.spawned_snail = pos;
                } else {
                    snail_respawn_timer_ = 1;  // retry next turn if board was full
                }
            }
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
    if (board_.at(row, col).is_numbered() || board_.at(row, col).is_snail()) {
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
        for (auto& rm : random_movers_) {
            rm.row++;
        }
    } else if (direction == "left") {
        for (auto& sm : slow_movers_) {
            sm.current_col++;
            sm.dest_col++;
        }
        for (auto& rm : random_movers_) {
            rm.col++;
        }
    }
    // "down" and "right" don't shift existing positions

    // Place a wall tile in the center of the new row/col on the first expansion
    expand_count_++;
    if (expand_count_ == 1) {
        int wall_r, wall_c;
        if (direction == "down") {
            wall_r = board_.rows() - 1;
            wall_c = board_.cols() / 2;
        } else if (direction == "up") {
            wall_r = 0;
            wall_c = board_.cols() / 2;
        } else if (direction == "right") {
            wall_r = board_.rows() / 2;
            wall_c = board_.cols() - 1;
        } else { // "left"
            wall_r = board_.rows() / 2;
            wall_c = 0;
        }
        board_.at(wall_r, wall_c).value = -3;
        board_.at(wall_r, wall_c).passive = PassiveType::NONE;
    }

    // Spawn a snail starting from Scary Forest, but only if one isn't already on the board
    if (tar_expand_ > 4096) {
        bool has_snail = false;
        for (int r = 0; r < board_.rows() && !has_snail; r++)
            for (int c = 0; c < board_.cols() && !has_snail; c++)
                if (board_.at(r, c).is_snail()) has_snail = true;
        if (!has_snail)
            board_.spawn_snail();
    }
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

std::vector<RandomMoverUpdate> GameEngine::advance_random_movers(std::set<std::pair<int,int>>& bomb_destroyed) {
    std::vector<RandomMoverUpdate> updates;

    // Update random_movers_ list based on current snail tiles (value == -2) on the board
    random_movers_.clear();
    for (int r = 0; r < board_.rows(); r++) {
        for (int c = 0; c < board_.cols(); c++) {
            if (board_.at(r, c).is_snail()) {
                RandomMoverState rm;
                rm.row = r;
                rm.col = c;
                random_movers_.push_back(rm);
            }
        }
    }

    // Move each snail in a random valid direction
    for (auto& rm : random_movers_) {
        // Skip if frozen by user
        if (frozen_tiles_.count({rm.row, rm.col})) {
            continue;
        }

        // Build list of valid directions (not out of bounds, empty or bomb)
        std::vector<std::pair<int,int>> valid_dirs;
        std::vector<std::pair<int,int>> directions = {{-1, 0}, {1, 0}, {0, -1}, {0, 1}}; // up, down, left, right

        for (const auto& [dr, dc] : directions) {
            int new_r = rm.row + dr;
            int new_c = rm.col + dc;

            // Check bounds
            if (new_r < 0 || new_r >= board_.rows() || new_c < 0 || new_c >= board_.cols()) {
                continue;
            }

            // Can move to empty cells or bombs (snail gets destroyed by bomb)
            if (board_.at(new_r, new_c).is_empty() || board_.at(new_r, new_c).is_bomb()) {
                valid_dirs.push_back({dr, dc});
            }
        }

        // If no valid moves, stay in place
        if (valid_dirs.empty()) {
            continue;
        }

        // Pick a random valid direction
        std::uniform_int_distribution<int> dir_dist(0, (int)valid_dirs.size() - 1);
        auto [dr, dc] = valid_dirs[dir_dist(rng_)];

        int new_r = rm.row + dr;
        int new_c = rm.col + dc;

        RandomMoverUpdate update;
        update.old_row = rm.row;
        update.old_col = rm.col;
        update.new_row = new_r;
        update.new_col = new_c;

        // Check if moving into bomb
        if (board_.at(new_r, new_c).is_bomb()) {
            // Both snail and bomb are destroyed
            board_.at(rm.row, rm.col).value = 0;   // Clear snail
            board_.at(new_r, new_c).value = 0;      // Consume bomb
            bomb_destroyed.insert({new_r, new_c});  // Particles at bomb/collision position
        } else {
            // Move snail to empty cell
            board_.at(new_r, new_c).value = -2;  // Snail value
            board_.at(rm.row, rm.col).value = 0;
            rm.row = new_r;
            rm.col = new_c;
        }

        updates.push_back(update);
    }

    return updates;
}

std::vector<RandomMoverState> GameEngine::get_random_movers() const {
    return random_movers_;
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

void GameEngine::detonate_adjacent_bombs(TurnResult& result, std::set<std::pair<int,int>>& effective_frozen, bool check_frozen_tiles) {
    const std::vector<std::pair<int,int>> dirs4 = {{-1,0},{1,0},{0,-1},{0,1}};

    struct Detonation { int br, bc, tr, tc; bool target_is_snail; };
    std::vector<Detonation> detonations;

    for (int r = 0; r < board_.rows(); r++) {
        for (int c = 0; c < board_.cols(); c++) {
            if (!board_.at(r, c).is_bomb()) continue;
            for (auto [dr, dc] : dirs4) {
                int nr = r + dr, nc = c + dc;
                if (nr < 0 || nr >= board_.rows() || nc < 0 || nc >= board_.cols()) continue;
                bool is_snail = board_.at(nr, nc).is_snail();
                // Bombs also destroy user-frozen regular tiles (freeze never protects from bombs)
                bool is_frozen_tile = check_frozen_tiles && !is_snail &&
                                      board_.at(nr, nc).is_numbered() &&
                                      frozen_tiles_.count({nr, nc}) > 0;
                if (is_snail || is_frozen_tile) {
                    detonations.push_back({r, c, nr, nc, is_snail});
                    break;
                }
            }
        }
    }

    for (auto& det : detonations) {
        if (!board_.at(det.br, det.bc).is_bomb()) continue;
        bool target_ok = det.target_is_snail
            ? board_.at(det.tr, det.tc).is_snail()
            : board_.at(det.tr, det.tc).is_numbered() && frozen_tiles_.count({det.tr, det.tc}) > 0;
        if (!target_ok) continue;

        board_.at(det.br, det.bc).value = 0;
        board_.at(det.tr, det.tc).value = 0;
        board_.at(det.tr, det.tc).passive = PassiveType::NONE;
        result.bomb_destroyed.insert({det.br, det.bc});
        result.bomb_destroyed.insert({det.tr, det.tc});
        effective_frozen.erase({det.tr, det.tc});
        frozen_tiles_.erase({det.tr, det.tc});
        if (det.target_is_snail)
            result.snail_bomb_kills.insert({det.tr, det.tc});
    }
}

void GameEngine::cascade_fill_behind(
    int empty_r, int empty_c,
    int dr, int dc,
    const std::set<std::pair<int,int>>& skip,
    std::vector<MoveInfo>& out_moves)
{
    int fill_r = empty_r, fill_c = empty_c;
    while (true) {
        int check_r = fill_r - dr, check_c = fill_c - dc;
        if (check_r < 0 || check_r >= board_.rows() ||
            check_c < 0 || check_c >= board_.cols()) break;

        // Only move plain numbered tiles — skip slow tiles, snails, bombs, walls.
        const Tile& ct = board_.at(check_r, check_c);
        if (!ct.is_numbered()) break;
        if (ct.passive == PassiveType::A_LITTLE_SLOW) break;
        if (skip.count({check_r, check_c})) break;       // active slow mover
        if (frozen_tiles_.count({check_r, check_c})) break;  // user-frozen

        Tile saved = ct;
        board_.at(check_r, check_c).value = 0;
        board_.at(check_r, check_c).passive = PassiveType::NONE;
        board_.at(fill_r, fill_c) = saved;

        out_moves.push_back({check_r, check_c, fill_r, fill_c, saved.value});

        fill_r = check_r;
        fill_c = check_c;
    }
}
