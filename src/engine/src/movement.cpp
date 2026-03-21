//2048Squared (title pending) copyright (c) 2026 River Knuuttila, common alias: Annie Valentine or aval. All Rights Reserved.
//Do not redistribute or reuse code without accrediting and explicit permission from author.
//Contact:
//+1 (808) 223 4780
//riverknuuttila2@outlook.com

#include "movement.h"
#include <algorithm>

namespace {

// Split a range [0, size) into segments separated by frozen positions.
// Each segment is [start, end) — a half-open interval.
std::vector<std::pair<int,int>> get_segments(int size, const std::set<int>& frozen_positions) {
    std::vector<std::pair<int,int>> segments;
    int seg_start = -1;
    for (int idx = 0; idx < size; idx++) {
        if (frozen_positions.count(idx)) {
            if (seg_start >= 0) {
                segments.push_back({seg_start, idx});
                seg_start = -1;
            }
        } else {
            if (seg_start < 0) {
                seg_start = idx;
            }
        }
    }
    if (seg_start >= 0) {
        segments.push_back({seg_start, size});
    }
    return segments;
}

struct TileEntry {
    int value;
    int orig;  // original position index
    PassiveType passive;
};

// ─── Horizontal segment processors ───

// Compact tiles left within a segment. Returns new values left-to-right.
std::vector<TileEntry> process_segment_left(
    const std::vector<TileEntry>& tiles, int row_idx, int seg_start,
    std::vector<MoveInfo>& moves, std::vector<MergeInfo>& merges,
    std::set<std::pair<int,int>>& bomb_destroyed,
    Board& board)
{
    std::vector<TileEntry> new_vals;
    int j = 0;
    int target = seg_start;

    while (j < (int)tiles.size()) {
        int value = tiles[j].value;
        int orig = tiles[j].orig;
        PassiveType passive = tiles[j].passive;

        if (value == -1) {
            // Bomb tile
            if (j < (int)tiles.size() - 1) {
                // Bomb destroys next tile
                if (orig != target)
                    moves.push_back({row_idx, orig, row_idx, target, value});
                if (tiles[j+1].orig != target)
                    moves.push_back({row_idx, tiles[j+1].orig, row_idx, target, tiles[j+1].value});
                bomb_destroyed.insert({row_idx, target});
                j += 2;
            } else {
                // Bomb is last tile, just moves
                new_vals.push_back({value, target, PassiveType::NONE});
                if (orig != target)
                    moves.push_back({row_idx, orig, row_idx, target, value});
                j++;
                target++;
            }
        } else if (j < (int)tiles.size() - 1 && tiles[j+1].value == -1) {
            // Next tile is bomb, destroys this tile
            if (orig != target)
                moves.push_back({row_idx, orig, row_idx, target, value});
            if (tiles[j+1].orig != target)
                moves.push_back({row_idx, tiles[j+1].orig, row_idx, target, tiles[j+1].value});
            bomb_destroyed.insert({row_idx, target});
            j += 2;
        } else if (j < (int)tiles.size() - 1 && value == tiles[j+1].value && value > 0) {
            // Merge with next tile
            int new_value = value * 2;
            // Passive inheritance: keep passive from either tile
            PassiveType merged_passive = PassiveType::NONE;
            if (passive != PassiveType::NONE)
                merged_passive = passive;
            else if (tiles[j+1].passive != PassiveType::NONE)
                merged_passive = tiles[j+1].passive;
            new_vals.push_back({new_value, target, merged_passive});
            if (orig != target)
                moves.push_back({row_idx, orig, row_idx, target, value});
            if (tiles[j+1].orig != target)
                moves.push_back({row_idx, tiles[j+1].orig, row_idx, target, tiles[j+1].value});
            merges.push_back({row_idx, target, new_value});
            j += 2;
            target++;
        } else {
            // Just move
            new_vals.push_back({value, target, passive});
            if (orig != target)
                moves.push_back({row_idx, orig, row_idx, target, value});
            j++;
            target++;
        }
    }
    return new_vals;
}

std::vector<TileEntry> process_segment_right(
    const std::vector<TileEntry>& tiles, int row_idx, int seg_end,
    std::vector<MoveInfo>& moves, std::vector<MergeInfo>& merges,
    std::set<std::pair<int,int>>& bomb_destroyed,
    Board& board)
{
    std::vector<TileEntry> new_vals;
    int j = (int)tiles.size() - 1;
    int target = seg_end - 1;

    while (j >= 0) {
        int value = tiles[j].value;
        int orig = tiles[j].orig;
        PassiveType passive = tiles[j].passive;

        if (value == -1) {
            if (j > 0) {
                if (orig != target)
                    moves.push_back({row_idx, orig, row_idx, target, value});
                if (tiles[j-1].orig != target)
                    moves.push_back({row_idx, tiles[j-1].orig, row_idx, target, tiles[j-1].value});
                bomb_destroyed.insert({row_idx, target});
                j -= 2;
            } else {
                new_vals.insert(new_vals.begin(), {value, target, PassiveType::NONE});
                if (orig != target)
                    moves.push_back({row_idx, orig, row_idx, target, value});
                j--;
                target--;
            }
        } else if (j > 0 && tiles[j-1].value == -1) {
            if (orig != target)
                moves.push_back({row_idx, orig, row_idx, target, value});
            if (tiles[j-1].orig != target)
                moves.push_back({row_idx, tiles[j-1].orig, row_idx, target, tiles[j-1].value});
            bomb_destroyed.insert({row_idx, target});
            j -= 2;
        } else if (j > 0 && value == tiles[j-1].value && value > 0) {
            int new_value = value * 2;
            PassiveType merged_passive = PassiveType::NONE;
            if (passive != PassiveType::NONE)
                merged_passive = passive;
            else if (tiles[j-1].passive != PassiveType::NONE)
                merged_passive = tiles[j-1].passive;
            new_vals.insert(new_vals.begin(), {new_value, target, merged_passive});
            if (orig != target)
                moves.push_back({row_idx, orig, row_idx, target, value});
            if (tiles[j-1].orig != target)
                moves.push_back({row_idx, tiles[j-1].orig, row_idx, target, tiles[j-1].value});
            merges.push_back({row_idx, target, new_value});
            j -= 2;
            target--;
        } else {
            new_vals.insert(new_vals.begin(), {value, target, passive});
            if (orig != target)
                moves.push_back({row_idx, orig, row_idx, target, value});
            j--;
            target--;
        }
    }
    return new_vals;
}

// ─── Vertical segment processors ───

std::vector<TileEntry> process_segment_up(
    const std::vector<TileEntry>& tiles, int col_idx, int seg_start,
    std::vector<MoveInfo>& moves, std::vector<MergeInfo>& merges,
    std::set<std::pair<int,int>>& bomb_destroyed,
    Board& board)
{
    std::vector<TileEntry> new_vals;
    int i = 0;
    int target = seg_start;

    while (i < (int)tiles.size()) {
        int value = tiles[i].value;
        int orig = tiles[i].orig;
        PassiveType passive = tiles[i].passive;

        if (value == -1) {
            if (i < (int)tiles.size() - 1) {
                if (orig != target)
                    moves.push_back({orig, col_idx, target, col_idx, value});
                if (tiles[i+1].orig != target)
                    moves.push_back({tiles[i+1].orig, col_idx, target, col_idx, tiles[i+1].value});
                bomb_destroyed.insert({target, col_idx});
                i += 2;
            } else {
                new_vals.push_back({value, target, PassiveType::NONE});
                if (orig != target)
                    moves.push_back({orig, col_idx, target, col_idx, value});
                i++;
                target++;
            }
        } else if (i < (int)tiles.size() - 1 && tiles[i+1].value == -1) {
            if (orig != target)
                moves.push_back({orig, col_idx, target, col_idx, value});
            if (tiles[i+1].orig != target)
                moves.push_back({tiles[i+1].orig, col_idx, target, col_idx, tiles[i+1].value});
            bomb_destroyed.insert({target, col_idx});
            i += 2;
        } else if (i < (int)tiles.size() - 1 && value == tiles[i+1].value && value > 0) {
            int new_value = value * 2;
            PassiveType merged_passive = PassiveType::NONE;
            if (passive != PassiveType::NONE)
                merged_passive = passive;
            else if (tiles[i+1].passive != PassiveType::NONE)
                merged_passive = tiles[i+1].passive;
            new_vals.push_back({new_value, target, merged_passive});
            if (orig != target)
                moves.push_back({orig, col_idx, target, col_idx, value});
            if (tiles[i+1].orig != target)
                moves.push_back({tiles[i+1].orig, col_idx, target, col_idx, tiles[i+1].value});
            merges.push_back({target, col_idx, new_value});
            i += 2;
            target++;
        } else {
            new_vals.push_back({value, target, passive});
            if (orig != target)
                moves.push_back({orig, col_idx, target, col_idx, value});
            i++;
            target++;
        }
    }
    return new_vals;
}

std::vector<TileEntry> process_segment_down(
    const std::vector<TileEntry>& tiles, int col_idx, int seg_end,
    std::vector<MoveInfo>& moves, std::vector<MergeInfo>& merges,
    std::set<std::pair<int,int>>& bomb_destroyed,
    Board& board)
{
    std::vector<TileEntry> new_vals;
    int i = (int)tiles.size() - 1;
    int target = seg_end - 1;

    while (i >= 0) {
        int value = tiles[i].value;
        int orig = tiles[i].orig;
        PassiveType passive = tiles[i].passive;

        if (value == -1) {
            if (i > 0) {
                if (orig != target)
                    moves.push_back({orig, col_idx, target, col_idx, value});
                if (tiles[i-1].orig != target)
                    moves.push_back({tiles[i-1].orig, col_idx, target, col_idx, tiles[i-1].value});
                bomb_destroyed.insert({target, col_idx});
                i -= 2;
            } else {
                new_vals.insert(new_vals.begin(), {value, target, PassiveType::NONE});
                if (orig != target)
                    moves.push_back({orig, col_idx, target, col_idx, value});
                i--;
                target--;
            }
        } else if (i > 0 && tiles[i-1].value == -1) {
            if (orig != target)
                moves.push_back({orig, col_idx, target, col_idx, value});
            if (tiles[i-1].orig != target)
                moves.push_back({tiles[i-1].orig, col_idx, target, col_idx, tiles[i-1].value});
            bomb_destroyed.insert({target, col_idx});
            i -= 2;
        } else if (i > 0 && value == tiles[i-1].value && value > 0) {
            int new_value = value * 2;
            PassiveType merged_passive = PassiveType::NONE;
            if (passive != PassiveType::NONE)
                merged_passive = passive;
            else if (tiles[i-1].passive != PassiveType::NONE)
                merged_passive = tiles[i-1].passive;
            new_vals.insert(new_vals.begin(), {new_value, target, merged_passive});
            if (orig != target)
                moves.push_back({orig, col_idx, target, col_idx, value});
            if (tiles[i-1].orig != target)
                moves.push_back({tiles[i-1].orig, col_idx, target, col_idx, tiles[i-1].value});
            merges.push_back({target, col_idx, new_value});
            i -= 2;
            target--;
        } else {
            new_vals.insert(new_vals.begin(), {value, target, passive});
            if (orig != target)
                moves.push_back({orig, col_idx, target, col_idx, value});
            i--;
            target--;
        }
    }
    return new_vals;
}

// Build the combined frozen set from explicit frozen tiles + slow mover positions
std::set<std::pair<int,int>> build_frozen_set(
    const std::set<std::pair<int,int>>& frozen,
    const std::vector<SlowMoverState>& slow_movers)
{
    auto combined = frozen;
    for (const auto& sm : slow_movers) {
        if (sm.active) {
            combined.insert({sm.current_row, sm.current_col});
        }
    }
    return combined;
}

} // anonymous namespace


namespace movement {

MoveResult move_left(Board& board,
                     const std::set<std::pair<int,int>>& frozen,
                     const std::vector<SlowMoverState>& slow_movers)
{
    auto effective_frozen = build_frozen_set(frozen, slow_movers);
    MoveResult result;
    int rows = board.rows();
    int cols = board.cols();

    // Save original grid for change detection
    auto original = board.to_flat_values();

    for (int i = 0; i < rows; i++) {
        std::set<int> frozen_cols;
        for (const auto& [fr, fc] : effective_frozen) {
            if (fr == i) frozen_cols.insert(fc);
        }
        auto segments = get_segments(cols, frozen_cols);

        for (auto [seg_start, seg_end] : segments) {
            std::vector<TileEntry> seg_tiles;
            for (int j = seg_start; j < seg_end; j++) {
                if (!board.at(i, j).is_empty()) {
                    seg_tiles.push_back({board.at(i, j).value, j, board.at(i, j).passive});
                }
            }
            auto new_vals = process_segment_left(seg_tiles, i, seg_start,
                                                  result.moves, result.merges,
                                                  result.bomb_destroyed, board);
            for (int idx = 0; idx < seg_end - seg_start; idx++) {
                int col = seg_start + idx;
                if (idx < (int)new_vals.size()) {
                    board.at(i, col).value = new_vals[idx].value;
                    board.at(i, col).passive = new_vals[idx].passive;
                } else {
                    board.at(i, col).value = 0;
                    board.at(i, col).passive = PassiveType::NONE;
                }
            }
        }
    }

    result.board_changed = (original != board.to_flat_values());
    return result;
}

MoveResult move_right(Board& board,
                      const std::set<std::pair<int,int>>& frozen,
                      const std::vector<SlowMoverState>& slow_movers)
{
    auto effective_frozen = build_frozen_set(frozen, slow_movers);
    MoveResult result;
    int rows = board.rows();
    int cols = board.cols();

    auto original = board.to_flat_values();

    for (int i = 0; i < rows; i++) {
        std::set<int> frozen_cols;
        for (const auto& [fr, fc] : effective_frozen) {
            if (fr == i) frozen_cols.insert(fc);
        }
        auto segments = get_segments(cols, frozen_cols);

        for (auto [seg_start, seg_end] : segments) {
            std::vector<TileEntry> seg_tiles;
            for (int j = seg_start; j < seg_end; j++) {
                if (!board.at(i, j).is_empty()) {
                    seg_tiles.push_back({board.at(i, j).value, j, board.at(i, j).passive});
                }
            }
            auto new_vals = process_segment_right(seg_tiles, i, seg_end,
                                                   result.moves, result.merges,
                                                   result.bomb_destroyed, board);
            int seg_len = seg_end - seg_start;
            for (int idx = 0; idx < seg_len; idx++) {
                int col = seg_start + idx;
                int right_idx = idx - (seg_len - (int)new_vals.size());
                if (right_idx >= 0) {
                    board.at(i, col).value = new_vals[right_idx].value;
                    board.at(i, col).passive = new_vals[right_idx].passive;
                } else {
                    board.at(i, col).value = 0;
                    board.at(i, col).passive = PassiveType::NONE;
                }
            }
        }
    }

    result.board_changed = (original != board.to_flat_values());
    return result;
}

MoveResult move_up(Board& board,
                   const std::set<std::pair<int,int>>& frozen,
                   const std::vector<SlowMoverState>& slow_movers)
{
    auto effective_frozen = build_frozen_set(frozen, slow_movers);
    MoveResult result;
    int rows = board.rows();
    int cols = board.cols();

    auto original = board.to_flat_values();

    for (int col = 0; col < cols; col++) {
        std::set<int> frozen_rows;
        for (const auto& [fr, fc] : effective_frozen) {
            if (fc == col) frozen_rows.insert(fr);
        }
        auto segments = get_segments(rows, frozen_rows);

        for (auto [seg_start, seg_end] : segments) {
            std::vector<TileEntry> seg_tiles;
            for (int row = seg_start; row < seg_end; row++) {
                if (!board.at(row, col).is_empty()) {
                    seg_tiles.push_back({board.at(row, col).value, row, board.at(row, col).passive});
                }
            }
            auto new_vals = process_segment_up(seg_tiles, col, seg_start,
                                                result.moves, result.merges,
                                                result.bomb_destroyed, board);
            for (int idx = 0; idx < seg_end - seg_start; idx++) {
                int row = seg_start + idx;
                if (idx < (int)new_vals.size()) {
                    board.at(row, col).value = new_vals[idx].value;
                    board.at(row, col).passive = new_vals[idx].passive;
                } else {
                    board.at(row, col).value = 0;
                    board.at(row, col).passive = PassiveType::NONE;
                }
            }
        }
    }

    result.board_changed = (original != board.to_flat_values());
    return result;
}

MoveResult move_down(Board& board,
                     const std::set<std::pair<int,int>>& frozen,
                     const std::vector<SlowMoverState>& slow_movers)
{
    auto effective_frozen = build_frozen_set(frozen, slow_movers);
    MoveResult result;
    int rows = board.rows();
    int cols = board.cols();

    auto original = board.to_flat_values();

    for (int col = 0; col < cols; col++) {
        std::set<int> frozen_rows;
        for (const auto& [fr, fc] : effective_frozen) {
            if (fc == col) frozen_rows.insert(fr);
        }
        auto segments = get_segments(rows, frozen_rows);

        for (auto [seg_start, seg_end] : segments) {
            std::vector<TileEntry> seg_tiles;
            for (int row = seg_start; row < seg_end; row++) {
                if (!board.at(row, col).is_empty()) {
                    seg_tiles.push_back({board.at(row, col).value, row, board.at(row, col).passive});
                }
            }
            auto new_vals = process_segment_down(seg_tiles, col, seg_end,
                                                  result.moves, result.merges,
                                                  result.bomb_destroyed, board);
            int seg_len = seg_end - seg_start;
            for (int idx = 0; idx < seg_len; idx++) {
                int row = seg_start + idx;
                int down_idx = idx - (seg_len - (int)new_vals.size());
                if (down_idx >= 0) {
                    board.at(row, col).value = new_vals[down_idx].value;
                    board.at(row, col).passive = new_vals[down_idx].passive;
                } else {
                    board.at(row, col).value = 0;
                    board.at(row, col).passive = PassiveType::NONE;
                }
            }
        }
    }

    result.board_changed = (original != board.to_flat_values());
    return result;
}

} // namespace movement
