//2048Squared (title pending) copyright (c) 2026 River Knuuttila, common alias: Annie Valentine or aval. All Rights Reserved.
//Do not redistribute or reuse code without accrediting and explicit permission from author.
//Contact:
//+1 (808) 223 4780
//riverknuuttila2@outlook.com

#include "slow_behavior.h"
#include <algorithm>
#include <cstdlib>

void SlowBehavior::pre_snapshot(const Board& board, int dr, int dc) {
    positions_.clear();
    for (int r = 0; r < board.rows(); r++)
        for (int c = 0; c < board.cols(); c++)
            if (board.at(r, c).is_numbered() && matches(board.at(r, c).passive))
                positions_.insert({r, c});
}

bool SlowBehavior::advance(MoveContext& ctx, TurnResult& result) {
    bool changed = false;
    Board& board = ctx.board;
    const int dr = ctx.dr, dc = ctx.dc;

    // Process tiles closest to the movement wall first.
    // Set iterates ascending; reverse for right (dc>0) or down (dr>0).
    std::vector<std::pair<int,int>> order(positions_.begin(), positions_.end());
    if (dc > 0 || dr > 0)
        std::reverse(order.begin(), order.end());

    for (const auto& [sr, sc] : order) {
        if (ctx.active_sm_positions.count({sr, sc})) continue;
        if (!board.at(sr, sc).is_numbered()) continue;
        if (!matches(board.at(sr, sc).passive)) continue;

        int tile_value = board.at(sr, sc).value;

        // Behind-merge: a regular tile may have compacted next to this frozen slow tile
        // during step 2. Merge it in before advancing.
        int behind_r = sr - dr, behind_c = sc - dc;
        if (behind_r >= 0 && behind_r < board.rows() &&
            behind_c >= 0 && behind_c < board.cols() &&
            board.at(behind_r, behind_c).is_numbered() &&
            board.at(behind_r, behind_c).value == tile_value) {

            int new_value = tile_value * 2;
            result.slow_tile_moves.push_back({behind_r, behind_c, sr, sc, tile_value});
            result.slow_tile_merges.push_back({sr, sc, new_value});
            board.at(behind_r, behind_c).value = 0;
            board.at(behind_r, behind_c).passive = PassiveType::NONE;
            board.at(sr, sc).value = new_value;
            tile_value = new_value;
            changed = true;
        }

        if (ctx.frozen_tiles.count({sr, sc})) continue;

        // Scan ahead (movement direction) to find ultimate destination.
        int dest_r = sr, dest_c = sc;
        int scan_r = sr + dr, scan_c = sc + dc;
        bool dest_is_merge = false;

        while (scan_r >= 0 && scan_r < board.rows() &&
               scan_c >= 0 && scan_c < board.cols()) {
            if (board.at(scan_r, scan_c).is_empty()) {
                dest_r = scan_r;
                dest_c = scan_c;
            } else if (board.at(scan_r, scan_c).value == tile_value &&
                       board.at(scan_r, scan_c).is_numbered() &&
                       !has_passive(board.at(scan_r, scan_c).passive, PassiveType::A_LITTLE_SLOW)) {
                // Merge with a non-slow tile ahead.
                // Slow-on-slow merges are handled exclusively by the behind-merge above,
                // processed in closest-to-wall-first order.
                dest_r = scan_r;
                dest_c = scan_c;
                dest_is_merge = true;
                break;
            } else {
                break;
            }
            scan_r += dr;
            scan_c += dc;
        }

        if (dest_r == sr && dest_c == sc) continue;

        int next_r = sr + dr, next_c = sc + dc;
        int total_dist = std::abs(dest_r - sr) + std::abs(dest_c - sc);

        if (next_r == dest_r && next_c == dest_c && dest_is_merge) {
            // Immediate forward merge.
            int new_value = tile_value * 2;
            PassiveType sr_passive = board.at(sr, sc).passive;
            board.at(sr, sc).value = 0;
            board.at(sr, sc).passive = PassiveType::NONE;
            board.at(dest_r, dest_c).value = new_value;
            board.at(dest_r, dest_c).passive = sr_passive;
            result.slow_tile_moves.push_back({sr, sc, dest_r, dest_c, tile_value});
            result.slow_tile_merges.push_back({dest_r, dest_c, new_value});
            changed = true;
            ctx.cascade_fill(sr, sc, result.slow_tile_moves);
        } else {
            // Move 1 cell; create a slow mover if destination is further away.
            Tile saved = board.at(sr, sc);
            board.at(sr, sc).value = 0;
            board.at(sr, sc).passive = PassiveType::NONE;
            board.at(next_r, next_c) = saved;
            result.slow_tile_moves.push_back({sr, sc, next_r, next_c, tile_value});
            changed = true;

            if (total_dist > 1) {
                SlowMoverState sm;
                sm.current_row = next_r; sm.current_col = next_c;
                sm.dest_row = dest_r;    sm.dest_col = dest_c;
                sm.dr = dr;              sm.dc = dc;
                sm.value = saved.value;
                sm.passive = saved.passive;
                sm.active = true;
                ctx.slow_movers.push_back(sm);
            }
            ctx.cascade_fill(sr, sc, result.slow_tile_moves);
        }
    }

    // Frozen slow mover merge check.
    // A regular tile may have slid next to a user-frozen slow mover during step 2;
    // merge it in now.
    for (auto& sm : ctx.slow_movers) {
        if (!sm.active) continue;
        if (!ctx.frozen_tiles.count({sm.current_row, sm.current_col})) continue;

        int adj_r = sm.current_row - dr;
        int adj_c = sm.current_col - dc;
        if (adj_r < 0 || adj_r >= board.rows() ||
            adj_c < 0 || adj_c >= board.cols()) continue;
        if (!board.at(adj_r, adj_c).is_numbered()) continue;
        if (board.at(adj_r, adj_c).value != sm.value) continue;

        int old_adj_value = board.at(adj_r, adj_c).value;
        int new_value = sm.value * 2;
        board.at(adj_r, adj_c).value = 0;
        board.at(adj_r, adj_c).passive = PassiveType::NONE;
        sm.value = new_value;
        board.at(sm.current_row, sm.current_col).value = new_value;

        // These go into main animation channels since they animate in phase 1.
        result.moves.push_back({adj_r, adj_c, sm.current_row, sm.current_col, old_adj_value});
        result.merges.push_back({sm.current_row, sm.current_col, new_value});
        changed = true;
    }

    return changed;
}
