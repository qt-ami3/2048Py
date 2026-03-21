//2048Squared (title pending) copyright (c) 2026 River Knuuttila, common alias: Annie Valentine or aval. All Rights Reserved.
//Do not redistribute or reuse code without accrediting and explicit permission from author.
//Contact:
//+1 (808) 223 4780
//riverknuuttila2@outlook.com

#pragma once

#include "tile_behavior.h"
#include <set>
#include <utility>

// Handles the CONTRARIAN passive (pure and combined with A_LITTLE_SLOW).
// Tiles move in the opposite direction of player input.
// Combined with A_LITTLE_SLOW: moves 1 step per turn in the opposite direction.
class ContrarianBehavior : public TileBehavior {
    std::set<std::pair<int,int>> positions_;
    std::set<std::pair<int,int>> pre_blocked_;

public:
    // Matches any tile with CONTRARIAN bit set (including slow+contrarian combos).
    bool matches(PassiveType p) const override {
        return has_passive(p, PassiveType::CONTRARIAN);
    }

    bool freeze_during_move() const override { return true; }
    bool freeze_tile_behind() const override { return false; }

    // Combined tiles (slow+contrarian) may have slow mover state that needs cleanup.
    bool requires_slow_mover_cleanup(PassiveType p) const override {
        return has_passive(p, PassiveType::A_LITTLE_SLOW);
    }

    void pre_snapshot(const Board& board, int dr, int dc) override;
    bool advance(MoveContext& ctx, TurnResult& result) override;
};
