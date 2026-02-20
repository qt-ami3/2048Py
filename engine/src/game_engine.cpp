//2048Squared (title pending) copyright (c) 2026 River Knuuttila, common alias: Annie Valentine or aval. All Rights Reserved.
//Do not redistribute or reuse code without accrediting and explicit permission from author.
//Contact:
//+1 (808) 223 4780
//riverknuuttila2@outlook.com

#include "game_engine.h"
#include "slow_behavior.h"
#include "contrarian_behavior.h"
#include <algorithm>

GameEngine::GameEngine(int rows, int cols)
    : board_(rows, cols),
      score_(4500),
      tar_expand_(2048),
      rng_(std::random_device{}())
{
    // Register passive behaviors in advance-phase order.
    // To add a new passive: implement TileBehavior, add one line here.
    behaviors_.push_back(std::make_unique<SlowBehavior>());
    behaviors_.push_back(std::make_unique<ContrarianBehavior>());

    board_.spawn_number();
    board_.spawn_number();
}

TurnResult GameEngine::process_move(const std::string& direction) {
    TurnResult result;

    int move_dr = 0, move_dc = 0;
    if      (direction == "up")    move_dr = -1;
    else if (direction == "down")  move_dr =  1;
    else if (direction == "left")  move_dc = -1;
    else if (direction == "right") move_dc =  1;

    // Phase 1: Each behavior snapshots pre-move state (positions, pre-blocked sets, etc.)
    for (auto& b : behaviors_)
        b->pre_snapshot(board_, move_dr, move_dc);

    // Phase 2: Build effective frozen set.
    // Starts with active slow movers + user-frozen tiles, then behaviors add their tiles.
    auto effective_frozen = get_effective_frozen();
    for (int r = 0; r < board_.rows(); r++) {
        for (int c = 0; c < board_.cols(); c++) {
            const Tile& tile = board_.at(r, c);
            if (!tile.is_numbered()) continue;
            for (auto& b : behaviors_) {
                if (b->matches(tile.passive) && b->freeze_during_move()) {
                    effective_frozen.insert({r, c});
                    // Freeze the same-value tile immediately behind if behavior requests it.
                    if (b->freeze_tile_behind()) {
                        int br = r - move_dr, bc = c - move_dc;
                        if (br >= 0 && br < board_.rows() &&
                            bc >= 0 && bc < board_.cols() &&
                            board_.at(br, bc).is_numbered() &&
                            board_.at(br, bc).value == tile.value) {
                            effective_frozen.insert({br, bc});
                        }
                    }
                    break;  // First matching behavior claims this tile.
                }
            }
        }
    }
    // Freeze snails and walls (not passive behaviors — special tile types).
    for (int r = 0; r < board_.rows(); r++)
        for (int c = 0; c < board_.cols(); c++)
            if (board_.at(r, c).is_snail() || board_.at(r, c).is_wall())
                effective_frozen.insert({r, c});

    int snails_before = 0;
    for (int r = 0; r < board_.rows(); r++)
        for (int c = 0; c < board_.cols(); c++)
            if (board_.at(r, c).is_snail()) snails_before++;

    // Phase 3: Pre-movement bomb detonation.
    detonate_adjacent_bombs(result, effective_frozen);

    // Phase 4: Regular movement (all non-frozen tiles).
    MoveResult move_result;
    if      (direction == "up")    move_result = movement::move_up   (board_, effective_frozen, slow_movers_);
    else if (direction == "down")  move_result = movement::move_down (board_, effective_frozen, slow_movers_);
    else if (direction == "left")  move_result = movement::move_left (board_, effective_frozen, slow_movers_);
    else if (direction == "right") move_result = movement::move_right(board_, effective_frozen, slow_movers_);

    // Phase 5: Post-movement bomb detonation.
    // Bombs may have slid up to frozen tiles; also check user-frozen tile adjacency.
    detonate_adjacent_bombs(result, effective_frozen, true);

    // Phase 6: Advance existing slow movers (from previous turns).
    result.slow_mover_updates = advance_slow_movers();

    // Build active slow mover positions (updated after advance removes finished movers).
    std::set<std::pair<int,int>> active_sm_positions;
    for (const auto& sm : slow_movers_)
        if (sm.active) active_sm_positions.insert({sm.current_row, sm.current_col});

    // Cascade callback: slide regular tiles into a cell vacated by a special tile.
    auto cascade_fn = [this, move_dr, move_dc, &active_sm_positions]
                      (int er, int ec, std::vector<MoveInfo>& moves) {
        cascade_fill_behind(er, ec, move_dr, move_dc, active_sm_positions, moves);
    };

    MoveContext ctx {
        board_, slow_movers_, frozen_tiles_, effective_frozen,
        active_sm_positions, move_dr, move_dc, cascade_fn
    };

    // Phase 7: Each behavior advances its tiles in registration order.
    // A bomb detonation pass runs after each behavior to catch newly adjacent bombs.
    for (auto& b : behaviors_) {
        bool changed = b->advance(ctx, result);
        move_result.board_changed |= changed;
        detonate_adjacent_bombs(result, effective_frozen);
    }

    // Validity check: at least one tile must have moved this turn.
    // Snail movement alone does not count as a valid turn (prevents turn farming).
    {
        bool slow_movers_moved = !result.slow_mover_updates.empty();
        if (!move_result.board_changed && !slow_movers_moved) {
            result.board_changed = false;
            return result;
        }
    }

    // Phase 8: Advance snails (only on valid turns).
    result.random_mover_updates = advance_random_movers(result.bomb_destroyed);

    std::set<std::pair<int,int>> snail_vacated;
    for (const auto& u : result.random_mover_updates)
        if (u.old_row != u.new_row || u.old_col != u.new_col)
            snail_vacated.insert({u.old_row, u.old_col});

    if (tar_expand_ > 4096) {
        int snails_after = 0;
        for (int r = 0; r < board_.rows(); r++)
            for (int c = 0; c < board_.cols(); c++)
                if (board_.at(r, c).is_snail()) snails_after++;
        if (snails_after < snails_before)
            snail_respawn_timer_ = 3;
    }

    // Cascade regular tiles into cells vacated by snails this turn.
    for (const auto& [vr, vc] : snail_vacated)
        if (board_.at(vr, vc).is_empty())
            cascade_fill_behind(vr, vc, move_dr, move_dc, active_sm_positions, result.slow_tile_moves);

    result.board_changed = true;
    result.moves   = move_result.moves;
    result.merges  = move_result.merges;
    result.bomb_destroyed.insert(move_result.bomb_destroyed.begin(),
                                  move_result.bomb_destroyed.end());

    frozen_tiles_.clear();

    result.points_gained = 0;
    for (const auto& m : result.merges) result.points_gained += m.new_value;
    score_ += result.points_gained;

    std::set<std::pair<int,int>> excluded;
    for (const auto& m  : result.merges)  excluded.insert({m.row, m.col});
    for (const auto& sm : slow_movers_)   if (sm.active) excluded.insert({sm.current_row, sm.current_col});
    for (const auto& rm : random_movers_) excluded.insert({rm.row, rm.col});

    result.spawned_tile = board_.spawn_number(move_result.bomb_destroyed);
    if (result.spawned_tile.first >= 0) excluded.insert(result.spawned_tile);

    result.passive_candidates = passive_roller_.roll(board_, result.merges, excluded);

    for (const auto& m : result.merges) {
        if (m.new_value == tar_expand_) {
            result.should_expand = true;
            tar_expand_ *= 2;
            break;
        }
    }

    if (snail_respawn_timer_ > 0) {
        snail_respawn_timer_--;
        if (snail_respawn_timer_ == 0 && tar_expand_ > 4096) {
            bool has_snail = false;
            for (int r = 0; r < board_.rows() && !has_snail; r++)
                for (int c = 0; c < board_.cols() && !has_snail; c++)
                    if (board_.at(r, c).is_snail()) has_snail = true;
            if (!has_snail) {
                auto pos = board_.spawn_snail();
                if (pos.first >= 0) result.spawned_snail = pos;
                else snail_respawn_timer_ = 1;
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
    int current = static_cast<int>(board_.at(row, col).passive);
    board_.at(row, col).passive = static_cast<PassiveType>(current | passive_type);
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

    if (direction == "up") {
        for (auto& sm : slow_movers_) { sm.current_row++; sm.dest_row++; }
        for (auto& rm : random_movers_) rm.row++;
    } else if (direction == "left") {
        for (auto& sm : slow_movers_) { sm.current_col++; sm.dest_col++; }
        for (auto& rm : random_movers_) rm.col++;
    }

    expand_count_++;
    if (expand_count_ == 1) {
        int wall_r, wall_c;
        if      (direction == "down")  { wall_r = board_.rows() - 1; wall_c = board_.cols() / 2; }
        else if (direction == "up")    { wall_r = 0;                 wall_c = board_.cols() / 2; }
        else if (direction == "right") { wall_r = board_.rows() / 2; wall_c = board_.cols() - 1; }
        else                           { wall_r = board_.rows() / 2; wall_c = 0; }
        board_.at(wall_r, wall_c).value = -3;
        board_.at(wall_r, wall_c).passive = PassiveType::NONE;
    }

    if (tar_expand_ > 4096) {
        bool has_snail = false;
        for (int r = 0; r < board_.rows() && !has_snail; r++)
            for (int c = 0; c < board_.cols() && !has_snail; c++)
                if (board_.at(r, c).is_snail()) has_snail = true;
        if (!has_snail) board_.spawn_snail();
    }
}

std::vector<SlowMoverUpdate> GameEngine::advance_slow_movers() {
    std::vector<SlowMoverUpdate> updates;

    for (auto& sm : slow_movers_) {
        if (!sm.active) continue;
        if (frozen_tiles_.count({sm.current_row, sm.current_col})) continue;

        int next_r = sm.current_row + sm.dr;
        int next_c = sm.current_col + sm.dc;

        if (sm.current_row == sm.dest_row && sm.current_col == sm.dest_col) {
            sm.active = false;
            updates.push_back({sm.current_row, sm.current_col,
                               sm.current_row, sm.current_col, sm.value, true});
            continue;
        }

        if (next_r < 0 || next_r >= board_.rows() ||
            next_c < 0 || next_c >= board_.cols()) {
            sm.active = false;
            updates.push_back({sm.current_row, sm.current_col,
                               sm.current_row, sm.current_col, sm.value, true});
            continue;
        }

        if (!board_.at(next_r, next_c).is_empty()) {
            if (board_.at(next_r, next_c).is_numbered() &&
                board_.at(next_r, next_c).value == sm.value) {
                int new_value = sm.value * 2;
                board_.at(sm.current_row, sm.current_col).value = 0;
                board_.at(sm.current_row, sm.current_col).passive = PassiveType::NONE;
                board_.at(next_r, next_c).value = new_value;
                board_.at(next_r, next_c).passive = sm.passive;
                sm.active = false;
                updates.push_back({sm.current_row, sm.current_col,
                                   next_r, next_c, new_value, true});
                continue;
            }
            sm.active = false;
            updates.push_back({sm.current_row, sm.current_col,
                               sm.current_row, sm.current_col, sm.value, true});
            continue;
        }

        SlowMoverUpdate update;
        update.old_row = sm.current_row; update.old_col = sm.current_col;
        update.new_row = next_r;         update.new_col = next_c;
        update.value = sm.value;

        board_.at(sm.current_row, sm.current_col).value = 0;
        board_.at(sm.current_row, sm.current_col).passive = PassiveType::NONE;
        board_.at(next_r, next_c).value = sm.value;
        board_.at(next_r, next_c).passive = sm.passive;

        sm.current_row = next_r;
        sm.current_col = next_c;

        update.finished = (next_r == sm.dest_row && next_c == sm.dest_col);
        if (update.finished) sm.active = false;
        updates.push_back(update);
    }

    slow_movers_.erase(
        std::remove_if(slow_movers_.begin(), slow_movers_.end(),
                       [](const SlowMoverState& sm) { return !sm.active; }),
        slow_movers_.end());

    return updates;
}

std::vector<RandomMoverUpdate> GameEngine::advance_random_movers(std::set<std::pair<int,int>>& bomb_destroyed) {
    std::vector<RandomMoverUpdate> updates;

    random_movers_.clear();
    for (int r = 0; r < board_.rows(); r++)
        for (int c = 0; c < board_.cols(); c++)
            if (board_.at(r, c).is_snail())
                random_movers_.push_back({r, c});

    for (auto& rm : random_movers_) {
        if (frozen_tiles_.count({rm.row, rm.col})) continue;

        std::vector<std::pair<int,int>> valid_dirs;
        for (auto [dr, dc] : std::vector<std::pair<int,int>>{{-1,0},{1,0},{0,-1},{0,1}}) {
            int nr = rm.row + dr, nc = rm.col + dc;
            if (nr < 0 || nr >= board_.rows() || nc < 0 || nc >= board_.cols()) continue;
            if (board_.at(nr, nc).is_empty() || board_.at(nr, nc).is_bomb())
                valid_dirs.push_back({dr, dc});
        }
        if (valid_dirs.empty()) continue;

        std::uniform_int_distribution<int> dist(0, (int)valid_dirs.size() - 1);
        auto [dr, dc] = valid_dirs[dist(rng_)];
        int new_r = rm.row + dr, new_c = rm.col + dc;

        RandomMoverUpdate update {rm.row, rm.col, new_r, new_c};

        if (board_.at(new_r, new_c).is_bomb()) {
            board_.at(rm.row, rm.col).value = 0;
            board_.at(new_r, new_c).value = 0;
            bomb_destroyed.insert({new_r, new_c});
        } else {
            board_.at(new_r, new_c).value = -2;
            board_.at(rm.row, rm.col).value = 0;
            rm.row = new_r; rm.col = new_c;
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
    for (const auto& sm : slow_movers_)
        if (sm.active) frozen.insert({sm.current_row, sm.current_col});
    return frozen;
}

void GameEngine::detonate_adjacent_bombs(TurnResult& result,
                                          std::set<std::pair<int,int>>& effective_frozen,
                                          bool check_frozen_tiles) {
    const std::vector<std::pair<int,int>> dirs4 = {{-1,0},{1,0},{0,-1},{0,1}};

    struct Detonation {
        int br, bc, tr, tc;
        bool target_is_snail;
        bool needs_slow_mover_cleanup;
        PassiveType target_passive;  // NONE means regular user-frozen tile
    };
    std::vector<Detonation> detonations;

    for (int r = 0; r < board_.rows(); r++) {
        for (int c = 0; c < board_.cols(); c++) {
            if (!board_.at(r, c).is_bomb()) continue;
            for (auto [dr, dc] : dirs4) {
                int nr = r + dr, nc = c + dc;
                if (nr < 0 || nr >= board_.rows() || nc < 0 || nc >= board_.cols()) continue;

                bool is_snail = board_.at(nr, nc).is_snail();
                bool is_frozen_tile = check_frozen_tiles && !is_snail &&
                                      board_.at(nr, nc).is_numbered() &&
                                      frozen_tiles_.count({nr, nc}) > 0;

                // Check if any behavior owns this tile (always detonatable when frozen).
                bool is_behavior_tile = false;
                bool needs_cleanup = false;
                PassiveType target_passive = PassiveType::NONE;
                if (!is_snail && board_.at(nr, nc).is_numbered()) {
                    for (auto& b : behaviors_) {
                        if (b->matches(board_.at(nr, nc).passive)) {
                            is_behavior_tile = true;
                            needs_cleanup = b->requires_slow_mover_cleanup(board_.at(nr, nc).passive);
                            target_passive = board_.at(nr, nc).passive;
                            break;
                        }
                    }
                }

                if (is_snail || is_frozen_tile || is_behavior_tile) {
                    detonations.push_back({r, c, nr, nc, is_snail, needs_cleanup, target_passive});
                    break;
                }
            }
        }
    }

    for (auto& det : detonations) {
        if (!board_.at(det.br, det.bc).is_bomb()) continue;

        bool target_ok;
        if (det.target_is_snail) {
            target_ok = board_.at(det.tr, det.tc).is_snail();
        } else if (det.target_passive != PassiveType::NONE) {
            // Behavior tile: verify still present with the same passive.
            target_ok = board_.at(det.tr, det.tc).is_numbered() &&
                        board_.at(det.tr, det.tc).passive == det.target_passive;
        } else {
            // Regular user-frozen tile.
            target_ok = board_.at(det.tr, det.tc).is_numbered() &&
                        frozen_tiles_.count({det.tr, det.tc}) > 0;
        }
        if (!target_ok) continue;

        board_.at(det.br, det.bc).value = 0;
        board_.at(det.tr, det.tc).value = 0;
        board_.at(det.tr, det.tc).passive = PassiveType::NONE;
        result.bomb_destroyed.insert({det.br, det.bc});
        result.bomb_destroyed.insert({det.tr, det.tc});
        effective_frozen.erase({det.tr, det.tc});
        frozen_tiles_.erase({det.tr, det.tc});

        if (det.needs_slow_mover_cleanup) {
            slow_movers_.erase(
                std::remove_if(slow_movers_.begin(), slow_movers_.end(),
                    [&det](const SlowMoverState& sm) {
                        return sm.current_row == det.tr && sm.current_col == det.tc;
                    }),
                slow_movers_.end());
        }

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

        const Tile& ct = board_.at(check_r, check_c);
        if (!ct.is_numbered()) break;

        // Stop at any tile owned by a behavior (special tiles don't cascade-slide).
        bool blocks = false;
        for (auto& b : behaviors_) {
            if (b->matches(ct.passive) && b->blocks_cascade()) {
                blocks = true;
                break;
            }
        }
        if (blocks) break;
        if (skip.count({check_r, check_c})) break;
        if (frozen_tiles_.count({check_r, check_c})) break;

        Tile saved = ct;
        board_.at(check_r, check_c).value = 0;
        board_.at(check_r, check_c).passive = PassiveType::NONE;
        board_.at(fill_r, fill_c) = saved;

        out_moves.push_back({check_r, check_c, fill_r, fill_c, saved.value});

        fill_r = check_r;
        fill_c = check_c;
    }
}
