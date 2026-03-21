//2048Squared (title pending) copyright (c) 2026 River Knuuttila, common alias: Annie Valentine or aval. All Rights Reserved.
//Do not redistribute or reuse code without accrediting and explicit permission from author.
//Contact:
//+1 (808) 223 4780
//riverknuuttila2@outlook.com

#pragma once

#include "tile_behavior.h"
#include <set>
#include <utility>

// Handles the A_LITTLE_SLOW passive (pure only — not combined with CONTRARIAN).
// Tiles move 1 step per turn in the player's direction, with behind-merge support.
class SlowBehavior : public TileBehavior {
    std::set<std::pair<int,int>> positions_;

public:
    // Pure A_LITTLE_SLOW only — combined with CONTRARIAN is owned by ContrarianBehavior.
    bool matches(PassiveType p) const override {
        return has_passive(p, PassiveType::A_LITTLE_SLOW)
            && !has_passive(p, PassiveType::CONTRARIAN);
    }

    bool freeze_during_move() const override { return true; }
    bool freeze_tile_behind() const override { return true; }
    bool requires_slow_mover_cleanup(PassiveType p) const override { return true; }

    void pre_snapshot(const Board& board, int dr, int dc) override;
    bool advance(MoveContext& ctx, TurnResult& result) override;
};
