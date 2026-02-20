//2048Squared (title pending) copyright (c) 2026 River Knuuttila, common alias: Annie Valentine or aval. All Rights Reserved.
//Do not redistribute or reuse code without accrediting and explicit permission from author.
//Contact:
//+1 (808) 223 4780
//riverknuuttila2@outlook.com

#include "contrarian_behavior.h"
#include <algorithm>
#include <cstdlib>

void ContrarianBehavior::pre_snapshot(const Board& board, int dr, int dc) {
    positions_.clear();
    pre_blocked_.clear();

    for (int r = 0; r < board.rows(); r++)
        for (int c = 0; c < board.cols(); c++)
            if (board.at(r, c).is_numbered() && matches(board.at(r, c).passive))
                positions_.insert({r, c});

    // Pre-compute which contrarian tiles are immediately blocked in their movement
    // direction BEFORE regular movement runs. This prevents regular tiles that compact
    // against a contrarian tile during step 2 from falsely blocking it in advance().
    int opp_dr = -dr, opp_dc = -dc;
    for (const auto& [cr, cc] : positions_) {
        int imm_r = cr + opp_dr, imm_c = cc + opp_dc;
        if (imm_r < 0 || imm_r >= board.rows() ||
            imm_c < 0 || imm_c >= board.cols()) {
            pre_blocked_.insert({cr, cc});
        } else {
            const Tile& t = board.at(imm_r, imm_c);
            if (!t.is_empty() && !has_passive(t.passive, PassiveType::CONTRARIAN))
                pre_blocked_.insert({cr, cc});
        }
    }
}

bool ContrarianBehavior::advance(MoveContext& ctx, TurnResult& result) {
    bool changed = false;
    Board& board = ctx.board;
    const int dr = ctx.dr, dc = ctx.dc;
    const int opp_dr = -dr, opp_dc = -dc;

    // Process leading-edge tiles first (closest to the opposite wall).
    // Set iterates ascending. opp moving right (opp_dc>0) or down (opp_dr>0) → reverse.
    std::vector<std::pair<int,int>> order(positions_.begin(), positions_.end());
    if (opp_dc > 0 || opp_dr > 0)
        std::reverse(order.begin(), order.end());

    for (const auto& [cr, cc] : order) {
        if (!board.at(cr, cc).is_numbered()) continue;
        if (!matches(board.at(cr, cc).passive)) continue;

        // Skip active slow-contrarian movers — advance_slow_movers handles them.
        if (ctx.active_sm_positions.count({cr, cc})) continue;

        // Skip if pre-move blocked (immediate opposite-direction cell was occupied).
        if (pre_blocked_.count({cr, cc})) continue;

        int tile_value = board.at(cr, cc).value;
        PassiveType tile_passive = board.at(cr, cc).passive;
        bool is_slow_contrarian = has_passive(tile_passive, PassiveType::A_LITTLE_SLOW);

        // Scan in the opposite direction to find ultimate destination.
        int dest_r = cr, dest_c = cc;
        int scan_r = cr + opp_dr, scan_c = cc + opp_dc;
        bool dest_is_merge = false;

        while (scan_r >= 0 && scan_r < board.rows() &&
               scan_c >= 0 && scan_c < board.cols()) {
            const Tile& t = board.at(scan_r, scan_c);
            if (t.is_empty()) {
                dest_r = scan_r; dest_c = scan_c;
            } else if (t.is_numbered() && t.value == tile_value) {
                dest_r = scan_r; dest_c = scan_c;
                dest_is_merge = true;
                break;
            } else {
                break;
            }
            scan_r += opp_dr;
            scan_c += opp_dc;
        }

        if (dest_r == cr && dest_c == cc) continue;

        int total_dist = std::abs(dest_r - cr) + std::abs(dest_c - cc);
        int next_r = cr + opp_dr, next_c = cc + opp_dc;

        if (dest_is_merge && (!is_slow_contrarian || total_dist == 1)) {
            // Immediate merge: pure contrarian (moves full distance) or
            // slow contrarian adjacent to its merge target.
            int new_value = tile_value * 2;
            board.at(cr, cc).value = 0;
            board.at(cr, cc).passive = PassiveType::NONE;
            board.at(dest_r, dest_c).value = new_value;
            board.at(dest_r, dest_c).passive = tile_passive;
            result.slow_tile_moves.push_back({cr, cc, dest_r, dest_c, tile_value});
            result.slow_tile_merges.push_back({dest_r, dest_c, new_value});
        } else {
            // Move: pure contrarian slides fully, slow contrarian moves 1 step.
            bool needs_sm = is_slow_contrarian && total_dist > 1;
            int actual_dest_r = needs_sm ? next_r : dest_r;
            int actual_dest_c = needs_sm ? next_c : dest_c;

            Tile saved = board.at(cr, cc);
            board.at(cr, cc).value = 0;
            board.at(cr, cc).passive = PassiveType::NONE;
            board.at(actual_dest_r, actual_dest_c) = saved;
            result.slow_tile_moves.push_back({cr, cc, actual_dest_r, actual_dest_c, tile_value});

            if (needs_sm) {
                SlowMoverState sm;
                sm.current_row = actual_dest_r; sm.current_col = actual_dest_c;
                sm.dest_row = dest_r;           sm.dest_col = dest_c;
                sm.dr = opp_dr;                 sm.dc = opp_dc;
                sm.value = saved.value;
                sm.passive = saved.passive;
                sm.active = true;
                ctx.slow_movers.push_back(sm);
            }
        }
        changed = true;
    }

    return changed;
}
