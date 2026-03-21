//2048Squared (title pending) copyright (c) 2026 River Knuuttila, common alias: Annie Valentine or aval. All Rights Reserved.
//Do not redistribute or reuse code without accrediting and explicit permission from author.
//Contact:
//+1 (808) 223 4780
//riverknuuttila2@outlook.com

#pragma once

#include "board.h"
#include "slow_mover.h"
#include "passive.h"
#include "turn_result.h"
#include <set>
#include <vector>
#include <functional>

// Context passed to TileBehavior::advance() — bundles all mutable engine state
// that behaviors need to read or write during their advance phase.
struct MoveContext {
    Board& board;
    std::vector<SlowMoverState>& slow_movers;
    std::set<std::pair<int,int>>& frozen_tiles;
    std::set<std::pair<int,int>>& effective_frozen;
    const std::set<std::pair<int,int>>& active_sm_positions;
    int dr, dc;  // player movement direction

    // Slide regular tiles into a cell vacated by a special tile.
    std::function<void(int, int, std::vector<MoveInfo>&)> cascade_fill;
};

// Abstract interface for a tile passive behavior.
// To add a new passive: implement this, register in GameEngine's constructor.
// That's the only place that needs to change.
class TileBehavior {
public:
    virtual ~TileBehavior() = default;

    // Returns true if a tile with this passive is owned by this behavior.
    // Used for freeze-building, cascade blocking, and bomb detection.
    virtual bool matches(PassiveType p) const = 0;

    // Should tiles of this type be frozen during regular movement?
    virtual bool freeze_during_move() const = 0;

    // Should the same-value tile immediately behind (opposite move dir) also be frozen?
    virtual bool freeze_tile_behind() const { return false; }

    // Called before any board mutations. Implementations snapshot pre-move state here.
    virtual void pre_snapshot(const Board& board, int dr, int dc) {}

    // Execute the advance phase for all tiles of this type.
    // Writes into result.slow_tile_moves / slow_tile_merges.
    // Returns true if any board change occurred.
    virtual bool advance(MoveContext& ctx, TurnResult& result) = 0;

    // Should cascade_fill_behind() stop at tiles owned by this behavior?
    virtual bool blocks_cascade() const { return true; }

    // When this behavior's tile is destroyed by a bomb, should slow_movers be cleaned up?
    // p is the full passive bitmask of the destroyed tile (may be combined).
    virtual bool requires_slow_mover_cleanup(PassiveType p) const { return false; }
};
